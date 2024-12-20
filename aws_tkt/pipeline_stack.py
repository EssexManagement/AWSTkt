import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
)
from constructs import Construct

import aws_tkt.constants as constants
from .lambda_layer_builder import LambdaLayerBuilder

import common.cdk.StandardCodePipeline
import common.cdk.StandardCodeBuild

class AwsTktPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(
            scope,
            construct_id,
            stack_name=construct_id,
            **kwargs)

        # LambdaLayerBuilder( self, "LambdaLayerBuilder" )

        stack_id=self.stack_name
        git_repo_name=constants.git_repo_name
        git_repo_org_name=constants.git_repo_org_name
        pipeline_source_gitbranch="main"
        codestar_connection_arn=f"arn:{self.partition}:codeconnections:{self.region}:{self.account}:connection/{constants.codestar_connection_id}"

        ### -----------------------------------
        pipeline_name = stack_id    ### perhaps it can be named better?
        stk_prefix = self.stack_name
        codebuild_projname = "Appln_CDKSynthDeploy"
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )
        print( f"pipeline_source_gitbranch = '{pipeline_source_gitbranch}' within "+ __file__ )

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
            git_repo_name     = git_repo_name,
            git_repo_org_name = git_repo_org_name,
            codestar_connection_arn   = codestar_connection_arn,
            pipeline_source_gitbranch = pipeline_source_gitbranch,
            source_artifact   = my_source_artif,
            codebase_root_folder = ".",
            # codebase_folders_that_trigger_pipeline = [ ],  Since developers will create arbitrary folders, NEVER define this param.
            codebase_ignore_paths=[
                ### Max 8 items !!!!!!!!!!!!!!!!!!
                "app_pipeline/**", "devops/**", "operations/**", "monitoring/**", "secops/**",
                # "cdk.context.json",
                # "tests",
                "scripts/**",
                "docs/**",
                # "image",
                "README*.md",
            ]
        )

        ### -----------------------------------

        a_build_action :aws_codepipeline_actions.CodeBuildAction = None

        # Build action within CodePipeline
        a_build_action, a_build_output = common.cdk.StandardCodeBuild.adv_CodeBuildCachingSynthAndDeploy_Python(
            cdk_scope = self,
            codebase_root_folder = ".",
            subproj_name = None,
            cb_proj_name = f"{stk_prefix}_{codebuild_projname}",
            source_artifact = my_source_artif,
            git_repo_url = f"{git_repo_org_name}/{git_repo_name}",
            cdk_app_pyfile="layers_app.py"
        )

        my_pipeline_v2.add_stage(
            stage_name = codebuild_projname,
            actions = [ a_build_action ],
        )

### EoF
