import os
import hashlib
import time
from pathlib import Path, PurePath
from typing import Union, TypeVar
import traceback

PathLike = TypeVar('PathLike', str, PurePath)

import docker
import shutil
import zipfile

from subprocess import PIPE, STDOUT

from aws_cdk import (
    aws_lambda,
    AssetHashType,
    IgnoreMode,
    SymlinkFollowMode,
    BundlingOptions,
    BundlingOutput,
    DockerImage,
    DockerVolume,
)

import common.FSUtils as FSUtils
import common.cdk.constants_cdk as constants_cdk
from common.cdk.standard_lambda import LambdaLayerOption
from cdk_utils.CloudFormation_util import (
    get_docker_platform,
    get_python_runtime_containerimage_uri,
    get_awslambda_runtime_containerimage_uri,
)

### ==========================================================================================================

### This is a cool-tip to drastically reduce the pandas & psycopg layers down in size by > 50% !!!
### This is generic and works on ANY LAYER !!!
### Not 100% sure about destroying ___pycache___ .. but right now, the sum-total-size of ALL layers is too big for Lambdas!

_STD_BUILD_POST_CMDS = (
    " && rm -rf python/botocore"
  + " && find . -name '*.txt' -type f -delete"
  + " && find . -name '*.md'  -type f -delete"
  + " && ( find . -name \"datasets\"    -type d | xargs rm -rf )"
  + " && ( find . -name \"examples\"    -type d | xargs rm -rf )"
  + " && ( find . -name \"tests\"       -type d | xargs rm -rf )"
  + " && ( find . -name \"*.dist-info\" -type d | xargs rm -rf )"
)
_STD_BUILD_POST_CMDS_SQUEEZE_MORE = (
    " && ( find . -name \"__pycache__\" -type d | xargs rm -rf )"
  + " && find . -name '*.pyc' -type f -delete"
  # + " && ( find . -name \"docs\"        -type d | xargs rm -rf )"  ### <------- rds_init lambda had error: No module named 'botocore.docs' !!!
)

### ==========================================================================================================

def _get_STD_BUILD_POST_CMDS(layer_opt : LambdaLayerOption) -> list:
    match layer_opt:
        case LambdaLayerOption.SMALLEST_ZIP_FILE_SLOW_COLDSTART: return _STD_BUILD_POST_CMDS + _STD_BUILD_POST_CMDS_SQUEEZE_MORE
        case LambdaLayerOption.LARGER_ZIP_FILE_FASTER_COLDSTART: return _STD_BUILD_POST_CMDS
        case _: raise MyException(f"!! INTERNAL ERROR !! Code needs to know how to handle LambdaLayerOption: '{layer_opt}'")

def _shrink_layer_zipfile(
    cmd :str,
    install_dir :Path,
    layer_opt : LambdaLayerOption,
) -> str:
    return  (
        # f"touch -f {inside_docker_output_path}/TEST && " +
        cmd
        + f" && cd {install_dir}" ### <------ important to do this, JUST-BEFORE the following line for _STD_BUILD_POST_CMDS
        + _get_STD_BUILD_POST_CMDS(layer_opt)  ### <-------- this helps to shrink Lambda-Layer zip-file-SIZE.     See more above
    )


### =================================================================================
### ---------------------------------------------------------------------------------
### =================================================================================

