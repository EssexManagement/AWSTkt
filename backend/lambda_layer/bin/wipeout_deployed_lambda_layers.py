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

### ==============================================================================================

from backend.lambda_layer.layers_config import LAYER_MODULES

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
        aws_profile :str,
        tier :str,
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
            aws_profile=aws_profile,
            tier=tier,
            debug=debug,
        )
        lambda_client = self.awsapi_invoker.session.client('lambda')

        lambdalayer_regex = regex.regex.Regex( aws_names.gen_awsresource_name_prefix( tier ) + '.*' )
        print( f"lambdalayer_regex: '{lambdalayer_regex}'" )
        lambdalayer_regex = regex.compile(lambdalayer_regex)

        # List of layers
        # layers = [
        #     "AWSTkt-backend-dev_psycopg2-pandas_amd64",
        #     "AWSTkt-backend-dev_psycopg3-pandas_amd64",
        #     "AWSTkt-backend-dev_psycopg2_amd64",
        #     "AWSTkt-backend-dev_psycopg3-pandas_arm64",
        #     "AWSTkt-backend-dev_psycopg3_arm64",
        #     "AWSTkt-backend-dev_psycopg2_arm64"
        # ]

        cpu_arch_list :List[aws_lambda.Architecture] = constants_cdk.CPU_ARCH_LIST
        layer_modules_list :list[any] = LAYER_MODULES
        app_specific_lambda_layer_names :list[str] = []

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
            if lambdalayer_regex.match( string=lyr_nm ):
                if 'Description' not in lyr['LatestMatchingVersion']:
                    print( f"\n!! ERROR !! No Description found for {lyr_nm} !!❌")
                    print(json.dumps(lyr,indent=4))
                    continue
                    sys.exit(67)
                if self.debug > 1: print(json.dumps(lyr,indent=4))
                lyr_descr = lyr['LatestMatchingVersion']['Description']
                if self.debug: print( f"HASH is '{lyr_descr}'" )
                lyr_ver = lyr['LatestMatchingVersion']['Version']
                lyr_ver_arn = lyr['LatestMatchingVersion']['LayerVersionArn']
                # lyr_ver = lyr.split(':')[-1]
                lyr_sha256_hex = lyr_descr
                print( '>', end="", flush=True)
                # time.sleep(15)
                if lyr_nm in app_specific_lambda_layer_names:
                    print( f"\nDeleting {lyr_nm} : {lyr_ver_arn}", end=" .. ", flush=True )
                    resp = lambda_client.delete_layer_version(
                        LayerName = lyr_nm,
                        VersionNumber = lyr_ver,
                    )
                    print( 'done!  ')


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

# if invoked via cli
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print( f"Usage:   python {sys.argv[0]} <AWS_PROFILE> <TIER>" )
        print( f"EXAMPLE: python {sys.argv[0]} FACT  dev " )
        sys,exit(1)
    else:
        aws_profile = sys.argv[1]
        tier = sys.argv[2]
        scr = GetHashesForLambdaLayers(
            appl_name = constants.CDK_APP_NAME,
            aws_profile = aws_profile,
            tier = tier,
            purpose = THIS_SCRIPT_DATA,
            debug = DEBUG,
        )

# EoScript
