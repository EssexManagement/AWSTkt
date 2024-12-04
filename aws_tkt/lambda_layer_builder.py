import os
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda,
    DockerImage,
    DockerVolume,
    BundlingOptions,
    BundlingOutput,
    SymlinkFollowMode,
    RemovalPolicy,
)
from constructs import Construct

import aws_tkt.constants as constants

class LambdaLayerBuilder(Construct):

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        layer_id = "psycopg2"

        cpu_arch = aws_lambda.Architecture.ARM_64
        cpu_arch_str = LambdaLayerBuilder.get_cpu_arch_as_str( cpu_arch )
        self._build_cpu_arch_specific_layer( cpu_arch, cpu_arch_str, layer_id )

        cpu_arch = aws_lambda.Architecture.X86_64
        cpu_arch_str = LambdaLayerBuilder.get_cpu_arch_as_str( cpu_arch )
        self._build_cpu_arch_specific_layer( cpu_arch, cpu_arch_str, layer_id )

    ### ---------------------------------------------------------------------
    @staticmethod
    def get_cpu_arch_as_str(cpu_arch :aws_lambda.Architecture) -> str:
        match cpu_arch.name:
            case aws_lambda.Architecture.ARM_64.name: return "arm64"
            case aws_lambda.Architecture.X86_64.name: return "amd64"
            case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch.name}'")

    ### ---------------------------------------------------------------------
    def _build_cpu_arch_specific_layer( self,
        cpu_arch :aws_lambda.Architecture,
        cpu_arch_str :str,
        layer_id :str,
    ) -> aws_lambda.LayerVersion:

        stk = Stack.of(self)

        layer_uniq_id = f"layer-{layer_id}-{cpu_arch_str}"
        layer_version_name = f"{stk.stack_name}_{layer_id}_{cpu_arch_str}"
        print( f"\nCreating aws_lambda.LayerVersion(): {layer_version_name} .. via lookup-Key= '{layer_id}-{cpu_arch_str}' // {cpu_arch.name} // {layer_uniq_id} .." )
        my_lambdalayer_asset = LambdaLayerBuilder._build_cpu_arch_specific_pythonmodules( cpu_arch_str )

        my_lambda_layerversion = aws_lambda.LayerVersion(
            scope = self,
            id = layer_uniq_id,
            layer_version_name = layer_version_name,
            code = my_lambdalayer_asset,
            # code = aws_lambda.Code.from_asset( str(my_lambda_layer_zipfile) ),
            compatible_runtimes = [aws_lambda.Runtime.PYTHON_3_12, aws_lambda.Runtime.PYTHON_3_11],
            # compatible_architectures=[cpu_arch],
            removal_policy = RemovalPolicy.DESTROY,
        )
        print( " .. .. done!\n")

    ### ---------------------------------------------------------------------
    @staticmethod
    def _get_docker_uri( cpu_arch_str :str ) -> str:
        match cpu_arch_str:
            ## Returns a string like:->  public.ecr.aws/lambda/python:3.12-x86_64
            case aws_lambda.Architecture.ARM_64.name:    return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-arm64"
            case aws_lambda.Architecture.X86_64.name:    return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-x86_64"
            case "aarch64":  return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-arm64"
            case "arm64":    return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-arm64"
            case "x86_64":   return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-x86_64"
            case "amd64":    return f"public.ecr.aws/lambda/python:{constants.LAMBDA_PYTHON_RUNTIME_VER_STR}-x86_64"
            case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")

    @staticmethod
    def _get_docker_platform(cpu_arch_str :str) -> str:
        match cpu_arch_str:
            case aws_lambda.Architecture.ARM_64.name:    return "linux/arm64"
            case aws_lambda.Architecture.X86_64.name:    return "linux/amd64"
            case "aarch64":  return "linux/arm64"
            case "arm64":    return "linux/arm64"
            case "x86_64":   return "linux/amd64"
            case "amd64":    return "linux/amd64"
            case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch_str}'")

    ### ---------------------------------------------------------------------
    @staticmethod
    def _build_cpu_arch_specific_pythonmodules( cpu_arch_str :str ) -> aws_lambda.LayerVersion:

        layer_fldr_path = "./src"

        docker_img_uri = LambdaLayerBuilder._get_docker_uri( cpu_arch_str )
        inside_docker_src_path    = "/asset-input"  ### This is the default-path within aws_lambda.Code.from_asset()
        inside_docker_output_path = "/asset-output" ### This is the default-path within aws_lambda.Code.from_asset()

        docker_env={} ### Passed onto Docker-Container when running
        docker_env['TARGETPLATFORM'] = LambdaLayerBuilder._get_docker_platform(cpu_arch_str)
        # 'DOCKER_DEFAULT_PLATFORM': os.environ['DOCKER_DEFAULT_PLATFORM'],
            ### ^^^^^^ ☝🏾☝🏾☝🏾 ! NOTE ! This is the critical-value, that ensures the cpu-arch for the Lambda-Layer is correct!!!

        if os.environ.get('BUILDPLATFORM') is not None:
            docker_env['BUILDPLATFORM'] = os.environ['BUILDPLATFORM']

        if os.environ.get('DOCKER_DEFAULT_PLATFORM') is not None:
            docker_env['DOCKER_DEFAULT_PLATFORM'] = os.environ['DOCKER_DEFAULT_PLATFORM']
        # else:
        #     docker_env['BUILDPLATFORM'] = get_docker_platform(cpu_arch_str)

        ### ---------------------------------------------
        my_asset :aws_lambda.AssetCode = aws_lambda.Code.from_asset(
            ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Code.html#aws_cdk.aws_lambda.Code.from_asset
            path = str(layer_fldr_path),
            deploy_time = True,
            follow_symlinks = SymlinkFollowMode.NEVER, ### ALWAYS|EXTERNAL|BLOCK_EXTERNAL,

            bundling = BundlingOptions(
                ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/BundlingOptions.html#aws_cdk.BundlingOptions
                platform = LambdaLayerBuilder._get_docker_platform(cpu_arch_str),
                image = DockerImage.from_registry( docker_img_uri ),
                entrypoint = [ "bash", "-c" ],
                    ### Attention: Since this-construct was meant for Lambdas-Funcs and -NOT- Layers, we are overriding the Lambda-launcher.
                command = [
                    # "bash",
                    # "-c",
                    f"pip install  --upgrade -r requirements.txt -t {inside_docker_output_path}/python --only-binary=:all:",
                ],
                ### docker run --rm -u "????:1360859114"
                ###     -w "/asset-input"
                ###     -v "..{projroot}../api/lambda_layer/psycopg:/asset-input:delegated"
                ###     -v "..{projroot}../cdk.out/asset.{U-U-I-D}:/asset-output:delegated"
                ###     "public.ecr.aws/lambda/python:3.12-arm64"
                ###     --entrypoint bash -c "pip install  --upgrade -r requirements.txt -t /asset-output/python"

                environment=docker_env, ### Passed onto Docker-Container when running
                output_type = BundlingOutput.NOT_ARCHIVED,
                # volumes = [
                #     DockerVolume(
                #         container_path = inside_docker_src_path,
                #         host_path = str(layer_fldr_path),
                #         # consistency = Only applicable for --macOS--    Default: DockerConsistency.DELEGATED
                #     ),
                #     # DockerVolume(
                #     #     # container_path = "/opt",
                #     #     container_path = inside_docker_output_path,
                #     #     host_path = str(host_output_path),
                #     #     # consistency = Only applicable for --macOS--    Default: DockerConsistency.DELEGATED
                #     # ),
                # ],
            ),
        )
        return my_asset

### EoF
