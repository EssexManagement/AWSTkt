from typing import Optional, Union
from enum import Enum, auto, unique
import os
import re
import pathlib

from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codebuild,
    aws_lambda,
    aws_s3,
    aws_iam,
    aws_secretsmanager,
    aws_logs,
    aws_codepipeline_actions as codepipeline_actions,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import get_cpu_arch_enum, get_cpu_arch_as_str
from .standard_logging import get_log_grp, LogGroupType

### ---------------------------------------------------------------------------------

def _get_logging_options(
    cdk_scope :Construct,
    tier :str,
    stk :Stack,
    subproj_name :str,
) -> aws_codebuild.LoggingOptions:
    return aws_codebuild.LoggingOptions(
        cloud_watch = aws_codebuild.CloudWatchLoggingOptions(
            enabled=True,
            log_group=get_log_grp(
                scope = cdk_scope,
                tier = tier,
                loggrp_type = LogGroupType.CodeBuild,
                what_is_being_logged=f'{stk.stack_name}-{subproj_name}',
            )
        )
    )

def _get_codebuild_linux_image(
    tier :str,
    cpu_arch :aws_lambda.Architecture,
) -> aws_codebuild.IBuildImage:
    # if tier in constants.STD_TIERS:
    match cpu_arch.name:
        case aws_lambda.Architecture.ARM_64.name: return constants_cdk.CODEBUILD_BUILD_IMAGE
        case aws_lambda.Architecture.X86_64.name: return constants_cdk.CODEBUILD_BUILD_IMAGE_X86
        case _: raise ValueError(f"Unsupported CPU architecture '{cpu_arch.name}'")


def _cache_chk_n_clean_cmd() -> str:

    """ nicely-compacted 1-liner bash-command that is a COMPLEX for-loop.
        NOTE: cache-cleanup -MUST- be done before doing any builds/cdk-synth/cdk-deploy within CodeBuild.
        FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
    """

    return "${CODEBUILD_SRC_DIR}/devops/bin/CodeBuild-InstallPhase-CleanUpOld-cmds.sh"

    ### The following (basically inline-bash-cmds used as-is within CodeBuild's commands) .. was getting TOO LARGE!!
    ### Hence the following has been replaced with a bash-script (see above)
    ###    The uncompacted-string in here, is for human-friendly editing.
    # one_liner_bash_cmd = f"""
    #     echo 'Checking cache age...';
    #     for dir in   .venv   node_modules   ~/.local/share/virtualenvs  .pipenv; do
    #         if [ -d "$dir" ]; then
    #             dir_age=$(find "$dir" -maxdepth 0 -mtime +1);
    #             if [ ! -z "$dir_age" ]; then
    #                 echo "Cache directory $dir is older than 24 hours, clearing...";
    #                 rm -rf "$dir";
    #             else
    #                 echo "Cache directory $dir is fresh (less than 24 hours old)";
    #             fi
    #         fi
    #     done
    #     """

#     return " ".join( one_liner_bash_cmd.split() ) ### split() and join() will replace \s+ with a single-whitespace-char!


def _pip_or_pipenv_install_cmd() -> str:

    """ nicely-compacted 1-liner bash-command that is a COMPLEX for-loop.
    """

    ### !! ATTENTION !! `venv` is installed into  `.`     and !! NOT !! into the traditional ~~.venv~~
    ### .venv/ can NOT be a symlink (which is what CodeBuild does to CACHED-folders)
    ### Hence we TRICK `python/pip` by `cd` into that symlink, and install `venv` module into `.` (a.k.a. CWD)
    ###    The uncompacted-string in here, is for human-friendly editing.
    one_liner_bash_cmd = """
            if [ -f requirements.txt ]; then
                mkdir -p .venv; cd .venv;
                python -m venv .;
                cd ..;
                .   .venv/bin/activate;
                pip install -r requirements.txt;
            elif [ -f Pipfile.lock ]; then
                pip install pipenv --user;
                pipenv sync --dev;
            else
                echo 'Both requirements.txt and Pipfile.lock are MISSING';
                exit 111;
            fi;
        """

    return " ".join( one_liner_bash_cmd.split() ) ### split() and join() will replace \s+ with a single-whitespace-char!


@unique
class _ArchiveCmds(Enum):
    CREATE_TARFILE = (auto(),),
    UN_TAR = (auto(),),

def _zip_cmds_re_cached_fldrs(
    tier :str,
    cmd1 :_ArchiveCmds,
    sub_proj_fldrpath :str,
    whether_to_use_adv_caching :bool,
    bucket_name :str,
) -> list[str]:
    """ internal-use only utility.
        All folders (like node_modules & python's venv) that do NOT work when cached, are to be zipped and restored via scripts.
    """
    retstr = f"""${{CODEBUILD_SRC_DIR}}/devops/bin/CodeBuild-InstallPhase-Archive-cmds.sh
        \"{tier}\"
        \"{ "un-tar" if ( cmd1.name == _ArchiveCmds.UN_TAR.name ) else "create-tar" }\"
        \"{ sub_proj_fldrpath }\"
        \"{ whether_to_use_adv_caching }\"
        \"{ bucket_name }\" ;
    """
    retstr = " ".join( retstr.split() )
    return retstr

    ### The following (basically inline-bash-cmds used as-is within CodeBuild's commands) .. was getting TOO LARGE!!
    ### Hence the following has been replaced with a bash-script (see above)
    # if not whether_to_use_adv_caching:
    #     return "echo \"--NO-- advanced-caching (for node_modules and python's-venv)\""

    # fldr_list = [
    #     "node_modules",
    #     ".venv"
    # ]
    # retstr = "pwd; ls -la; ls -la $( readlink node_modules ); "
    # for ddd in fldr_list:
    #     if cmd1:
    #         # retstr += f"date; tar -xf ./{ddd}.tar {sub_proj_fldrpath}/{ddd}; "
    #         retstr += f"date; tar -xf $( readlink ./{ddd}.tar ) {sub_proj_fldrpath}/{ddd}; "
    #     else:
    #         retstr += f"date; tar -cf ./{ddd}.tar {sub_proj_fldrpath}/{ddd}; "
    # retstr += " date; "
    # return retstr



def _gen_NodeJSCodeBuild_cache_fldrs_list(
    whether_to_use_adv_caching :bool,
    sub_proj_fldrpath :str,
) -> str:

    """ internal-use only utility.
        Generate (as appropriate based on `whether_to_use_adv_caching` bool-param) ..
            .. the list of folder-paths to CACHE within CodeBuild-PROJECT.
        Folder-paths for BOTH node_modules ONLY (for NodeJS-only CodeBuild-projects)
    """

    if whether_to_use_adv_caching:
        cb_cache = {
            "paths": []
        }
        fldr_list = ["."]
        if not sub_proj_fldrpath == '.':
            fldr_list.append(sub_proj_fldrpath)
        for ddd in fldr_list:
            cb_cache["paths"].append(
                f"{ddd}/{constants_cdk.CODEBUILD_FILECACHE_FLDRPATH}/**/*", ### CodeBuild only caches Folders. So, files have to be put into a folder!
            )
    else:
        cb_cache = None

    return cb_cache


