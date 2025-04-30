#!/usr/bin/env python3
import sys
import os
from aws_cdk import (
    App,
    Environment,
    Tags,
    Stack,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from cdk_utils.CloudFormation_util import add_tags

from app_pipeline.FrontendStacks import Gen_AllFrontendApplicationStacks

### -------------------------------------------------------------------------------------

app = App()

tier :str = app.node.try_get_context("tier")
git_branch :str = CdkDotJson_util.lkp_git_branch( cdk_scope=app, tier=tier )
# git_branch :str = constants.get_git_branch( tier=tier )
aws_env :str = constants_cdk.get_aws_env( tier=tier )
print( f"tier = '{tier}' within "+ __file__ )
print( f"git_branch = '{git_branch}' within "+ __file__ )
print( f"aws_env = '{aws_env}' within "+ __file__ )
if not tier or tier.lower().strip() == "":
    print( f"!! ERROR !! tier is EMPTY == '{tier}'.  Pass in proper value via CDK's CLI-argument '--context tier=\"dev\"' !!!!!!!!" )
    sys.exit(31)

# if tier in constants.STD_TIERS:
#     pipeline_account = app.node.try_get_context("aws_env")[tier]
# else:  ### developer specific tier
#     pipeline_account = app.node.try_get_context("aws_env")[ "dev" ]
# # if tier in constants.UPPER_TIERS: ### ["int", "uat", "prod"]:
# #     pipeline_account = app.node.try_get_context("aws_env")["cicd"]
# # else:
# #     pipeline_account = app.node.try_get_context("aws_env")["dev"]

env = Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    # account=pipeline_account["account_id"],
    # region=pipeline_account["region"]
)

### -----------------------------------

### ----- following code should be __SIMILAR__ (NOT identical)  to the lines 102-110 of `deployment.py`
all_stks = Gen_AllFrontendApplicationStacks(
    scope   = app,
    id_     = f"{constants.CDK_APP_NAME}-{constants.CDK_FRONTEND_COMPONENT_NAME}-{tier}",
    stack_prefix = f"{constants.CDK_APP_NAME}-{constants.CDK_FRONTEND_COMPONENT_NAME}-{tier}",
    tier    = tier,
    aws_env = aws_env,
    git_branch = git_branch,
    env = env,  ### kwargs !!!
)

### -----------------------------------

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

app.synth()

### EoF
