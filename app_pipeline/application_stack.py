import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
)

from constructs import Construct

import constants as constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import get_cpu_arch_enum
from backend.common_aws_resources_stack import CommonAWSResourcesStack, LAYER_MODULES

class AwsTktApplicationStacks():
    """ Creates all the various Application's stacks.  This is in itself a PLAIN-Python-class!!!
    """

    def __init__(self,
        scope: Construct,
        construct_id: str,
        tier: str,
        aws_env :str,
        git_branch :str,
        **kwargs
    ) -> None:
        HDR = " AwsTktApplicationStacks()'s constructor inside "+ __file__
        # super().__init__( scope, construct_id )

        stk_prefix = aws_names.gen_awsresource_name_prefix( tier, constants.CDK_COMPONENT_NAME )

        cpu_arch_str: str = os.environ.get("CPU_ARCH", None)
        print( f"CPU_ARCH (Env-Var) = '{cpu_arch_str}' within "+ HDR )
        cpu_arch = get_cpu_arch_enum( cpu_arch_str )
        # cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64|x86_64' string
        print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )

        ### Stack # 1
        CommonAWSResourcesStack(
            scope = scope,
            id = f"{construct_id}-CommonAWSRrcs-{cpu_arch_str}", ### <-------- note!! Using the param(construct_id) to create a NEW sub-construct-id!!!
            tier = tier,
            aws_env=aws_env,
            git_branch=git_branch,
            # lambda_configs = lambda_configs,
            stk_prefix=stk_prefix,
            cpu_arch_list = [cpu_arch],   ### Once cpu-arch at a time (as one CodeBuild-instance cannot handle 2 different cpu-arch)
            # layer_modules_list = LAYER_MODULES,
            **kwargs,
        )

### EoF
