from constructs import Construct

from aws_cdk import (
    Stack,
    Tags,
    aws_lambda,
    aws_ec2,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names

### ---------------------------------------------------------------------------------------------------

""" ENUM -to-> str
    Standardizes all string-values to "arm64" & "amd64" (Skipping "x86_64")
    Param: cpu_arch :aws_lambda.Architecture
"""
def get_cpu_arch_as_str(cpu_arch :aws_lambda.Architecture) -> str:
    match cpu_arch.name:
        case aws_lambda.Architecture.ARM_64.name: return "arm64"
        case aws_lambda.Architecture.X86_64.name: return "amd64"
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch.name}'")

### ---------------
""" str -to-> ENUM
    Valid input values are: "arm64", "amd64", "x86_64"
    Returns aws_lambda.Architecture
"""
def get_cpu_arch_enum(cpu_arch_str :str) -> aws_lambda.Architecture:
    match cpu_arch_str:
        case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:    return aws_lambda.Architecture.ARM_64
        case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:    return aws_lambda.Architecture.X86_64
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")

### ---------------
""" str -to-> "linux/??" docker-compliant-platform.
    Valid input values are: "arm64", "amd64", "x86_64"
    Returns "linux/???" as appropriate
"""
def get_docker_platform(cpu_arch_str :str) -> str:
    match cpu_arch_str:
        case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:    return "linux/arm64"
        case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:    return "linux/amd64"
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")

### ---------------
""" AWS Official Container-images for PYTHON-Lambda-runtime.
    !! WARNING !!
            $ docker run --rm -it public.ecr.aws/lambda/python  --command bash
            ERROR! entrypoint requires the handler name to be the first argument
    str -to-> "public.ecr.aws/lambda/python:3.12-{CPU}}" AWS-official Lambda-runtime-Container-images.
    Valid input values are: "arm64", "amd64", "x86_64"
    Returns "linux/???" as appropriate
"""
def get_awslambda_runtime_containerimage_uri(cpu_arch_str :str) -> str:
    match cpu_arch_str:
        ## Return a string like:->  public.ecr.aws/lambda/python:3.12-x86_64
        case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:    return f"public.ecr.aws/lambda/python:{constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR}-arm64"
        case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:    return f"public.ecr.aws/lambda/python:{constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR}-x86_64"
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")

### ---------------
""" 3rd party / Docker
    !! Inside CodeBuild -- ERROR:
    !! docker: Error response from daemon: toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit.
    ATTENTION: This is NOT CPU=-specific image !!!!!
    str -to-> "public.ecr.aws/docker/library/python:3.12"
    Valid input values are: "arm64", "amd64", "x86_64"
    Returns "linux/???" as appropriate
"""
def get_python_runtime_containerimage_uri(cpu_arch_str :str) -> str:
    match cpu_arch_str:
        case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:    return f"public.ecr.aws/docker/library/python:{constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR}"
        case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:    return f"public.ecr.aws/docker/library/python:{constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR}"
        ### Inside CodeBuild -- ERROR:
        ### docker: Error response from daemon: toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit.
        # case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:    return "arm64v8/python" ### https://hub.docker.com/r/arm64v8/python/
        # case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:    return "amd64/python"   ### https://hub.docker.com/r/amd64/python/
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")
    ### return f"public.ecr.aws/docker/library/python:{constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR}"

### ---------------------------------------------------------------------------------------------------

def get_vpc_privatesubnet_type(
    vpc :aws_ec2.IVpc,
    # tier :str,
    # aws_env :str,
) -> aws_ec2.SubnetType:
    """ If any ISOLATED subnets exist, return aws_ec2.SubnetType.PRIVATE_ISOLATED
        Else, if any PRIVATE subnets exist, return aws_ec2.SubnetType.PRIVATE_WITH_EGRESS
        Else, throw an error
    """

    if len( vpc.isolated_subnets ):
        return aws_ec2.SubnetType.PRIVATE_ISOLATED
    if len( vpc.private_subnets ):
        return aws_ec2.SubnetType.PRIVATE_WITH_EGRESS
    raise f"ERROR !! ❌❌❌ Vpc '{vpc.vpc_id if vpc else None}' has --NEITHER-- Private Nor Isolated Subnets!!"

