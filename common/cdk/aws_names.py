import constants

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

""" Supports Standardized naming for ANY AWS-Resource.  See also `gen_awsresource_name()` """
def gen_awsresource_name_prefix(
    tier :str,
    cdk_component_name :str = constants.CDK_COMPONENT_NAME,
) -> str:
    return f"{constants.CDK_APP_NAME}-{cdk_component_name}-{tier}"

### ----------------------------------------------------------------
""" Standardized naming for ANY AWS-Resource.
    This relies on `gen_awsresource_name_PREFIX()`, which is also defined in the same python-module.
"""
def gen_awsresource_name(
    tier :str,
    cdk_component_name :str,
    simple_resource_name :str,
) -> str:
    prefix = gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )
    return f"{prefix}-{simple_resource_name}"


### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

### The `dev` environment's VPC is shared by DEVELOPER-environments also.
# SHARED_VPC_NAME = f"{CDK_APP_NAME}-{CDK_COMPONENT_NAME}-pipeline-dev/{CDK_APP_NAME}-{CDK_COMPONENT_NAME}-dev/Stateful/vpc_db/VPC"
def get_vpc_name( tier :str ) -> str:
    if tier not in constants.STD_TIERS:
        tier = "dev"
    return f"{gen_awsresource_name_prefix(tier)}/Stateful/vpc-only/VPC"
    # return f"{gen_awsresource_name_prefix(tier)}/{gen_awsresource_name_prefix(tier)}/Stateful/vpc_db/VPC"

def get_subnet_name( tier :str, simple_subnet_name :str ) -> str:
    if tier not in constants.STD_TIERS:
        tier = "dev"
    return f"{gen_awsresource_name_prefix(tier)}-{simple_subnet_name}"
    # return f"{gen_awsresource_name_prefix(tier)}/{gen_awsresource_name_prefix(tier)}/Stateful/vpc_db/VPC"

### ----------------------------------------------------------------
""" Standardized naming for Lambdas """
def gen_lambda_name( tier :str, simple_lambda_name :str ) -> str:
    return f"{gen_awsresource_name_prefix(tier)}-{simple_lambda_name}"

### ----------------------------------------------------------------
""" Standardized naming for BUCKETS """
def gen_bucket_name( tier :str, simple_bucket_name :str ) -> str:
    return f"{constants.ENTERPRISE_NAME}-{gen_awsresource_name_prefix(tier)}-{simple_bucket_name}".lower()


### ----------------------------------------------------------------
""" Standardized naming for dynamo tables """
def gen_dynamo_table_name( tier :str, simple_table_name :str ) -> str:
    return f"{constants.ENTERPRISE_NAME}-{gen_awsresource_name_prefix(tier)}-{simple_table_name}".lower()


### ----------------------------------------------------------------

""" Since Lambda-Layers need to be the 1st things created, so that any stack with any lambda can take advantage of such layers..
    .. and since we do NOT want Stack-output/references between the "common-stack" (that creates the layers) with the various OTHER stacks ..
    .. the best way is to have proper naming convention for the Lambda-Layers.

    param # 1 tier :str - dev|test|int|uat|stage|prod
    param # 2 simple_commonstack_name :str - Typically `CommonAWSRrcs` (without the AppName or tier)
    param # 3 simple_lambdalayer_name :str - The simplest-name of the layer.   No-Chip-architecture in the name!!
            Example: `psycopg2` and `psycopg-pandas`
    param # 4 cpu_arch_str :str - 'arm64'|'amd64'
"""
def gen_common_lambdalayer_name(
    tier :str,
    simple_commonstack_name :str,
    simple_lambdalayer_name :str,
    cpu_arch_str :str,
    component_name :str = constants.CDK_COMPONENT_NAME,
) -> str:
    return f"{constants.CDK_APP_NAME}-{component_name}-{tier}_{simple_commonstack_name}_{simple_lambdalayer_name}_{cpu_arch_str}"


def gen_lambdalayer_name(
    tier :str,
    simple_lambdalayer_name :str,
    cpu_arch_str :str,
    component_name :str = constants.CDK_COMPONENT_NAME,
) -> str:
    return f"{constants.CDK_APP_NAME}-{component_name}-{tier}_{simple_lambdalayer_name}_{cpu_arch_str}"

### -----------------------------------
    ###  No !!! We cannot use $LATEST as the suffix for a Lambda Layer ARN.
    ###  When working with Lambda Layers, you must specify an explicit version number in the ARN.
    ###  Each time you publish a new layer version, it gets assigned a sequential-version#, and ..
    ###  .. you --MUST-- reference that specific version number. [2]
    ###
    ### Resource handler returned message: "1 validation error detected:
    ### Value '[arn:aws:lambda:us-east-1:127516845550:layer:FACT-backend-dev-CommonAWSRrcs_psycopg2_arm64,
    ###         arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension-Arm64:20]'
    ### at 'layers' failed to satisfy constraint: Member must satisfy constraint:
    ### [   Member must have length less than or equal to 2048,
    ###     Member must have length greater than or equal to 1,
    ###     Member must satisfy regular expression pattern: (arn:(aws[a-zA-Z-]*)?:lambda:[a-z]{2}((-gov)|(-iso([a-z]?)))?-[a-z]+-\d{1}:\d{12}:layer:[a-zA-Z0-9-_]+:[0-9]+)
    ###         |(arn:[a-zA-Z0-9-]+:lambda:::awslayer:[a-zA-Z0-9-_]+) <--- Do NOT use this ARN-format (REF: https://github.com/awsdocs/aws-lambda-developer-guide/pull/155#issuecomment-614973379)
    ###     Member must not be null
    ### ]"
# def gen_lambdalayer_arn( stk :Stack, fullname :str, ) -> str:
#     return f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer:{fullname}" <--- does NOT work without Version#

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

""" reverses what the above utility functions do! """
def extract_simple_resource_name(
    tier :str,
    resource_name :str,
) -> str:
    retstr = resource_name
    retstr = retstr.replace(f"{constants.ENTERPRISE_NAME}-", "")
    retstr = retstr.replace(f"{constants.HUMAN_FRIENDLY_APP_NAME}-", "")
    retstr = retstr.replace(f"{constants.CDK_APP_NAME}-", "")
    retstr = retstr.replace(f"{constants.CDK_COMPONENT_NAME}-", "")
    retstr = retstr.replace(f"-pipeline", "")
    retstr = retstr.replace(f"{tier}-", "")
    retstr = retstr.replace(f"-{tier}", "")
    return retstr

### ===============================================================================================

### EoF
