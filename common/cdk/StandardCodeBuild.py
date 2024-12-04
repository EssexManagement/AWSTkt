from typing import Optional, Union
import os
import re
import pathlib

from constructs import Construct
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codebuild,
    aws_lambda,
    aws_iam,
    aws_secretsmanager,
    aws_logs,
    aws_codepipeline_actions as codepipeline_actions,
)

import aws_tkt.constants as constants

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
    8th param:  OPTIONAL: cdk_app_pyfile :str -- Example: all_pipelines.py (this is located in root-folder of git-repo)
    9th param:  OPTIONAL: python_version# as a string
    Returns on objects of types:-
                1. codepipeline_actions.CodeBuildAction
                3. codepipeline.Artifact (representing the BUILD-Artifact)
"""
def adv_CodeBuildCachingSynthAndDeploy_Python(
    cdk_scope :Construct,
    codebase_root_folder :str,
    subproj_name :Optional[Union[str,pathlib.Path]],
    cb_proj_name :str,
    source_artifact :codepipeline.Artifact,
    git_repo_url :Optional[str] = None,
    cdk_app_pyfile :Optional[str] = None,
    python_version :str = constants.CDK_APP_PYTHON_VERSION,
    tier :str = "dev",
) -> tuple[codepipeline_actions.CodeBuildAction, codepipeline.Artifact]:

    HDR = " : standard_CodeBuildSynthAndDeploy_Python(): "
    print(f"subproj_name={subproj_name}"+ HDR )
    print(f"codebase_root_folder={codebase_root_folder}"+ HDR )
    print(f"cb_proj_name={cb_proj_name}"+ HDR )

    stk = Stack.of(cdk_scope)

    cdk_deploy_command = f"npx cdk deploy  --require-approval never --quiet --all --context tier=\"{tier}\""
    if cdk_app_pyfile:   cdk_deploy_command = cdk_deploy_command + f" --app \"python3 {cdk_app_pyfile}\" "
    if git_repo_url:     cdk_deploy_command = cdk_deploy_command + f" --context git_repo=\"{git_repo_url}\""
    ### Example: cdk_deploy_command = f"npx cdk deploy  --require-approval never --quiet --all --context tier=\"{tier}\" --context TIER=\"{tier}\" --context git_repo=\"{git_repo_url}\""


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
            "version": "0.2",
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
            build_image  = constants.CODEBUILD_BUILD_IMAGE,
            compute_type = constants.CODEBUILD_EC2_SIZE,
        ),
        # logging = _get_logging_options( cdk_scope, tier, stk, subproj_name )
    )

    my_build_action = codepipeline_actions.CodeBuildAction(
        action_name = f'AdvBuild_CDKSynth_{subproj_name}', ### /^[a-zA-Z0-9.@_-]{1,100}$/
        input   = source_artifact,
        outputs = [my_build_output],
        project = cb_project,
    )

    enhance_CodeBuild_role_for_cdkdeploy( cb_role=cb_project.role, stk=stk )

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
            resources=[f"arn:{stk.partition}:secretsmanager:{stk.region}:{stk.account}:secret:{CDK_APP_NAME}*"],
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
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stack/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:cloudformation:{stk.region}:{stk.account}:stackset/{CDK_APP_NAME}*",
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
                f"arn:{stk.partition}:iam::{stk.account}:role/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:iam::{stk.account}:policy/{CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["cognito-idp:*"],
            resources=[
                f"arn:{stk.partition}:cognito-idp:{stk.region}:{stk.account}:userpool/{CDK_APP_NAME}*",
    ]))
    # cb_role.add_to_principal_policy(
    #     aws_iam.PolicyStatement(
    #         actions=["cognito-identity:*"],
    #         resources=[
    #             f"arn:{stk.partition}:cognito-identity:{stk.region}:{stk.account}:identitypool/{CDK_APP_NAME}*",
    # ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["codebuild:*"],
            resources=[
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:build/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:project/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:report/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:codebuild:{stk.region}:{stk.account}:report-group/{CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["codepipeline:*"],
            resources=[
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:action-type:*",
                f"arn:{stk.partition}:codepipeline:{stk.region}:{stk.account}:webhook:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["lambda:*"],
            resources=[
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:function/{CDK_APP_NAME}*",
                f"arn:{stk.partition}:lambda:{stk.region}:{stk.account}:layer/{CDK_APP_NAME}*",
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
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:execution:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:express:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:states:{stk.region}:{stk.account}:stateMachine:{CDK_APP_NAME}*",
                # f"arn:{stk.partition}:states:{stk.region}:{stk.account}:mapRun:*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["rds:*"],
            resources=[
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:auto-backup:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:subgrp:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:snapshot:{CDK_APP_NAME}*",
                f"arn:{stk.partition}:rds:{stk.region}:{stk.account}:db:{CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["dynamodb:*"],
            resources=[
                f"arn:{stk.partition}:dynamodb:{stk.region}:{stk.account}:table/{CDK_APP_NAME}*",
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
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:database/{CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:table/{CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:tableVersion/{CDK_APP_NAME}*",
    #             f"arn:{stk.partition}:glue:{stk.region}:{stk.account}:userDefinedFunction/{CDK_APP_NAME}*",
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
                f"arn:{stk.partition}:sns:{stk.region}:{stk.account}:{CDK_APP_NAME}*",
    ]))
    cb_role.add_to_principal_policy(
        aws_iam.PolicyStatement(
            actions=["sqs:*"],
            resources=[
                f"arn:{stk.partition}:sqs:{stk.region}:{stk.account}:{CDK_APP_NAME}*",
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
