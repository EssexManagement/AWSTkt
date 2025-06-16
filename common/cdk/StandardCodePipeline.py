from typing import Sequence, Optional, Union, List
import os

from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    RemovalPolicy,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
    aws_codestarconnections,
    aws_iam,
    aws_s3,
    aws_secretsmanager,
    SecretValue,
)

from common.cdk.retention_base import (
    DATA_CLASSIFICATION_TYPES,
    DataClassification,
    S3_LIFECYCLE_RULES,
)
from common.cdk.StandardBucket import (
    create_std_bucket,
    gen_bucket_lifecycle,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names

### ---------------------------------------------------------------------------------
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
    codebase_ignore_paths :list[str] = [ "tmp" ],
                            ### REF: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitfilepathfiltercriteria.html
    pipeline_variables :Optional[list[codepipeline.Variable]] = None,
    trigger_for_any_gitbranch :bool = False,
    **kwargs
) -> codepipeline.Pipeline:
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

    effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER

    ### ATTENTION: We are -NOT- using GitHubSourceAction, since Triggers-for-GitHub are -NOT- supported via CloudFormation.
    ###             See more details near codepipeline.TriggerProps(..) and add_property_override(..)
    # my_source_action = aws_codepipeline_actions.GitHubSourceAction(
    #     action_name='GitHub-Source',
    #     owner=git_repo_org_name,
    #     repo=git_repo_name,
    #     branch=pipeline_source_gitbranch,
    #     output=source_artifact,
    #     oauth_token=SecretValue.secrets_manager(secret_id=gitTokenRefARN),
    #     trigger=aws_codepipeline_actions.GitHubTrigger.WEBHOOK,
    # )
    my_source_action = aws_codepipeline_actions.CodeStarConnectionsSourceAction(
        action_name='Source',
        owner=git_repo_org_name,
        repo=git_repo_name,
        branch = pipeline_source_gitbranch if not trigger_for_any_gitbranch else None,
        code_build_clone_output=True,
        output=source_artifact,
        connection_arn=codestar_connection_arn,
        trigger_on_push=False if tier in constants.UPPER_TIERS else True,
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
    # if tier == constants.DEV_TIER or tier == constants.INT_TIER:
    #     mytriggers = None
    # else:
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
    data_classification_type = DATA_CLASSIFICATION_TYPES.SCRATCH

    all_lifecycle_rules: dict[str, Sequence[aws_s3.LifecycleRule]] = gen_bucket_lifecycle(
        tier = tier,
        data_classification_type = data_classification_type,
        prefixes_for_s3_tiers={ S3_LIFECYCLE_RULES.SCRATCH.name: [''], },
    )

    my_pipeline_artifact_bkt_name = aws_names.make_bucket_name_globally_unique( pipeline_name +"-CodePpln-artif" )
    my_pipeline_artifact_bkt = create_std_bucket(
        scope = cdk_scope,
        id    = "artif-bkt",
        tier  = tier,
        bucket_name = my_pipeline_artifact_bkt_name,
        data_classification_type = data_classification_type,
        lifecycle_rules = list(all_lifecycle_rules[S3_LIFECYCLE_RULES.SCRATCH.name]),
        removal_policy = RemovalPolicy.DESTROY,
    )

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
        artifact_bucket = my_pipeline_artifact_bkt,
        variables = pipeline_variables,
    )

    ### Create policy to allow using CodeStar-connection
    codestar_policy = aws_iam.PolicyStatement(
        effect=aws_iam.Effect.ALLOW,
        actions=["codestar-connections:UseConnection"],
        resources=[codestar_connection_arn]
    )
    my_pipeline.role.add_to_principal_policy( codestar_policy )

    my_pipeline.my_pipeline_artifact_bkt      = my_pipeline_artifact_bkt # type: ignore
    my_pipeline.my_pipeline_artifact_bkt_name = my_pipeline_artifact_bkt_name # type: ignore

    # Convert the my_pipeline variable to another variable of raw CloudFormation Resource-Type of "AWS::CodePipeline::Pipeline"
    myPipelineRawCfn :codepipeline.CfnPipeline = my_pipeline.node.default_child # type: ignore

    if effective_tier == constants.DEV_TIER:
        ### We need to MANUALLY ovveride mytriggers=[codepipeline.TriggerProps( ..)
        ### since (see above) .. .. .. WARNING: Git tags is the only supported event type!!!
        ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitpushfilter.html
        branch_trigger_1 = { "Includes": [ pipeline_source_gitbranch ] }
        FilePaths_trigger_1 = {
            "Includes": codebase_folders_that_trigger_pipeline,
            "Excludes": codebase_ignore_paths,
        }
        branch_trigger_2 = None
        FilePaths_trigger_2 = None
        ### ---- 2nd set of trigger (optional)
        if tier == constants.DEV_TIER and trigger_for_any_gitbranch:
            ### This is EXCLUSIVELY for use by `dev` tier's Meta-pipeline !!!     Note: we're NOT checking `effective_tier`
            ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitpushfilter.html
            branch_trigger_2 = { "Includes": ["**"], "Excludes": ["main","master","test","stage","qa"] }  # Wildcard == all branches, except of course `main` git-branch!
            FilePaths_trigger_2 = { "Includes": [ "cdk.json", "tests/**" ], }
                    ### This "FilePaths" tricks CodePipeline's `SourceAction` to trigger ONLY for:
                    ###   (1) new "valid-cdk" git-branches or ..
                    ###   (2) whenever cdk.json changes for an EXISING git-branch.
        ### ---- combine all push-triggers
        push_trigger :list[dict[str, dict[str, dict[str, list[str]]] | dict[str, list[str]]]] = []
        push_trigger = [{ "Branches": branch_trigger_1, "FilePaths": FilePaths_trigger_1 }]
        if branch_trigger_2 and FilePaths_trigger_2:
            push_trigger.append({ "Branches": branch_trigger_2, "FilePaths": FilePaths_trigger_2 })
        ### ----------------
        myPipelineRawCfn.add_property_override("Triggers", [{
            "GitConfiguration": {
                ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitconfiguration.html
            "Push": push_trigger,
                # "Push": [{
                #     "Branches": { "Includes": [ (pipeline_source_gitbranch if not trigger_for_any_gitbranch else "*") ] },
                #     "FilePaths": ([{
                #         ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codepipeline-pipeline-gitpushfilter.html
                #         "Includes": codebase_folders_that_trigger_pipeline,
                #         "Excludes": codebase_ignore_paths,
                #     }] if not trigger_for_any_gitbranch else None),
                # }],
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

"""
    Creates a NEW AWS-CodeStar-connection, with the provided connection-name (optional param #4).
    Right now, the tier & aws_env parameters (#2 & #3) are ignored.
"""
def create_codestar_connection(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    codestar_connection_name :str = f"{constants.CDK_APP_NAME}-GitHub-V2",
) -> str:
    """ Looks up `cdk.json` file and .. .. returns codestar_connection_arn :str
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str
        Parameter #4 - (OPTIONAL) codestar_connection_name :str (defaults to '{APP_NAME}-GitHub-V2')
    """
    stk = Stack.of(cdk_scope)

    ### WARNING !!! maxLength: 32
    print( f"codestar_connection_name = '{codestar_connection_name}' within "+ __file__ )

    # effective_tier = tier if tier in constants.STD_TIERS else "dev"
    # codestar_connection_name = f"{constants.CDK_APP_NAME}-GitHub-V2-{effective_tier}"

    codestar_connection = aws_codestarconnections.CfnConnection( scope=cdk_scope, id="codestar-connection",
        connection_name = codestar_connection_name,
        provider_type = "GitHub",
    )
    Tags.of(codestar_connection).add(key="ResourceName", value =stk.stack_name+"-CodeStarConn-"+codestar_connection_name)
    codestar_connection_arn = codestar_connection.ref

    print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )

    return codestar_connection_arn

### ---------------------------------------------------------------------------------

### EoF