class LambdaLayerProps():
    """ Structured way to EASILY creating new Lambda-layers, avoiding typos, while also ensuring future-enhancements can be caught at "compile-time".
        Has 3 properties:
        lambda_layer_id :str,
        lambda_layer_fldr :Path,
        lambda_layer_sizing_option :LambdaLayerOption,
    """

    @property
    def lambda_layer_id(self) -> str:
        return self._lambda_layer_id

    @property
    def lambda_layer_fldr(self) -> Path:
        return self._lambda_layer_fldr

    @property
    def lambda_layer_sizing_option(self) -> LambdaLayerOption:
        return self._lambda_layer_sizing_option

    def __init__(self,
        lambda_layer_id :str,
        lambda_layer_fldr :Path,
        lambda_layer_sizing_option :LambdaLayerOption,
    ):
        """ Examples of parameter-values:
                lambda_layer_id = "psycopg3-pandas"
                lambda_layer_fldr = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/psycopg'
                lambda_layer_sizing_option LambdaLayerOption.LARGER_ZIP_FILE_FASTER_COLDSTART
        """
        self._lambda_layer_id = lambda_layer_id
        self._lambda_layer_fldr = lambda_layer_fldr
        self._lambda_layer_sizing_option = lambda_layer_sizing_option

        ### private constants.
        # _LAMBDA_LAYER_BUILDER_SCRIPT = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/bin/etl-lambdalayer-builder-venv.sh'
        ### x86_764: pip3 install --platform manylinux2014_x86_64  --target . --python-version 3.12 --only-binary=:all: psycopg2-binary
        ### arm64:   pip3 install --platform manylinux2014_aarch64 --target . --python-version 3.12 --only-binary=:all: psycopg2-binary
                ### REF: https://medium.com/@bloggeraj392/creating-a-psycopg2-layer-for-aws-lambda-a-step-by-step-guide-a2498c97c11e

        # _ZIP_FILE_SIMPLENAME = "psycopg-layer-{}.zip"
        ### Assuming it will be created into the folder specified via the `layer_fldr_path` param below.
        ### For accuracy, check the `Dockerfile` within `lambda_layer/psycopg` subfolder.

### =================================================================================
### ---------------------------------------------------------------------------------
### =================================================================================

