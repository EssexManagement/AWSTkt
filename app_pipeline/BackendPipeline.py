import os
from typing import Optional

from aws_cdk import (
    Stack,
    RemovalPolicy,
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

### ---------------------------------------------------------------------------------------------------

class BackendAppDeployPipelineStack(Stack):
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
            5th param:  git_branch :dtr
        """
        super().__init__(
            scope,
            stack_id,
            stack_name=stack_id,
            **kwargs)

        ### -----------------------------------
        pipeline_name = stack_id    ### perhaps it can be named better?
        stk_prefix = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=constants.CDK_BACKEND_COMPONENT_NAME )
        codebuild_projname = "Appln_CDKSynthDeploy"

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
        ### numerous CPU-specific 𝜆-layers are created in ISOLATED CodeBuild-projects.

        all_build_actions :list[aws_codepipeline_actions.CodeBuildAction] = []

        for cpu_arch in constants_cdk.CPU_ARCH_LIST:
            cpu_arch_str: str = get_cpu_arch_as_str( cpu_arch )
            # cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64|x86_64' string

            # Build action within CodePipeline
            a_build_action, a_build_output = common.cdk.StandardCodeBuild.adv_CodeBuildCachingSynthAndDeploy_Python(
                cdk_scope = self,
                tier = tier,
                codebase_root_folder = ".",
                subproj_name = None,
                cb_proj_name = f"{stk_prefix}_LambdaLayer",
                source_artifact = my_source_artif,
                cpu_arch = cpu_arch,
                git_repo_url = f"{git_repo_org_name}/{git_repo_name}",
                cdk_app_pyfile="cdk_lambda_layers_app.py",
                whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
                my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt, # type: ignore
                my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name, # type: ignore
                addl_cdk_context = {
                    "CPU_ARCH": cpu_arch_str
                }
            )
            all_build_actions.append( a_build_action )

        ### all of these above build-actions MUST happen in parallel, as they are same builds happening on different CPUs-architectures.
        my_pipeline_v2.add_stage(
            stage_name = f"codebuild_LambdaLayers-ALL-CpuArch",
            actions = all_build_actions,
        )

        ### -----------------------------------
        ### Pipeline-stage to Build+Deploy the application

        a_build_action :Optional[aws_codepipeline_actions.CodeBuildAction] = None

        # Build action within CodePipeline
        a_build_action, a_build_output = common.cdk.StandardCodeBuild.adv_CodeBuildCachingSynthAndDeploy_Python(
            cdk_scope = self,
            tier = tier,
            codebase_root_folder = ".",
            subproj_name = None,
            cb_proj_name = f"{stk_prefix}_{codebuild_projname}",
            source_artifact = my_source_artif,
            cpu_arch = constants_cdk.DEFAULT_CPU_ARCH,
            git_repo_url = f"{git_repo_org_name}/{git_repo_name}",
            cdk_app_pyfile="cdk_backend_app.py",
            whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
            my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt, # type: ignore
            my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name, # type: ignore
            addl_cdk_context = {
                "CPU_ARCH": constants_cdk.DEFAULT_CPU_ARCH_NAMESTR
            }
        )

        ### all of these above build-actions MUST happen in parallel, as they are same builds happening on different CPUs-architectures.
        my_pipeline_v2.add_stage(
            stage_name = f"{codebuild_projname}-{constants_cdk.DEFAULT_CPU_ARCH_NAMESTR}",
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

        ### -----------------------------------

        # my_stage = BackendStage(
        #     scope   = self,
        #     id_     = f"{APP_NAME}-{COMPONENT_NAME}-{tier}",
        #     tier    = tier,
        #     aws_env = aws_env,
        #     git_branch = app_git_branch,
        #     env = Environment(
        #         account = os.environ["CDK_DEFAULT_ACCOUNT"],
        #         region  = os.environ["CDK_DEFAULT_REGION"],
        #     ),
        #     # env=Environment( account=account, region=region ),
        # )

        # # TODO API BDD test
        # my_pipeline_v2.add_stage(
        #     stage_name = "Backend-Synth-All-Stacks",
        #     actions = [ synth_action, deploy_action ],
        # )

        ### -----------------------------------

        # test_step: pipelines.Step = pipelines.CodeBuildStep(
        #     "UI BDD Tests",
        #     env_from_cfn_outputs={
        #         "user_pool_id": my_stage.user_pool_id(),
        #         "user_pool_client_id": my_stage.user_pool_client_id() #,
        #         # "user_pool_client_secret": my_stage.user_pool_client_secret()
        #     },
        #     commands=[
        #         "echo \"user_pool_id: ${user_pool_id}\"",
        #         "echo \"user_pool_client_id: ${user_pool_client_id}\"",
        #         # "echo user_pool_client_secret: $user_pool_client_secret",
        #         # "cd tests/bdd_tests",
        #         # "export PROJECT_ROOT=$(pwd)",
        #         # "echo $PROJECT_ROOT",
        #         # '/bin/bash -c "source scripts/system_setup.sh && install_dependencies" ',
        #         # "ls -alt",
        #         # '/bin/bash -c "source scripts/run_test.sh && db_warmup" ',
        #         # '/bin/bash -c "source scripts/run_test.sh && run_bdd_tests" ',
        #     ],
        #     # partial_build_spec=codebuild.BuildSpec.from_object(
        #     #     {
        #     #         "reports": {
        #     #             "cucumber_reports": {
        #     #                 "files": ["cucumber-output-chrome.html"],
        #     #                 "base-directory": "tests/bdd_tests/cucumber_results",
        #     #                 "file-format": "html",
        #     #             }
        #     #         },
        #     #     }
        #     # ),
        # )

        # # TODO APIs-only BACKEND-only tests
        # my_pipeline_v2.add_stage(
        #     stage_name = "unit-tests",
        #     stage=my_stage,
        #     post=[test_step],
        # )

        ### -----------------------------------

        # gitauth_secret.grant_read( pipeline_lvl2.pipeline.role )

        # Give CodeBuild/pipeline.role permissions to invoke ec2:DescribeVpcs action
        # ???????????????? a_build_action .grant_principal.add_to_principal_policy(
        #     aws_iam.PolicyStatement(
        #         actions=["ec2:*"],
        #         resources=["*"],
        #     )
        # )

        # my_pipeline_v2.role.add_to_principal_policy(
        #     aws_iam.PolicyStatement(
        #         actions=[
        #             "codestar-connections:*",
        #             ### "codestar-connections:UseConnection",
        #         ],
        #         resources=[
        #             '*'
        #             # codestar_connection_arn
        #         ],
        #     )
        # )
        # my_pipeline_v2.role.add_to_principal_policy(
        #     aws_iam.PolicyStatement(
        #         actions=[ "appconfig:*", ],
        #         resources=[ '*' ],
        #     )
        # )

### EoF
