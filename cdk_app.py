#!/usr/bin/env python3
import sys
import os
import pathlib
import platform
from aws_cdk import (
    App,
    Aspects,
    Environment,
    Tags,
    Stack,
)

from cdk_nag import (
    AwsSolutionsChecks,
    HIPAASecurityChecks,
    NIST80053R5Checks,
    NagSuppressions,
    NagPack,
)

from cdk_utils.CloudFormation_util import add_tags

from cdk_app.AllStacks import Gen_AllApplicationStacks

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CdkDotJson_util

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

### ...............................

aws_profile = app.node.try_get_context( 'AWSPROFILE' )
### detect if running on macos/windows LAPTOP --versus-- running inside AWS-CodeBuild
if platform.system() == 'Darwin' or platform.system() == "Windows":
    if aws_profile is None:
        print( f"!! ERROR !! '-c AWSPROFILE=...'  commandline-argument is missing.  Assuming this is running INSIDE AWS-CodeBuild!❌" )
        sys.exit( 5 )

### ...............................

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

### ..............................................................................................

#__ LAMBDA_LAYER_HASHES_LOCALFILEPATH = "backend/lambda_layer/lambda_layer_hashes.py"
### Avoid hardcoding (as in above line)!!! Instead do as follows.
import backend.lambda_layer.lambda_layer_hashes as lambda_layer_hashes_module
LAMBDA_LAYER_HASHES_LOCALFILEPATH = lambda_layer_hashes_module.__file__
from backend.lambda_layer.bin.get_lambda_layer_hashes import GetHashesForLambdaLayers

### Dynamically update the code in the file `backend/lambda_layer/lambda_layer_hashes.py` (with the latest sha256-hashes downloaded from AWS)
GetHashesForLambdaLayers(
    appl_name = constants.CDK_APP_NAME,
    aws_profile = aws_profile, ### Note: when running inside CodeBuild, `awsprofile` -MUST- be None.
    tier = tier,
    file_to_save_hashes_into = pathlib.Path( LAMBDA_LAYER_HASHES_LOCALFILEPATH ),
    # purpose = THIS_SCRIPT_DATA,
    debug = False,
)
# Dump the contents of the file `backend/lambda_layer/lambda_layer_hashes.py` (for debugging purposes)
with open( LAMBDA_LAYER_HASHES_LOCALFILEPATH, 'r' ) as f:
    print( f.read() )

### ..............................................................................................

### ----- following code should be __SIMILAR__ (NOT identical)  to the lines 102-110 of `deployment.py`
all_stks = Gen_AllApplicationStacks(
    app   = app,
    id_     = f"{constants.CDK_APP_NAME}-{constants.CDK_COMPONENT_NAME}-{tier}",
    stack_prefix = f"{constants.CDK_APP_NAME}-{constants.CDK_COMPONENT_NAME}-{tier}",
    tier    = tier,
    aws_env = aws_env,
    git_branch = git_branch,
    env = env,  ### kwargs !!!
)

### -----------------------------------

add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### Must precede `synth()` invocation.
### Use cdk-nag, to check CloudFormation: https://github.com/cdklabs/cdk-nag/blob/HEAD/RULES.md
# Aspects.of(app).add(AwsSolutionsChecks(verbose=False))
# Aspects.of(app).add(HIPAASecurityChecks(verbose=True))
# Aspects.of(app).add(NIST80053R5Checks(verbose=True))
# NagSuppressions.add_resource_suppressions(
#     construct = app.stateless_stack.api_construct,
#     suppressions = [
#         {   "id": "AwsSolutions-APIG3", "reason": "API Gateway is not associated with AWS WAFv2 web ACL, due to Payload-limitations", }
#     ],
#     apply_to_children = True
# )
### -------------------------------
# ### Suppress: [Error at /FACT-backend-pipeline-sarma/FACT-backend-sarma_Appln_CDKSynthDeploy-arm64-CodeBuild-arm64/Role/DefaultPolicy/Resource] AwsSolutions-IAM5[Resource::arn:<AWS::Partition>:ec2:us-east-1:127516845550:network-interface/*]: The IAM entity contains wildcard permissions and does not have a cdk-nag rule suppression with evidence for those permission.
# NagSuppressions.add_resource_suppressions(
#     construct = app.stateless_stack.api_construct,
#     suppressions = [{
#         'id': 'AwsSolutions-IAM5',
#         'reason': 'CodeBuild requires network interface permissions to run in VPC. This is AWS managed policy permission.',
#         'appliesTo': ['Resource::arn:<AWS::Partition>:ec2:us-east-1:127516845550:network-interface/*']
#     }],
#     apply_to_children = True,
# )


app.synth()

### -------------------------------

### Must -FOLLOW- `synth()` invocation.
### Verify CloudFormation generated by various constructs

# Backend Constructs
# from backend.infra.cdk_tests.test_cdk_backend_stk import test_backend_cdk_synth
# test_backend_cdk_synth(app)

# ETL constructs
# from backend.infrastructure.cdk_tests.test_cdk_etl_stk import test_etl_cdk_synth
# test_etl_cdk_synth(app)

# QuickSight construct
# ..

### EoF