""" HOW-TO USE: Take a look at class `LambdaLayersAssetBuilder()` within `backend/common_aws_resources_stack.py`
    Step 1: Create all your layer-related files into a new sub-folder.
    Step 2: Initialize the following constructor.
    Step 3: Call the `build_lambda_layers()` method to create the Lambda-layers for EACH INDIVIDUAL cpu-architecture!

    param # 1 : lambda_layer_id :str -- Simple-name of the Lambda-layer. The deployed-Layer's name is prefixed by Stack-Name.
    param # 2 : lambda_layer_builder_script :Path -- pathlib.Path to the folder containing the Lambda-layer source code.
"""
class LambdaLayerUtility():

    ### =================================================================================

    @staticmethod
    def gen_sha256_hash_for_layer( layer_fldr_path :PathLike) -> str:
        """
            param # 1: layer_fldr_path :Path -- pathlib.Path to the folder containing the Lambda-layer source code.
            RETURNS: The SHA256 hash (of `Pipfile.lock`) which is then encoded as hex.  See the algorithm inside `FSUtils.get_sha256_hex_hash_for_file()`
        """
        ### Now calculate the SHA-256 hash and then convert it into HEX
        pipfile_lock = "Pipfile.lock"
        requirements_txt = "requirements.txt"
        if FSUtils.is_valid_file(FSUtils.join_path(layer_fldr_path, pipfile_lock)):
            asset_hash = FSUtils.get_sha256_hex_hash_for_file( layer_fldr_path, pipfile_lock )
        elif FSUtils.is_valid_file(FSUtils.join_path(layer_fldr_path, requirements_txt)):
            asset_hash = FSUtils.get_sha256_hex_hash_for_file( layer_fldr_path, requirements_txt )
        else:
            raise FileNotFoundError(f"Neither {pipfile_lock} nor {requirements_txt} found in {layer_fldr_path}")
        print( f"asset_hash = '{asset_hash}'" )

        return asset_hash

    ### =================================================================================

    def __init__(self,
        lambda_layer_id :str,
        lambda_layer_builder_script :Path,
    ) -> None:
        self._lambda_layer_id = lambda_layer_id
        # self._lambda_layer_builder_script_path = lambda_layer_builder_script
        ### Assuming it will be created into the folder specified via the `layer_fldr_path` param below.
        ### For accuracy, check the `Dockerfile` within `lambda_layer/psycopg` subfolder.

    ### -----------------------------------------------

    """ Build a CPU-architecture specific Lambda-layer -- using Docker (AWS-official Python-Container-Image)
        Once you have initialized this class via constructor, this method makes it very easy to create MULTIPLE chip-arch specific layers.

        param # 1 : tier :str -- dev|test|int|uat|stage|prod
        param # 2 : cpu_arch_str :str -- 'arm64'|'x86_64'
        param # 3 : layer_fldr_path :Path -- pathlib.Path to the folder containing the Lambda-layer source code.
        param # 4 : layer_opt : LambdaLayerOption -- See `common.cdk.StandardLambdaLayer.py` for ENUM's details.

        Returns: pathlib.Path to the ZIP-file.
    """
        # param # 4 : reuse_if_exists :bool -- do NOT recreate the LambdaLayer if it already exists.  Default: do NOT reuse
    def build_lambda_layer_using_docker(self,
        # scope :Construct,  ### No longer needed as we're NOT using aws_docker_assets construct.
        tier :str,
        cpu_arch_str :str,
        layer_fldr_path :Path,
        layer_opt : LambdaLayerOption,
        # zipfile_simplename :str,
        # reuse_if_exists :bool = False,  ### re-use does NOT work with `CodeAsset`.  So, unfortunately, we have to rebuild everytime!
    ) -> tuple[aws_lambda.AssetCode, str]:
        HDR = f" -- build_lambda_layer(tier={tier},cpu={cpu_arch_str}): within {__file__}"

        print( f"\nlayer_fldr_path(as-is) = '{layer_fldr_path}' in "+HDR )
        layer_fldr_path = layer_fldr_path.resolve().absolute()
        print( f"layer_fldr_path(absolute) = '{layer_fldr_path}' " )

        # print( f"self._lambda_layer_builder_script_path(as-is) = '{self._lambda_layer_builder_script_path}' in "+HDR )
        # layer_builder_script_path = self._lambda_layer_builder_script_path.resolve().absolute()
        # print( f"layer_builder_script_path(absolute) = '{layer_builder_script_path}' " )

        # zipfile_simplename =  zipfile_simplename.format(cpu_arch_str)
        # print( f"zipfile_simplename = '{zipfile_simplename}' "+HDR )
        # layer_zipfile_path = layer_fldr_path / zipfile_simplename
        # print( f"layer_zipfile_path = '{layer_zipfile_path}' " )
        # if reuse_if_exists and layer_zipfile_path.exists():
        #     print(f"Reusing existing Lambda-layer ZIP-file at '{layer_zipfile_path}' "+HDR )
        #     return layer_zipfile_path

        ### ------------------------------------
        docker_img_uri =  get_python_runtime_containerimage_uri(cpu_arch_str)
        inside_docker_src_path    = "/asset-input"  ### This is the default-path within aws_lambda.Code.from_asset()
        inside_docker_output_path = "/asset-output" ### This is the default-path within aws_lambda.Code.from_asset()
        print( f"docker_img_uri = '{docker_img_uri}', inside_docker_src_path = '{inside_docker_src_path}', inside_docker_output_path ='{inside_docker_output_path}' " )

        # host_output_path = Path( f"/tmp/cdk/{__file__}/{self._lambda_layer_id}-{tier}-{cpu_arch_str}/" )
        # print( f"host_output_path = '{host_output_path}' ")
        # ### make sure this folder exists and is empty
        # if host_output_path.exists():
        #     shutil.rmtree( "/tmp/cdk" )
        #     # shutil.rmtree( str(host_path) )
        # host_output_path.mkdir( parents=True, exist_ok=True )

        # ### We are --FORCED-- to pass in ENV-VARs to Docker, for 2 very-wierd USE-CASES!
        # ### USE-CASE #1 is still valid -- only-installing BINARIES and NOT-the-source-code (when installing PyPi-modules, either with `pip` or `pipenv`)
        # ### USE-CASE #2 -- not working -- is to enable Docker-in-Docker (which --FAILS-- inside AWS-CodeBuild)
        # ### FYI: `aws_lambda.Code.from_asset()` is -NOT- actually doing anything -- until this Asset is used in the `aws_lambda.LayerVersion()` construct.
        # ###       By which time, all the values of "platform" within BuildOptions are OVERWRITTEN each time this is invoked!!!
        # ###       >> Bundling asset FACT-backend-dev/CommonAWSRrcs/layer-psycopg2-arm64/Code/Stage...
        # ###       >> Unable to find image 'public.ecr.aws/lambda/python:3.12-arm64' locally
        # ###       >> 3.12-arm64: Pulling from lambda/python
        # ###       >> Digest: sha256:04f633717595035419032727f8f28ac29cdd0400e6b3ca9a4cac23bea4bb0bb6
        # ###       >> Status: Image is up to date for public.ecr.aws/lambda/python:3.12-arm64
        # ###       >> docker: image with reference public.ecr.aws/lambda/python:3.12-arm64 was found but does not match the specified platform: wanted linux/amd64, actual: linux/arm64/v8.
        docker_env={} ### Passed onto Docker-Container when running
        docker_env['PIP_ONLY_BINARY'] = ':all:'  ### use-case #1 mentioned above in comments
                ### REF: https://pip.pypa.io/en/stable/cli/pip_install/
        docker_env['PIP_TARGET'] = f"{inside_docker_output_path}/python"  ### use-case #1 mentioned above in comments
                ### Attention: `pipenv` does -NOT- support `-t` a.k.a. `--target` CLI-arg, like plain `pip` cmd does.  Hence this env-var!!!
        docker_env['PIPENV_VENV_IN_PROJECT'] = "1"   ### Keep virtualenv in project directory.  This is REQUIRED, since we are using `PIP_TARGET` (a.k.a. --target cli-arg for `pip` command)
        docker_env['HOME']                   = f"{inside_docker_src_path}"
        docker_env['PIPENV_HOME']            = "/tmp/pipenv"
        ### Disable generating a new Pipenv's Pipfile.lock .. via environment variables
        docker_env['PIPENV_NOSPIN']          = '1'
        docker_env['PIPENV_SKIP_LOCK']       = '1'  # Prevents updating Pipfile.lock

        ### Following is re: use-case #2 mentioned above in comments (FYI: following does NOT work in AWS-CodeBuild)
        # docker_env['TARGETPLATFORM'] = get_docker_platform(cpu_arch_str)
        # # 'DOCKER_DEFAULT_PLATFORM': os.environ['DOCKER_DEFAULT_PLATFORM'],
        #     ### ^^^^^^ ☝🏾☝🏾☝🏾 ! NOTE ! This is the critical-value, that ensures the cpu-arch for the Lambda-Layer is correct!!!
        # if os.environ.get('BUILDPLATFORM') is not None:
        #     docker_env['BUILDPLATFORM'] = os.environ['BUILDPLATFORM']
        # if os.environ.get('DOCKER_DEFAULT_PLATFORM') is not None:
        #     docker_env['DOCKER_DEFAULT_PLATFORM'] = os.environ['DOCKER_DEFAULT_PLATFORM']
        # # else:
        # #     docker_env['BUILDPLATFORM'] = get_docker_platform(cpu_arch_str)

        ### ------------------------------------
        # match cpu_arch_str:
        #     ### REF: https://github.com/pypa/manylinux
        #     ### !!! WARNING !!! Support for manylinux1 has ended on January 1st, 2022.
        #     ### !!! WARNING !!! Support for manylinux1 has ended on January 1st, 2022.
        #     ### !!! WARNING !!! Support for manylinux1 has ended on January 1st, 2022.
        #     ### !!! WARNING !!! Support for manylinux1 has ended on January 1st, 2022.
        #     ### !WARNING! only "manylinux1" works on Amazon-Linux1/2/2024/.. & also works on Ubuntu 16.04+ and Debian9+
        #     case "arm64":  pip_platform = "manylinux2014_arm64"
        #     case "x86_64": pip_platform = "manylinux2014_x86_64"

        ### ---------------------------------------------
        ### Following Docker-based approach will create a zipfile automatically, with the MUCH-simpler `/python/**` folder-heirarchy.
        ### !! Attention !! pip's ERROR: Can not combine '--user' and '--target' (which is an ENV-VAR `PIP_TARGET` to this Docker)
        cmd =  f"""
            pip install pipenv &&
            PYTHONPATH={inside_docker_output_path}/python PATH={inside_docker_output_path}/python/bin:$PATH pipenv sync --dev
        """
                ### !! Attention !! pip's ERROR: Can not combine '--user' and '--target' (which is an ENV-VAR `PIP_TARGET` to this Docker)
                ### !! WARNING !! avoid use of pip3's cli-args "--platform {pip_platform}" !!! See switch/match above.
                ### Note: Avoid `pipenv install`.  switch to `pipenv sync` which is More deterministic than `pipenv install`
        cmd = ' '.join( cmd.split() ) ### split() and join() will replace \s+ with a single-whitespace-char!

        my_asset :aws_lambda.AssetCode = aws_lambda.Code.from_asset(
            ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Code.html#aws_cdk.aws_lambda.Code.from_asset
            path = str(layer_fldr_path),
            deploy_time = False, ### !!! Warning !!! setting this to FALSE, will ..
                ### .. .. cause ZIP-file to vanish, and be uploaded to cdk's s3-bucket everytime.
                ### Lambda-Layer will then interpret that (latest timestamp of 3-object) as if, the layer has changed.
                ### Then, update of Layer will happen, following which Stack-Output will be updated -- which fails!
                ### Bottomline: For Lambda-Layers, always set `deploy_time` to `False`
            follow_symlinks = SymlinkFollowMode.NEVER, ### ALWAYS|EXTERNAL|BLOCK_EXTERNAL,
            # ignore_mode=IgnoreMode.GLOB ### Default!  FYI: to use for exclude patterns
            # asset_hash_type=AssetHashType.CUSTOM, ## |OUTPUT|SOURCE  If assetHash is configured, this option must be undefined or AssetHashType.CUSTOM
            # asset_hash = asset_hash,

            bundling = BundlingOptions(
                ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/BundlingOptions.html#aws_cdk.BundlingOptions
                platform = get_docker_platform(cpu_arch_str),
                image = DockerImage.from_registry( docker_img_uri ),
                environment=docker_env, ### Passed onto Docker-Container when running
                entrypoint = [ "bash", "-c" ],
                    ### Attention: Since this-construct was meant for Lambdas-Funcs and -NOT- Layers, we are overriding the Lambda-launcher.
                command = [
                    # "bash",
                    # "-c",
                    _shrink_layer_zipfile(
                        # cmd = f"pip install  --upgrade -r requirements.txt -t {inside_docker_output_path}/python --only-binary=:all:",
                        cmd = cmd,
                        install_dir = inside_docker_output_path,
                        layer_opt = layer_opt
                    )
                ],
                ### docker run --rm -u "????:1360859114"
                ###     -w "/asset-input"
                ###     -v "..{projroot}../api/lambda_layer/psycopg:/asset-input:delegated"
                ###     -v "..{projroot}../cdk.out/asset.3c8{U-U-I-D}6a8:/asset-output:delegated"
                ###     "public.ecr.aws/lambda/python:3.12-arm64"
                ###     --entrypoint bash -c "pip install  --upgrade -r requirements.txt -t /asset-output/python"
                ### working_directory= .. can be anything.. as pip-install in "command" above will NOT be affected by this param.

                volumes = [
                    DockerVolume(
                        container_path = inside_docker_src_path,
                        host_path = str(layer_fldr_path),
                        # consistency = Only applicable for --macOS--    Default: DockerConsistency.DELEGATED
                    ),
                    # DockerVolume(
                    #     # container_path = "/opt",
                    #     container_path = inside_docker_output_path,
                    #     host_path = str(host_output_path),
                    #     # consistency = Only applicable for --macOS--    Default: DockerConsistency.DELEGATED
                    # ),
                ],
                output_type = BundlingOutput.NOT_ARCHIVED,
                ### https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.BundlingOutput.html
                        ### ARCHIVED: The bundling output-directory includes a single .zip or .jar file -- which will be used as the final bundle.
                        ### NOT_ARCHIVED: The bundling output-directory contains 1+ files which'll be archived + uploaded as a .zip file to S3.
                        ### AUTO_DISCOVER: (Default) If the bundling output-directory contains a single archive file (zip or jar), it behaves just as ARCHIVED.
                        ###        Otherwise, it will behave just as if NOT_ARCHIVED was provided.
                        ### SINGLE_FILE: The bundling output-directory includes --JUST-- 1 file (behaves as if you provided ARCHIVED).
                        ###     But !!!!! If the output directory contains 1+ files/folder, bundling will fail with ERROR.
                ## network :str,
                ## user :str, ### Note: always look to AVOID ROOT-privileges.
                ## security_opt : str, ### ??? https://docs.docker.com/engine/security/
                ## bundling_file_access = Default: - BundlingFileAccess.BIND_MOUNT; Access-mechanism used to make source files available to the bundling container and to return the bundling output back to the host.
                ## image = DockerImage.from_build(
                ##     path = str(layer_fldr_path),
                ##     platform = get_docker_platform(cpu_arch_str),
                ##     cache_disabled=False,
                ##     ## target_stage = .. ### For Multi-Stage Docker-Builds !! Default: - Build all stages defined in the Dockerfile
                ##     ## build_args = { ### `ARGS` inside `Dockerfile`
                ##     ##     "LAYER_BUILDER_SCRIPT": str(layer_builder_script_path),
                ##     ##     "LAYER_FLD": str(layer_fldr_path),
                ##     ##     "LAYER_ZIPFILE": str(layer_zipfile_path)
                ##     ## },
                ## ),
            ),
        )

        return my_asset

        ### ---------------------------------------------
        # return aws_ecr_assets.DockerImageAsset(
        #     ### -NO- way to use "volumes/mounts" via this construct!!!
        #     scope = scope,
        #     id = f"{self._lambda_layer_id}-{tier}-{cpu_arch_str}",
        #     directory = str(layer_fldr_path),
        #     platform = get_docker_platform(cpu_arch_str),
        #     cache_disabled=False,
        #     follow_symlinks=False,
        #     # outputs= .. where to store the Docker-Image
        #     # build_args = { ### `ARGS` inside `Dockerfile`
        #     #     "LAYER_BUILDER_SCRIPT": str(layer_builder_script_path),
        #     #     "LAYER_FLD": str(layer_fldr_path),
        #     #     "LAYER_ZIPFILE": str(layer_zipfile_path)
        #     # },
        # )

        # ### ---------------------------------------------
        # # print("Creating python-VENV virtual-environment...")
        # # venv.create('.venv', with_pip=True, clear=True, symlinks=True )

        # subprocess.run([
        #         str(layer_builder_script_path),
        #         str(layer_fldr_path),
        #         str(layer_zipfile_path)
        #     ],
        #     check=True, stdout=PIPE, stderr=STDOUT
        # )

        # # ### Cleanup
        # # print( "Cleaning-up ", str(layer_fldr_path / "python") )
        # # shutil.rmtree( str(layer_fldr_path / "python"), ignore_errors=False )

        return layer_zipfile_path

    ### -----------------------------------------------------------------------------------

