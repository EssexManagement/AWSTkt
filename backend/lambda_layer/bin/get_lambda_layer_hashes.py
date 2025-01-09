import sys
import boto3
import os
import pathlib
import json
import time
import regex
from typing import Sequence, List
from datetime import datetime, timedelta
import traceback

from aws_cdk import (
    aws_lambda,
)

from backend.lambda_layer.bin.generic_aws_cli_script import ( GenericAWSCLIScript )
import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import add_tags, get_cpu_arch_as_str

from backend.common_aws_resources_stack import LAYER_MODULES

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

THIS_SCRIPT_DATA = "LambdaLayers"
DEBUG = False

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class GetHashesForLambdaLayers(GenericAWSCLIScript):

    def __init__(self,
        appl_name :str,
        tier :str,
        file_to_save_hashes_into :pathlib.Path,
        purpose :str = THIS_SCRIPT_DATA,
        debug :bool = False,
    ) -> None:
        """ Use boto3 to lookup all Lambda-Layers that belong to this constants.CDK_APP_NAME.
            Then get the description-field of each Lambda-Layer (which should be the HASH for the zip-file inside it)
            Save all these SHA-256 HEX hashes into a file
        """
        super().__init__(
            appl_name=appl_name,
            purpose=purpose,
            debug=debug,
        )

        lambdalayer_regex = regex.regex.Regex( aws_names.gen_awsresource_name_prefix( tier ) + '.*' )
        print( f"lambdalayer_regex: '{lambdalayer_regex}'" )

        cpu_arch_list :List[aws_lambda.Architecture] = constants_cdk.CPU_ARCH_LIST
        layer_modules_list :list[any] = LAYER_MODULES
        app_specific_lambda_layer_names :list[str] = []
        app_specific_lambda_layer_arns  :list[str] = []
        app_specific_lambda_layer_hashes:list[str] = []

        for cpu_arch in cpu_arch_list:
            for layer in layer_modules_list:
                cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
                layer_id = layer.LAMBDA_LAYER_ID
                layer_version_name = aws_names.gen_lambdalayer_name(
                    tier = tier,
                    simple_lambdalayer_name = layer_id,
                    cpu_arch_str = cpu_arch_str )
                print( f"\tWill be looking for a DEPLOYED-layer named '{layer_version_name}'.." )
                app_specific_lambda_layer_names.append( layer_version_name )

        lambda_client = self.session.client("lambda")

        layers_list = self.awsapi_invoker.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'lambda',
            api_method_name = "list_layers",
            response_key = 'Layers',
            json_output_filepath = self.json_output_filepath,
            additional_params={},
            # additional_params={ "StackStatusFilter": ALL_ACTIVE_STACK_STATUSES },
            cache_no_older_than = 1, ### Override the value for 'self.cache_no_older_than' .. as stacks frequently change every-day!
        )
        if self.debug > 1: print(layers_list)
        sample_boto3_response = { 'NextMarker': 'string',
            'Layers': [{
                'LayerName': 'string',
                'LayerArn': 'string',
                'LatestMatchingVersion': {
                    'LayerVersionArn': 'string',
                    'Version': 123,
                    'Description': 'string',
                    'CreatedDate': 'string',
                    'CompatibleRuntimes': [ "'nodejs'|'nodejs4.3'|'nodejs6.10'|'nodejs8.10'|'nodejs10.x'|'nodejs12.x'|'nodejs14.x'|'nodejs16.x'|'java8'|'java8.al2'|'java11'|'python2.7'|'python3.6'|'python3.7'|'python3.8'|'python3.9'|'dotnetcore1.0'|'dotnetcore2.0'|'dotnetcore2.1'|'dotnetcore3.1'|'dotnet6'|'dotnet8'|'nodejs4.3-edge'|'go1.x'|'ruby2.5'|'ruby2.7'|'provided'|'provided.al2'|'nodejs18.x'|'python3.10'|'java17'|'ruby3.2'|'ruby3.3'|'python3.11'|'nodejs20.x'|'provided.al2023'|'python3.12'|'java21'|'python3.13'|'nodejs22.x'", ],
                    'LicenseInfo': 'string',
                    'CompatibleArchitectures': [ "'x86_64'|'arm64'", ]
                }
            }]
        }

        for lyr in layers_list:
            lyr_nm = lyr['LayerName']
            lyr_arn = lyr['LayerArn']
            # lyr_nm = lyr.split(':')[-2]
            print( '.', end="", flush=True)
            if self.debug > 1: print(lyr_nm +' : '+ lyr_arn, flush=True)
            if regex.match( pattern=lambdalayer_regex, string=lyr_nm ):
                lyr_ver = lyr['LatestMatchingVersion']['Version']
                lyr_ver_arn = lyr['LatestMatchingVersion']['LayerVersionArn']
                # lyr_ver = lyr.split(':')[-1]
                if 'Description' in lyr['LatestMatchingVersion']:
                    lyr_descr = lyr['LatestMatchingVersion']['Description']
                    if self.debug > 2: print(lyr_descr)
                else:
                    print( f"\n!! ERROR !! No Description found for {lyr_nm} !!❌")
                    print(json.dumps(lyr,indent=4))
                    continue
                    sys.exit(67)
                lyr_sha256_hex = lyr_descr
                print( '>', end="", flush=True)
                # time.sleep(15)
                if lyr_nm in app_specific_lambda_layer_names:
                    print( f"✅ {lyr_nm} : {lyr_ver_arn}" )
                    app_specific_lambda_layer_arns.append( lyr_ver_arn )
                    app_specific_lambda_layer_hashes.append( lyr_sha256_hex )

        if len(app_specific_lambda_layer_arns) <= 0:
            print( f"\n\n!! ERROR !! No Lambda-Layers found for {lambdalayer_regex} !!❌❌❌\n")
            sys.exit(68)

        # write the lambda-layers details to a file
        with open(file_to_save_hashes_into, 'w') as f:
            w_ = '!'*25; w1 = f"# {w_} WARNING  {w_}\n"; w2 = f"# {w_} do --NOT-- edit this file  {w_}\n";
            f.write( w1 + w2 + w1 + w2 )
            f.write( f"\n#This file is autogenerated by {__file__}\n" )
            f.write( f"\n#This file -WAS- autogenerated on {constants_cdk.localized_now}\n\n" )
            f.write(  "lambda_layer_hashes :dict[str, dict[str, str]] = {\n" )
            first_item = False
            for name, arn, hsh in zip(app_specific_lambda_layer_names, app_specific_lambda_layer_arns,app_specific_lambda_layer_hashes):
                f.write( f'    "{name}" : {{ "arn" : "{arn}", "sha256_hex" : "{hsh}" }},\n' )
            f.write( '}\n\n' + w1 + w2 + w1 + w2 )
            f.close()

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

# if invoked via cli
if __name__ == "__main__":
    if len(sys.argv) >= 4:
        tier = sys.argv[2]
        file_to_save_hashes_into = sys.argv[3]
        scr = GetHashesForLambdaLayers(
            appl_name=constants.CDK_APP_NAME,
            tier=tier,
            purpose=THIS_SCRIPT_DATA,
            file_to_save_hashes_into = file_to_save_hashes_into,
            debug=DEBUG,
        )
    else:
        print( f"Usage:   python {sys.argv[0]} <AWS_PROFILE> <TIER> <file-to-save-hashes-into>" )
        print( f"EXAMPLE: python {sys.argv[0]} FACT  dev  lambda_layer_hashes.py" )

# EoScript
