#!/usr/bin/env python3
import os
import pathlib
import time
import sys
import platform

import aws_cdk as cdk
from constructs import Construct

import constants as constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import get_cpu_arch_enum, get_cpu_arch_as_str, add_tags
from backend.common_aws_resources_stack import CommonAWSResourcesStack
from backend.AllStacks import AppStack

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

HDR = " inside "+ __file__

tier=constants.DEV_TIER
aws_env = constants.DEV_TIER  ### <---- Hardcoded !!!
git_branch = constants.get_git_branch(tier)

stk_prefix = aws_names.gen_awsresource_name_prefix( tier, constants.CDK_COMPONENT_NAME )

env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
    # account=pipeline_account["account_id"],
    # region=pipeline_account["region"]
)

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

app = cdk.App()

scope :Construct = app

""" Creates all the various Application's stacks.  This is in itself a PLAIN-Python-class!!!
"""



# cpu_arch_str: str = os.environ.get("CPU_ARCH", None)
cpu_arch_str: str = app.node.try_get_context( 'CPU_ARCH' )
print( f"CPU_ARCH (Env-Var) = '{cpu_arch_str}' within "+ HDR )
if not cpu_arch_str:
    print( f"!! ERROR !! '-c =CPU_ARCH=x86_64|arm64'  commandline-argument is missing.  Assuming this is running INSIDE AWS-CodeBuild!❌" )
    sys.exit( 3 )
cpu_arch = get_cpu_arch_enum( cpu_arch_str )
# cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64|x86_64' string
print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
if cpu_arch_str != get_cpu_arch_as_str(cpu_arch):
    print( f"!! ERROR !! Invalid value of '-c =CPU_ARCH={cpu_arch_str}'  commandline-argument!❌" )
    print( f"!! ERROR !! Valid values are: ", end="");
    c :cdk.aws_lambda.Architecture;
    for c in constants_cdk.CPU_ARCH_LIST:
        print( get_cpu_arch_as_str(c), end=", ")
    print()
    sys.exit( 4 )

aws_profile = app.node.try_get_context( 'AWSPROFILE' )
### detect if running on macos/windows LAPTOP --versus-- running inside AWS-CodeBuild
if platform.system() == 'Darwin' or platform.system() == "Windows":
    if aws_profile is None:
        print( f"!! ERROR !! '-c AWSPROFILE=...'  commandline-argument is missing.  Assuming this is running INSIDE AWS-CodeBuild!❌" )
        sys.exit( 5 )

### ..............................................................................................

#__ LAMBDA_LAYER_HASHES_LOCALFILEPATH = "backend/lambda_layer/lambda_layer_hashes.py"
### Avoid hardcoding (as in above line)!!! Instead do as follows.
import backend.lambda_layer.lambda_layer_hashes as lambda_layer_hashes_module
LAMBDA_LAYER_HASHES_LOCALFILEPATH = lambda_layer_hashes_module.__file__
from backend.lambda_layer.bin.get_lambda_layer_hashes import GetHashesForLambdaLayers

### Dynamically update the code in the file `backend/lambda_layer/lambda_layer_hashes.py` (with the latest sha256-hashes downloaded from AWS)
GetHashesForLambdaLayers(
    appl_name = constants.CDK_APP_NAME,
    aws_profile = aws_profile,
    tier = tier,
    file_to_save_hashes_into = pathlib.Path( LAMBDA_LAYER_HASHES_LOCALFILEPATH ),
    # purpose = THIS_SCRIPT_DATA,
    debug = False,
)
# Dump the contents of the file `backend/lambda_layer/lambda_layer_hashes.py` (for debugging purposes)
with open( LAMBDA_LAYER_HASHES_LOCALFILEPATH, 'r' ) as f:
    print( f.read() )

### ..............................................................................................

### Stack # 1
common_stk = CommonAWSResourcesStack(
    scope = scope,
    simple_id = f"CommonRsrc-{cpu_arch_str}",
    stk_prefix = stk_prefix,
    tier = tier,
    aws_env=aws_env,
    git_branch=git_branch,
    cpu_arch_list = [cpu_arch],   ### Once cpu-arch at a time (as one CodeBuild-instance cannot handle 2 different cpu-arch)

    env = env,  ### kwargs !!!
)

### ..............................................................................................

### Stack # 2
AppStack(
    scope = scope,
    simple_id = f"AppStk-{cpu_arch_str}",
    stk_prefix = stk_prefix,
    tier = tier,
    aws_env=aws_env,
    git_branch=git_branch,
    cpu_arch_str = cpu_arch_str,
    common_stk = common_stk,

    env = env,  ### kwargs !!!
)

### ..............................................................................................

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

app.synth()

### EoF
