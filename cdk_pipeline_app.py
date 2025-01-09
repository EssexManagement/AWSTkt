#!/usr/bin/env python3
import os
import sys

import aws_cdk as cdk

import constants as constants
import common.cdk.aws_names as aws_names
from app_pipeline.pipeline_stack import AwsTktPipelineStack
from cdk_utils.CloudFormation_util import get_cpu_arch_enum, add_tags

### ..............................................................................................

tier = constants.DEV_TIER
aws_env = constants.DEV_TIER  ### <---- Hardcoded !!!
git_branch = constants.get_git_branch(tier)

stk_prefix = aws_names.gen_awsresource_name_prefix( tier, constants.CDK_COMPONENT_NAME )

env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
    # account=pipeline_account["account_id"],
    # region=pipeline_account["region"]
)

app = cdk.App()

HDR = " inside "+ __file__

### ..............................................................................................

# cpu_arch_str: str = os.environ.get("CPU_ARCH", None)
cpu_arch_str: str = app.node.try_get_context( 'CPU_ARCH' )
print( f"CPU_ARCH (Env-Var) = '{cpu_arch_str}' within "+ HDR )
if not cpu_arch_str:
    print( f"!! ERROR !! '-c =CPU_ARCH=x86_64|arm64'  commandline-argument is missing.  Assuming this is running INSIDE AWS-CodeBuild!❌" )
    sys.exit( 3 )
cpu_arch = get_cpu_arch_enum( cpu_arch_str )
# cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64|x86_64' string
print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )

### ..............................................................................................

AwsTktPipelineStack( scope=app,
    construct_id=f"{constants.CDK_APP_NAME}-PIPELINE",
    tier=tier,
    aws_env=constants.DEV_TIER,
    git_branch=constants.get_git_branch(tier),
)

### ..............................................................................................

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

app.synth()

### ..............................................................................................
