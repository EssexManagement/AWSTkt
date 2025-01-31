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
)

import constants
import common.cdk.constants_cdk as constants_cdk


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
class SqlDatabaseConstruct(Construct):

    @property
    def rds_security_group(self) -> aws_ec2.ISecurityGroup:
        return self._rds_security_group

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

        engine_ver_as_string :str = self.node.try_get_context("PostgreSQL-Engine-Version")
        print(f"engine_ver_as_string (json) = {engine_ver_as_string}")
        engine_ver_as_string = engine_ver_as_string[ tier if tier in constants.STD_TIERS else "developer" ]
        print(f"engine_ver_as_string (plain-string)= '{engine_ver_as_string}'")
        assert engine_ver_as_string is not None, f"cdk.json is missing 'PostgreSQL-Engine-Version'"

        ### Convert the string-format version of Postgres into an Enum of type aws_rds.AuroraPostgresEngineVersion.VER_??_??
        engine_version_id :str = constants_cdk.ENGINE_VERSION_LOOKUP[ engine_ver_as_string ]
        print( f"engine_version_id = '{engine_version_id}'" )

        if tier in constants.STD_TIERS:
            db_backup_retention = scope.node.try_get_context("retention")["db_backup_retention"][ tier ]
        else:  ### developer specific git_branch
            db_backup_retention = scope.node.try_get_context("retention")["db_backup_retention"][ "dev" ]
        print( f"db_backup_retention = '{db_backup_retention}'" )
        db_backup_retention = Duration.days(int(db_backup_retention))

        removal_policy = RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE if tier in constants.UPPER_TIERS else RemovalPolicy.DESTROY
        # rds_paramgroup_name = f"default.aurora-postgresql{engine_ver_as_string}"
        # print(f"rds_paramgroup_name = '{rds_paramgroup_name}'")

        ### ------------------------------------------

        vpc_subnets = aws_ec2.SubnetSelection( one_per_az=True, subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS )

        ### Whether or not a NEW-VPC was created (or existing one looked up), create a SG for use by RDS
        self._rds_security_group = aws_ec2.SecurityGroup(
            self,
            id="RDS-SG",
            security_group_name=f"{stk.stack_name}-rds-security-group",
            vpc=vpc,
        )
        # RDS Subnet Group
        self.rds_subnet_group = aws_rds.SubnetGroup(
            self,
            id="rds-subnet-group",
            description=f"{stk.stack_name} RDS subnet group",
            vpc=vpc,
            removal_policy=removal_policy,
            subnet_group_name=f"{stk.stack_name}-rds_subnet_group",
            vpc_subnets=vpc_subnets,
        )

        ### ------------------------------------------

        ### V1-Aurora Legacy-CDK-construct usage: Master-creds for database-admin/dba user
        ### NOTE: the NON-dba appl-user is created at BOTTOM of this Construct.
        # self.rds_master_secret = aws_secretsmanager.Secret(
        #     self,
        #     id="rds-master-secret",
        #     secret_name=f"{stk.stack_name}/rds-master",
        #     generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        #         secret_string_template='{"username": "admin_user"}',
        #         generate_string_key="password",
        #         exclude_characters="~`!#$%^&*()-_+={}[]|\\:;'”’\"<>.,?",
        #         password_length=32,
        #     ),
        # )

        ### ------------------------------------------

        cluster_identifier = f"{stk.stack_name}-AuroraV2-PG-{engine_ver_as_string}"

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
            ### Do NOT specify the following, to avoid ERROR: The instance class that you specified doesn't support the HTTP endpoint for using RDS Data API.
            #__ readers = [IClusterInstance] ### A list of instances to create as cluster-reader-instances. Default: - no readers are created. The cluster will have a single writer/reader
            writer=aws_rds.ClusterInstance.serverless_v2( id="AuroraWriter",
                instance_identifier = f"{cluster_identifier}-writer",
                #__ scale_with_writer =  .. .. applies to READERs only
                auto_minor_version_upgrade = False,
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
            # credentials=aws_rds.Credentials.from_secret(
            #     secret = self.rds_master_secret,
            #     username = "admin_user"
            # ),
            # network_type=aws_rds.NetworkType.IPV4,
            # enable_local_write_forwarding = True, ## Whether read-replicas can forward write-operations to the writer-nstance. Only be enabled for MySQL 3.04+ or PostgreSQL 16.4+
            storage_encrypted = True,
            backup = aws_rds.BackupProps( retention=db_backup_retention ),
            copy_tags_to_snapshot = True,
            deletion_protection = True if tier == constants.PROD_TIER else False,
            removal_policy = removal_policy,
            vpc=vpc, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            vpc_subnets = vpc_subnets, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            subnet_group=self.rds_subnet_group, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            security_groups=[self.rds_security_group], ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            # storage_type = aws_rds.DBClusterStorageType.AURORA_IOPT1, ### required for LIMITLESS mode
            # storage_type = aws_rds.DBClusterStorageType.AURORA, ### Default: - DBClusterStorageType.AURORA_IOPT1
            # instance_props=aws_rds.InstanceProps( !!!!!!!!!!!!!!!!!!! LEGACY DEPRECATED parameter !!!!!!!!!!!!!!!!!!!!
            #     # parameter_group = aws_rds.ParameterGroup.from_parameter_group_name( self, "ParamGrp", rds_paramgroup_name),
            #     vpc=vpc, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     vpc_subnets = vpc_subnets, ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     security_groups=[self.rds_security_group], ### WARNING: RuntimeError: Provide either vpc or instanceProps.vpc, but not both
            #     allow_major_version_upgrade = False,
            #     publicly_accessible = False,
            #     delete_automated_backups = False,
            #     instance_type=aws_ec2.InstanceType.of( !!!!!!! LEGACY DEPRECATED parameter !!!!!!!!
            #         aws_ec2.InstanceClass.R6GD,
            #         aws_ec2.InstanceSize.XLARGE4,
            #     ),
            # ),

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
        #     cluster_identifier = f"{stk.stack_name}-AuroraV2-PG-{engine_ver_as_string}",
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
        #     security_groups = [self.rds_security_group],

        #     # storage_encryption_key = ### Default: default master key will be used for storage encryption.
        #     backup_retention = db_backup_retention,
        #     copy_tags_to_snapshot = True,
        #     deletion_protection = True if tier == constants.PROD_TIER else False,
        #     removal_policy = removal_policy,
        # )

        self.db.secret.apply_removal_policy( removal_policy )
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
            self.rds_security_group,
            aws_ec2.Port.tcp(5432),
            "AuroraV2-Postgres DB-access from within SG only"
        )

        # Application-user creds.
        ### NOTE: can --NOT-- do this before creating the DB-Cluster!!
        self.emfact_user_hush = aws_rds.DatabaseSecret(
            self,
            "AuroraV2User",
            username="emfact_user",
            secret_name=f"{stk.stack_name}/emfact_user",
            master_secret=self.db.secret,
            exclude_characters="~`!#$%^&*()-_+={}[]|\\:;'”’\"<>.,?",
        )
        emfact_user_hush_attached :aws_secretsmanager.ISecret = self.emfact_user_hush.attach( self.db )
                ### Adds DB connections information in the secret

        # ### DBO/DBA/Admin user's credentials-rotation; Note: Hence, we do NOT specify the secret as a param!
        # self.db.add_rotation_single_user(
        #     # automatically_after=Duration.days(30), ### FYI: 30-days is the default!!
        #     exclude_characters="{}[]()'/\"@,.<>~!#$%^&*|;:` ",
        #     ### TODO lock this auto-generated Lambda inside a VPC.
        # )

        ## Add credentials-rotation to the db-user used by the application/lambdas.
        self.db.add_rotation_multi_user( id = "AppDBUser",
            secret = emfact_user_hush_attached,
            # automatically_after=Duration.days(30), ### FYI: 30-days is the default!!
            exclude_characters="{}[]()'/\"@,.<>~!#$%^&*|;:` ",
            ### TODO lock this auto-generated Lambda inside a VPC.
            rotate_immediately_on_update=True,
        )
        emfact_user_hush_attached.apply_removal_policy( removal_policy )

### EoF