def _gen_PythonCodeBuild_cache_fldrs_list(
    whether_to_use_adv_caching :bool,
    sub_proj_fldrpath :str,
) -> str:

    """ internal-use only utility.
        Generate (as appropriate based on `whether_to_use_adv_caching` bool-param) ..
            .. the list of folder-paths to CACHE within CodeBuild-PROJECT.
        Folder-paths for BOTH node_modules as well as Python(pipenv/pip)
    """

    if whether_to_use_adv_caching:
        cb_cache = {
            "paths": []
        }
        fldr_list = ["."] # initialize
        if not sub_proj_fldrpath == '.':
            fldr_list.append(sub_proj_fldrpath)
        for ddd in fldr_list:
                cb_cache["paths"].append( f"{ddd}/{constants_cdk.CODEBUILD_FILECACHE_FLDRPATH}/**/*" ) ### CodeBuild only caches Folders. So, files have to be put into a folder!
                cb_cache["paths"].append( f"{ddd}/.pipenv/**/*" )  # Add this for pipenv cache
                ### .venv/ can NOT be a symlink (which is what CodeBuild does to CACHED-folders)
                ### .node_modules/ can NOT be a symlink (which is what CodeBuild does to CACHED-folders)
                # cb_cache["paths"].append( f"{ddd}/node_modules/**/*" )
                # cb_cache["paths"].append( f"{ddd}/.venv/**/*" )
        ### This line below is FIXED path from user-home-dir
        cb_cache["paths"].append( "~/.local/share/virtualenvs/**/*" ) # Add this re: pipenv cache
    else:
        cb_cache = None

    return cb_cache


### ---------------------------------------------------------------------------------
def standard_CodeBuildDeploy_AWS_SAM(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    stack_name :str,
    source_artifact :codepipeline.Artifact,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    addl_env_vars :dict[str,str] = {},
    nodejs_version :str = constants_cdk.CDK_NODEJS_VERSION,
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        Simple AWS-SAM build AWS-SAM deploy only.
        Simple AWS-SAM build AWS-SAM deploy only.
        Simple AWS-SAM build AWS-SAM deploy only.
        This variation is for -BOTH- Python & MNodeJS/TypeScript based AWS-SAM-projects

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        4th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
        5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
        6th param:  stack_name   :str  => explicitly specifying the stack_name
        7th param"  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        8th param:  (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        9th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        10th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        11th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)
        Returns on objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_CodeBuildDeploy_AWS-SAM(): "
    stk = Stack.of(cdk_scope)

    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}"
    print( f"cb_proj_name='{cb_proj_name}'" )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    ### Full Deploy only
    ### automatically detect if Git-Repo-codebase is using Plain-Pip (and .venv) or whether the Git-Repo-Codebase is using Pipenv/Pifile
    aws_sam_build_n_deploy  =  " sam build; "
    aws_sam_build_n_deploy += f" sam deploy --stack-name \"{stack_name}\" "
    aws_sam_build_n_deploy += f" --parameter-overrides Tier=\"{tier}\" DateTimeStamp=\"{constants_cdk.BUILD_KICKOFF_TIMESTAMP_LOCAL_STR}\""
    aws_sam_build_n_deploy += f" --capabilities CAPABILITY_NAMED_IAM --no-confirm-changeset --on-failure DELETE"

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope = cdk_scope,
        id    = f'{subproj_name}-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',
        build_spec=aws_codebuild.BuildSpec.from_object({
            'version': '0.2',
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'nodejs': nodejs_version,
                    },
                    'commands': [

                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f'cd {sub_proj_fldrpath}',
                        "pwd",
                        "env",

                        'npm --version; node --version; npx cdk --version',
                    ],
                },
                'build': {
                    'commands': [ aws_sam_build_n_deploy ]
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                }
            },
            # 'artifacts': {
            #     'base-directory': f'{sub_proj_fldrpath}/????????',
            #     'files': ['**/*']
            # },
            "cache": _gen_NodeJSCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath )
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment(
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = _get_codebuild_linux_image( tier, cpu_arch ),
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                **addl_env_vars,
            }
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_AWSSAM_Deploy_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk ) ### cdk_scope=cb_project, tier=tier, )

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)

    return my_build_action, my_build_output


