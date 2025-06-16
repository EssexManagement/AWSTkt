import os
import subprocess
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

class LambdaLayersBuilderStacks(Stack):
    def __init__( self,
        scope: Construct,
        simple_id: str,
        stk_prefix :Optional[str],
        tier :str,
        aws_env :str,
        git_branch :str,
        cpu_arch_list :List[aws_lambda.Architecture] = constants_cdk.CPU_ARCH_LIST,
        layer_modules_list :list[LambdaLayerProps] = LAYER_MODULES,
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

        ### -------- build the 𝜆-layers by CPU-ARCH -------

        for cpu_arch in cpu_arch_list:
            print( f"\nChecking whether to build 𝜆-layers for {cpu_arch.name} .." )

            for layer in layer_modules_list:

                skip_for_cpu_arch = True;
                print( "\n𝜆-layer "+ layer.lambda_layer_id, end=": " )
                for larch in layer.cpu_arch:
                    print( f"layer.cpu_arch = '{larch.name}'", end=' .. ' )
                    if cpu_arch.name == larch.name:
                        skip_for_cpu_arch = False
                print( '' ) # end of line

                if not skip_for_cpu_arch:
                    self._create_lambda_layer( tier, cpu_arch, layer )
                else:
                    print( f"Lambda-Layer '{layer.lambda_layer_id}' .. is --NOT-- supported for CPU-Arch '{cpu_arch.name}'" )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)


    ### ---------------------------------------------------------------------------------------------------------------------
    def _create_lambda_layer(self,
        tier :str,
        cpu_arch :aws_lambda.Architecture,
        layer :LambdaLayerProps,
    ) -> None:
        """ For each cpu-architecture, create lambda-layers (assuming `LambdaLayersAssetBuilder` class has done its job properly)
        """
        this_stk = Stack.of(self)
        cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )

        print( '$'*60)
        print( f"Building Lambda-Layer ZIP-file for CPU-Arch: '{cpu_arch_str}' .. .." )
        print( '^'*120 )
        layer_id = layer.lambda_layer_id
        layer_fldr_path = layer.lambda_layer_fldr
        layer_sizing_option :LambdaLayerOption = layer.lambda_layer_sizing_option
        print( f"layer-id = '{layer_id}', layer_fldr_path='{layer_fldr_path}' sizing/cold-start-option='{layer_sizing_option}' .." )

        lkp_str_key :str = aws_names.gen_lambdalayer_name( tier, layer_id, cpu_arch_str )
        print( f"lkp_str_key = '{lkp_str_key}'" )
        ### Since the file `backend/lambda_layer/lambda_layer_hashes.py` was updated -by- this CDK-synth-execution (happened within `cdk_lambda_layers_app.py`), we need to DYNAMICALLY reload it.
        dyn_reloaded_module = importlib.reload(backend.lambda_layer.lambda_layer_hashes)
        lkp_obj = dyn_reloaded_module.lambda_layer_hashes.get( tier )
        lkp_lyr :dict[str, str] = lkp_obj.get( lkp_str_key ) if lkp_obj else None
        print( json.dumps(lkp_lyr, indent=4) )
        lkp_lyr_arn  = lkp_lyr.get('arn') if lkp_lyr else None
        lkp_lyr_hash = lkp_lyr.get('sha256_hex') if lkp_lyr else None

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
            print( f"Lookup 𝜆-layer for layer_id ='{layer_id}' and cpu_arch_str= '{cpu_arch_str}' returned: '{myasset_sha256_hash}'" )
            pass
            ### we "pass" and proceed with the fact that `my_lambdalayer_asset` === None.

        ### -------------------------------------
        if myasset_sha256_hash == None:
            myasset_sha256_hash  = LambdaLayerUtility.gen_sha256_hash_for_layer( layer_fldr_path = layer_fldr_path )
            print( f"Pipfile/requirements.txt sha256_hash = '{myasset_sha256_hash}' for layer_fldr_path = '{layer_fldr_path}'" )

        ### Detect of anything has changed with this Lambda-Layer (by comparing HASH from deployed-layer with above `myasset_sha256_hash`)
        if lkp_lyr_hash and myasset_sha256_hash and lkp_lyr_hash == myasset_sha256_hash:
            print( f"Lambda-Layer '{layer_id}' with CPU-Arch '{cpu_arch_str}' is UNCHANGED.  Skipping re-building the Lambda-Layer." )

            ### ! Attention ! This from_layer_version_attribute() invocation uses "common" stack as Scope.
            ### So, this "my_lambda_layerversion" will NOT work in another stack!!!!!!!!
            # my_lambda_layerversion = aws_lambda.LayerVersion.from_layer_version_attributes( scope = self,
            #     id = f"lkp-layer-{layer_id}-{cpu_arch_str}",
            #     layer_version_arn = lkp_lyr_arn,
            # )

            return

        ### -------------------------------------
        ### This means .. the Layer needs to be RE-built and RE-deployed !!!
        ### SOMETHING HAS CHANGED re: this 𝜆-Layer.  We must cdk-build + deploy a NEW VERSION of this 𝜆-LAYER.
        print( f"Lambda-Layer '{layer_id}' with CPU-Arch '{cpu_arch_str}' has CHANGED!!!  Old hash ='{lkp_lyr_hash}' --versus-- new hash = '{myasset_sha256_hash}'" )

        if layer.builder_cmd:
            ### SCENARIO: if the `layer.lambda_layer_fldr` contains a `Makefile`, then simply run a shell to execute `make`, and then set my_lambdalayer_asset to the CDK-Asset pointed to the file "{layer.lambda_layer_fldr}/build/layer.zip" file
            ###           or .. if the layer is built with a unique-shell command
            pass
        else:
            ### SCENARIO: Else, we assume there's (instead) a `Pipfile` that will be used to create a Lambda-Layer Zip-file
            # if the "Pipfile" modified-timestamp is more recent than that of "Pipefile.lock" throw an exception
            FSUtils.assert_not_newer_than( myfile=pathlib.Path(f"{layer_fldr_path}/Pipfile"),         newer_than_this=pathlib.Path(f"{layer_fldr_path}/Pipfile.lock"),     ignore_missing_files=False )
            FSUtils.assert_not_newer_than( myfile=pathlib.Path(f"{layer_fldr_path}/requirements.in"), newer_than_this=pathlib.Path(f"{layer_fldr_path}/requirements.txt"), ignore_missing_files=True )

        if not my_lambdalayer_asset:
            if layer.builder_cmd:
                ### SCENARIO: if the `layer.lambda_layer_fldr` contains a `Makefile`, then simply run a shell to execute `make`, and then set my_lambdalayer_asset to the CDK-Asset pointed to the file "{layer.lambda_layer_fldr}/build/layer.zip" file
                ###           or .. if the layer is built with a unique-shell command
                process = subprocess.run(
                    args = layer.builder_cmd,
                    cwd = layer.lambda_layer_fldr,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                my_lambdalayer_asset = aws_lambda.AssetCode.from_asset( str(layer.lambda_layer_fldr / "build" / layer.lambda_layer_zipfilename) );
            else:
                ### SCENARIO: Else, we assume there's (instead) a `Pipfile` that will be used to create a Lambda-Layer Zip-file
                util = LambdaLayerUtility(
                    lambda_layer_id = layer.lambda_layer_id,
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
                asset_sha256_hash = myasset_sha256_hash,
            )
            print( '.'*120, '\n' )

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
            removal_policy = RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
        )

        LambdaConfigs.cache_lambda_layer(
            layer_simple_name = layer_id,
            cpu_arch_str = cpu_arch_str,
            stk_containing_layers = this_stk,
            layer = my_lambda_layerversion,
            asset_sha256_hash = myasset_sha256_hash,
        )
        print( '_'*120 )

        print( "done" )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### EoF
