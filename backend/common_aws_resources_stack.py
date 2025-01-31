import os
import pathlib
from typing import Optional, Dict, List
import json
import importlib

from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda,
    aws_logs,
    aws_iam,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import common.FSUtils as FSUtils
from common.cdk.standard_lambda import LambdaLayerOption
from cdk_utils.CloudFormation_util import add_tags, get_cpu_arch_as_str
from common.cdk.StandardLambdaLayer import LambdaLayerUtility, LambdaLayerProps

from api import config
from api.config import LambdaConfigs
from backend.lambda_layer.layers_config import LAYER_MODULES

### NOTE: We specifically need this variation of DYNAMICALLY importing `backend.lambda_layer.lambda_layer_hashes`
import backend.lambda_layer.lambda_layer_hashes

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class CommonAWSResourcesStack(Stack):
    def __init__( self,
        scope: Construct,
        simple_id: str,
        stk_prefix :Optional[str],
        tier :str,
        aws_env :str,
        git_branch :str,
        cpu_arch_list :List[aws_lambda.Architecture] = constants_cdk.CPU_ARCH_LIST,
        layer_modules_list :list[any] = LAYER_MODULES,
        **kwargs,
    ) -> None:
        """ In a separate stack, use CDK-Lookup for AWS-Resources (created from all other stacks).
            Example: Lambda-Layers (incl. building the ZIP-files for the Python-layers)

            1st param:  typical CDK scope (parent Construct/stack)
            2nd param:  simple_id :str  => Very simple stack_id (do --NOT-- PREFIX it with `stk_prefix` (next param) that's common across all stacks in the app);
                        See also `stk_prefix` optional-parameter.
            3rd param:  stk_prefix :str     => This is typically common-PREFIX across all stacks, to make all stacks look uniform.
            4th param:  tier :str           => (dev|int|uat|tier)
            5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE; Example: DEVINT_SHARED|UAT|PROD
            6th param : git_branch :str - the git branch that is being deployed
            7th param: (OPTIONAL) cpu_arch_list :list[str]     => OPTIONAL;  For CodeBuild-on-AWS make sure this list is of length = 1!!!
            8th param: (OPTIONAL) layer_module_list :list[Custom-PyModules] => OPTIONAL;  See `LAYER_MODULES` global-constant for example and details.
        """
        super().__init__( scope=scope,
            id = simple_id,
            stack_name = f"{stk_prefix}-{simple_id}".replace('_',''),
            **kwargs
        )

        self.tier = tier

        ### -------- build the 𝜆-layers by CPU-ARCH -------

        print( '^'*120 )
        for cpu_arch in cpu_arch_list:

            for layer in layer_modules_list:

                self._lookup_lambda_layer( tier, cpu_arch, layer )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)
        print( '_'*120 )


    ### ---------------------------------------------------------------------------------------------------------------------
    def _lookup_lambda_layer(self,
        tier :str,
        cpu_arch :aws_lambda.Architecture,
        layer :LambdaLayerProps,
    ) -> None:
        """ For each cpu-architecture, LOOKUP lambda-layers (assuming creation of these 𝜆-layers was done properly ELSEWHERE/SOMEWHERE)
        """
        this_stk = Stack.of(self)
        cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )

        print( f"preparing to lookup Lambda-Layer for CPU-Arch: '{cpu_arch_str}' .. .." )
        layer_id = layer.lambda_layer_id
        layer_fldr_path = layer.lambda_layer_fldr
        layer_sizing_option :LambdaLayerOption = layer.lambda_layer_sizing_option
        print( f"layer-id = '{layer_id}', layer_fldr_path='{layer_fldr_path}' sizing/cold-start-option='{layer_sizing_option}' .." )

        lkp_str_key :str = aws_names.gen_lambdalayer_name( tier, layer_id, cpu_arch_str )
        print( f"lkp_str_key = '{lkp_str_key}'" )
        ### Since the file `backend/lambda_layer/lambda_layer_hashes.py` was updated -by- this CDK-synth-execution (happened within `cdk_lambda_layers_app.py`), we need to DYNAMICALLY reload it.
        dyn_reloaded_module = importlib.reload(backend.lambda_layer.lambda_layer_hashes)
        lkp_obj = dyn_reloaded_module.lambda_layer_hashes.get( tier )
        print( json.dumps(lkp_obj, indent=4, default=str) )
        lkp_lyr :dict[str, str] = lkp_obj.get( lkp_str_key ) if lkp_obj else None
        print( json.dumps(lkp_lyr, indent=4) )
        lkp_lyr_arn  = lkp_lyr.get('arn') if lkp_lyr else None
        lkp_lyr_hash = lkp_lyr.get('sha256_hex') if lkp_lyr else None
        print( f"lkp_lyr_arn = '{lkp_lyr_arn}'" )
        print( f"lkp_lyr_hash = '{lkp_lyr_hash}'" )

        my_lambdalayer_asset = None
        myasset_sha256_hash  = None
        try:
            my_lambdalayer_asset, myasset_sha256_hash = config.LambdaConfigs.lookup_lambda_layer(
                layer_simple_name = layer_id,
                stk_containing_layers = Stack.of(self),
                cpu_arch_str = cpu_arch_str,
            )
        except config.MyLambdaConfigException as e:
            ### The presence of `config.MyLambdaConfigException` ==> implies ==> not found.  This design ensures only a 2-element-tupe is returned by `lookup_lambda_layer_asset()`
            ### This same exception is FATAL elsewhere.  But not here.

            config.LambdaConfigs.cache_lambda_layer(
                layer_simple_name = layer_id,
                cpu_arch_str = cpu_arch_str,
                stk_containing_layers = Stack.of(self),
                layer = aws_lambda.LayerVersion.from_layer_version_arn( self,
                        id = lkp_str_key,
                        layer_version_arn = lkp_lyr_arn,
                ),
                asset_sha256_hash = myasset_sha256_hash,
                overwrite = False,
            )

        print( my_lambdalayer_asset )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### EoF