### ---------------------------------------------------------------------------------------------------

def add_tags( a_construct :Construct, tier :str, aws_env :str, git_branch :str, component_name :str = constants.CDK_BACKEND_COMPONENT_NAME ) -> None:
    effective_tier = tier if tier in constants.STD_TIERS else "dev"
    gr = a_construct.node.try_get_context("git_repo")
    ver = a_construct.node.try_get_context("git-source")
    support_email = constants.DefaultITSupportEmailAddress
    # support_email=a_construct.node.try_get_context("support-email")[tier]
    generic_rsrc_name = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=component_name )
    if ver: ver=ver["git_commit_hashes"]
    if ver and tier in ver:
        ver=ver[tier]
    else:
        ver="N/A"
    if not ver: ver="N/A"
    Tags.of(a_construct).add(key="PRODUCT", value=constants.HUMAN_FRIENDLY_APP_NAME.lower())
    Tags.of(a_construct).add(key="Project", value=constants.HUMAN_FRIENDLY_APP_NAME.lower())            ### CBIIT
    Tags.of(a_construct).add(key="ApplicationName", value=constants.HUMAN_FRIENDLY_APP_NAME.lower())    ### CBIIT
    Tags.of(a_construct).add(key="ENVIRONMENT",  value=effective_tier.lower())
    Tags.of(a_construct).add(key="EnvironmentTier",  value=effective_tier.upper())                      ### CBIIT
    ### `Runtime` CBIIT-Tag is only for EC2-based instances (incl. EC2-based-RDS)
    Tags.of(a_construct).add(key="VERSION", value = ver)
    Tags.of(a_construct).add(key="application", value=constants.CDK_APP_NAME)
    Tags.of(a_construct).add(key="component",   value=component_name)
    Tags.of(a_construct).add(key="ResourceFunction",   value=component_name)                            ### CBIIT
    Tags.of(a_construct).add(key="tier",  value=tier)
    Tags.of(a_construct).add(key="ResourceName",  value=generic_rsrc_name)                              ### CBIIT
    Tags.of(a_construct).add(key="aws_env",  value=aws_env)
    Tags.of(a_construct).add(key="git_branch", value=git_branch)
    Tags.of(a_construct).add(key="CreatedBy", value=support_email)                                  ### CBIIT
    if tier in constants.UPPER_TIERS:
        Tags.of(a_construct).add(key="BUILD", value=constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR)
        Tags.of(a_construct).add(key="CreateDate", value=constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR)     ### CBIIT
    if gr:
        Tags.of(a_construct).add(key="SOURCE", value = gr)
        Tags.of(a_construct).add(key="repo",   value = gr)

### ------------------------------

def get_tags_as_json( tier :str, aws_env :str, git_branch :str, component_name :str = constants.CDK_BACKEND_COMPONENT_NAME ) -> None:
    effective_tier = tier if tier in constants.STD_TIERS else "dev"
    rsrc_name = aws_names.gen_awsresource_name( tier=tier, simple_resource_name="VPCEndPt", cdk_component_name=component_name )
    retdict = {
        "PRODUCT": constants.HUMAN_FRIENDLY_APP_NAME.lower(),
        "Project": constants.HUMAN_FRIENDLY_APP_NAME.lower(),           ### CBIIT
        "ApplicationName": constants.HUMAN_FRIENDLY_APP_NAME.lower(),   ### CBIIT
        "ENVIRONMENT":  effective_tier.lower(),
        "EnvironmentTier":  effective_tier.lower(),                     ### CBIIT
        ### `Runtime` CBIIT-Tag is only for EC2-based instances (incl. EC2-based-RDS)
        "VERSION": "Not-defined-VPC-EndPoints",
        "application": constants.CDK_APP_NAME,
        "component":   component_name,
        "ResourceFunction":   component_name,                           ### CBIIT
        "tier":  tier,
        "ResourceName":  rsrc_name,                                     ### CBIIT
        "aws_env":  aws_env,
        "git_branch": git_branch,
        # "BUILD": constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR if tier == constants.PROD_TIER or tier == constants.UAT_TIER else None,
    }
    if tier in constants.STD_TIERS:
        retdict["BUILD"] =constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR
        retdict["CreateDate"] =constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR ### CBIIT
        retdict["CreatedBy"] =constants.DefaultITSupportEmailAddress    ### CBIIT
    return retdict

