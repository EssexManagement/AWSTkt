import os
import pathlib
import sys
import json
from typing import List, Optional, Tuple
import importlib

from aws_cdk import (
    Stack,
    CfnOutput,  CfnParameter,
    Duration,
    RemovalPolicy,
    aws_lambda,
    aws_logs,
    aws_iam,
    aws_lambda_python_alpha,
    aws_s3,
    aws_ec2,
    aws_rds,
)
from constructs import Construct

import constants as constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CloudFormation_util as CFUtil

from common.cdk.standard_lambda import StandardLambda

from backend.vpc_w_subnets import VpcWithSubnetsConstruct
from backend.common_aws_resources_stack import CommonAWSResourcesStack
from backend.database.infra.infrastructure import SqlDatabaseConstruct
from security.cognito.infrastructure import MyUserPool

from common.cdk.retention_base import (
    DATA_CLASSIFICATION_TYPES,
    S3_LIFECYCLE_RULES,
)
from common.cdk.StandardBucket import (
    create_std_bucket,
    gen_bucket_lifecycle,
    add_lifecycle_rules_to_bucket,
)

from api.config import LambdaConfigs

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

HDR = " inside "+ __file__

class StackReferences:
    def __init__(self):
        pass

stk_refs = StackReferences()

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================


class Gen_AllApplicationStacks(Construct):
    def __init__( self,
        scope: Construct,
        simple_id: str,
        stack_prefix :Optional[str],
        tier :str,
        aws_env :str,
        git_branch :str,
        cpu_arch_str :str,
        common_stk :Stack,
        **kwargs,
    ) -> None:
        """ In a separate stack, create AWS-REsources needed across all other stacks.
            Example: Lambda-Layers (incl. building the ZIP-files for the Python-layers)

            1st param:  typical CDK scope (parent Construct/stack)
            2nd param:  simple_id :str  => Very simple stack_id (do --NOT-- PREFIX it with `stack_prefix` (next param) that's common across all stacks in the app);
                        See also `stack_prefix` optional-parameter.
            3rd param:  stack_prefix :str     => This is typically common-PREFIX across all stacks, to make all stacks look uniform.
            4th param:  tier :str           => (dev|int|uat|tier)
            5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE; Example: DEVINT_SHARED|UAT|PROD
            6th param : git_branch :str - the git branch that is being deployed
            7th param:  cpu_arch_str :str  => "arm64" or "amd64"
        """
        super().__init__(scope, id_)   ### This is --NOT-- as stack; So, Do NOT pass kwargs (into Constructs)!

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        ### ----------------------------------------------
        bundling_stks :list[str] = self.node.try_get_context("aws:cdk:bundling-stacks")
        bundlings_all_stks = bundling_stks.index("**") >= 0

        ### ----------------------------------------------
        id_ = stack_prefix+ "-AWSLandingZone"
        # if bundlings_all_stks or (bundling_stks.index(id_) >= 0):
        aws_landingzone = AWSLandingZoneStack(  ### Do nothing Stack-construct.  Acts as "scope" construct below.
            scope = self,
            id_ = id_,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            **kwargs
        )

        common_stk = CommonAWSResourcesStack(
            scope = None,
            simple_id = "CommonRsrcs",
            stack_prefix = stack_prefix,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            **kwargs
        )

        lambdas_stk = LambdaStack(
            scope = None,
            simple_id = "CommonRsrcs",
            stack_prefix = stack_prefix,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            vpc = aws_landingzone.vpc,
            common_stk = common_stk,
            # db_stk = db_stk,
            **kwargs
        )

### ..............................................................................................

