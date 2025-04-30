import pathlib
from typing import Optional, Sequence
from enum import Enum, auto, unique

from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    RemovalPolicy,
    aws_logs,
    aws_ec2,
    aws_lambda,
    aws_lambda_python_alpha,
    aws_ecr,
    aws_ecr_assets,
)

import constants
import common.cdk.aws_names as aws_names
import common.cdk.constants_cdk as constants_cdk
from cdk_utils.CloudFormation_util import get_vpc_privatesubnet_type
from cdk_utils.CloudFormation_util import get_cpu_arch_as_str
from common.cdk.standard_logging import get_log_grp, LogGroupType

### =================================================================================================

LAMBDA_INSIGHTS_VERSION: aws_lambda.LambdaInsightsVersion =  aws_lambda.LambdaInsightsVersion.VERSION_1_0_333_0
# LAMBDA_INSIGHTS_VERSION = "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:16"  ### !!! Do NOT USE. OLD.  FYI only.
### aws lambda get-layer-version-by-arn --arn arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:16  --profile ${AWSPROFILE} --region ${AWSREGION}
### This Insights LambdaLayer's ZIP-file is about 4,294,333 bytes in size.
### ... which when unzipped = 10,884 KB

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

""" If you need to pack a LOT of pypi-python-modules into a layer, choose `SMALLEST_ZIP_FILE_SLOW_COLDSTART`, which ensures -NO- `__pycache__` folders are included in zip-file (to reduce space).
    If you re -NOT- using super-large pypi-modules like `pandas`, then `LARGER_ZIP_FILE_FASTER_COLDSTART` will ensure `__pycache__` folders are retained within zip-file.
"""
@unique
class LambdaLayerOption(Enum):
    SMALLEST_ZIP_FILE_SLOW_COLDSTART = (auto()),
    LARGER_ZIP_FILE_FASTER_COLDSTART = (auto()),

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

### private

class MyException(Exception):
    pass

_DEFAULT_LAMBDA_PYTHON_RUNTIME = aws_lambda.Runtime.PYTHON_3_12

# _LAMBDA_ADOT_CONFIG: aws_lambda.AdotInstrumentationConfig = aws_lambda.AdotInstrumentationConfig(
#     layer_version=aws_lambda.AdotLayerVersion.from_python_sdk_layer_version(
#         aws_lambda.AdotLambdaLayerPythonSdkVersion.LATEST
#     ),
#     exec_wrapper=aws_lambda.AdotLambdaExecWrapper.INSTRUMENT_HANDLER,
# )

""" REF: https://aws-otel.github.io/docs/getting-started/lambda/lambda-python
    Contains OpenTelemetry Python v1.25.0
    Contains ADOT Collector v0.40.0
"""
def get_LAMBDA_OTEL_LAYER_ARN( stk :Stack, cpu_arch :aws_lambda.Architecture ) -> str:
    HDR = f" :get_LAMBDA_OTEL_LAYER_ARN() within "+ __file__
    cpu_arch_str: str = constants_cdk.get_cpu_arch_as_str( cpu_arch )
    return f"arn:{stk.partition}:lambda:{stk.region}:901920570463:layer:aws-otel-python-{cpu_arch_str}-ver-1-25-0:1"

# """ REF: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versions.html
# """
# def get_LAMBDA_INSIGHTS_LAYER_ARN(stk :Stack, cpu_arch :aws_lambda.Architecture) -> str:
#     return f"arn:{stk.partition}:lambda:{stk.region}:580247275435:layer:LambdaInsightsExtension-{cpu_arch.name}:20"

### =================================================================================================

