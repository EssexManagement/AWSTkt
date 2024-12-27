from constructs import Construct

from aws_cdk import (
    Stack,
    Tags,
    aws_lambda,
)

import constants
import common.cdk.constants_cdk as constants_cdk

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

def add_tags( a_construct :Construct, tier :str, aws_env :str, git_branch :str ) -> None:
    Tags.of(a_construct).add(key="PRODUCT", value=constants.HUMAN_FRIENDLY_APP_NAME.lower())
    Tags.of(a_construct).add(key="ENVIRONMENT",  value=tier.lower())
    Tags.of(a_construct).add(key="VERSION", value=a_construct.node.try_get_context("git-source")["git_commit_hashes"][tier])
    Tags.of(a_construct).add(key="application", value=constants.CDK_APP_NAME)
    Tags.of(a_construct).add(key="component",   value=constants.CDK_COMPONENT_NAME)
    Tags.of(a_construct).add(key="tier",  value=tier)
    Tags.of(a_construct).add(key="aws_env",  value=aws_env)
    Tags.of(a_construct).add(key="git_branch", value=git_branch)
    Tags.of(a_construct).add(key="BUILD", value=constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR)
    if a_construct.node.try_get_context("git_repo"):
        Tags.of(a_construct).add(key="SOURCE", value=a_construct.node.try_get_context("git_repo"))
        Tags.of(a_construct).add(key="repo",   value=a_construct.node.try_get_context("git_repo"))

### ---------------------------------------------------------------------------------------------------

### EoF
