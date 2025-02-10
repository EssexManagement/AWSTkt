from typing import Optional, Union
import os
import re
import pathlib

from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codebuild,
    aws_iam,
    aws_secretsmanager,
    aws_logs,
    aws_codepipeline_actions as codepipeline_actions,
)

import constants
import common.cdk.constants_cdk as constants_cdk
from common.cdk.standard_logging import get_log_grp, LogGroupType

### ---------------------------------------------------------------------------------

CODEBUILD_BUILD_IMAGE = aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3
CODEBUILD_BUILD_IMAGE_UBUNTU = aws_codebuild.LinuxBuildImage.STANDARD_7_0
CODEBUILD_EC2_SIZE    = aws_codebuild.ComputeType.X2_LARGE

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

### ---------------------------------------------------------------------------------
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
    Returns on objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""
def standard_CodeBuildSynth_NodeJS(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_CodeBuildSynth_NodeJS(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    stk = Stack.of(cdk_scope)

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    ### Synth only
    cdk_synth_command  =  "npx cdk synth  --quiet --all"
    cdk_synth_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"
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
        scope=cdk_scope,
        id=f'{subproj_name}-CodeBuild',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',
        build_spec=aws_codebuild.BuildSpec.from_object({
            'version': '0.2',
            "env": {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If "env" is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            'phases': {
                'install': {
                    'commands': [
                        # ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        # ### Give CodeBuild permissions to access Docker daemon
                        # "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        # "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f'cd {sub_proj_fldrpath}',
                        "pwd",
                        'npm i --include-dev',
                        'npm --version; node --version; npx cdk --version',
                    ],
                },
                'build': {
                    'commands': [ cdk_synth_command ]
                }
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            }
        }),
        environment=aws_codebuild.BuildEnvironment(
            build_image  = CODEBUILD_BUILD_IMAGE,
            compute_type = CODEBUILD_EC2_SIZE,
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
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
    7th param:  OPTIONAL: python_version # as a string
    Returns on objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""
def standard_CodeBuildSynth_Python(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Union[str,pathlib.Path],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_CodeBuildSynth_Python(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    ### Synth only
    cdk_synth_command  =  "npx cdk synth  --quiet --all"
    cdk_synth_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_synth_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_synth_command += f" --context git_repo=\"{git_repo_url}\""

    stk = Stack.of(cdk_scope)

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope=cdk_scope,
        id=f'{subproj_name}-CodeBuild',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            "version": 0.2,
            "env": {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If "env" is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": python_version
                    },
                    "commands": [
                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        'npm i --include-dev',

                        "python -m venv .venv",
                        "  .   .venv/bin/activate",
                        "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        "python -m pip install -r requirements.txt",
                        'npm --version; node --version; python --version; pip --version; npx cdk --version',
                    ],
                },
                "build": {
                    "commands": [ cdk_synth_command ]
                },
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },

            # "cache": {
            #     "paths": [
            #         ".venv/**/*",
            #         "node_modules/**/*",
            #     ]
            # }
        }),
        environment=aws_codebuild.BuildEnvironment(
            build_image  = CODEBUILD_BUILD_IMAGE,
            compute_type = CODEBUILD_EC2_SIZE,
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
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
    7th param:  OPTIONAL: git_repo_url :str -- ghORG/gitRepoName.git
    8th param:  OPTIONAL: cdk_app_pyfile :str -- Example: cdk_pipelines_app.py (this is located in root-folder of git-repo)
    9th param:  OPTIONAL: python_version# as a string
    Returns on objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""
def adv_CodeBuildCachingSynthAndDeploy_Python(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Optional[Union[str,pathlib.Path]],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    git_repo_url :Optional[str] = None,
    cdk_app_pyfile :Optional[str] = None,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_CodeBuildSynthAndDeploy_Python(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    stk = Stack.of(cdk_scope)

    cdk_deploy_command  =  "npx cdk deploy  --quiet --all"
    cdk_deploy_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_deploy_command += f" --context tier=\"{tier}\""
    if cdk_app_pyfile:   cdk_deploy_command += f" --app \"python3 {cdk_app_pyfile}\""
    if git_repo_url:     cdk_deploy_command += f" --context git_repo=\"{git_repo_url}\""

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    artif_name = re.sub(r'[^\w\s]', '', artif_name) ### Artifact-name has restrictions/
    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope=cdk_scope,
        id=f'{subproj_name}-CodeBuild',
        project_name=cb_proj_name,

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            "version": 0.2,
            "env": {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If "env" is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": python_version
                    },
                    "commands": [
                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        "env",
                        "npm i --include-dev",

                        "python -m venv .venv",
                        "  .   .venv/bin/activate",
                        "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        "python -m pip install -r requirements.txt",
                        'npm --version; node --version; python --version; pip --version; npx cdk --version',
                        f"jq '.context.[\"git-source\"].git_commit_hashes.{tier}' cdk.json --raw-output",
                        'git checkout --force', ### to address ---> error: Your local changes to the following files would be overwritten by checkout: package-lock.json
                        f"git checkout $(jq '.context.[\"git-source\"].git_commit_hashes.{tier}' cdk.json --raw-output)",
                    ],
                },
                "build": {
                    "commands": [ cdk_deploy_command ]
                    ### NOTE !! cdk deploy is expected via function-parameter-inputs/
                },
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },

            # "cache": {
            #     "paths": [
            #         ".venv/**/*",
            #         "node_modules/**/*",
            #     ]
            # }

        }),
        environment=aws_codebuild.BuildEnvironment(
            build_image  = CODEBUILD_BUILD_IMAGE,
            compute_type = CODEBUILD_EC2_SIZE,
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout=Duration.minutes(120),
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name = f'AdvBuild_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input   = source_artifact,
        outputs = [my_build_output],
        project = cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk )

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
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
    7th param:  OPTIONAL: python_version # as a string
    8th param:  OPTIONAL: where is the JS/TS/VueJS/ReactJS code-base located in this git-repo;  Default = "frontend/ui"
    Returns on objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""
def standard_CodeBuildSynthDeploy_FrontendPythonCDK(
    cdk_scope :Construct,
    tier :str,
    codebase_root_folder :str,
    subproj_name :Optional[Union[str,pathlib.Path]],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    python_version :str = constants_cdk.CDK_APP_PYTHON_VERSION,
    frontend_vuejs_rootfolder :str = "frontend/ui",
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_CodeBuildSynth_FrontendPythonCDK(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    cdk_deploy_command  =  "npx cdk deploy  --quiet --all"
    cdk_deploy_command +=  " --require-approval never --concurrency 10 --asset-parallelism true --asset-prebuild"
    cdk_deploy_command += f" --context tier=\"{tier}\""
    if git_repo_url:     cdk_deploy_command += f" --context git_repo=\"{git_repo_url}\""

    stk = Stack.of(cdk_scope)

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    git_repo_org_name = source_artifact.get_metadata( key="git_repo_org_name"  )
    git_repo_name = source_artifact.get_metadata( key="git_repo_name"  )
    git_repo_url  = f"{git_repo_org_name}/{git_repo_name}"
    print( f"git_repo_url={git_repo_url} within "+ HDR )

    my_build_output  = codepipeline.Artifact("build_"+artif_name)

    cb_project = aws_codebuild.PipelineProject(
        scope=cdk_scope,
        id=f'{subproj_name}-CodeBuild',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',

        # cache=aws_codebuild.Cache.local(aws_codebuild.LocalCacheMode.CUSTOM),     ### match this with the `cache` json-element inside the BuildSpec below.

        build_spec = aws_codebuild.BuildSpec.from_object({
            "version": 0.2,
            "env": {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "variables": { ### If "env" is defined, it --BETTER-- have a "variables" sub-section !!!
                    "NoSuch": "Variable"
                }
            },
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": python_version
                    },
                    "commands": [
                        ### requests.exceptions.HTTPError: 409 Client Error: Conflict for url: http+docker://localhost/v1.44/containers/??????????v=False&link=False&force=False
                        ### Give CodeBuild permissions to access Docker daemon
                        "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2 & ",
                        "timeout 15 sh -c 'until docker info; do echo .; sleep 1; done'", ### wait for Docker-daemon to finish RE-STARTING.
                        f"cd {sub_proj_fldrpath}",
                        "pwd",
                        'npm i --include-dev',

                        "python -m venv .venv",
                        "  .   .venv/bin/activate",
                        "pip install --upgrade pip",
                        # "python -m pip install pip-tools",
                        # "python -m piptools compile --quiet --resolver=backtracking requirements.in",
                        "python -m pip install -r requirements.txt",
                        'npm --version; node --version; python --version; pip --version; npx cdk --version',
                    ],
                },
                "build": {
                    "commands": [
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
            },
            'artifacts': {
                'base-directory': f'{sub_proj_fldrpath}/cdk.out',
                'files': ['**/*']
            },

            # "cache": {
            #     "paths": [
            #         ".venv/**/*",
            #         "node_modules/**/*",
            #     ]
            # }
        }),
        environment=aws_codebuild.BuildEnvironment(
            build_image  = CODEBUILD_BUILD_IMAGE,
            compute_type = CODEBUILD_EC2_SIZE,
        ),
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout=Duration.minutes(120),
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'Build_NpmBuild_CDKSynthDeploy_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_project,
    )

    return my_build_action, my_build_output

### ---------------------------------------------------------------------------------
"""
    -NO- CDK !!
    Just BDDs via Frontend / Chromium based JS/TS frameworks.

    1st param:  typical CDK scope (parent Construct/stack)
    2nd param:  tier :str           => (dev|int|uat|tier)
    3th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                    Example-Values: "devops/"  "Operations/"
    4th param:  subproj_name :str     => typically the sub-folder's name
                 /or/ can ALSO be the relative-folder-PATH (relative to above `codebase_root_folder` param).
    5th param:  cb_proj_name :str  => When the Infrastructure project in `subfldr` is deployed, DEFINE what the CodeBuild-Project should be named.
    6th param:  source_artifact :codepipeline.Artifact => It representing the SOURCE (usually configured via `cdk_utils/StandardCodePipeline.py`)
    7th param:  frontend_website_url :str => The URL of the frontend website being tested.
    8th param:  test_user_sm_name :str -- Name of SM entry (containing creds to a SIMULATED END-USER for BDDs).
                        Example: f"{constants.CDK_APP_NAME}/{tier}/testing/frontend/test_user"
    9th param:  OPTIONAL: frontend_vuejs_rootfolder :str -- where is the JS/TS/VueJS/ReactJS code-base located in this git-repo;  Default = "frontend/ui"

    Returns 2 objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""

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
    frontend_vuejs_rootfolder :str = "frontend/ui",
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_BDDs_JSTSVuejsReactjs(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    stk = Stack.of(cdk_scope)

    artif_name, subproj_name, sub_proj_fldrpath = gen_artifact_name(
        tier=tier,
        codebase_root_folder=codebase_root_folder,
        subproj_name=subproj_name,
        cb_proj_name=cb_proj_name
    )

    my_build_output  = codepipeline.Artifact("BDDs_"+artif_name)

    cb_pipeline_project = aws_codebuild.PipelineProject(
        scope=cdk_scope,
        id=f'{subproj_name}-BDDs-CodeBuild',
        project_name=cb_proj_name,
        ### project_name=f'{pipeline_id}-{subproj_name}',
        build_spec=aws_codebuild.BuildSpec.from_object({
            'version': '0.2',
            "env": {        ### Ubuntu requires "bash" to be explicitly specified. AL2 does NOT. So .. ..
                "shell": "bash",
                "secrets-manager": {
                    "EMFACT_PASSWORD_CCDI": "$TEST_PROVIDER_SM:EMFACT_PASSWORD_CCDI",
                },
                "variables": { ### If "env" is defined, it --BETTER-- have a "variables" sub-section !!!
                    "ENDPOINT_URL": frontend_website_url,
                    # "STAGE": tier, ### LEGACY !!! QE-team has standardized all their script already on this env-variable.
                    # "tier": tier,
                    # "aws_env": aws_env,
                    # "git_branch": git_branch,
                },
            },
            'phases': {
                'install': {
                    'commands': [
                        f'cd {sub_proj_fldrpath}',
                        "pwd",
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
                }
            },
            "reports": {
                "cucumber_reports": {
                    "files": "cucumber-output-chromeHeadless.json",
                    "base-directory": "tests/bdd_tests/cucumber_results",
                    "file-format": "CUCUMBERJSON",
                }
            },
        }),
        environment=aws_codebuild.BuildEnvironment( ### What kind of machine or O/S to use for CodeBuild
            build_image  = CODEBUILD_BUILD_IMAGE_UBUNTU, ### <--------- Chromium-headless REQUIRES Ubuntu. -NOT- AL.
            compute_type = CODEBUILD_EC2_SIZE,
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
        },
        logging = _get_logging_options( cdk_scope, tier, stk, subproj_name ),
        timeout = constants_cdk.BDD_CODEBUILD_TIMEOUT,
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name=f'BDDs_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input=source_artifact,
        outputs=[my_build_output],
        project=cb_pipeline_project,
    )

    ### -----------------------------
    test_user_sm = aws_secretsmanager.Secret.from_secret_name_v2(
        scope = cdk_scope,
        id = 'TestUserHidden',
        secret_name = test_user_sm_name)

    test_user_sm.grant_read(cb_pipeline_project.grant_principal)

    return my_build_action, my_build_output


### ---------------------------------------------------------------------------------------------
### =============================================================================================
### ---------------------------------------------------------------------------------------------

""" To run `cdk deploy` from within CodeBuild, we need a LOT of permissions (to create & destroy)
"""
def enhance_CodeBuild_role_for_cdkdeploy(
    cb_role :aws_iam.Role,
    stk :Stack,
) -> aws_iam.Role:

    ### To fix the error: ❌  FACT-backend-dev-SNSStack failed: AccessDenied: User: arn:aws:sts::???:assumed-role/FACT-backend-pipeline-dev-emFACTbackendcdkCodeBuild-???/AWSCodeBuild-2da0a582-???
    ###         is not authorized to perform: iam:PassRole
    ###         on resource: arn:aws:iam::??????:role/cdk-hnb659fds-cfn-exec-role-??????-??????
    ###         because no identity-based policy allows the iam:PassRole action
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions = ["iam:PassRole"], ### PassRole vs. AssumedRole(see next policy below)
            resources = [
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-cfn-exec-role-{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-deploy-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-file-publishing-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-image-publishing-role--{stk.account}-{stk.region}",
                f"arn:{stk.partition}:iam::{stk.account}:role/cdk-*-lookup-role--{stk.account}-{stk.region}",
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
    ###                        "arn:aws:iam::??????:role/FACT-backend-pipeline-dev-emFACTbackendcdkCodeBuild-????????????????????????"
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
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:{stk.partition}:ssm:{stk.region}:{stk.account}:parameter/cdk-bootstrap/*"],
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
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stackset/{constants.CDK_APP_NAME}*",
                # f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:changeSet/*",
    ]))

    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["s3:*"],
            resources=[f"arn:{stk.partition}:s3:::cdk-*"],
    ))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["iam:Attach*", "iam:Create*", "iam:Delete*", "iam:Get*", "iam:List*", "iam:Put*", "iam:UpdateRole*", "iam:Tag*", "iam:Untag*"],
            resources=[
                f"arn:{stk.partition}:iam::{stk.account}:role/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:iam::{stk.account}:policy/{constants.CDK_APP_NAME}*",
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
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function/{constants.CDK_APP_NAME}*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer/{constants.CDK_APP_NAME}*",
    ]))
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

### ---------------------------------------------------------------------------------

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
def gen_artifact_name(
    tier :str,
    codebase_root_folder :str,
    subproj_name :str,
    cb_proj_name :str
) -> tuple[str,str, str]:

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