#     """ !! DOES NOT WORK !!

# WARNING: The directory '/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
# Defaulting to user installation because normal site-packages is not writeable
# Requirement already satisfied: pip in /usr/local/lib/python3.13/site-packages (24.3.1)
# WARNING: The directory '/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
# ERROR: Could not find a version that satisfies the requirement psycopg2-binary==2.9.10 (from versions: none)
# ERROR: No matching distribution found for psycopg2-binary==2.9.10

#         Build a CPU-architecture specific Lambda-layer.
#         Once you have initialized this class via constructor, this method makes it very easy to create MULTIPLE chip-arch specific layers.

#         param # 1 : tier :str -- dev|test|int|uat|stage|prod
#         param # 2 : cpu_arch_str :str -- 'arm64'|'x86_64'
#         param # 3 : layer_fldr_path :Path -- pathlib.Path to the folder containing the Lambda-layer source code.
#         param # 4 : layer_opt : LambdaLayerOption -- See `common.cdk.StandardLambdaLayer.py` for ENUM's details.

#         Returns the pathlib.Path to the ZIP-file.
#     """
#     def build_lambda_layer(self,
#         tier :str,
#         cpu_arch_str :str,
#         layer_fldr_path :Path,
#         layer_opt : LambdaLayerOption,
#         # zipfile_simplename :str,
#         # reuse_if_exists :bool = False,  ### re-use does NOT work with `CodeAsset`.  So, unfortunately, we have to rebuild everytime!
#     ) -> aws_lambda.AssetCode:
#         HDR = f" -- build_lambda_layer(tier={tier},cpu={cpu_arch_str}): within {__file__}"

