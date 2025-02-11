### This is a --manually-- deployed Pipeline called "{CDK_APP_NAME}-meta-pipeline-{tier}".
### Warning !! --NOT-- a good idea to use this for ~prod~ or ~uat~ ! -NOT- a good idea at all.
### It helps to automatically UPDATE OTHER pipelines.
### Example: This pipeline will keep updating the "devops" and ""

### This file is --sooooooo-- identical to "app_pipeline/pipeline.py" ..
###     .. that, in the long-term, we should GENERALIZE the latter.
### But, for now, since this meta_pipeline.py is to be RARELY used, .. leave things as they are right now.

import os
import json
import re
from typing import Sequence, Optional, List

from constructs import Construct
from aws_cdk import (
    Stack, Environment, Tags,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names

from cdk_utils.CloudFormation_util import add_tags
import cdk_utils.CdkDotJson_util

import common.cdk.StandardCodePipeline
import common.cdk.StandardCodeBuild

### ---------------------------------------------------------------------------------------------------

class MetaPipelineUpdatesOtherPipelinesStack(Stack):
    """
        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  stack_id :str
        3rd param:  tier (dev|int|uat|tier)
        4th param:  aws_env - typically the AWS_ACCOUNT AWSPROFILE (DEVINT_SHARED|UAT|PROD)
        5th param:  git_branch :str; Currently UN-USED !!!! (NOTE: When CodePipeline-or-CodeBuild do a git-clone, this will be the DEFAULT-git-branch that they'll use)
    """
    def __init__(self,
        scope: Construct,
        stack_id: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        **kwargs
    ) -> None:
        super().__init__(scope=scope, id=stack_id, **kwargs)

        ### -----------------------------------
        pipeline_name = stack_id    ### perhaps it can be named better?
        stk_prefix = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name="MetaPipeline" )
        # stk_prefix = f"{constants.CDK_APP_NAME}-MetaPipeline-{tier}"
        codebuild_projname = "MetaPipeline"
        cdk_app_pyfile = "cdk_pipelines_app.py"

        ### -----------------------------------
        _ , git_repo_name , git_repo_org_name = cdk_utils.CdkDotJson_util.lkp_gitrepo_details(cdk_scope=self)

        ### -----------------------------
        git_src_code_config , _ , git_commit_hash, pipeline_source_gitbranch = cdk_utils.CdkDotJson_util.lkp_cdk_json(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env )
        codestar_connection_arn = cdk_utils.CdkDotJson_util.lkp_cdk_json_for_codestar_arn(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env,
                                                                    git_src_code_config=git_src_code_config )


        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )
        print( f"pipeline_source_gitbranch = '{pipeline_source_gitbranch}' within "+ __file__ )
        print( f"git_commit_hash='{git_commit_hash}' within "+__file__ )

        ### ---------------------------------------------

        # Source stage
        my_source_artif = codepipeline.Artifact()
        my_source_artif.set_metadata( key="git_repo_org_name", value=git_repo_org_name )
        my_source_artif.set_metadata( key="git_repo_name",     value=git_repo_name )

        ### -----------------------------------

        my_pipeline_v2 :codepipeline.Pipeline = common.cdk.StandardCodePipeline.createStandardPipeline(
            cdk_scope = self,
            pipeline_name = pipeline_name,
            stack_id = None,
            tier = tier,
            aws_env = aws_env,
            git_repo_name     = git_repo_name,
            git_repo_org_name = git_repo_org_name,
            codestar_connection_arn   = codestar_connection_arn,
            pipeline_source_gitbranch = pipeline_source_gitbranch,
            source_artifact   = my_source_artif,
            codebase_root_folder = ".",
            codebase_folders_that_trigger_pipeline = [
                "devops/**",
                "operations/**",
                "common/**",     "cdk_utils/**",
                "app_pipeline/**",
            ],
            codebase_ignore_paths=[
                ### Max 8 items !!!!!!!!!!!!!!!!!!
                "api/**", "backend/**",  "cognito/**",
                "etl/**", "user_data/**",
                "scripts/**",
                "tests/**",
            ]
        )

        ### -----------------------------------

        a_build_action :aws_codepipeline_actions.CodeBuildAction = None

        # Build action within CodePipeline
        a_build_action, a_build_output = common.cdk.StandardCodeBuild.adv_CodeBuildCachingSynthAndDeploy_Python(
            cdk_scope = self,
            tier = tier,
            codebase_root_folder = ".",
            subproj_name = None,
            cb_proj_name = f"{stk_prefix}_{codebuild_projname}",
            source_artifact = my_source_artif,
            git_repo_url = f"{git_repo_org_name}/{git_repo_name}",
            cdk_app_pyfile = cdk_app_pyfile,
            whether_to_use_adv_caching = constants_cdk.USE_ADVANCED_CODEBUILD_CACHE,
            my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt,
            my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name,
        )

        my_pipeline_v2.add_stage(
            stage_name = codebuild_projname,
            actions = [ a_build_action ],
        )

        ### -----------------------------------

        add_tags(a_construct=my_pipeline_v2, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch)

### EoF
