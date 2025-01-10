import os
import pathlib
import sys
import json
from typing import List, Optional
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

from backend.lambda_layer.layers_config import LAYER_MODULES

### NOTE: We specifically need this variation of DYNAMICALLY importing `backend.lambda_layer.lambda_layer_hashes`
import backend.lambda_layer.lambda_layer_hashes

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

HDR = " inside "+ __file__


class AppStack(Stack):
    def __init__( self,
        scope: Construct,
        simple_id: str,
        stk_prefix :Optional[str],
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
            2nd param:  simple_id :str  => Very simple stack_id (do --NOT-- PREFIX it with `stk_prefix` (next param) that's common across all stacks in the app);
                        See also `stk_prefix` optional-parameter.
            3rd param:  stk_prefix :str     => This is typically common-PREFIX across all stacks, to make all stacks look uniform.
            4th param:  tier :str           => (dev|int|uat|tier)
            5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE; Example: DEVINT_SHARED|UAT|PROD
            6th param : git_branch :str - the git branch that is being deployed
            7th param:  cpu_arch_str :str  => "arm64" or "amd64"
        """
        super().__init__( scope=scope,
            id = simple_id,
            stack_name = f"{stk_prefix}-{simple_id}".replace('_',''),
            **kwargs
        )

        self.tier = tier
        layer_id = LAYER_MODULES[0].LAMBDA_LAYER_ID  ### <--------------- hardcoding the layer to use !!!!!!!!!!!!!
        layer_full_name = f"{aws_names.gen_lambdalayer_name(tier,layer_id,cpu_arch_str)}"
        print( f"{HDR} - layer_full_name = {layer_full_name}" )
        ### Since the file `backend/lambda_layer/lambda_layer_hashes.py` was updated -by- this CDK-synth-execution (happened within `layers_app.py`), we need to DYNAMICALLY reload it.
        lambda_layer_hashes = importlib.reload(backend.lambda_layer.lambda_layer_hashes)
        layer_version_arn :str = lambda_layer_hashes.get(tier).get( layer_full_name ).get('arn')
        print( f"{HDR} - layer_version_arn = {layer_version_arn}" )
        # layer_version_arn = f"arn:{self.partition}:lambda:{self.region}:{self.account}:layer:{aws_names.gen_lambdalayer_name(tier,layer_id,cpu_arch_str)}"
            ### Example: arn:aws:lambda:us-east-1:123456789012:layer:AWSTkt-backend-dev_psycopg3-pandas_amd64:5

        ### Since the Layers are built in another Stack, LambdaConfigs.lookup_lambda_layer() will fail .. .. even if I use `stk_containing_layers = common_stk` !!!
        my_lambda_layerversion = aws_lambda.LayerVersion.from_layer_version_attributes( scope = self,
            id = f"lkp-layer-{layer_id}-{cpu_arch_str}",
            layer_version_arn = layer_version_arn,
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

### ..............................................................................................

### EoF
