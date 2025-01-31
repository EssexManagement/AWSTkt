### This is an alternate to the "standard CDK's"  `app.py`
###
### To be used as:
###     npx cdk synth --app "python3 cdk_pipelines_app.py" -o cdk.out --quiet   \
###                     -c tier=${TIER} -c git_repo=${GITHUB_REPOSITORY}    \
###                     --profile ${AWSPROFILE} --region ${AWSREGION}

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
from cdk_utils.CloudFormation_util import add_tags
import cdk_utils.CdkDotJson_util

from cdk_app.pipeline_stack import AwsTktPipelineStack

### ..............................................................................................

app = App()

tier :str = app.node.try_get_context("tier")
git_branch :str = constants.get_git_branch( tier=tier )
aws_env :str = constants.get_aws_env( tier=tier )
print( f"tier = '{tier}' within "+ __file__ )
print( f"git_branch = '{git_branch}' within "+ __file__ )
print( f"aws_env = '{aws_env}' within "+ __file__ )
if not tier or tier.lower().strip() == "":
    print( f"!! ERROR !! tier is EMPTY == '{tier}'.  Pass in proper value via CDK's CLI-argument '--context tier=\"dev\"' !!!!!!!!" )
    sys.exit(31)
git_src_code_config , _ , git_commit_hash, pipeline_source_gitbranch = cdk_utils.CdkDotJson_util.lkp_cdk_json(
                                                            cdk_scope = app, ### This stack
                                                            tier = tier,
                                                            aws_env = aws_env)
print( f"git_commit_hash='{git_commit_hash}' within "+__file__ )

env = Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    # account=pipeline_account["account_id"],
    # region=pipeline_account["region"]
)

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
### EoF
