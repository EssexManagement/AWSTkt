from os import path, environ
from typing import Optional, Dict, List
import json

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
from common.cdk.standard_lambda import LambdaLayerOption
from cdk_utils.CloudFormation_util import add_tags, get_cpu_arch_as_str
from common.cdk.lambda_layer_util import LambdaLayerUtility

from api import config
from api.config import LambdaConfigs
import backend.lambda_layer.psycopg.lambda_layer_psycopg as layer_psycopg
import backend.lambda_layer.psycopg_pandas.lambda_layer_psycopg_pandas as layer_psycopg_pandas
import backend.lambda_layer.psycopg3.lambda_layer_psycopg3 as layer_psycopg3
import backend.lambda_layer.psycopg3_pandas.lambda_layer_psycopg3_pandas as layer_psycopg3_pandas
### ==============================================================================================

LAYER_MODULES = [
    layer_psycopg,
    layer_psycopg_pandas,
    layer_psycopg3,
    layer_psycopg3_pandas
]

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
        """ In a separate stack, create AWS-REsources needed across all other stacks.
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

        ### -------- 𝜆-layers by CPU-ARCH -------

        for cpu_arch in cpu_arch_list:

            for layer in layer_modules_list:

                self._create_lambda_layer( tier, cpu_arch, layer )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)


    ### ---------------------------------------------------------------------------------------------------------------------
    def _create_lambda_layer(self,
        tier :str,
        cpu_arch :aws_lambda.Architecture,
        layer :any,
    ) -> None:
        """ For each cpu-architecture, create lambda-layers (assuming `LambdaLayersAssetBuilder` class has done its job properly)
        """
        stk = Stack.of(self)
        cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )

        print( '$'*120)
        print( f"Building Lambda-Layer ZIP-file for CPU-Arch: '{cpu_arch_str}' .. .." )
        print( '^'*120 )
        layer_id = layer.LAMBDA_LAYER_ID
        layer_fldr_path = layer.LAMBDA_LAYER_FLDR
        layer_sizing_option :LambdaLayerOption = layer.LAMBDA_LAYER_SIZING_OPTION
        print( f"layer-id = '{layer_id}', layer_fldr_path='{layer_fldr_path}' sizing/cold-start-option='{layer_sizing_option}' .." )

        my_lambdalayer_asset = None
        myasset_sha256_hash  = None
        try:
            my_lambdalayer_asset, myasset_sha256_hash = config.LambdaConfigs.lookup_lambda_layer_asset(
                layer_name = layer_id,
                cpu_arch_str = cpu_arch_str,
            )
        except config.MyLambdaConfigException as e:
            ### The presence of `config.MyLambdaConfigException` ==> implies ==> not found.  This design ensures only a 2-element-tupe is returned by `lookup_lambda_layer_asset()`
            ### This same exception is FATAL elsewhere.  But not here.
            pass
            ### we "pass" and proceed with the fact that `my_lambdalayer_asset` === None.

        if not my_lambdalayer_asset:

            util = LambdaLayerUtility(
                lambda_layer_id = layer.LAMBDA_LAYER_ID,
                lambda_layer_builder_script = None ### was: layer.LAMBDA_LAYER_BUILDER_SCRIPT,
            )
            my_lambdalayer_asset, myasset_sha256_hash = util.build_lambda_layer_using_docker(
                tier = tier,
                cpu_arch_str = cpu_arch_str,
                layer_fldr_path = layer_fldr_path,
                layer_opt = layer_sizing_option,
                # zipfile_simplename = layer_zipfilename,
            )
            config.LambdaConfigs.cache_lambda_layer_asset(
                layer_name = layer_id,
                cpu_arch_str = cpu_arch_str,
                layer_asset = my_lambdalayer_asset,
                asset_sha256_hash = myasset_sha256_hash,
            )
            print( '.'*120 )

        print( my_lambdalayer_asset )

        layer_uniq_id = f"layer-{layer_id}-{cpu_arch_str}"
        layer_version_name = aws_names.gen_lambdalayer_name(
            tier = tier,
            simple_lambdalayer_name = layer_id,
            cpu_arch_str = cpu_arch_str )
        print( f"Creating aws_lambda.LayerVersion(): {layer_version_name} .. via lookup-Key= '{layer_id}-{cpu_arch_str}' // {cpu_arch_str} // {layer_uniq_id} .." )

        my_lambda_layerversion = aws_lambda.LayerVersion(
            scope = self,
            id = layer_uniq_id,
            layer_version_name = layer_version_name,
            code = my_lambdalayer_asset,
            description = myasset_sha256_hash,
            # code = aws_lambda.Code.from_asset( str(my_lambda_layer_zipfile) ),
            compatible_runtimes = [aws_lambda.Runtime.PYTHON_3_12, aws_lambda.Runtime.PYTHON_3_11],
            # compatible_architectures=[cpu_arch],
            removal_policy = RemovalPolicy.DESTROY,
        )

        LambdaConfigs.cache_lambda_layer(
            layer_name = layer_id,
            cpu_arch_str = cpu_arch_str,
            stk = stk,
            layer = my_lambda_layerversion,
            asset_sha256_hash = myasset_sha256_hash,
        )
        print( '_'*120 )

        print( "done" )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### EoF