### ---------------------------------------------------------------------------------
def standard_CodeBuildSynth_NodeJS(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    addl_env_vars :dict[str,str] = {},
    nodejs_version :str = constants_cdk.CDK_NODEJS_VERSION,
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        Simple CDK-Synth only.
        Simple CDK-Synth only.
        Simple CDK-Synth only.
        -NO- Caching supported.  -NO- cdk-deploy included.
        This variation is for NodeJS-based CDK-projects

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        4th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
        5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
        6th param"  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        7th param:  (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        8th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        9th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        10th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)
        Returns on objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_CodeBuildSynth_NodeJS(): "
    stk = Stack.of(cdk_scope)

    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}"
    print( f"cb_proj_name='{cb_proj_name}'" )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    ### Synth only
    ### automatically detect if Git-Repo-codebase is using Plain-Pip (and .venv) or whether the Git-Repo-Codebase is using Pipenv/Pifile
    cdk_synth_command  =  " npx cdk synth  --quiet --all"
    cdk_synth_command +=  " --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_synth_command += f" --context TIER=\"{tier}\""
    cdk_synth_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_synth_command += f" --context git_repo=\"{git_repo_url}\""

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope = cdk_scope,
        id    = f'{subproj_name}-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',
        build_spec=aws_codebuild.BuildSpec.from_object({
            'version': '0.2',
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'nodejs': nodejs_version,
                    },
                    'commands': [

                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f'cd {sub_proj_fldrpath}',
                        "pwd",
                        "env",

                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.UN_TAR, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### Downloads TAR-files and un-tars them (acting like custom-cache mechanism)
                        ### cache-cleanup before doing anything else
                        ### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
                        _cache_chk_n_clean_cmd(),

                        'npm --version; node --version; npx cdk --version',
                        'npm i --include-dev',
                    ],
                },
                'build': {
                    'commands': [ cdk_synth_command ]
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                }
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },
            "cache": _gen_NodeJSCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath )
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment(
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = _get_codebuild_linux_image( tier, cpu_arch ),
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                **addl_env_vars,
            }
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk ) ### cdk_scope=cb_project, tier=tier, )

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
def standard_CodeBuildSynth_Python(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
    addl_env_vars :dict[str,str] = {},
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        Simple CDK-Synth only.
        Simple CDK-Synth only.
        Simple CDK-Synth only.
        -NO- Caching supported.  -NO- cdk-deploy included.
        This variation is for simple Python-based CDK-projects.

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        4th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
        5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
        6th param:  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        7th param: (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        8th param:  OPTIONAL: python_version # as a string
        9th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        10th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        11th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)
        Returns on objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_CodeBuildSynth_Python(): "
    stk = Stack.of(cdk_scope)

    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}"
    print( f"cb_proj_name='{cb_proj_name}'" )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    ### Synth only
    ### automatically detect if Git-Repo-codebase is using Plain-Pip (and .venv) or whether the Git-Repo-Codebase is using Pipenv/Pifile
    cdk_synth_command  =  "if [ -f requirements.txt ]; then PRFX=\"\"; elif [ -f Pipfile.lock ]; then PRFX=\"pipenv run\"; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; "
    cdk_synth_command +=  "$PRFX npx cdk synth  --quiet --all"
    cdk_synth_command +=  " --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_synth_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_synth_command += f" --context git_repo=\"{git_repo_url}\""

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope = cdk_scope,
        id    = f'{subproj_name}-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            'version': 0.2,
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable",
                    "PIPENV_CACHE_DIR": ".pipenv/pipcache", ## LOCAL-DIR location for Pipenv to store it’s package cache. Default is to use appdir’s user cache directory.
                    "WORKON_HOME": ".pipenv/venvs" ### https://docs.pipenv.org/advanced/#custom-virtual-environment-location
                }
            },
            "phases": {
                'install': {
                    'runtime-versions': {
                        "python": python_version
                    },
                    'commands': [

                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        "env",

                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.UN_TAR, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### Downloads TAR-files and un-tars them (acting like custom-cache mechanism)
                        # cache-cleanup before doing anything else
                        ### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
                        _cache_chk_n_clean_cmd(),

                        'npm i --include-dev',

                        "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        _pip_or_pipenv_install_cmd(),
                        ### ERROR: Pip Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
                        ###     Courtesy Notice: Pipenv found itself running within a virtual environment,  so it will automatically use that environment, instead of  creating its own for any project.
                        ###     You can set PIPENV_IGNORE_VIRTUALENVS=1 to force pipenv to ignore that environment and create  its own instead.
                        ###     You can set PIPENV_VERBOSITY=-1 to suppress this warning.
                        'npm --version; node --version; python --version; pip --version',
                        "if [ -f requirements.txt ]; then npx cdk --version; elif [ -f Pipfile.lock ]; then pipenv run npx cdk --version; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; ",
                    ],
                },
                'build': {
                    'commands': [ cdk_synth_command ]
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                },
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },
            "cache": _gen_PythonCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath )
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment(
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = _get_codebuild_linux_image( tier, cpu_arch ),
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                **addl_env_vars,
            }
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk ) ### cdk_scope=cb_project, tier=tier, )

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
def adv_CodeBuildCachingSynthAndDeploy_Python(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Optional[Union[str,pathlib.Path]],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    git_repo_url :Optional[str] = None,
    cdk_app_pyfile :Optional[str] = None,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
    addl_env_vars :dict[str,str] = {},
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
    addl_cdk_context :dict[str,str] = {},
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        Single "CodePipeline" Action, that will use `venv` to CACHE the pip-install, and then do BOTH cdk-synth + cdk-deploy.

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        4th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
                    Can also be None!
        5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is finally deployed, DEFINE what the CodeBuild-Project should be named (as viewed within CodeBuild-CONSOLE).
        6th param:  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        7th param: (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        8th param:  OPTIONAL: git_repo_url :str -- ghORG/gitRepoName.git
        9th param:  OPTIONAL: cdk_app_pyfile :str -- Example: all_pipelines.py (this is located in root-folder of git-repo)
        10th param:  OPTIONAL: python_version# as a string
        11th param:  (OPTIONAL) addl_env_vars :dict -- pass in Env-Vars to CodeBuild
        12th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        13th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        14th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)
        15th param:  OPTIONAL: addl_cdk_context -- equivalent of "-c CTX_KEY='..' "  CDK-CLI command args
        Returns on objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_CodeBuildSynthAndDeploy_Python(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}"
    print( f"cb_proj_name='{cb_proj_name}'" )

    stk = Stack.of(cdk_scope)

    ### --------------------------
    ### automatically detect if Git-Repo-codebase is using Plain-Pip (and .venv) or whether the Git-Repo-Codebase is using Pipenv/Pifile
    cdk_deploy_command  =  " if [ -f requirements.txt ]; then PRFX=\"\"; elif [ -f Pipfile.lock ]; then PRFX=\"pipenv run\"; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; "
    cdk_deploy_command +=  " $PRFX npx cdk deploy  --quiet --all"
    cdk_deploy_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"

    cdk_deploy_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_deploy_command += f" --context git_repo=\"{git_repo_url}\""
    for key in addl_cdk_context.keys():
        cdk_deploy_command += f" --context {key}=\"{addl_cdk_context.get(key)}\""

    if cdk_app_pyfile:   cdk_deploy_command += f" --app \"python3 {cdk_app_pyfile}\""

    ### --------------------------
    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    artif_name = re.sub(r'[^\w\s]', '', artif_name) ### Artifact-name has restrictions/
    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope = cdk_scope,
        id    = f'{subproj_name}-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            'version': 0.2,
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable",
                    "PIPENV_CACHE_DIR": ".pipenv/pipcache", ## LOCAL-DIR location for Pipenv to store it’s package cache. Default is to use appdir’s user cache directory.
                    "WORKON_HOME": ".pipenv/venvs" ### https://docs.pipenv.org/advanced/#custom-virtual-environment-location
                }
            },
            "phases": {
                'install': {
                    'runtime-versions': {
                        "python": python_version
                    },
                    'commands': [

                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        "env",

                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.UN_TAR, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### Downloads TAR-files and un-tars them (acting like custom-cache mechanism)
                        # cache-cleanup before doing anything else
                        ### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
                        _cache_chk_n_clean_cmd(),

                        "npm i --include-dev",

                        "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        _pip_or_pipenv_install_cmd(),
                        ### ERROR: Pip Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
                        ###     Courtesy Notice: Pipenv found itself running within a virtual environment,  so it will automatically use that environment, instead of  creating its own for any project.
                        ###     You can set PIPENV_IGNORE_VIRTUALENVS=1 to force pipenv to ignore that environment and create  its own instead.
                        ###     You can set PIPENV_VERBOSITY=-1 to suppress this warning.
                        'npm --version; node --version; python --version; pip --version',
                        "if [ -f requirements.txt ]; then npx cdk --version; elif [ -f Pipfile.lock ]; then pipenv run npx cdk --version; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; ",
                        f"jq '.context.[\"git-source\"].git_commit_hashes.{tier}' cdk.json --raw-output",
                        'git checkout --force', ### to address ---> error: Your local changes to the following files would be overwritten by checkout: package-lock.json
                        f"git checkout $(jq '.context.[\"git-source\"].git_commit_hashes.{tier}' cdk.json --raw-output)",
                    ],
                },
                'build': {
                    'commands': [ cdk_deploy_command ]
                    ### NOTE !! cdk deploy is expected via function-parameter-inputs/
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                },
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },

            "cache": _gen_PythonCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath )
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment(
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = _get_codebuild_linux_image( tier, cpu_arch ),
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                **addl_env_vars,
            }
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout=Duration.minutes(120),
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name = f'Adv_CDKSynthDeploy_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input   = source_artifact,
        outputs = [my_build_output],
        project = cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk ) ### cdk_scope=cb_project, tier=tier, )

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
def standard_CodeBuildSynthDeploy_FrontendPythonCDK(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Optional[Union[str,pathlib.Path]],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    cdk_app_pyfile :Optional[str] = None,
    nodejs_version :str = constants_cdk.FRONTEND_NODEJS_VERSION,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
    frontend_vuejs_rootfolder :str = "frontend/ui",
    addl_env_vars :dict[str,str] = {},
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        Simple CDK-Synth only. -NO- Caching supported.  -NO- cdk-deploy included.
        This variation is for WIERD-combination of:
            1. frontend is written in TypeScript (and so .. npm commands!)
            2. cdk-synth/deploy is via Python-based CDK-codebase ( and so .. .. pip!)

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        4th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
                    Can also be None!
        5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
        6th param:  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        7th param: (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        8th param:  OPTIONAL: cdk_app_pyfile :str -- Example: all_pipelines.py (this is located in root-folder of git-repo)
        9th param:  OPTIONAL: python_version # as a string
        10th param:  OPTIONAL: where is the JS/TS/VueJS/ReactJS code-base located in this git-repo;  Default = "frontend/ui"
        11th param:  (OPTIONAL) addl_env_vars :dict -- pass in Env-Vars to CodeBuild
        12th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        13th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        14th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)
        Returns on objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_CodeBuildSynth_FrontendPythonCDK(): "
    stk = Stack.of(cdk_scope)

    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}"
    print( f"cb_proj_name='{cb_proj_name}'" )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    ### automatically detect if Git-Repo-codebase is using Plain-Pip (and .venv) or whether the Git-Repo-Codebase is using Pipenv/Pifile
    cdk_deploy_command  =  "if [ -f requirements.txt ]; then PRFX=\"\"; elif [ -f Pipfile.lock ]; then PRFX=\"pipenv run\"; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; "
    cdk_deploy_command +=  "$PRFX npx cdk deploy  --quiet --all"
    if cdk_app_pyfile:   cdk_deploy_command += f" --app \"python3 {cdk_app_pyfile}\""
    cdk_deploy_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_deploy_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_deploy_command += f" --context git_repo=\"{git_repo_url}\""

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope=cdk_scope,
        id=f'{subproj_name}-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            'version': 0.2,
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable",
                    "PIPENV_CACHE_DIR": ".pipenv/pipcache", ## LOCAL-DIR location for Pipenv to store it’s package cache. Default is to use appdir’s user cache directory.
                    "WORKON_HOME": ".pipenv/venvs" ### https://docs.pipenv.org/advanced/#custom-virtual-environment-location
                }
            },
            "phases": {
                'install': {
                    'runtime-versions': {
                        'python': python_version,
                        'nodejs': nodejs_version,
                    },
                    'commands': [

                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        "env",

                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.UN_TAR, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### Downloads TAR-files and un-tars them (acting like custom-cache mechanism)
                        # cache-cleanup before doing anything else
                        ### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
                        _cache_chk_n_clean_cmd(),

                        'npm i --include-dev',

                       "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        _pip_or_pipenv_install_cmd(),
                        ### ERROR: Pip Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
                        ###     Courtesy Notice: Pipenv found itself running within a virtual environment,  so it will automatically use that environment, instead of  creating its own for any project.
                        ###     You can set PIPENV_IGNORE_VIRTUALENVS=1 to force pipenv to ignore that environment and create  its own instead.
                        ###     You can set PIPENV_VERBOSITY=-1 to suppress this warning.
                        'npm --version; node --version; python --version; pip --version',
                        "if [ -f requirements.txt ]; then npx cdk --version; elif [ -f Pipfile.lock ]; then pipenv run npx cdk --version; else echo 'Both requirements.txt and Pipfile.lock are MISSING'; exit 111; fi; ",
                    ],
                },
                'build': {
                    'commands': [
                        ### 1st create frontend JS/TS/Vuejs/Reactjs deployable

                        f"cd {frontend_vuejs_rootfolder}",    ### go into a subfolder!
                        # f"pushd {frontend_vuejs_rootfolder}",    ### error: pushd: not found

                        "npm install @vue/cli",
                        "npm i ",
                        "npm run build",

                        "cd ../..",  ### return back to "project-root"
                        # "popd",  ###  error: pushd: not found

                        ### cdk-deploy (that uses the frontend-deployable created above)
                        cdk_deploy_command,
                    ]
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                },
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },
            "cache": _gen_PythonCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath )
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment(
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = _get_codebuild_linux_image( tier, cpu_arch ),
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                **addl_env_vars,
            }
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout=Duration.minutes(120),
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_NpmBuild_CDKSynthDeploy_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk ) ### cdk_scope=cb_project, tier=tier, )

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------

