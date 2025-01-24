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
cdk_component_name=f"{constants.CDK_COMPONENT_NAME}-pipeline"
stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

AwsTktPipelineStack( scope=app,
    stack_id=stack_id,
    tier=tier,
    aws_env=constants.DEV_TIER,
    git_branch=constants.get_git_branch(tier),
)

### ..............................................................................................

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

app.synth()

### ..............................................................................................