class StandardLambda():
    """Standardizing the way Lambdas are created ACROSS the project
        Use a different DEFAULT timeout for -ALL- lambdas.
        Use a MINIMUM MemorySize for -ALL- lambdas, so that LambdaLayers can be supported.
    """

    def update_vpc( self, new_vpc_info: aws_ec2.IVpc ) -> None:
        self._vpc = new_vpc_info

    def add_sg( self, new_sg: aws_ec2.ISecurityGroup ) -> None:
        self._sg_lambda.append( new_sg)

    def update_sg( self, new_sg: aws_ec2.ISecurityGroup ) -> None:
        self._sg_lambda = [new_sg]

    def update_sgs( self, new_sgs: list[aws_ec2.ISecurityGroup] ) -> None:
        self._sg_lambda = new_sgs

    ###------------------------------------------------
    def __init__( self,
        create_within_vpc :bool,
        vpc :Optional[aws_ec2.IVpc],
        sg_lambda: Optional[list[aws_ec2.ISecurityGroup]],
        tier: str,
        min_memory :Optional[int] = None,
        default_timeout :Optional[Duration] = None,
    ) -> None:
        super().__init__()

        if create_within_vpc and vpc:
            self._vpc = vpc
            self._construct_id_suffix = self._vpc.vpc_id
        else:
            self._vpc = None
            self._construct_id_suffix = "noVPC"
        self._sg_lambda = sg_lambda
        self._tier = tier
        self.default_timeout = default_timeout
        self.min_memory = min_memory

    ###------------------------------------------------
    def _get_description(self,
        description :Optional[str],
        stk :Stack,
        lambda_name :str,
        handler :str,
        code_src :str,
    ) -> str:
        if description is None:
            # description: str = f"{stknm} {lambda_name}.{handler}"
            description: str = f"{stk.stack_name} {lambda_name}.{handler} code_src={code_src}"
        if len(description) > 251:
            description = description[:250]
            ### Error: Function description can not be longer than 256 characters but has 307 characters.
        return description

    ###------------------------------------------------
    """ One place to decide what are DEFAULT (AWS-owned) Lambda-Layers to include in all Lambdas.
        Example: All Lambdas should have OTEL-layer.
    """
    def _get_layers(self,
        layers :Optional[list[aws_lambda.ILayerVersion]],
    ) -> Sequence[aws_lambda.ILayerVersion]:

        # otel_arn = get_LAMBDA_OTEL_LAYER_ARN( stk=Stack.of(scope), cpu_arch=architecture  );
        # # __ insights_arn = get_LAMBDA_INSIGHTS_LAYER_ARN( stk=Stack.of(scope), cpu_arch=architecture ),
        # otel_layer = aws_lambda.LayerVersion.from_layer_version_arn( scope=scope, id="otel-"+lambda_name, layer_version_arn=otel_arn, )

        # all_layers = [ otel_layer  ]
        all_layers = None

        if layers:
            if all_layers:
                all_layers.extend(layers)
            else:
                all_layers = layers

        return all_layers

    ###------------------------------------------------
    """ Create a typical aws_lambda.PythonLambda(..)
    """
    def create_lambda( self,
        scope: Construct,
        lambda_name: str,
        index: str,
        handler: str,
        path_to_lambda_src_root: pathlib.Path,
        description: str = None,
        environment: dict = None,
        memory_size: int = None,
        timeout: int = None,
        architecture: Optional[aws_lambda.Architecture] = None,
        runtime :Optional[aws_lambda.Runtime] = None,
        layers :Optional[list[aws_lambda.ILayerVersion]] = None,
        **kwargs
    ) -> aws_lambda_python_alpha.PythonFunction:

        stk = Stack.of(scope)
        description = self._get_description(
            description=description,
            stk=stk,
            lambda_name=lambda_name,
            handler=handler,
            code_src=str(path_to_lambda_src_root)
        )

        my_log_group = get_log_grp(
            scope = scope,
            tier  = self._tier,
            loggrp_type = LogGroupType.Lambda,
            what_is_being_logged = lambda_name,
            # loggrp_name= ..
        )

        all_layers = self._get_layers( layers=layers )

        ### REF: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda_python_alpha/PythonFunction.html
        pyfn = aws_lambda_python_alpha.PythonFunction(
            scope = scope,
            id = lambda_name,

            function_name = lambda_name,
            index = index,
            handler = handler,
            entry = str(path_to_lambda_src_root),
            description = description,

            environment = environment,
            memory_size = memory_size or self.min_memory,

            vpc = self._vpc,
            vpc_subnets = aws_ec2.SubnetSelection(subnet_type=get_vpc_privatesubnet_type(self._vpc)) if self._vpc else None,
            security_groups = self._sg_lambda if self._sg_lambda and self._vpc else None,

            timeout = timeout or self.default_timeout,
            runtime = runtime or _DEFAULT_LAMBDA_PYTHON_RUNTIME,
            architecture = architecture,
            tracing = aws_lambda.Tracing.ACTIVE,
            recursive_loop = aws_lambda.RecursiveLoop.TERMINATE,
            retry_attempts = 0,
            log_group = my_log_group,

            # adot_instrumentation=_LAMBDA_ADOT_CONFIG,
            insights_version=LAMBDA_INSIGHTS_VERSION,
            layers=all_layers,

            **kwargs
        )
        pyfn.apply_removal_policy( RemovalPolicy.DESTROY )
        return pyfn


    ###------------------------------------------------
    """ After a Container-image has been built (whether Docker or other OCI-commands) ..
        .. and AFTER that container-image has been pushed to an ECR-Repo ..
        .. use that ECR-Repo container-image to create a new aws_lambda.Lambda()

        At this point in time, LAYERS can -NOT- be supported for Container-lambdas
    """
    def create_container_image_lambda( self,
        scope: Construct,
        lambda_name: str,
        code: aws_lambda.EcrImageCode,
        ecr_repo :aws_ecr.IRepository,
        description: str = None,
        environment: dict = None,
        memory_size: int = None,
        timeout: int = None,
        # index: str,   ### Not meainingful (and ignored) for ECR-Repo and ZIP-file based Lambdas
        # handler: str, ### Not meainingful (and ignored) for ECR-Repo and ZIP-file based Lambdas
        # architecture: Optional[aws_lambda.Architecture] = None,
                ### Not meainingful (and ignored) for ECR-Repo and ZIP-file based Lambdas
        # runtime :Optional[aws_lambda.Runtime] = None,
                ### Not meainingful (and ignored) for ECR-Repo and ZIP-file based Lambdas
        # layers :Optional[list[aws_lambda.ILayerVersion]] = None,
                ### At this point in time, LAYERS can -NOT- be supported for Container-lambdas
        **kwargs
    ) -> aws_lambda.Function:

        stk = Stack.of(scope)
        description = self._get_description(
            description=description,
            stk=stk,
            lambda_name=lambda_name,
            handler="DockerImage",
            code_src = ecr_repo.repository_arn,
        )

        my_log_group = get_log_grp(
            scope = scope,
            tier  = self._tier,
            loggrp_type = LogGroupType.Lambda,
            what_is_being_logged = f"LogsCustRetention_{lambda_name}",
            # loggrp_name= ..
        )

        ### At this point in time, LAYERS can -NOT- be supported for Container-lambdas
        # all_layers = self._get_layers( layers=layers )

        ### REF: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda_python_alpha/PythonFunction.html
        newfunc = aws_lambda.Function(
            scope = scope,
            id = lambda_name,

            function_name = lambda_name,
            code = code,
            handler=aws_lambda.Handler.FROM_IMAGE,
            runtime=aws_lambda.Runtime.FROM_IMAGE,

            description = description,
            environment = environment,
            memory_size = memory_size or self.min_memory,

            vpc = self._vpc,
            vpc_subnets = aws_ec2.SubnetSelection(subnet_type=get_vpc_privatesubnet_type(self._vpc)) if self._vpc else None,
            security_groups = self._sg_lambda if self._sg_lambda and self._vpc else None,

            timeout = timeout or self.default_timeout,
            tracing = aws_lambda.Tracing.ACTIVE,
            recursive_loop = aws_lambda.RecursiveLoop.TERMINATE,
            retry_attempts = 0,
            log_group = my_log_group,

            ### At this point in time, LAYERS can -NOT- be supported for Container-lambdas
            # adot_instrumentation=_LAMBDA_ADOT_CONFIG,
            # insights_version=LAMBDA_INSIGHTS_VERSION,
            # layers=all_layers,

            **kwargs
        )
        # add a specific Tag called "ResourceName"
        Tags.of(newfunc).add(key="ResourceName", value=stk.stack_name+"-"+lambda_name)

        return newfunc

### EoF