def standard_BDDs_JSTSVuejsReactjs(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    git_branch :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    frontend_website_url :str,
    test_user_sm_name :str,
    cpu_arch :aws_lambda.Architecture = aws_lambda.Architecture.ARM_64,
    frontend_vuejs_rootfolder :str = "frontend/ui",
    addl_env_vars :dict[str,str] = {},
    whether_to_use_adv_caching :bool = False,
    my_pipeline_artifact_bkt :Optional[aws_s3.IBucket] = None,
    my_pipeline_artifact_bkt_name :Optional[str] = None,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:
    """
        -NO- CDK !!
        Just BDDs via Frontend / Chromium based JS/TS frameworks.

        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  tier :str           => (dev|int|uat|tier)
        3rd param:  aws_env :str        => AWS_Account ID or a well-agreed common AWS-Profile
        4th param:  git_branch :str     => the specific branch's code that is being deployed-n-BDD-tested inside CodeBuild
        5th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        6th param:  subproj_name :str     => typically the sub-folder's name
                    /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
        7th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
        8th param:  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
        9th param:  frontend_website_url :str => The URL of the frontend website being tested.
        10th param:  test_user_sm_name :str -- Name of SM entry (containing creds to a SIMULATED END-USER for BDDs).
                            Example: f"{constants.CDK_APP_NAME}/{tier}/testing/frontend/test_user"
        11th param: (OPTIONAL) cpu_arch :aws_lambda.Architecture => OPTIONAL;  Default=aws_lambda.Architecture.ARM_64
        12th param:  OPTIONAL: frontend_vuejs_rootfolder :str -- where is the JS/TS/VueJS/ReactJS code-base located in this git-repo;  Default = "frontend/ui"
        13th param:  (OPTIONAL) whether_to_use_adv_caching :bool -- since CodeBuild can --NOT-- cache "node_modules" and python's "venv", 'True' will turn on VERY ADVANCED HARD-to-FOLLOW caching, that could come to bit your ass later.
        14th param: (OPTIONAL) my_pipeline_artifact_bkt :aws_s3;IBucket (only used for advanced-caching)
        15th param: (OPTIONAL) my_pipeline_artifact_bkt_name :str -- NAME of above bucket-param (only used for advanced-caching)

        Returns 2 objects of types:-
                    1. codepipeline_actions.CodeBuildAction
                    3. codepipeline.Artifact (representing the BUILD-Artifact)
    """

    HDR = " : standard_BDDs_JSTSVuejsReactjs(): "
    stk = Stack.of(cdk_scope)

    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )
    print( f"CPU-ARCH (Enum) ='{cpu_arch.name}'" )
    cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
    print( f"CPU_ARCH(str) = '{cpu_arch_str}'" )
    cb_proj_name += f"-{cpu_arch_str}";
    print( f"cb_proj_name='{cb_proj_name}'" );
    if not cpu_arch.name == aws_lambda.Architecture.X86_64.name:
        raise Exception( f"param CPU-ARCH (Enum) = '{cpu_arch.name}' and should be X86 ONLY !!! within "+ HDR )

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("BDDs_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope = cdk_scope,
        id    = f'{subproj_name}-BDDs-CodeBuild-{cpu_arch_str}',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',
        build_spec=aws_codebuild.BuildSpec.from_object({
            'version': '0.2',
            'env': {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "secrets-manager": {
                    "EMFACT_PASSWORD_CCDI": "$TEST_PROVIDER_SM:EMFACT_PASSWORD_CCDI",
                },
                "variables": { ### If 'env' is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable",
                    "ENDPOINT_URL": frontend_website_url,
                    # "STAGE": tier, ### LEGACY !!! QE-team's standardized env-variable, is set inside `phases` below.
                    # "tier": tier,  ### ! Warning ! QE-team prefers it hardcoded INSIDE `phases` below.
                    # "aws_env": aws_env,
                    # "git_branch": git_branch,
                },
            },
            'phases': {
                'install': {
                    'commands': [

                        f'cd {sub_proj_fldrpath}',
                        "pwd",
                        "env",

                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.UN_TAR, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### Downloads TAR-files and un-tars them (acting like custom-cache mechanism)
                        # cache-cleanup before doing anything else
                        ### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
                        _cache_chk_n_clean_cmd(),

                        'npm i --include-dev',
                        'npm --version; node --version; npx cdk --version',
                    ],
                },
                'build': {
                    'commands': [
                        ### Per https://github.com/aws/aws-codebuild-docker-images/issues/562
                        "wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
                        "apt-get update -y",
                        "apt-get install -y ./google-chrome*.deb",
                        "which google-chrome",
                        "which google-chrome-stable",

                        "echo ==== frontend_url ====",
                        "echo $ENDPOINT_URL",
                        "echo ==============",
                        f"export STAGE={tier}",
                        "echo ==== STAGE ====",
                        "echo $STAGE",
                        "echo ==== tier ====",
                        f"export TIER={tier}; export tier={tier}",
                        "echo TIER=$TIER",
                        "echo tier=$tier",
                        "echo ==== AWS-Environment ====",
                        f"export aws_env={aws_env}",
                        "echo $aws_env",
                        "echo ==== Git-branch ====",
                        f"export git_branch={git_branch}",
                        "echo $git_branch",
                        "echo ==============",
                        "echo $EMFACT_PASSWORD_CCDI",
                        "echo ==============",
                        # "curl -Ssf $ENDPOINT_URL",
                        # "curl -s -o /dev/null -D -  $ENDPOINT_URL/api/v1/biomarkers",
                        # "sleep 30",
                        # "curl -s -o /dev/null -D -  $ENDPOINT_URL/api/v1/biomarkers",
                        "cd tests/bdd_tests",
                        "export PROJECT_ROOT=$(pwd)",
                        "echo $PROJECT_ROOT",
                        '/bin/bash -c "source scripts/system_setup.sh && install_dependencies" ',
                        "ls -alt",
                        '/bin/bash -c "source scripts/run_test.sh && db_warmup" ',
                        '/bin/bash -c "source scripts/run_test.sh && run_ccdi_bdd_tests" ',
                    ]
                },
                'post_build': {
                    'commands': [
                        ### Just for node_modules & python-venv, we have a WORKAROUND for caching  zip-up the folder (as appropriate) before/after doing anything else.
                        _zip_cmds_re_cached_fldrs( tier, _ArchiveCmds.CREATE_TARFILE, sub_proj_fldrpath, whether_to_use_adv_caching, my_pipeline_artifact_bkt_name ),
                                                    ### ONLY if necessary, creates '.tar' files, and uploads to S3-bucket
                    ]
                }
            },
            "reports": {
                "cucumber_reports": {
                    "files": "cucumber-output-chromeHeadless.json",
                    "base-directory": "tests/bdd_tests/cucumber_results",
                    "file-format": "CUCUMBERJSON",
                }
            },
            "cache": _gen_NodeJSCodeBuild_cache_fldrs_list( whether_to_use_adv_caching, sub_proj_fldrpath ),
                ### REF: https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html#caching-local
                ### In above URL, you'll note that "aws_codebuild.LocalCacheMode.CUSTOM" === "local caching"
                ### In above URL, you'll note that .. Only directories can be specified for caching. You cannot specify individual files.
                ### In above URL, you'll note that .. Local caching is --NOT-- supported when CodeBuild runs in --VPC-- !!!
                ### NOTE: Avoid directory names that are the same in the source and in the cache.
        }),
        cache = aws_codebuild.Cache.local( aws_codebuild.LocalCacheMode.CUSTOM ),
                ### This above line converts to following CloudFormation:
                ###        "Cache": {
                ###             "Type": "LOCAL",
                ###             "Modes": [ "LOCAL_CUSTOM_CACHE" ]
                ###        },

        environment=aws_codebuild.BuildEnvironment( ### What kind of machine or O/S to use for CodeBuild
            privileged   = (cpu_arch.name == aws_lambda.Architecture.X86_64.name), ### Docker running on -ONLY- X86-based EC2s/CodeBuild-images.  Do NOT ask why!!!
            build_image  = constants_cdk.CODEBUILD_BUILD_IMAGE_UBUNTU, ### <--------- Chromium-headless REQUIRES Ubuntu. -NOT- AmznLinux !!!!!!!!!!!!!!!!!!
            compute_type = constants_cdk.CODEBUILD_EC2_SIZE,
            environment_variables = {
                "TIER":     aws_codebuild.BuildEnvironmentVariable( value=tier, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                # "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable( value=cpu_arch_str, type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                "CPU_ARCH": aws_codebuild.BuildEnvironmentVariable(
                    value = get_cpu_arch_as_str(aws_lambda.Architecture.X86_64), ### <----------- Warning: CPU id hardcoded !!!!!!!!!!
                    type  = aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
            }
        ),
        environment_variables={
            "TEST_PROVIDER_SM": aws_codebuild.BuildEnvironmentVariable(
                # type=aws_codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                value=test_user_sm_name,
            ),
            "DEBIAN_FRONTEND": aws_codebuild.BuildEnvironmentVariable(
                type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                value="noninteractive",                                 ### apt-get be quieter
            ),
            **addl_env_vars,
        },
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout = constants_cdk.BDD_CODEBUILD_TIMEOUT,
    )
    if whether_to_use_adv_caching:
        my_pipeline_artifact_bkt.grant_read_write( cb_project )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'BDDs_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    ### -----------------------------
    test_user_sm = aws_secretsmanager.Secret.from_secret_name_v2(
        scope = cdk_scope,
        id = 'TestUserHidden',
        secret_name = test_user_sm_name)

    test_user_sm.grant_read(cb_project.grant_principal)

    Tags.of(cb_project).add(key="ResourceName", value =stk.stack_name+"-CodeBuild-"+cb_proj_name)
    return my_build_action, my_build_output


### ---------------------------------------------------------------------------------------------
### =============================================================================================
### ---------------------------------------------------------------------------------------------

def enhance_CodeBuild_role_for_cdkdeploy(
    cb_role :aws_iam.Role,
    stk :Stack,
    # cdk_scope :Construct,
    # tier :str,
) -> aws_iam.Role:
    """ To run `cdk deploy` from within CodeBuild, we need a LOT of permissions (to create & destroy)
    """

    ### To fix the error: ❌  {CDK_APP_NAME}-backend-dev-SNSStack failed: AccessDenied: User: arn:aws:sts::???:assumed-role/{CDK_APP_NAME}-backend-pipeline-dev-emFACTbackendcdkCodeBuild-???/AWSCodeBuild-2da0a582-???
    ###         is not authorized to perform: iam:PassRole
    ###         on resource: arn:aws:iam::??????:role/cdk-hnb659fds-cfn-exec-role-??????-??????
    ###         because no identity-based policy allows the iam:PassRole action
    ###   User: arn:aws:sts::{AccountId}:assumed-role/{CDK_APP_NAME}-devops-pipeline-sarm-CdkscleanupOrphanResource-{UUID}/AWSCodeBuild-{UUID}++ is not authorized to perform: iam:PassRole on resource: arn:aws:iam::{AAccountId}:role/{CDK_APP_NAME}-devops-sarma-CleanupOrphanRes-MyLambdaFuncRole
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions = ["iam:PassRole"], ### PassRole vs. AssumedRole(see next policy below)
            resources = [
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-cfn-exec-role-{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-deploy-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-file-publishing-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-image-publishing-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-lookup-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/{constants.CDK_APP_NAME}-*", ### ... devops-{tier}-*-CleanupOrphanRes-MyLambdaFuncRole*",
                f"arn:{stk.partition}:iam::{stk.account}:role/wipeout-bucket*", ### ... devops-{tier}-*-CleanupOrphanRes-MyLambdaFuncRole*",
                f"arn:{stk.partition}:iam::{stk.account}:role/sleep-random*", ### ... devops-{tier}-*-CleanupOrphanRes-MyLambdaFuncRole*",
    ]))
    ### To fix the error: ❌ current credentials could not be used to assume
    ###         'arn:aws:iam::?????:role/cdk-hnb659fds-file-publishing-role-??????-??????',
    ###         but are for the right account. Proceeding anyway.
    ## ..
    ## ..
    ### 👉🏾👉🏾👉🏾 You need to UPDATE that "file-publishing" Role -- add this "cb_role" as one of the Principals who can sts:Assume that file-publishing-role
    ###    {
    ###        "Version": "2008-10-17",
    ###        "Statement": [
    ###            {
    ###                "Effect": "Allow",
    ###                "Principal": {
    ###                    "AWS": [
    ###                        "arn:aws:iam::??????:root",
    ###                        "arn:aws:iam::??????:role/{CDK_APP_NAME}-backend-pipeline-dev-emFACTbackendcdkCodeBuild-????????????????????????"
    ###                    ]
    ###                },
    ###                "Action": "sts:AssumeRole",
    ###                "Condition": {
    ###                    "ArnLike": {
    ###                        "aws:PrincipalArn": "arn:aws:iam::??????:role/FACT-backend-pipeline-*-emFACTbackendcdkCodeBuild-*"
    ###                    }
    ###                }
    ###            }
    ###        ]
    ###    }


    ### To fix the error: This CDK deployment requires bootstrap stack version '6', but during the confirmation via SSM parameter /cdk-bootstrap/hnb659fds/version the following error occurred: AccessDeniedException: User: arn:aws:sts::xxx:assumed-role/FACT-backend-pipeline-dev-emFACTbackendcdkCodeBuild-/AWSCodeBuild--bc6949a5cd77 is not authorized to perform: ssm:GetParameter on resource: arn:aws:ssm:??????:??????:parameter/cdk-bootstrap/hnb659fds/version because no identity-based policy allows the ssm:GetParameter action
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["kms:List*"],
            resources=["*"],
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["secretsmanager:*"],
            resources=[f"arn:{stk.partition}:secretsmanager:{stk.region}:{stk.account}:secret:{constants.CDK_APP_NAME}*"],
    ))
    ###     CREATE_FAILED  AWS::ApplicationInsights::Application   ApplicationInsightsMonitoring   Resource handler Resource handler returned message: "Missing necessary read permission. Please check here for more detail: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/appinsights-account-based-onboarding-permissions.html
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
                "ssm:PutParameter",
                "ssm:DeleteParameter",
            ],
            resources=[
                f"arn:{stk.partition}:ssm:{stk.region}:{stk.account}:parameter/cdk-bootstrap/*",
                f"arn:{stk.partition}:ssm:{stk.region}:{stk.account}:parameter/AmazonCloudWatch-ApplicationInsights-*"
            ],
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=[
                "logs:DescribeLogGroups",
                "logs:CreateLogGroup",
                "logs:PutRetentionPolicy",
            ],
            resources=[ "*" ]
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["cloudwatch:*"],
            resources=[
                f"arn:{stk.partition}:cloudwatch::{stk.account}:dashboard/*",
                f"arn:{stk.partition}:cloudwatch:{stk.region}:{stk.account}:alarm:*",
                f"arn:{stk.partition}:cloudwatch:{stk.region}:{stk.account}:service/:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["kms:Decrypt", "kms:Encrypt", "kms:CreateKey", "kms:DeleteAlias", "kms:ListAliases", "kms:PutKeyPolicy"],
            resources=[
                f"arn:{stk.partition}:kms:{stk.region}:{stk.account}:alias/*",
                f"arn:{stk.partition}:kms:{stk.region}:{stk.account}:key/*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["cloudformation:*"],
            resources=[
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/sleep-random*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/wipeout-bucket*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/StepFn-DeleteStacks*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/StepFn-Cleanup*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stackset/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/aws-sam-cli-managed-default/*", ### Running "sam deploy" within CodeBuild.
                f"arn:{stk.partition}:cloudformation:{stk.region}:aws:transform/Serverless-2016-10-31*", ### Running "sam deploy" within CodeBuild.
                                                                ### Note: "AccountId" == "aws"
                # f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:changeSet/*",
    ]))

    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["s3:*"],
            resources=[
                f"arn:{stk.partition}:s3:::cdk-*",
                f"arn:{stk.partition}:s3:::aws-sam-cli-managed-default-samclisourcebucket*", ### for running AWS-SAM deploy within CodeBuild
            ]
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=[
                "iam:Attach*", "iam:Detach*",
                "iam:Create*", "iam:Delete*",
                "iam:Get*", "iam:List*",
                "iam:Put*", "iam:UpdateRole*",
                "iam:Tag*", "iam:Untag*"
            ],
            resources=[
                f"arn:{stk.partition}:iam::{stk.account}:role/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:iam::{stk.account}:policy/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:iam::{stk.account}:role/wipeout-bucket*",
                f"arn:{stk.partition}:iam::{stk.account}:policy/wipeout-bucket*",
                f"arn:{stk.partition}:iam::{stk.account}:role/sleep-random*",
                f"arn:{stk.partition}:iam::{stk.account}:policy/sleep-random*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["cognito-idp:*"],
            resources=[
                f"arn:{stk.partition}:cognito-idp:{stk.region}:{stk.account}:userpool/{constants.CDK_APP_NAME}*",
    ]))
    # cb_role.add_to_principal_policy(
    #     aws_iam.PolicyStatement(
    #         actions=["cognito-identity:*"],
    #         resources=[
    #             f"arn:{stk.partition}:cognito-identity:{stk.region}:{stk.account}:identitypool/{constants.CDK_APP_NAME}*",
    # ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["codebuild:*"],
            resources=[
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:build/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:project/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:report/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:report-group/{constants.CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["codepipeline:*"],
            resources=[
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:action-type:*",
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:webhook:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["lambda:*"],
            resources=[
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function:sleep-random*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function:wipeout-bucket*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer/{constants.CDK_APP_NAME}*",
            # resources=[ f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer:{aws_names.gen_awsresource_name_prefix(tier)}*", ],
            # actions=[ "lambda:GetLayerVersion", "lambda:GetLayerVersionPolicy", "lambda:DeleteLayerVersion", ],
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=[ "lambda:ListLayers", "lambda:ListLayerVersions", "lambda:ListFunctions",  ],
            resources=["*"], ### Attention: This must be '*' unlike the previous policy above !!!
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["execute-api:*"],
            resources=[
                f"arn:{stk.partition}:execute-api:{stk.region}:{stk.account}:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["apigateway:*"],
            resources=[
                f"arn:{stk.partition}:apigateway:{stk.region}::*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["states:*"],
            resources=[
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:activity:*",
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:execution:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:express:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:stateMachine:{constants.CDK_APP_NAME}*",
                # f"arn:{stk.partition}:states:{stk.region}:{stk.account}:mapRun:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["rds:*"],
            resources=[
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:auto-backup:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:subgrp:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:snapshot:{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:db:{constants.CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["dynamodb:*"],
            resources=[
                f"arn:{stk.partition}:dynamodb:{stk.region}:{stk.account}:table/{constants.CDK_APP_NAME}*",
    ]))
    # cb_role.add_to_principal_policy(
    #     aws_iam.PolicyStatement(
    #         actions=["glue:*"],
    #         resources=[
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:job/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:trigger/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:crawler/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:catalog",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:registry/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:schema/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:workflow/*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:database/{constants.CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:table/{constants.CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:tableVersion/{constants.CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:userDefinedFunction/{constants.CDK_APP_NAME}*",
    # ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            sid="EC2ResourcesOnlyAccess",
            actions=["ec2:*"],
            resources=[
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:elastic-ip/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:network-interface/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:security-group/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:subnet/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:vpc/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:vpc-endpoint/*",
                f"arn:{stk.partition}:ec2:{stk.region}:{stk.account}:vpc-endpoint-connection/*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            sid="BasicVpcSubnetLookupAccess",
            actions=[
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSecurityGroupRules",
                "ec2:DescribeSubnets",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeTags",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeVpnGateways",
            ],
            resources=[ '*' ]
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            sid="CreateModifyVpcNewSubnetNewVPCEndpts",
            actions=[
                "ec2:CreateVpc",
                "ec2:DeleteVpc",
                "ec2:DescribeVpcBlockPublicAccessOptions",
                "ec2:ModifyVpcAttribute",
                "ec2:CreateSubnet",
                "ec2:DeleteSubnet",
                "ec2:ModifySubnetAttribute",
                "ec2:CreateTags",
                "ec2:DeleteTags",
                "ec2:DescribeRouteTables",
                "ec2:CreateRouteTable",
                "ec2:DeleteRouteTable",
                "ec2:AssociateRouteTable",
                "ec2:DisassociateRouteTable",
                "ec2:CreateRoute",
                "ec2:DeleteRoute",
                "ec2:CreateNetworkInterface",
                "ec2:DeleteNetworkInterface",
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeVpcEndpointServices",
                "ec2:DescribeVpcEndpointServiceConfigurations",
                "ec2:DescribeVpcEndpointConnectionNotifications",
                "ec2:CreateVpcEndpoint",
                "ec2:DeleteVpcEndpoints",
                "ec2:ModifyVpcEndpoint",
                ### Following are needed for using AWS IPAM (IP Address Manager) to allocate a `10.0.0.0/17` & `10.0.8.0/17` CIDR blocks
                "ec2:AssociateVpcCidrBlock",
                "ec2:DescribeVpcs",
                "ec2:DescribeIpamPools",
                "ec2:GetIpamPoolAllocations",
                "ec2:AllocateIpamPoolCidr",
            ],
            resources=[ '*' ],
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            sid="Rt53HostedDomainAccess",
            actions=[
                "route53:ListDomains*",
                "route53:ListHostedZone*",
                "route53:GetHostedZone*",
                "route53:GetChange",
                "route53:ListResourceRecordSet*",
                "route53:ChangeResourceRecordSets",
                "route53:ListTagsFor*",
                "route53:Update*",
            ],
            resources=[
                '*',
                # "arn:aws:route53:::hostedzone/*",
                # "arn:aws:route53:::change/*",
            ]
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            sid="ACMCertMgrAccess",
            actions=[
                "acm:RequestCertificate",
                "acm:DescribeCertificate",
                "acm:DeleteCertificate",
                "acm:AddTagsToCertificate",
                "acm:ListTagsForCertificate",
            ],
            resources= ["*"],
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["cloudfront:*"],
            resources=[
                f"arn:{stk.partition}:cloudfront::{stk.account}:distribution/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:origin-access-identity/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:field-level-*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:cache-policy/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:origin-access-control/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:origin-request-policy/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:response-headers-policy/*",
                f"arn:{stk.partition}:cloudfront::{stk.account}:function/*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["events:*"],
            resources=[
                f"arn:{stk.partition}:events:{stk.region}::event-source/*",
                f"arn:{stk.partition}:events:{stk.region}:{stk.account}:event-bus/*",
                f"arn:{stk.partition}:events:{stk.region}:{stk.account}:rule/*",
                f"arn:{stk.partition}:events:{stk.region}:{stk.account}:api-destination/*",
                f"arn:{stk.partition}:events:{stk.region}:{stk.account}:endpoint/*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["sns:*"],
            resources=[
                f"arn:{stk.partition}:sns:{stk.region}:{stk.account}:{constants.CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["sqs:*"],
            resources=[
                f"arn:{stk.partition}:sqs:{stk.region}:{stk.account}:{constants.CDK_APP_NAME}*",
    ]))
    ### To fix the error: User: arn:aws:sts::??????:assumed-role/FACT-backend-pipeline-dev-emFACTbackendcdkCodeBuild-???????/AWSCodeBuild-?????????????
    ###         is not authorized to perform: ecr:DescribeRepositories on resource:
    ###         arn:aws:ecr:??????:xxx:repository/cdk-xxx-container-assets-xxx-??????
    ###         because no identity-based policy allows the ecr:DescribeRepositories action
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["ecr:*"],
            resources=[ f"arn:{stk.partition}:ecr:{stk.region}:{stk.account}:repository/cdk-*-container-assets-{stk.account}-{stk.region}" ],
    ))
    ### FACT-backend-dev-StatelessETL: fail:
    ###     User: arn:aws:sts::????:assumed-role/FACT-backend-pipeline-dev-emFACTbackendcdkCodeBuild-????/AWSCodeBuild-????????????????????????????????????
    ###     is not authorized to perform: ecr:GetAuthorizationToken           on resource: *
    ###     because no identity-based policy allows the ecr:GetAuthorizationToken action
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken"],
            resources=[ "*" ],
    ))
    ### Since AWS-SAM template (and Lambda-Best-Practice) is to associate NEW-Lambdas with Resource-Groups ..
    ###     CREATE_FAILED  AWS::ApplicationInsights::Application   ApplicationInsightsMonitoring   Resource handler Resource handler returned message: "Missing necessary read permission. Please check here for more detail: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/appinsights-account-based-onboarding-permissions.html
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=[
                "resource-groups:CreateGroup",
                "resource-groups:UpdateGroup",
                "resource-groups:DeleteGroup",
                "resource-groups:GetGroup",
                "resource-groups:ListGroups",
                "resource-groups:ListGroupResources",
                "resource-groups:GetGroupQuery",
                "resource-groups:Tag",
                "resource-groups:Untag",
                "tag:GetResources",
            ],
            resources=["*"]
    ))
    ### applicationinsights:DescribeApplication on resource: arn:aws:applicationinsights:{Region}:{AccountId}:application/resource-group/ApplicationInsights-SAM-FACT-devops-sarma-CleanupOrphanResources
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=[
                "applicationinsights:*",
                "applicationinsights:DescribeApplication",
            ],
            resources=[
                f"arn:{stk.partition}:applicationinsights:{stk.region}:{stk.account}:application/resource-group/ApplicationInsights-SAM-{constants.CDK_APP_NAME}*"
            ]
    ))

### ---------------------------------------------------------------------------------

def gen_artifact_name(
    tier :str,
    codebase_root_folder :str,
    subproj_name :str,
    cb_proj_name :str
) -> tuple[str,str, str]:
    """ common-code reused in multiple CodeBuild constructs in this file.

        param #1: codebase_root_folder :str -- must be valid and must be provided!
        param #2: subproj_name :str -- can be None.
        param #3: cb_proj_name :str -- must be valid and must be provided

        If subproj_name (param #2) is null, it will be set to proper-globally-unique-value.
        Returns 3 strings (that is, a 3-tuple):
            1. a globally-unique ARTIFACT-NAME.
            1. either returns the original NON-None subproj_name or the proper-value (if its is None)
            1. The (derived) actual path to the subproject
    """

    if subproj_name:
        if isinstance(subproj_name, pathlib.Path):
            subproj_name = str(subproj_name)

        sub_proj_fldrpath = f"{codebase_root_folder}/{subproj_name}"
        ### now replace the value of subproj_name --0 to be usable as "safe names/Ids"
        subproj_name = re.sub(r'[^\w\s]', '', subproj_name)
        artif_name = f'{cb_proj_name}/{codebase_root_folder}/{subproj_name}.template.json'

    else:
        sub_proj_fldrpath = "."
        subproj_name = cb_proj_name
        artif_name = f'{cb_proj_name}.template.json'

    artif_name = tier +"-"+ re.sub(r'[^\w\s]', '', artif_name)

    return ( artif_name, subproj_name, sub_proj_fldrpath )


### EoF