#         """ !! DOES NOT WORK !!

#         WARNING: The directory '/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
#         Defaulting to user installation because normal site-packages is not writeable
#         Requirement already satisfied: pip in /usr/local/lib/python3.13/site-packages (24.3.1)
#         WARNING: The directory '/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
#         ERROR: Could not find a version that satisfies the requirement psycopg2-binary==2.9.10 (from versions: none)
#         ERROR: No matching distribution found for psycopg2-binary==2.9.10
#         """

#         print( f"\nlayer_fldr_path(as-is) = '{layer_fldr_path}' in "+HDR )
#         layer_fldr_path = layer_fldr_path.resolve().absolute()
#         print( f"layer_fldr_path(absolute) = '{layer_fldr_path}' " )

#         # zipfile_simplename =  zipfile_simplename.format(cpu_arch_str)
#         # print( f"zipfile_simplename = '{zipfile_simplename}' "+HDR )
#         # layer_zipfile_path = layer_fldr_path / zipfile_simplename
#         # print( f"layer_zipfile_path = '{layer_zipfile_path}' " )
#         # if reuse_if_exists and layer_zipfile_path.exists():
#         #     print(f"Reusing existing Lambda-layer ZIP-file at '{layer_zipfile_path}' "+HDR )
#         #     return layer_zipfile_path

