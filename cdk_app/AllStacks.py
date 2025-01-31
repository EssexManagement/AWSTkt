import os
import pathlib
import sys
import json
from typing import List, Optional, Tuple
import importlib

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda,
    aws_logs,
    aws_iam,
    aws_lambda_python_alpha
)
from constructs import Construct

import constants as constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CloudFormation_util as CFUtil
from common.cdk.standard_lambda import StandardLambda

from backend.vpc_w_subnets import VpcWithSubnetsConstruct
from backend.common_aws_resources_stack import CommonAWSResourcesStack

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


class AppStack(Stack):
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
        super().__init__( scope=scope,
            id = simple_id,
            stack_name = f"{stack_prefix}-{simple_id}".replace('_',''),
            **kwargs
        )

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

        layer_id = LAYER_MODULES[0].LAMBDA_LAYER_ID  ### <--------------- hardcoding the layer to use !!!!!!!!!!!!!
        layer_full_name = f"{aws_names.gen_lambdalayer_name(tier,layer_id,cpu_arch_str)}"
        print( f"{HDR} - layer_full_name = {layer_full_name}" )
        ### Since the file `backend/lambda_layer/lambda_layer_hashes.py` was updated -by- this CDK-synth-execution (happened within `cdk_lambda_layers_app.py`), we need to DYNAMICALLY reload it.
        dyn_reloaded_module = importlib.reload(backend.lambda_layer.lambda_layer_hashes)
        lkp_obj = dyn_reloaded_module.lambda_layer_hashes.get(tier)
        lkp_obj = lkp_obj.get( layer_full_name ) if lkp_obj else None
        layer_version_arn :str = lkp_obj.get('arn') if lkp_obj else None
        print( f"{HDR} - layer_version_arn = {layer_version_arn}" )
        # layer_version_arn = f"arn:{self.partition}:lambda:{self.region}:{self.account}:layer:{aws_names.gen_lambdalayer_name(tier,layer_id,cpu_arch_str)}"
            ### Example: arn:aws:lambda:us-east-1:123456789012:layer:AWSTkt-backend-dev_psycopg3-pandas_amd64:5

        if ( layer_version_arn ):
            ### Since the Layers are built in another Stack, LambdaConfigs.lookup_lambda_layer() will fail .. .. even if I use `stk_containing_layers = common_stk` !!!
            my_lambda_layerversion = aws_lambda.LayerVersion.from_layer_version_attributes( scope = self,
                id = f"lkp-layer-{layer_id}-{cpu_arch_str}",
                layer_version_arn = layer_version_arn,
            )
        else:
            ### this Lambda-Layer (99% sure) has NOT yet been deployed (hence ARNs are missing inside `backend.lambda_layer.lambda_layer_hashes`)
            ### So, we use the CDK-Construct from the other stack.
            my_lambda_layerversion, _ = LambdaConfigs.lookup_lambda_layer(
                layer_simple_name = layer_id,
                stk_containing_layers = common_stk,
                cpu_arch_str = cpu_arch_str,
            )

        print( my_lambda_layerversion )
        print( my_lambda_layerversion.layer_version_arn )
        ### Since the variable `layer_version_arn` does -NOT- include the version# .. we should expect the resposne to be for the LATEST-version of the layer
        layers = [ my_lambda_layerversion ]

        lambda_factory = StandardLambda( vpc=None, sg_lambda=None, tier=tier, min_memory=None, default_timeout=None )
        lambda_factory.create_lambda(
            scope=self,
            lambda_name=aws_names.gen_lambda_name( tier, f"myTestPythonFn-{cpu_arch_str}" ),
            path_to_lambda_src_root="backend/src/lambda",
            index="handler.py",
            handler="handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            architecture=CFUtil.get_cpu_arch_enum( cpu_arch_str ),
            layers=layers,
            timeout=Duration.seconds(30),
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

### ..............................................................................................

### EoF
