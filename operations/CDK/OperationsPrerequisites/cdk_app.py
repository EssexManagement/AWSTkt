#!/usr/bin/env python3
import os
import sys
from aws_cdk import (
    App,
    Aspects,
    Environment,
    Tags,
    Stack,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import add_tags

from src.all_stacks import OperationsPrerequisitesStack, AWSLandingZoneStack, FoundationalResourcesStack

### -------------------------------------------------------------------------------------

app = App()

tier :str = app.node.try_get_context("tier")
git_branch :str = "N/A" ### constants.get_git_branch( tier=tier )
aws_env :str = constants_cdk.get_aws_env( tier=tier )
print( f"tier = '{tier}' within "+ __file__ )
print( f"git_branch = '{git_branch}' within "+ __file__ )
print( f"aws_env = '{aws_env}' within "+ __file__ )

### -----------------------------------
if not tier or tier.lower().strip() == "":
    print( f"!! ERROR !!❌ tier is EMPTY == '{tier}'.  Pass in proper value via CDK's CLI-argument '--context tier=\"dev\"' !!!!!!!!" )
    sys.exit(31)

if tier != constants.ACCT_NONPROD and tier != constants.ACCT_PROD:
    print( f"!! ERROR !! tier NOT allowed == '{tier}'.  Allowed values are: {constants.ACCT_NONPROD} & {constants.ACCT_PROD}" )
    # print( f"!! ERROR !!❌ tier NOT allowed == '{tier}'.  Allowed values are '{constants.DEV_TIER}' and '{constants.PROD_TIER}'" )
    sys.exit(31)

### ...............................

env = Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    # account=pipeline_account["account_id"],
    # region=pipeline_account["region"]
)

### ...............................

app = App()

### ----------------------------------------------

stack_id = "FoundationalRrcs"

foundational_stk = FoundationalResourcesStack(
    app = app,
    construct_id = stack_id,
    stknm = stack_id,
    aws_env = aws_env,
    ### ----- **kwargs ------
    env = env,
)

### ...............................
stack_id = "AWSLandingZone"

aws_landingzone = AWSLandingZoneStack(
    app = app,
    construct_id = stack_id,
    stknm = stack_id,
    aws_env = aws_env,
    git_branch = git_branch,
    ### ----- **kwargs ------
    env = env,
)
aws_landingzone.add_dependency( foundational_stk )

### ----------------------------------------------

stack_id = "OperationsPrerequisites"
# cdk_component_name=f"{constants.CDK_OPERATIONS_COMPONENT_NAME}"
# cdk_component_name=f"{constants.CDK_DEVOPS_COMPONENT_NAME}-shared"
# cdk_component_name=f"{constants.CDK_DEVOPS_COMPONENT_NAME}-{tier}"
# stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )
# stack_prefix = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

ops_prereq_stk = OperationsPrerequisitesStack(
    app = app,
    construct_id = stack_id,
    stknm = stack_id,
    aws_env = aws_env,
    tier = tier,
    ### ----- **kwargs ------
    env = env,
)
ops_prereq_stk.add_dependency( foundational_stk )
ops_prereq_stk.add_dependency( aws_landingzone )

### ----------------------------------------------

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

app.synth()