#         ### ------------------------------------
#         docker_img_uri =  get_python_runtime_containerimage_uri(cpu_arch_str)
#         inside_docker_src_path    = "/asset-input"  ### This is the default-path within aws_lambda.Code.from_asset()
#         inside_docker_output_path = "/asset-output" ### This is the default-path within aws_lambda.Code.from_asset()
#         print( f"docker_img_uri = '{docker_img_uri}', inside_docker_src_path = '{inside_docker_src_path}', inside_docker_output_path ='{inside_docker_output_path}' " )

#         # host_output_path = Path( f"/tmp/cdk/{__file__}/{self._lambda_layer_id}-{tier}-{cpu_arch_str}/" )
#         # print( f"host_output_path = '{host_output_path}' ")
#         # ### make sure this folder exists and is empty
#         # if host_output_path.exists():
#         #     shutil.rmtree( "/tmp/cdk" )
#         #     # shutil.rmtree( str(host_path) )
#         # host_output_path.mkdir( parents=True, exist_ok=True )

#         ### ------------------------------------
#         match cpu_arch_str:
#             ## Return a string like:->  public.ecr.aws/lambda/python:3.12-x86_64
#             case "aarch64" | "arm64" | aws_lambda.Architecture.ARM_64.name:     pip_platform = "manylinux2014_arm64"
#             case "x86_64"  | "amd64" | aws_lambda.Architecture.X86_64.name:     pip_platform = "manylinux2014_x86_64"
#             case _: raise RuntimeError(f"!! INTERNAL ERROR !! Unknown CPU architecture: '{cpu_arch_str}'")

