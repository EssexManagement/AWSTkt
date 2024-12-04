from typing import Sequence, Optional, List
import os

from constructs import Construct
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
    aws_iam,
    aws_s3,
    aws_secretsmanager,
    SecretValue,
    aws_codepipeline_actions as codepipeline_actions,
)

### ---------------------------------------------------------------------------------
"""
    1st param:  typical CDK scope (parent Construct/stack)
    2nd param:  pipeline_name :str  => Usually, pass in the stack_id as
    3rd param:  stack_id :str       => NOT in use. Pass in None for now.
    4th param:  tier :str           => (dev|int|uat|tier)
    5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE; Example: DEVINT_SHARED|UAT|PROD
    6th param:  git_repo_name :str  => (simple name only. NOT the URL)
    7th param:  git_repo_org_name :str
    8th param:  codestar_connection_arn :str => (ideally lookup it up from cdk.json and pass it in here)
    9th param:  pipeline_source_gitbranch :str => (Typically, `dev|main|git-tag1|...` as provided in cdk.json's `git_commit_hashes` element)
    10th param: codebase_root_folder :str => SubFolder within which to find the code-base .. or .. it contains all the folders representing various "subprojects".
                    Example-Values:     "devops/"  "Operations/"
                    Example-Value:      "." <-- implying root-folder of git-repo
    11th param: source_artifact :codepipeline.Artifact => Can NOT be None!

    12th param: OPTIONAL: codebase_folders_that_trigger_pipeline :list[str] => a list of folder-paths to trigger the pipeline.
                    NOTE: Only useful for Pipelines like Meta-Pipeline and devops-pipeline.
    13th param: OPTIONAL: codebase_ignore_paths :list[str] => a list of folder-paths to IGNORE (for pipeline-triggers)
                    REF: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitfilepathfiltercriteria.html
                    Use this to prevent unnecessary pipeline-triggers.

    Returns a valid instance of "aws_codepipeline.Pipeline" construct.
        This returned-pipeline will AUTOMATICALLY include a CodeStarConnectionsSourceAction
"""
def createStandardPipeline(
    cdk_scope: Construct,
    pipeline_name: str,
    stack_id: Optional[str],
    tier :str,
    aws_env :str,
    git_repo_name: str,
    git_repo_org_name: str,
    codestar_connection_arn :str,
    pipeline_source_gitbranch :str,
    codebase_root_folder :str,
    source_artifact: codepipeline.Artifact,
    codebase_folders_that_trigger_pipeline :Optional[list[str]] = None,
    codebase_ignore_paths :Optional[list[str]] = [ "tmp" ],
                            ### REF: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitfilepathfiltercriteria.html
    **kwargs
) -> codepipeline.Pipeline:

    ### ATTENTION: We are -NOT- using GitHubSourceAction, since Triggers-for-GitHub are -NOT- supported via CloudFormation.
    ###             See more details near codepipeline.TriggerProps(..) and add_property_override(..)
    # my_source_action = codepipeline_actions.GitHubSourceAction(
    #     action_name='GitHub-Source',
    #     owner=git_repo_org_name,
    #     repo=git_repo_name,
    #     branch=pipeline_source_gitbranch,
    #     output=source_artifact,
    #     oauth_token=SecretValue.secrets_manager(secret_id=gitTokenRefARN),
    #     trigger=codepipeline_actions.GitHubTrigger.WEBHOOK,
    # )
    my_source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
        action_name='Source',
        owner=git_repo_org_name,
        repo=git_repo_name,
        branch=pipeline_source_gitbranch,
        output=source_artifact,
        connection_arn=codestar_connection_arn,
        trigger_on_push=False,
    )

    ### -----------------------------------
    if not codebase_root_folder or codebase_root_folder == "." or codebase_root_folder == "/" or codebase_root_folder == "":
        if not codebase_folders_that_trigger_pipeline:
            codebase_folders_that_trigger_pipeline = ["**"]
    else:
        if not codebase_folders_that_trigger_pipeline:
            codebase_folders_that_trigger_pipeline = [codebase_root_folder+"/**"]

    ### Note: CDK does -NOT- support this as of Oct 2024. See "add_property_override()" below.
    ### WARNING: Git tags is the only supported event type. <<----------------
    # ### Create the Triggers that will kickoff the CodePipeline
    #     mytriggers=[codepipeline.TriggerProps(
    #         ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codepipeline/TriggerProps.html
    #         provider_type=codepipeline.ProviderType.CODE_STAR_SOURCE_CONNECTION, ###  <<---------------------- !!!!!!!!!!
    #         git_configuration=codepipeline.GitConfiguration(
    #             ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codepipeline/GitConfiguration.html
    #             source_action=my_source_action,
    #             push_filter=[{
    #                 ### WARNING: Git tags is the only supported event type. <<----------------
    #                 ### WARNING: Git tags is the only supported event type. <<----------------
    #                 ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codepipeline/GitConfiguration.html
    #                 "Branches" : pipeline_source_gitbranch,
    #                 "FilePaths" : {
    #                     "Include" : codebase_folders_that_trigger_pipeline,
    #                     "Exclude" : codebase_ignore_paths,
    #                     # "Exclude" : [codebase_root_folder+"/**/.gitkeep"]"
    #                 },
    #                 # "Tags" : GitTagFilterCriteria
    #             }],
    #             # push_filter=[codepipeline.GitPushFilter("Git Tags????")],
    #             # pull_request_filter=[
    #             #     codepipeline.GitPullRequestFilter(
    #             #         ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codepipeline/GitPullRequestFilter.html
    #             #         branches_includes=[pipeline_source_gitbranch],
    #             #         file_paths_includes = codebase_folders_that_trigger_pipeline
    #             #     )
    #             # ],
    #         )
    #     )]

    ### -----------------------------------
    ### Create the basic pipeline.
    my_pipeline = codepipeline.Pipeline(
        scope = cdk_scope,
        id = 'V2Pipeline',  # this is construct_id
        pipeline_name = pipeline_name,
        pipeline_type = codepipeline.PipelineType.V2,
        execution_mode = codepipeline.ExecutionMode.SUPERSEDED,
        # triggers = None,  ### Note: CDK does -NOT- support this as of Oct 2024. See "add_property_override()" below.
        restart_execution_on_update = False,  ### Just cuz Pipeline was updated, does NOT mean App's code-base changed!
        cross_account_keys = False,
    )
    # Convert the my_pipeline variable to another variable of raw CloudFormation Resource-Type of "AWS::CodePipeline::Pipeline"
    myPipelineRawCfn :codepipeline.CfnPipeline = my_pipeline.node.default_child

    ### We need to MANUALLY ovveride mytriggers=[codepipeline.TriggerProps( ..)
    ### since (see above) .. .. .. WARNING: Git tags is the only supported event type!!!
    myPipelineRawCfn.add_property_override("Triggers", [{
        "GitConfiguration": {
            ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitconfiguration.html
            "Push": [{"FilePaths": {
                ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitpushfilter.html
                "Includes": codebase_folders_that_trigger_pipeline,
                "Excludes": codebase_ignore_paths,
            }}],
            "SourceActionName": my_source_action.action_properties.action_name,
        },
        "ProviderType": "CodeStarSourceConnection",
            ### WARNING: Even in RAW-CloudFormation, the ONLY Allowed-value: CodeStarSourceConnection
            ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-pipelinetriggerdeclaration.html
    }])

    my_pipeline.add_stage(
        stage_name='Source',
        actions=[my_source_action]
    )

    return my_pipeline

### ---------------------------------------------------------------------------------

### EoF
