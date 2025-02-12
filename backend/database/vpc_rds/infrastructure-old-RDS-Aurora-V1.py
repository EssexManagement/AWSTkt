from constructs import Construct
from os import path

from aws_cdk import CustomResource, Duration, RemovalPolicy, Stack
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager,
)

import constants
from common.cdk.standard_lambda import StandardLambda

ENGINE_VERSION_LOOKUP :dict = {
    '11': rds.AuroraPostgresEngineVersion.VER_11_13,
    '12': rds.AuroraPostgresEngineVersion.VER_12_18,
    '13': rds.AuroraPostgresEngineVersion.VER_13_12,
    '14': rds.AuroraPostgresEngineVersion.VER_14_11,
    '15': rds.AuroraPostgresEngineVersion.VER_15_6,
    '16': rds.AuroraPostgresEngineVersion.VER_16_2,
}

class CommonVpc(Construct):
    @property
    def vpc(self) -> ec2.IVpc:
        return self._vpc

    @property
    def rds_security_group(self) -> ec2.ISecurityGroup:
        return self._rds_security_group

    def __init__(self, scope: Construct, id_: str,
            tier :str,
            aws_env :str,
            git_branch :str,
            cidr: str,
            **kwargs
    ) -> None:
        super().__init__(scope, id_, **kwargs)
        stack = Stack.of(self)

        # VPC
        if tier not in constants.STD_TIERS:
            print( f"For tier='{tier}', --NOT-- creating a new VPC. Instead RE-USING dev-environment's VPC='{constants.get_vpc_name(tier)}' // "+ __file__)
            self._vpc = ec2.Vpc.from_lookup(self, f"vpcLookup", vpc_name=constants.get_vpc_name(tier))
        else:
            self._vpc = ec2.Vpc(
                self,
                id="VPC",
                # cidr=cidr,  ### Deprecated. Use ip_addresses as shown below.
                ip_addresses=ec2.IpAddresses.cidr(cidr),
                max_azs=2,
                nat_gateways=1,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="public",
                        cidr_mask=24,
                        reserved=False,
                        subnet_type=ec2.SubnetType.PUBLIC,
                    ),
                    ec2.SubnetConfiguration(
                        name="private",
                        cidr_mask=24,
                        reserved=False,
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    ),
                    ec2.SubnetConfiguration(
                        name="DB",
                        cidr_mask=24,
                        reserved=False,
                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    ),
                    # ec2.SubnetConfiguration(
                    #     name="DB2", cidr_mask=24,
                    #     reserved=False, subnet_type=ec2.SubnetType.ISOLATED
                    # )
                ],
                restrict_default_security_group=True,
                enable_dns_hostnames=True,
                enable_dns_support=True,
            )

        self._rds_security_group = ec2.SecurityGroup(
            self,
            id="rds-security-group",
            security_group_name=f"{stack.stack_name}-rds-security-group",
            vpc=self._vpc,
        )




class VpcRds(Construct):
    def __init__(self, scope: Construct, id_: str,
            tier :str,
            aws_env :str,
            git_branch :str,
            vpc :ec2.IVpc,
            rds_security_group :ec2.ISecurityGroup,
            db_backup_retention: int,
            **kwargs
    ) -> None:
        super().__init__(scope, id_, **kwargs)
        self.vpc = vpc
        self.rds_security_group = rds_security_group
        stack = Stack.of(self)

        engine_ver_as_string = self.node.try_get_context("PostgreSQL-Engine-Version")
        print(f"engine_ver_as_string (json) = {engine_ver_as_string}")
        engine_ver_as_string = engine_ver_as_string[ tier if tier in constants.STD_TIERS else "developer" ]
        print(f"engine_ver_as_string (plain-string)= '{engine_ver_as_string}'")
        assert engine_ver_as_string is not None, f"cdk.json is missing 'PostgreSQL-Engine-Version'"

        engine_version_id = ENGINE_VERSION_LOOKUP[engine_ver_as_string]
        print(f"engine_version_id = '{engine_version_id}'")

        rds_paramgroup_name = f"default.aurora-postgresql{engine_ver_as_string}"
        print(f"rds_paramgroup_name = '{rds_paramgroup_name}'")

        rds_master_secret = aws_secretsmanager.Secret(
            self,
            id="rds-master-secret",
            secret_name=f"{stack.stack_name}/rds-master",
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin_user"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=16,
            ),
        )

        # RDS
        self.rds_subnet_group = rds.SubnetGroup(
            self,
            id="rds-subnet-group",
            description=f"{stack.stack_name} RDS subnet group",
            vpc=self.vpc,
            # the properties below are optional
            removal_policy=RemovalPolicy.DESTROY,
            subnet_group_name=f"{stack.stack_name}-rds_subnet_group",
            vpc_subnets=ec2.SubnetSelection(
                one_per_az=True, subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        self.db = rds.ServerlessCluster(
            self,
            id="emfact-db",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=engine_version_id),
            vpc=self.vpc,
            # cluster_identifier=f"{stack.stack_name}-postgres",
            cluster_identifier=f"{stack.stack_name}-postgres-{engine_ver_as_string}",
            enable_data_api=True,
            credentials=rds.Credentials.from_secret(
                username="admin_user",
                secret=rds_master_secret,
            ),
            # credentials=rds.Credentials.from_generated_secret(
            #     username="admin_user", secret_name=f"{stack.stack_name}/rds-master",
            #     exclude_characters="~`!#$%^&*()-_+={}[]|\\:;'”’\"<>.,?",
            # ),
            scaling=rds.ServerlessScalingOptions(
                auto_pause=Duration.minutes(5),
                min_capacity=rds.AuroraCapacityUnit.ACU_2,
                max_capacity=rds.AuroraCapacityUnit.ACU_192,
            ),
            default_database_name="essex_emfact",
            subnet_group=self.rds_subnet_group,
            security_groups=[self.rds_security_group],
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, "ParameterGroup", rds_paramgroup_name
            ),
            backup_retention=Duration.days(db_backup_retention),
            copy_tags_to_snapshot=True,
            removal_policy=RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE if tier == constants.PROD_TIER else RemovalPolicy.DESTROY,
            deletion_protection=True if tier == constants.PROD_TIER else False,
        )

        self.db.connections.allow_from(self.rds_security_group, ec2.Port.tcp(5432))

        self.db.add_rotation_single_user(
            automatically_after=Duration.days(1), exclude_characters="{}[]()'\\/"
        )

        self.emfact_user_hush = rds.DatabaseSecret(
            self,
            "emfactUserSecret",
            username="emfact_user",
            secret_name=f"{stack.stack_name}/emfact_user",  # optional, defaults to a CloudFormation-generated name # change to emfact_user
            master_secret=self.db.secret,
            exclude_characters="{}[]()'/\\",

        )
        emfact_user_unpublished_attached = self.emfact_user_hush.attach( self.db )
                ### Adds DB connections information in the secret

        # self.db.add_rotation_multi_user( "MyUser", secret = emfact_user_unpublished_attached )
                ### Add rotation using the multi user scheme

### EoF