#         ### ---------------------------------------------
#         asset_hash = FSUtils.get_sha256_hex_hash_for_file( layer_fldr_path, "requirements.txt" )
#         print( f"asset_hash = '{asset_hash}'" )
#         # cmd = f"pip install  --upgrade -r requirements.txt -t {inside_docker_output_path}/python --only-binary=:all:",
#                 ### !! WARNING !! avoid use of pip3's cli-args "--platform {pip_platform}" !!! See switch/match above.
#         cmd = f"pip install --upgrade pip && pip install --only-binary=:all: --upgrade  --target=package --implementation cp --platform {pip_platform} --python-version {constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR} -r requirements.txt"
#         print( f"cmd = '{cmd}'" )
#         my_asset :aws_lambda.AssetCode = aws_lambda.Code.from_asset(
#             path = str(layer_fldr_path),
#             deploy_time = False, ### !!! Warning !!! setting this to FALSE, will ..
#             follow_symlinks = SymlinkFollowMode.NEVER, ### ALWAYS|EXTERNAL|BLOCK_EXTERNAL,
#             asset_hash_type=AssetHashType.CUSTOM, ## |OUTPUT|SOURCE  If assetHash is configured, this option must be undefined or AssetHashType.CUSTOM
#             asset_hash = asset_hash,

#             bundling = BundlingOptions(
#                 platform = get_docker_platform(cpu_arch_str),
#                 image = DockerImage.from_registry( docker_img_uri ),
#                 entrypoint = [ "bash", "-c" ],
#                 command = [
#                     _shrink_layer_zipfile(
#                         cmd = cmd,
#                         install_dir = inside_docker_output_path,
#                         layer_opt = layer_opt
#                     )
#                 ],
#                 volumes = [
#                     DockerVolume(
#                         container_path = inside_docker_src_path,
#                         host_path = str(layer_fldr_path),
#                     ),
#                 ],
#                 security_opt="seccomp=unconfined",  # Gives full privileges
#                 # security_opt="seccomp=default",
#                     # 3rd Option: If you need specific capabilities, use Docker's --cap-add instead
#                     ### WARNING -- This 3rd option MUST be configured in other Docker settings, --NOT-- in `security_opt`
#                 output_type = BundlingOutput.NOT_ARCHIVED,
#             ),
#         )
#         return my_asset

    ### =================================================================================
    ### ---------------------------------------------------------------------------------
    ### =================================================================================