class LambdaStack(Stack):
    """ Just Lambdas of various languages.
        Some inside a VPC, and some are NOT.
    """

    def __init__(self,
        scope: Construct,
        simple_id: str,
        stk_prefix :Optional[str],
        tier: str,
        aws_env: str,
        git_branch: str,
        vpc :aws_ec2.Vpc,
        common_stk :CommonAWSResourcesStack,
        cpu_arch_str: str = constants_cdk.DEFAULT_CPU_ARCH_NAMESTR,
        # db_stk :SqlDatabaseConstruct,
        **kwargs
    ) -> None:
        super().__init__( scope=scope,
            id = simple_id,
            stack_name = f"{stk_prefix}-{simple_id}".replace('_',''),
            **kwargs
        )

        ### ----- constants -----
        lambda_simple_name = "myTestPythonFn"
        lambda_fullname=aws_names.gen_lambda_name( tier, f"{lambda_simple_name}-{cpu_arch_str}" )

        from backend.lambda_layer.psycopg.LayerConfig import props
        layer_simple_id = props.lambda_layer_id  ### <--------------- hardcoding the layer to use !!!!!!!!!!!!!

        ### ----- derived-variables -----
        layer_full_name = f"{aws_names.gen_lambdalayer_name(tier,layer_simple_id,cpu_arch_str)}"
        print( f"{HDR} - layer_full_name = {layer_full_name}" )
        lambda_layers_names = [ layer_full_name ]

        # layer_version_arn = f"arn:{self.partition}:lambda:{self.region}:{self.account}:layer:{aws_names.gen_lambdalayer_name(tier,layer_simple_id,cpu_arch_str)}"
            ### Example: arn:aws:lambda:us-east-1:123456789012:layer:AWSTkt-backend-dev_psycopg3-pandas_amd64:5

        ### ----- 𝜆-Layers lookup -----
        lambda_specific_layers = []  ### initialized to None above. Hence.
        for nm in lambda_layers_names:
            print( f"\tincluding the lambda_layer: '{nm}' for '{lambda_fullname}'" )
            myLayerObj, _ = LambdaConfigs.lookup_lambda_layer(
                layer_simple_name = nm,
                stk_containing_layers = common_stk,
                cpu_arch_str = cpu_arch_str,
            )
            lambda_specific_layers.append( myLayerObj )
            print( myLayerObj )
            print( myLayerObj.layer_version_arn )
            ### Since the variable `layer_version_arn` does -NOT- include the version# .. we should expect the resposne to be for the LATEST-version of the layer
        print(f"lambda_specific_layers are '{lambda_specific_layers}'")

        layers = [ myLayerObj ]

        lambda_factory = StandardLambda( vpc=None, sg_lambda=None, tier=tier, min_memory=None, default_timeout=None )
        lambda_factory.create_lambda(
            scope=self,
            lambda_name = lambda_fullname,
            path_to_lambda_src_root = "backend/src/lambda",
            index = "handler.py",
            handler = "handler",
            runtime = aws_lambda.Runtime.PYTHON_3_12,
            architecture = CFUtil.get_cpu_arch_enum( cpu_arch_str ),
            layers = layers,
            timeout = Duration.seconds(30),
        )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class StatefulStack(Stack):
    """ Just the RDS Aurora and Stack-Outputs.
        Has 2 RDS-related properties: self.rds_con and self.rds;
            The former is a CDK-construct SqlDatabaseConstruct, while the latter is aws_cdk.aws_rds.DatabaseCluster instance.
        Also, has a Security-Group property named `rds_security_group`
    """

    @property
    def rds(self) -> aws_rds.DatabaseCluster:
        return self._rds

    @property
    def rds_security_group(self) -> aws_ec2.ISecurityGroup:
        return self._rds_security_group

    def __init__(self,
        scope: Construct,
        id_: str,
        tier: str,
        aws_env: str,
        git_branch: str,
        vpc :aws_ec2.Vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, id_, stack_name=id_, **kwargs)

        self.rds_con = SqlDatabaseConstruct(scope = self,
            id_ = "AuroraV2PG",
            tier = tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc = vpc,
        )
        self._rds = self.rds_con.db
        self._rds_security_group  = self.rds_con.rds_security_group

        CfnOutput(self, id=f"vpc-{tier}", export_name=f"vpc-{tier}", value=vpc.vpc_id)

        CfnOutput( self,
            id="emfact-user-secret",
            export_name=f"{self.stack_name}-emfact-user-secret-name",
            value=self.rds_con.emfact_user_hush.secret_name,
        )

        CfnOutput( self,
            id="rds_security_group",
            export_name=f"{self.stack_name}-rds-security-group-id",
            value=self.rds_security_group.security_group_id,
        )

        CfnOutput( self,
            id="db",
            export_name=f"{self.stack_name}-db-cluster-id",
            value=self.rds.cluster_identifier,
        )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class CognitoStack(Stack):
    def __init__(self, scope: Construct, id_: str,
            tier :str,
            git_branch :str,
            aws_env :str,
            **kwargs
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        _user_pool = MyUserPool(self, "user pool",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
        )
        self.user_pool = _user_pool.user_pool
        self.api_client = _user_pool.api_client

        self._user_pool_id = CfnOutput(
            self,
            id="UserPoolID",
            export_name=f"{self.stack_name}-UserPoolID",
            value=self.user_pool.user_pool_id,
        )

        self._domain_name = CfnOutput(
            self,
            id="UserPoolDomain",
            export_name=f"{self.stack_name}-UserPoolDomain",
            value=_user_pool.user_pool_domain.domain_name,
        )

        self._user_pool_client_id = CfnOutput(
            self,
            id="UIClientID",
            export_name=f"{self.stack_name}-UIClientID",
            value=_user_pool.ui_client.user_pool_client_id,
        )

        # self._user_pool_client_secret = CfnOutput(
        #     self,
        #     id="APIClientID",
        #     export_name=f"{self.stack_name}-APIClientID",
        #     value=_user_pool.api_client.user_pool_client_secret,
        # )
        print('&'* 200)
        print(dict(tier=tier, aws_env=aws_env, git_branch=git_branch))
        print('&' * 200)
        CFUtil.add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)

### ..............................................................................................

class BucketsStack(Stack):
    def __init__(self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)


        data_classification_type: DATA_CLASSIFICATION_TYPES = DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY
        all_lifecycle_rules: dict[str, aws_s3.LifecycleRule] = gen_bucket_lifecycle(
            tier=tier,
            data_classification_type=data_classification_type, enabled=True
        )

        self.search_results_bucket: aws_s3.Bucket = create_std_bucket(
            scope = self,
            id = 'buckets',
            bucket_name = aws_names.gen_bucket_name( tier=tier, simple_bucket_name="session-results" ).lower(),
            tier = tier,
            data_classification_type = data_classification_type,
            enable_S3PreSignedURLs = True,
            lifecycle_rules=all_lifecycle_rules[S3_LIFECYCLE_RULES.SCRATCH.name],
            # cors_rule_list=[cors_rule],
        )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class AWSLandingZoneStack(Stack):
    """ Has 3 properties: vpc_con, vpc and rds_security_group
    """

    def __init__(self,
        scope: Construct,
        id_: str,
        tier: str,
        aws_env: str,
        git_branch: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id_, stack_name=id_, **kwargs)

        # define stack-cloudformation-param named "cdkAppName"
        cdk_app_name_cfnp = CfnParameter(self, "cdkAppName",
            type="String",
            description="The name of the CDK app",
            default=constants.CDK_APP_NAME,
        )

        self.vpc_con = VpcWithSubnetsConstruct( scope = self,
            construct_id = "vpc-only",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            cdk_app_name = cdk_app_name_cfnp,
        )

        self.vpc = self.vpc_con.vpc

### EoF
