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

CPU_ARCH_LIST = [
    aws_lambda.Architecture.ARM_64,
    # aws_lambda.Architecture.X86_64 ### !!!!!!!!!!!!!!!!!!!!!! TODO WARNING temporarily disabled, until fix is found to AWS-CodeBuild's CDK-Synth Docker-failures (even tho' cdk-synth works just fine on Laptop)
]

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

""" In a separate stack, create AWS-REsources needed across all other stacks.
    Example: Lambda-Layers (incl. building the ZIP-files for the Python-layers)
"""
class CommonAWSResourcesStack(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        # inside_vpc_lambda_factory :StandardLambda,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope,
                id=id_,
                stack_name = f"{scope.stack_prefix}-{id_}",
                **kwargs)

        self.tier = tier

        ### -------- 𝜆-layers -------

        self._create_lambda_layers( tier )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)


    ### ---------------------------------------------------------------------------------------------------------------------
    """ For each cpu-architecture, create lambda-layers (assuming `LambdaLayersAssetBuilder` class has done its job properly)
    """
    def _create_lambda_layers(self, tier :str):
        stk = Stack.of(self)

        for cpu_arch in CPU_ARCH_LIST:
            cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
            # cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64|x86_64' string

            print( '$'*120)
            print( f"Building Lambda-Layer ZIP-file for CPU-Arch: '{cpu_arch_str}' .. .." )


            for layer in LAYER_MODULES:
                print( '^'*120 )
                layer_id = layer.LAMBDA_LAYER_ID
                layer_fldr_path = layer.LAMBDA_LAYER_FLDR
                layer_sizing_option :LambdaLayerOption = layer.LAMBDA_LAYER_SIZING_OPTION
                print( f"layer-id = '{layer_id}', layer_fldr_path='{layer_fldr_path}' sizing/cold-start-option='{layer_sizing_option}' .." )

                my_lambdalayer_asset = None
                try:
                    my_lambdalayer_asset = config.LambdaConfigs.lookup_lambda_layer_asset(
                        layer_name = layer_id,
                        cpu_arch_str = cpu_arch_str,
                    )
                except config.MyLambdaConfigException as e:
                    pass

                if not my_lambdalayer_asset:

                    util = LambdaLayerUtility(
                        lambda_layer_id = layer.LAMBDA_LAYER_ID,
                        lambda_layer_builder_script = None ### was: layer.LAMBDA_LAYER_BUILDER_SCRIPT,
                    )
                    my_lambdalayer_asset = util.build_lambda_layer_using_docker(
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
                    )
                    print( '.'*120 )

                print( my_lambdalayer_asset )

                layer_uniq_id = f"layer-{layer_id}-{cpu_arch_str}"
                layer_version_name = aws_names.gen_lambdalayer_name(
                    stk = stk,
                    simple_lambdalayer_name = layer_id,
                    cpu_arch_str = cpu_arch_str )
                print( f"Creating aws_lambda.LayerVersion(): {layer_version_name} .. via lookup-Key= '{layer_id}-{cpu_arch_str}' // {cpu_arch.name} // {layer_uniq_id} .." )

                my_lambda_layerversion = aws_lambda.LayerVersion(
                    scope = self,
                    id = layer_uniq_id,
                    layer_version_name = layer_version_name,
                    code = my_lambdalayer_asset,
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
                )
                print( '_'*120 )


            print( "done" )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### EoF
