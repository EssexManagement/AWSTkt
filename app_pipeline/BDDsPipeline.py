import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_lambda,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
)
from constructs import Construct

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from cdk_utils.CloudFormation_util import get_cpu_arch_as_str

import common.cdk.StandardCodePipeline
import common.cdk.StandardCodeBuild
from aws_cdk import aws_lambda

### ---------------------------------------------------------------------------------------------------

class BDDsPipelineStack(Stack):
    def __init__(self,
        scope: Construct,
        stack_id: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        **kwargs
    ) -> None:
        """
            1st param:  typical CDK scope (parent Construct/stack)
            2nd param:  stack_id :str
            3rd param:  tier (dev|int|uat|tier)
            4th param:  aws_env - typically the AWS_ACCOUNT AWSPROFILE (DEVINT_SHARED|UAT|PROD)
            5th param:  git_branch :str; Currently UN-USED !!!! (NOTE: When CodePipeline-or-CodeBuild do a git-clone, this will be the DEFAULT-git-branch that they'll use)
        """
        super().__init__(
            scope,
            stack_id,
            stack_name=stack_id,
            **kwargs)

        ### -----------------------------------
        pipeline_name = stack_id    ### perhaps it can be named better?
        stk_prefix = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=constants.CDK_FRONTEND_COMPONENT_NAME )
        # stk_prefix = f"{constants.CDK_APP_NAME}-{constants.CDK_COMPONENT_NAME}-{tier}"

        ### -----------------------------------
        _ , git_repo_name , git_repo_org_name = CdkDotJson_util.lkp_gitrepo_details(cdk_scope=self)

        ### -----------------------------------
        git_src_code_config , _ , app_git_branch, pipeline_source_gitbranch = CdkDotJson_util.lkp_cdk_json(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env)
        codestar_connection_arn = CdkDotJson_util.lkp_cdk_json_for_codestar_arn(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env,
                                                                    git_src_code_config=git_src_code_config)

        # codestar_connection_arn=f"arn:{self.partition}:codeconnections:{self.region}:{self.account}:connection/{???}"

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"App's git_branch='{app_git_branch}' within "+ __file__ )
        print( f"pipelin's source_gitbranch = '{pipeline_source_gitbranch}' within "+ __file__ )
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )

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
                "frontend/**",
                "tests/**",
                # "tests/bdd_tests/package.json", ### QE-team can upgrade Chromium version frequently.
                # "tests/bdd_tests/package-lock.json", ### QE-team can upgrade Chromium version frequently.
            ], ### TODO what if developers violate this and create new folders???
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
        a_build_output :codepipeline.Artifact = None

        test_user_sm_name :str = f"{constants.CDK_APP_NAME}/{tier}/testing/frontend/test_user"

        _, frontend_website_FQDN = CdkDotJson_util.lkp_website_details( cdk_scope=self, tier=tier )

        codebuild_projname = "BDDs"

        a_build_action :aws_codepipeline_actions.CodeBuildAction = None
        a_build_output :codepipeline.Artifact = None

        # Build action within CodePipeline
        a_build_action, a_build_output = common.cdk.StandardCodeBuild.standard_BDDs_JSTSVuejsReactjs(
            cdk_scope = self,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            codebase_root_folder = ".",
            subproj_name = None,
            cb_proj_name = f"{stk_prefix}_{codebuild_projname}",
            source_artifact = my_source_artif,
            frontend_website_url = frontend_website_FQDN,
            test_user_sm_name = test_user_sm_name,
            cpu_arch = aws_lambda.Architecture.X86_64,  ### We need Ubuntu-on-X86 for Chrome-Headless
            frontend_vuejs_rootfolder="frontend/ui",
            whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
            my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt,
            my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name,
        )

        my_bdd_stage = my_pipeline_v2.add_stage(
            stage_name = codebuild_projname,
            actions = [ a_build_action ],
        )

        ### -----------------------------------

        ### Mark found a classic "race-condition" where CodePipeline AWS-resource was starting to get created BEFORE the Key-Alias and other dependency-resources were COMPLETELY created.
        my_pipeline_v2.role.node.add_dependency( my_pipeline_v2.artifact_bucket )
        # pipeline_lvl2.pipeline.node.add_dependency( pipeline_lvl2.pipeline.artifact_bucket.encryption_key )
        # pipeline_lvl2.pipeline.role.node.add_dependency( pipeline_lvl2.pipeline.artifact_bucket.encryption_key )
        # pipeline_lvl2.pipeline.role.node.add_dependency( pipeline_lvl2.pipeline.artifact_bucket.policy )
        # pipeline_lvl2.pipeline.node.add_dependency( pipeline_lvl2.pipeline.role ) ### Circular dependency alert!!!!!!!!!
        # pipeline_lvl2.pipeline.artifact_bucket.node.add_dependency( pipeline_lvl2.pipeline.artifact_bucket.encryption_key ) ### Circular dependency alert!

### EoF