### ------------------------------

def get_tags_as_array( tier :str, aws_env :str, git_branch :str, component_name :str = constants.CDK_BACKEND_COMPONENT_NAME ) -> list[dict[str,str]]:
    effective_tier = tier if tier in constants.STD_TIERS else "dev"
    rsrc_name = aws_names.gen_awsresource_name( tier=tier, simple_resource_name="VPCEndPt", cdk_component_name=component_name )
    retlist = [
        { "Key": "PRODUCT", "Value": constants.HUMAN_FRIENDLY_APP_NAME.lower() },
        { "Key": "Project", "Value": constants.HUMAN_FRIENDLY_APP_NAME.lower() },   ### CBIIT
        { "Key": "ApplicationName", "Value": constants.HUMAN_FRIENDLY_APP_NAME.lower() },   ### CBIIT
        { "Key": "ENVIRONMENT", "Value": effective_tier.lower() },
        { "Key": "EnvironmentTier", "Value": effective_tier.lower() },  ### CBIIT
        { "Key": "VERSION", "Value": "Not-defined-VPC-EndPoints" },
        { "Key": "application", "Value": constants.CDK_APP_NAME },
        { "Key": "component", "Value":   component_name },
        { "Key": "ResourceFunction", "Value":   component_name },       ### CBIIT
        { "Key": "tier", "Value": tier },
        { "Key": "ResourceName", "Value": rsrc_name },                  ### CBIIT
        { "Key": "aws_env", "Value":  aws_env },
        { "Key": "git_branch", "Value": git_branch },
        # { "Key": "BUILD", "Value": constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR if tier == constants.PROD_TIER or tier == constants.UAT_TIER else None },
    ]
    if tier in constants.STD_TIERS:
        retlist.append( { "Key": "BUILD", "Value": constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR } )
        retlist.append( { "Key": "CreateDate", "Value": constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR } )   ### CBIIT
        retlist.append( { "Key": "CreatedBy", "Value": constants.DefaultITSupportEmailAddress } )       ### CBIIT
    return retlist

### ---------------------------------------------------------------------------------------------------

### https://github.com/awsdocs/aws-cloudformation-user-guide/blob/c03a45977c5a506e09a22dbe05ff980bec79b805/doc_source/aws-properties-rds-database-instance.md#cfn-rds-dbinstance-masteruserpassword
def get_RDS_password_exclude_pattern_adminuser() -> str:
    ### Can -NOT- contain forward-slash, single-quote, dbl-quote, @-sign
    # exclude_characters="~`!#$%^&*-_+={}[]()|\\:;'”’\"<>.,?"
    exclude_characters="~`@#$%^&*+={}[]()|\\:;'\"”<>,/? "
    ### allowed-chars: '-', '_' '.' '!'
    return exclude_characters

def get_RDS_password_exclude_pattern_alphanum_only() -> str:
    # exclude_characters="~`!#$%^&*-_+={}[]()|\\:;'”’\"<>.,?"
    exclude_characters="~`@#$%^&*+={}[]()|\\:;'\"”<>,/? "  ### Same as for other func above
    ### allowed-chars: '-', '_' '.' '!'
    return exclude_characters

### ---------------------------------------------------------------------------------------------------

### EoF