### =================================================================================
### ---------------------------------------------------------------------------------
### =================================================================================

# docker run -v "${layer_zipfile_path}":/var/task               \
#     "public.ecr.aws/sam/build-python3.10"       \
#     /bin/sh -c "pip install -r /var/task/requirements.txt -t python/lib/python3.10/site-packages/"
# find ./python -name 'tests'|xargs -I {} rm -rf {}
# cd ./  && zip -qr ${zipFileName}  ./python

### -----------------------
### Prepare volume mounting onto Docker-container

# mount_path = f"/var/task/{zipfile_simplename}/"
# # mount_path = f"/var/task/"

### Initialize Docker client
#--> client = docker.from_env()
### sometimes above can fail inside AWS-CodeBuild. So ..Initialize Docker-client with retry logic

# volumes = {}
# volumes[str(layer_fldr_path)] = {
#     'bind': mount_path,
#     'mode': 'rw'
# }
# print( volumes )

# ### NOTE !! The following multiple-lines of code/cmds
# ### Each must be a STRING representing a standalone shell-command.
# ### Each of these are concatenated into ONE single LONG shell-command (with individual shell-commands separated by "&&")
# docker_cmds = [
#     # f"ls -la {mount_path} ",
#     f"pip install -r {mount_path}/requirements.txt -t {mount_path}/python/lib/python{constants_cdk.CDK_APP_PYTHON_VERSION}/site-packages/ ",
#     # f"find {mount_path}/python " + " -name 'tests' -type d -exec rm -rf {} ",  ### String-concatenation! to prevent intepretation of 2nd {}
# ]

def run_docker(
    cpu_arch_str :str,
    volumes :dict,
    docker_cmds :list[str]
):

    platform = get_docker_platform( cpu_arch_str=cpu_arch_str )

    max_retries = 3
    retry_delay = 5
    is_success = False
    for attempt in range(max_retries):
        try:
            # Try different Docker socket configurations
            if os.path.exists('/var/run/docker.sock'):
                client = docker.from_env()
                print("Connected to Docker daemon via /var/run/docker.sock")
            else:
                client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
                print("Connected to Docker daemon via tcp://127.0.0.1:2375")

            # Test Docker connection
            client.ping()
            is_success = True
            print("Docker connection (docker-client.ping) successful.")
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    # if attempt >= max_retries - 1:
    if not is_success:
        raise Exception(f"!! FAILURE !! to connect to Docker-daemon after {max_retries} attempts: {str(e)}")


    # Run container with mounted volume
    container = client.containers.run(
        platform = platform,
        image="public.ecr.aws/sam/build-python3.12",
        command=[
            "/bin/sh",
            "-c",
            ### Warning: The following multiple-lines of code, must be STRINGs that are concatenated into ONE single LONG shell-command (with individual shell-commands separated by "&&")
            ' && '.join( docker_cmds )
        ],
        volumes=volumes,
        privileged=True,
        remove = True,
        # auto_remove=True,  # Automatically remove container when it exits
        detach = False,  # Wait for the container to complete
        stderr=True,
        stdout=True,
        # stream=True,
    )

### ---------------------------------------------------------------------------------
### ---------------------------------------------------------------------------------

def create_zipfile(
    layer_zipfile_path :Path,
    layer_fldr_path :Path,
):
    ### Create zip file
    file_patt_to_not_include = "tests"
    with zipfile.ZipFile(layer_zipfile_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        src_root_fldr = layer_fldr_path / ".venv/lib"
        for root, dirs, files in os.walk(src_root_fldr):
            ### Remove directories matching file-patt from dirs list to prevent walking into them
            dirs[:] = [d for d in dirs if d != file_patt_to_not_include]
            ### Skip if current entry matches file-patt
            if os.path.basename(root) == file_patt_to_not_include:
                continue
            for file in files:
                if os.path.basename(file) == file_patt_to_not_include:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, layer_fldr_path)
                zipf.write(file_path, arcname)

### EoF
