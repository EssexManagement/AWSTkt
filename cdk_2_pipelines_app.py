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

from app_pipeline.pipeline  import AppDeployPipelineStack ### ./pipeline.py
from devops.pipeline        import MultiCdkSubProjectsPipelineStack
from operations.pipeline    import OperationsPipelineStack
from devops.meta_pipeline   import MetaPipelineUpdatesOtherPipelinesStack

### -------------------------------------------------------------------------------------

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
cdk_component_name=f"{constants.CDK_COMPONENT_NAME}-pipeline"
stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

stk = AppDeployPipelineStack(
    scope=app,
    stack_id=stack_id,
    tier=tier,
    aws_env=aws_env,
    git_branch=git_branch,
    env=env ### kwargs
)

add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )

### -----------------------------------
cdk_component_name=f"devops-pipeline"
stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

multstks = MultiCdkSubProjectsPipelineStack(
    scope=app,
    stack_id=stack_id,
    tier=tier,
    git_branch=git_branch,
    aws_env=aws_env,
    env=env ### kwargs
)

add_tags( a_construct=multstks, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )

### -----------------------------------
# cdk_component_name=f"operations-pipeline"
# stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

# stk = OperationsPipelineStack(
#     scope=app,
#     stack_id=stack_id,
#     tier=tier,
#     git_branch=git_branch,
#     aws_env=aws_env,
#     env=env ### kwargs
# )

# add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )

### -----------------------------------
if tier == constants.DEV_TIER or tier not in constants.STD_TIERS:
    cdk_component_name=f"meta-pipeline"
    stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )

    stk = MetaPipelineUpdatesOtherPipelinesStack(
        scope=app,
        stack_id=stack_id,
        tier=tier,
        git_branch=git_branch,
        aws_env=aws_env,
        env=env ### kwargs
    )

    add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )

### -----------------------------------

app.synth()


### EoF
