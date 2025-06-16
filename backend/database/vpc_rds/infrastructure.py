from typing import Optional, Union
from constructs import Construct
from os import path

from aws_cdk import (
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    CfnOutput,
    aws_ec2,
    aws_rds,
    aws_secretsmanager,
    aws_kms,
    aws_logs,
)

import constants
import common.cdk.constants_cdk as constants_cdk
from cdk_utils.CloudFormation_util import (
    add_tags,
    get_vpc_privatesubnet_type,
    get_RDS_password_exclude_pattern_adminuser,
    get_RDS_password_exclude_pattern_alphanum_only,
)
import cdk_utils.CdkDotJson_util as CdkDotJson_util

from common.cdk.retention_base import DATA_CLASSIFICATION_TYPES, DataClassification

class SqlDatabaseConstruct(Construct):
    """
        V2-Aurora Postgres DB-instance.
        Key security and best practices implemented:
        > Multi-User (unlike the single-user V1-Aurora)
        > Separate application-user, from admin/dba user
        > Uses Aurora Serverless v2 with minimum capacity of 0.5 ACUs (lowest possible) [2]
        > Placed in private isolated subnets
        > Secure password generation with appropriate exclusion of problematic characters
        > Automatic secret rotation every 30 days
        > Deletion protection for production environment
        > Different removal policies for production vs non-production
        > Backup retention enabled
        > Uses AWS Secrets Manager for credential management
        > Security group restrictions for database access
        > Multi-AZ deployment by default for high availability
    """

    @property
    def rds_security_group(self) -> aws_ec2.ISecurityGroup:
        return self._rds_security_group

    ### ------------------------------------------------------------------------
    @staticmethod
    def get_engine_ver_as_str(
        cdk_scope :Construct,
        tier :str,
    ) -> str:
        """
            returns the Postgres-Engine-version# as specified in `cdk.json`
        """
        engine_ver_as_string :str = cdk_scope.node.try_get_context("PostgreSQL-Engine-Version")
        print(f"engine_ver_as_string (json) = {engine_ver_as_string}")
        engine_ver_as_string = engine_ver_as_string[ tier if tier in constants.STD_TIERS else "developer" ]
        print(f"engine_ver_as_string (plain-string)= '{engine_ver_as_string}'")
        assert engine_ver_as_string is not None, f"cdk.json is missing 'PostgreSQL-Engine-Version'"
        return engine_ver_as_string

    @staticmethod
    def get_rds_cluster_identifier(
        stateful_stack_name :Stack,
        engine_ver_as_string :str,
    ) -> str:
        """
            Standardizes the  RDS-Aurora-V2 cluster's identifier.

            !!!WARNING!!!

            The 1st parameter must ONLY be the StateFUL-stack's name!

            --NOT-- any stack!
        """
        return f"{stateful_stack_name}-AuroraV2-PG-{engine_ver_as_string}"

    ### ------------------------------------------------------------------------
    def __init__(self, scope: Construct, id_: str,
            tier :str,
            aws_env :str,
            git_branch :str,
            vpc :aws_ec2.IVpc,
            **kwargs
    ) -> None:
        super().__init__(scope, id_, **kwargs)

        stk = Stack.of(self)

        ### --------- RDS & Postgres settings ---------
        default_database_name = "essex_emfact"
        serverless_aurorav2_max_capacity = 128  # MAX 256

        engine_ver_as_string = self.get_engine_ver_as_str( scope, tier )

        ### Convert the string-format version of Postgres into an Enum of type aws_rds.AuroraPostgresEngineVersion.VER_??_??
        engine_version_id :str = constants_cdk.ENGINE_VERSION_LOOKUP[ engine_ver_as_string ]
        print( f"engine_version_id = '{engine_version_id}'" )

        cluster_identifier = SqlDatabaseConstruct.get_rds_cluster_identifier( stk.stack_name, engine_ver_as_string )

        if tier in constants.STD_TIERS:
            db_backup_retention = scope.node.try_get_context("retention")["db_backup_retention"][ tier ]
        else:  ### developer specific git_branch
            db_backup_retention = scope.node.try_get_context("retention")["db_backup_retention"][ "dev" ]
        print( f"db_backup_retention = '{db_backup_retention}'" )
        db_backup_retention = Duration.days(int(db_backup_retention))

        removal_policy = RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE if tier in constants.UPPER_TIERS else RemovalPolicy.DESTROY
        # rds_paramgroup_name = f"default.aurora-postgresql{engine_ver_as_string}"
        # print(f"rds_paramgroup_name = '{rds_paramgroup_name}'")

        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
        [ acct_wide_vpc_details, vpc_details_for_tier ] = CdkDotJson_util.get_cdk_json_vpc_details( scope, aws_env, tier )
        SG_IDs_for_vpc_endpts :Optional[list[str]] = vpc_details_for_tier["VPCEndPts-SG"]
        print( f"SGs for vpc_endpts = '{SG_IDs_for_vpc_endpts}'")

        ### ------------------------------------------

        vpc_subnets = aws_ec2.SubnetSelection( one_per_az=True, subnet_type=get_vpc_privatesubnet_type(vpc) )

        ### Whether or not a NEW-VPC was created (or existing one looked up), create a SG for use by RDS
        self._rds_security_group = aws_ec2.SecurityGroup(
            self,
            id="RDS-SG",
            security_group_name = cluster_identifier,
            vpc=vpc,
        )
        self._rds_security_group.apply_removal_policy( removal_policy )
        # RDS Subnet Group
        self.rds_subnet_group = aws_rds.SubnetGroup(
            self,
            id="rds-subnet-group",
            description=f"{stk.stack_name} RDS subnet group",
            vpc=vpc,
            removal_policy=removal_policy,
            subnet_group_name = cluster_identifier,
            vpc_subnets=vpc_subnets,
        )
        self.rds_subnet_group.apply_removal_policy( removal_policy )

        sg_list_for_all_lambdas :list[aws_ec2.ISecurityGroup] = [self.rds_security_group]
        if SG_IDs_for_vpc_endpts:
            for sgid in SG_IDs_for_vpc_endpts:
                sg_con = aws_ec2.SecurityGroup.from_lookup_by_id( scope=self, id="lkpSg-"+sgid, security_group_id=sgid )
                if sg_con:
                    sg_list_for_all_lambdas.append( sg_con )
                    sg_con.add_ingress_rule(
                        peer = self.rds_security_group,
                        connection = aws_ec2.Port.HTTPS,
                        description = f"Allow inbound from RDS-SGs {sgid}",
                        remote_rule = True, ### <---------------------
                    )
                    self.rds_security_group.add_egress_rule(
                        peer = sg_con,
                        connection = aws_ec2.Port.HTTPS,
                        description = f"Allow outbound from RDS-SGs {sgid} to VPCEndPt-SG",
                    )

        ### ------------------------------------------

        # ### Before creating Lambdas to do secret-rotation, create VPC endpoints for SecretsManager
        # ### Note: This is taken care of, within the `backend/vpc_w_subnets.py`
        # secrets_manager_endpoint = aws_ec2.InterfaceVpcEndpoint(self, "SecretsManagerVPCEndpoint",
        #     vpc=vpc,
        #     service=aws_ec2.InterfaceVpcEndpointService(f"com.amazonaws.{Stack.of(self).region}.secretsmanager"),
        #     subnets=aws_ec2.SubnetSelection(
        #         subnet_type=get_vpc_privatesubnet_type(vpc),
        #         one_per_az=True
        #     ),
        #     private_dns_enabled=True
        # )

        ### V1-Aurora Legacy-CDK-construct usage: Master-creds for database-admin/dba user
        ### NOTE: the NON-dba appl-user is created at BOTTOM of this Construct.
        # self.rds_master_secret = aws_secretsmanager.Secret(
        #     self,
        #     id="rds-master-secret",
        #     secret_name=f"{stk.stack_name}/rds-master",
        #     generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        #         secret_string_template='{"username": "admin_user"}',
        #         generate_string_key="password",
        #         exclude_characters=get_RDS_password_exclude_pattern_adminuser(),
        #         password_length=32,
        #     ),
        # )

        rds_encryption_key_arn = CdkDotJson_util.lkp_cdk_json_for_kms_key( scope, tier, None, CdkDotJson_util.AwsServiceNamesForKmsKeys.rds )
        print( f"rds_encryption_key_arn = '{rds_encryption_key_arn}'" )
        rds_encryption_key = aws_kms.Key.from_key_arn(scope=scope, id="KmsKeyLkp-rds", key_arn=rds_encryption_key_arn)

        secret_encryption_key_arn = CdkDotJson_util.lkp_cdk_json_for_kms_key( scope, tier, None, CdkDotJson_util.AwsServiceNamesForKmsKeys.secretsmanager )
        print( f"secret_encryption_key_arn = '{secret_encryption_key_arn}'" )
        secret_encryption_key = aws_kms.Key.from_key_arn(scope=scope, id="KmsKeyLkp-secrets", key_arn=secret_encryption_key_arn)

        ### Use Credentials.fromGeneratedSecret with custom username
        admin_credentials = aws_rds.Credentials.from_generated_secret(
            username = "aurorav2_pgsql",  ### MasterUsername: MUST match pattern ^[a-zA-Z]{1}[a-zA-Z0-9_]*$]
            secret_name = f"{stk.stack_name}-AuroraV2-PGv16-AdminUser",
            exclude_characters = get_RDS_password_exclude_pattern_adminuser(),
            encryption_key = secret_encryption_key,
        )

        ### RuntimeError: Error: Cannot apply RemovalPolicy: no child or not a CfnResource. Apply the removal policy on the CfnResource directly.
        # admin_credentials.encryption_key.apply_removal_policy( removal_policy )

        ### ------------------------------------------

        ### Aurora Serverless v2 Cluster for PostgreSQL-v16
        self.db = aws_rds.DatabaseCluster( self,
            ### ??? NOT-Serverless
            ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/DatabaseCluster.html
            id="AuroraV2-PGSQL",
            default_database_name = default_database_name,
            cluster_identifier = cluster_identifier,
            engine = aws_rds.DatabaseClusterEngine.aurora_postgres(version=engine_version_id),
            enable_data_api = True, ### Default = False
            auto_minor_version_upgrade = True, ### NIST 800-53 finding: RDS automatic minor version upgrades should be enabled
            credentials = admin_credentials,
            ### Do NOT specify the following, to avoid ERROR: The instance class that you specified doesn't support the HTTP endpoint for using RDS Data API.
            #__ readers = [IClusterInstance] ### A list of instances to create as cluster-reader-instances. Default: - no readers are created. The cluster will have a single writer/reader
            writer=aws_rds.ClusterInstance.serverless_v2( id="AuroraWriter",
                instance_identifier = f"{cluster_identifier}-writer",
                #__ scale_with_writer =  .. .. applies to READERs only
                auto_minor_version_upgrade = True, ### NIST 800-53 finding: RDS automatic minor version upgrades should be enabled
                allow_major_version_upgrade = False,
                publicly_accessible = False,
            ),
            # parameter_group=aws_rds.ParameterGroup.from_parameter_group_name(
            #     self,
            #     "ParameterGroup",
            #     f"default.aurora-postgresql{engine_ver_as_string}"
            # ),
            serverless_v2_min_capacity = 1.0,  # DEFAULT is 0.5 (lowest possible)
            serverless_v2_max_capacity = serverless_aurorav2_max_capacity,
            # instances = [0-9]+, ### !!!!! LEGACY DEPRECATED parameter !!!  DEFAULT = 2 (Writer + 1-Reader)
            ### In V1-Aurora, we have to EXPLICITY provide the secret.  Not so for V2!
            ### In V2-Aurora, Default-CDK-construct's behavior is to create a NEW username of 'admin' (or 'postgres' for PostgreSQL) and SecretsManager-generated password
            # network_type=aws_rds.NetworkType.IPV4,
            # enable_local_write_forwarding = True, ## Whether read-replicas can forward write-operations to the writer-nstance. Only be enabled for MySQL 3.04+ or PostgreSQL 16.4+
            storage_encrypted = True,
            storage_encryption_key = rds_encryption_key,
            backup = aws_rds.BackupProps( retention=db_backup_retention ),
            copy_tags_to_snapshot = True,
            deletion_protection = True if tier == constants.PROD_TIER else False,
            removal_policy = removal_policy,
            vpc=vpc, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            vpc_subnets = vpc_subnets, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            subnet_group=self.rds_subnet_group, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            security_groups=sg_list_for_all_lambdas, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            # storage_type = aws_rds.DBClusterStorageType.AURORA_IOPT1, ### required for LIMITLESS mode
            # storage_type = aws_rds.DBClusterStorageType.AURORA, ### Default: - DBClusterStorageType.AURORA_IOPT1
            # instance_props=aws_rds.InstanceProps( !!!!!!!!!!!!!!!!!!! LEGACY DEPRECATED parameter !!!!!!!!!!!!!!!!!!!!
            #     # parameter_group = aws_rds.ParameterGroup.from_parameter_group_name( self, "ParamGrp", rds_paramgroup_name),
            #     vpc=vpc, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     vpc_subnets = vpc_subnets, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     security_groups=sg_list_for_all_lambdas, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     allow_major_version_upgrade = False,
            #     publicly_accessible = False,
            #     delete_automated_backups = False,
            #     instance_type=aws_ec2.InstanceType.of( !!!!!!! LEGACY DEPRECATED parameter !!!!!!!!
            #         aws_ec2.InstanceClass.R6GD,
            #         aws_ec2.InstanceSize.XLARGE4,
            #     ),
            # ),

            #### [Error AuroraV2PG/AuroraV2-PGSQL/Resource] HIPAA.Security-RDSLoggingEnabled[LogExport::postgresql]: The non-Aurora RDS DB instance or Aurora cluster does not have all CloudWatch log types exported - (Control IDs: 164.308(a)(3)(ii)(A), 164.308(a)(5)(ii)(C)). To help with logging and monitoring within your environment, ensure Amazon Relational Database Service (Amazon RDS) logging is enabled. With Amazon RDS logging, you can capture events such as connections, disconnections, queries, or tables queried.This is a granular rule that returns individual findings that can be suppressed with 'appliesTo'. The findings are in the format 'LogExport::<log>' for exported logs. Example: appliesTo: ['LogExport::audit'].
            cloudwatch_logs_exports = ['postgresql'], ### REF: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-dbcluster.html#cfn-rds-dbcluster-enablecloudwatchlogsexports
                        ### Samples: https://github.com/aws/aws-cdk/blob/main/packages/aws-cdk-lib/aws-rds/README.md
            cloudwatch_logs_retention = DataClassification.retention_enum_for( tier, DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS ),

            # cluster_scailability_type=aws_rds.ClusterScailabilityType.STANDARD,
            # enable_performance_insights=True, ### RuntimeError: Performance Insights must be enabled for Aurora Limitless Database.
            # performance_insight_retention=aws_rds.PerformanceInsightRetention.MONTHS_1,
            # enable_cluster_level_enhanced_monitoring=True,  ### RuntimeError: Cluster level enhanced monitoring must be set for Aurora Limitless Database. Please set 'monitoringInterval' and enable 'enableClusterLevelEnhancedMonitoring'.
            # monitoring_interval=Duration.seconds(60),       ### Max 1 minute. RuntimeError: Cluster level enhanced monitoring must be set for Aurora Limitless Database. Please set 'monitoringInterval' and enable 'enableClusterLevelEnhancedMonitoring'.
                                        ### Default: NO enhanced monitoring
            # monitoring_role -- Default: Role is Automatically created -- will be used to manage DB instances monitoring
            # cloudwatch_logs_exports = [str] ###  list of log-types that need to be enabled, for exporting to CW-Logs. Default: - --NO-- log exports
            # cloudwatch_logs_retention = RetentionDays() ### Default: - logs --NEVER-- expire.  # of days log-events are kept in CW-Logs. To remove the retention policy, set the value to Infinity.

            # backtrack_window = .. MySql only.
            # s3_export_buckets = .. MySql only.
            # s3_import_buckets = .. MySql only.
        )

        ### This creates a V1-Aurora instance !!!!!!!!!!!!!!!!!
        # self.db = aws_rds.ServerlessCluster( ### https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_rds.ServerlessCluster.html
        #     self,
        #     id="AuroraV2-PGSQL",
        #     default_database_name = default_database_name,
        #     cluster_identifier = SqlDatabaseConstruct.get_rds_cluster_identifier( stk, engine_ver_as_string ),
        #     engine = aws_rds.DatabaseClusterEngine.aurora_postgres(version=engine_version_id),
        #     enable_data_api = True, ### Default = False
        #     ### In V1-Aurora, we have to EXPLICITY provide the secret.  Not so for V2!
        #     ### In V2-Aurora, Default-CDK-construct's behavior is to create a NEW username of 'admin' (or 'postgres' for PostgreSQL) and SecretsManager-generated password
        #     # credentials=aws_rds.Credentials.from_secret(
        #     #     secret = self.rds_master_secret,
        #     #     username = "admin_user"
        #     # ),
        #     scaling=aws_rds.ServerlessScalingOptions(
        #         auto_pause = Duration.minutes(10) if tier != constants.PROD_TIER else None,
        #         min_capacity = aws_rds.AuroraCapacityUnit.ACU_1,
        #         max_capacity = aws_rds.AuroraCapacityUnit.ACU_256,
        #     ),

        #     vpc=vpc,
        #     vpc_subnets = vpc_subnets,
        #     subnet_group = self.rds_subnet_group,
        #     security_groups = sg_list_for_all_lambdas,

        #     # storage_encryption_key = ### Default: default master key will be used for storage encryption.
        #     backup_retention = db_backup_retention,
        #     copy_tags_to_snapshot = True,
        #     deletion_protection = True if tier == constants.PROD_TIER else False,
        #     removal_policy = removal_policy,
        # )

        self.db.secret.apply_removal_policy( removal_policy )
        id="RDSAdminCredsRotation"
        self.db.secret.add_rotation_schedule(  ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/DatabaseSecret.html#aws_cdk.aws_rds.DatabaseSecret.add_rotation_schedule
            id = id,
            automatically_after = Duration.days(30),
            hosted_rotation = aws_secretsmanager.HostedRotation.postgre_sql_single_user(
                exclude_characters = get_RDS_password_exclude_pattern_adminuser(),
                function_name = f"{cluster_identifier}-{id}",
                # function_name = f"{stk.stack_name}-{cluster_identifier}-{id}",
                vpc = vpc,
                vpc_subnets = aws_ec2.SubnetSelection(
                    subnet_type = get_vpc_privatesubnet_type(vpc),
                    one_per_az = True,
                ),
                security_groups = sg_list_for_all_lambdas,
            )
        )
        ### !!! WARNNG !!!
        ### `self.db.secret` is --NOT-- AWS::SecretsManager::Secret.   It is actually a CustomResource created by CDK !!!!!!
        ### Attention: Because the secret is created as part of the DatabaseCluster's internal implementation, we can NOT update the secret's description!
        # self.db.secret.node.add_property_override( "Description", f"RDS-Postgres DBA/DBO/Admin/SuperUser credentials for {self.db.cluster_identifier}" )
        # self.db.secret.node.add_property_override( "Name", f"{self.db.cluster_identifier} DBA/DBO/Admin/Super User" )

        ### !!! WARNING !!!
        ### Follwing will --NOT-- work.  To loop thru all the childre of this construct and update the secret's description
        # print( f"\tAdminUserSecret's node.id = '{self.db.secret.node.id}' ..", end="" ); print( type(aws_secretsmanager.CfnSecret) )
        #         ### Warning@ "secret" is of type = "JSIIAbstractClass" and it prints out as `<class 'jsii._runtime.JSIIAbstractClass'>` !!!
        # for child in self.db.node.children:
        #     print( f"\tchild = '{child.node.id}' .. ", end="" ); print ( type(child) )
        #     if isinstance(child, aws_secretsmanager.CfnSecret):
        #         for grandchild in child.node.children:
        #             print( f"\t\tGRANDchild = '{grandchild.node.id}' .. ", end="" ); print ( type(grandchild) )
        #             ### This INNER-loop prints NOTHING !!!
        #         child.add_property_override( "Description", f"RDS-Postgres DBA/DBO/Admin/SuperUser credentials for {self.db.cluster_identifier}" )
        #         child.add_property_override( "Name", f"{self.db.cluster_identifier} DBA/DBO/Admin/Super User" )
        #         break

        # Allow access from security group
        self.db.connections.allow_from(
            other = self.rds_security_group,
            port_range = aws_ec2.Port.tcp(5432),
            description = "AuroraV2-Postgres DB-access from within SG only",
        )

        # Application-user creds.
        ### NOTE: can --NOT-- do this before creating the DB-Cluster!!
        self.emfact_user_hush = aws_rds.DatabaseSecret( self, "AuroraV2User",
            username = constants.RDS_APPLN_USER_NAME,
            secret_name = f"{stk.stack_name}/{constants.RDS_APPLN_USER_NAME}",
            master_secret = self.db.secret,
            exclude_characters = get_RDS_password_exclude_pattern_alphanum_only(),
            encryption_key = secret_encryption_key,
        )
        self.emfact_user_hush.apply_removal_policy( removal_policy )
        emfact_user_hush_attached :aws_secretsmanager.ISecret = self.emfact_user_hush.attach( self.db )
                ### Adds DB connections information in the secret

        # ### DBO/DBA/Admin user's credentials-rotation; Note: Hence, we do NOT specify the secret as a param!
        # self.db.add_rotation_single_user(
        #     # automatically_after=Duration.days(30), ### FYI: 30-days is the default!!
        #     exclude_characters=get_RDS_password_exclude_pattern_alphanum_only(),
        #     ### TODO lock this auto-generated Lambda inside a VPC.
        # )

        ## Add credentials-rotation to the db-user used by the application/lambdas.
        id="AppDBUser"
        emfact_user_hush_attached.add_rotation_schedule(  ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/DatabaseSecret.html#aws_cdk.aws_rds.DatabaseSecret.add_rotation_schedule
            id = id,
            rotate_immediately_on_update = False,
            automatically_after = Duration.days(30) if tier in constants.UPPER_TIERS else Duration.days(1),
            # automatically_after=Duration.days(30), ### FYI: 30-days is the default!!
            hosted_rotation = aws_secretsmanager.HostedRotation.postgre_sql_single_user(
                exclude_characters = get_RDS_password_exclude_pattern_alphanum_only(),
                function_name = f"{cluster_identifier}-{id}",
                # function_name = f"{stk.stack_name}-{cluster_identifier}-{id}",
                vpc = vpc,
                vpc_subnets = aws_ec2.SubnetSelection(
                    subnet_type = get_vpc_privatesubnet_type(vpc),
                    one_per_az = True,
                ),
                security_groups = sg_list_for_all_lambdas,
            )
        )
        emfact_user_hush_attached.apply_removal_policy( removal_policy )

        ### ------ RDS Proxy // Database-Proxy // DB-Proxy -------
        # Create RDS Proxy
        self.db_proxy = aws_rds.DatabaseProxy( self.db, 'MyDBProxy',
            proxy_target = aws_rds.ProxyTarget.from_cluster(self.db),
            secrets = [
                self.db.secret,  ### DBA-Admin
                self.emfact_user_hush,  ### Appl-DB-User
            ],
            db_proxy_name = cluster_identifier, ###  [a-zA-Z](?:-?[a-zA-Z0-9]+)*
            vpc = vpc,
            require_tls = True,
            iam_auth = True,  # Require IAM authentication
            vpc_subnets = aws_ec2.SubnetSelection(
                # subnet_group_name = .. this is --NOT-- the same as self.rds_subnet_group !!
                subnet_type = get_vpc_privatesubnet_type(vpc),
                one_per_az = True,
            ),
            security_groups = sg_list_for_all_lambdas,
            debug_logging=True
        )
        self.db_proxy.apply_removal_policy( RemovalPolicy.DESTROY ) ### Even for Upper-tiers!!

        ### self.db_proxy.db_proxy_name
        ### self.db_proxy.db_proxy_arn
        ### self.db_proxy.endpoint

        # Add security group rule to allow access from the proxy to the database
        self.db.connections.allow_from(
            self.db_proxy,
            aws_ec2.Port.tcp(5432),
            "From RDS-Proxy to AuroraV2-Postgres-cluster",
        )
        self.db_proxy.connections.allow_from(
            self.rds_security_group,  ### Attention: Assumption: All Lambdas are running inside this same SG as RDS-Aurora.
            aws_ec2.Port.tcp(5432),
            "From Lambdas running inside SAME-SG as AuroraV2-Postgres-cluster, into AG of RDS-Proxy",
        )

        add_tags( self.db_proxy, tier, aws_env, git_branch )
        # self.db_proxy.node.add_dependency(self.db)
        # self.db.node.add_dependency(self.rds_security_group)
        # self.db.node.add_dependency(self.rds_subnet_group)

### EoF
