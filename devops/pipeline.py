import pathlib
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

THIS_COMPONENT = "devops"

### ---------------------------------------------------------------------------------------------------

class MultiCdkSubProjectsPipelineStack(Stack):
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
        sub_projects = { ### sub-Folder-Name --maps-to--> [ list-of-1+-StackNAMEs ]
            'cleanup-stacks':  [aws_names.gen_awsresource_name( simple_resource_name='CleanupStacks',  tier=tier, cdk_component_name=THIS_COMPONENT, )],
            '1-click-end2end': [aws_names.gen_awsresource_name( simple_resource_name='1ClickEnd2End',  tier=tier, cdk_component_name=THIS_COMPONENT, )],
            'post-deployment': [aws_names.gen_awsresource_name( simple_resource_name='PostDeployment', tier=tier, cdk_component_name=THIS_COMPONENT, )],
            'cleanupOrphanResources': [aws_names.gen_awsresource_name( simple_resource_name='CleanupOrphanResources', tier=tier, cdk_component_name=THIS_COMPONENT, )],
            # Do NOT use -> 'RDSInstanceSetup': [aws_names.gen_awsresource_name( simple_resource_name='RDSInstanceSetup', tier=tier, cdk_component_name=THIS_COMPONENT, )],
        }

        codebase_ignore_paths=[
            ### Max 8 items !!!!!!!!!!!!!!!!!!
            "scripts/**", "docs/**", "image/**",
            "README*.md",
        ]

        ### -----------------------------------
        _ , git_repo_name , git_repo_org_name = cdk_utils.CdkDotJson_util.lkp_gitrepo_details(cdk_scope=self)

        ### -----------------------------
        git_src_code_config , _ , git_commit_hash, pipeline_source_gitbranch = cdk_utils.CdkDotJson_util.lkp_cdk_json(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env)
        codestar_connection_arn = cdk_utils.CdkDotJson_util.lkp_cdk_json_for_codestar_arn(
                                                                    cdk_scope=self, ### This stack
                                                                    tier=tier,
                                                                    aws_env=aws_env,
                                                                    git_src_code_config=git_src_code_config)

        MultiCdkSubProjectsPipeline( scope=self,
            construct_id = "Cdks",
            pipeline_name = stack_id,
            # second_component_name = THIS_COMPONENT,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_commit_hash,
            git_repo_name = git_repo_name,
            git_repo_org_name = git_repo_org_name,
            codestar_connection_arn = codestar_connection_arn,
            pipeline_source_gitbranch = pipeline_source_gitbranch,
            codebase_root_folder = THIS_COMPONENT, ### based on the value, this is everything at "./devops/*"
            sub_projects = sub_projects,
            codebase_ignore_paths = codebase_ignore_paths,
        )

        add_tags(a_construct=self, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch)

### ---------------------------------------------------------------------------------
class MultiCdkSubProjectsPipeline(Construct):
    def __init__(self,
        scope: Construct,
        construct_id: str,
        pipeline_name: str,
        # second_component_name: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        git_repo_name: str,
        git_repo_org_name: str,
        codestar_connection_arn :str,
        pipeline_source_gitbranch :str,
        codebase_root_folder :str,
        sub_projects :dict,
        codebase_ignore_paths :list[str],
        **kwargs
    ) -> None:
        """
            1st param:  typical CDK scope (parent Construct/stack)
            2nd param:  typical CDK construct_id
            3rd param:  pipeline_name :str  => Usually, pass in the stack_id as
            4th param:  tier :str           => (dev|int|uat|tier)
            5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE (DEVINT_SHARED|UAT|PROD)
            6th param:  git_branch :str    => Currently UN-USED !!!! (NOTE: When CodePipeline-or-CodeBuild do a git-clone, this will be the DEFAULT-git-branch that they'll use)
            7th param:  git_repo_name :str  => (simple name only. NOT the URL)
            8th param:  git_repo_org_name :str
            9th param:  codestar_connection_arn :str => (ideally lookup it up from cdk.json and pass it in here)
            10th param: pipeline_source_gitbranch :str => (Typically, `dev|main|git-tag1|...` as provided in cdk.json's `git_commit_hashes` element)
            11th param: codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                            Example-Values: "devops/"  "Operations/"
            12th param: sub_projects :dict (Dictionary).
                            Example: The subprojects under `devops/` folder-tree :-
                            { ### sub-FolderName & StackName
                                'cleanup-stacks':   f"{constants.CDK_APP_NAME}-{THIS_COMPONENT}-{tier}-CleanupStacks",
                                '1-click-end2end':  f"{constants.CDK_APP_NAME}-{THIS_COMPONENT}-{tier}-1ClickEnd2End",
                                'post-deployment':  f"{constants.CDK_APP_NAME}-{THIS_COMPONENT}-{tier}-PostDeployment",
                            }
            14th param: codebase_ignore_paths :list => (List of paths that will --NOT-- trigger CodePipeline.
                            Example: ["scripts", "docs", "image", "README*.md"])
        """
        super().__init__(scope, construct_id, **kwargs)

        stk = Stack.of(self)

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )
        print( f"pipeline_source_gitbranch = '{pipeline_source_gitbranch}' within "+ __file__ )
        print( f"codebase_root_folder = '{codebase_root_folder}' within "+ __file__ )
        print( f"sub_projects = .. .. within "+ __file__ )
        print( json.dumps(sub_projects, indent=4) )
        print( f"codebase_ignore_paths = {codebase_ignore_paths} "+ __file__ )

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
            codebase_root_folder = codebase_root_folder,
            source_artifact = my_source_artif,
            codebase_folders_that_trigger_pipeline = [ f"{key}/**" for key in sub_projects.keys() ],  ### <-------- Note!
            codebase_ignore_paths=codebase_ignore_paths,
        )

        ### --------------------------------------------
        common_label = f"{constants.CDK_APP_NAME}-devops-{tier}"
        build_stage_actions  = []
        deploy_stage_actions = []

        # Create build and deploy stages for each sub-project
        for subproj_name in sub_projects.keys():

            multiple_stacks = sub_projects[subproj_name]
            # subproj_stkname = aws_names.gen_awsresource_name(
            #     tier=tier,
            #     cdk_component_name=f"{THIS_COMPONENT}-CloudEngg",
            #     simple_resource_name=subproj_name,
            # )

            a_build_action :Optional[aws_codepipeline_actions.CodeBuildAction] = None
            a_build_output :Optional[codepipeline.Artifact] = None

            # within the folder f'./{subproj_name}', if there's a file 'template.yaml' set the variable "aws_sam_project" to true
            cdk_project :bool     = pathlib.Path(f'{codebase_root_folder}/{subproj_name}/cdk.json').exists();
            aws_sam_project :bool = pathlib.Path(f'{codebase_root_folder}/{subproj_name}/template.yaml').exists();
            python_cdk_project :bool = pathlib.Path(f'{codebase_root_folder}/{subproj_name}/requirements.txt').exists();
            if not cdk_project and not aws_sam_project:
                raise Exception(f"Neither 'cdk.json' nor 'template.yaml' found in {codebase_root_folder}/{subproj_name} !!!!")

            if cdk_project and not aws_sam_project:

                if not python_cdk_project:
                    ### Purely JavaScript/TypeScript/NodeJS-based CDK-project
                    a_build_action, a_build_output = common.cdk.StandardCodeBuild.standard_CodeBuildDeploy_NodeJS(
                        cdk_scope = self,
                        tier = tier,
                        codebase_root_folder = codebase_root_folder,
                        subproj_name = subproj_name,
                        cb_proj_name = f"{common_label}_{subproj_name}",
                        source_artifact = my_source_artif,
                        whether_to_switch_git_commithash = (tier   not   in constants.STD_TIERS), ### True for developer-branches/ticket-tiers only
                        whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
                        my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt, # type: ignore
                        my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name, # type: ignore
                    )
                else:
                    ### this is a Python-based CDK-project
                    # -ONLY- pure cdk-SYNTH actions within CodePipeline
                    a_build_action, a_build_output = common.cdk.StandardCodeBuild.standard_CodeBuildSynth_Python(
                        cdk_scope = self,
                        tier = tier,
                        codebase_root_folder = codebase_root_folder,
                        subproj_name = subproj_name,
                        cb_proj_name = f"{common_label}_{subproj_name}",
                        source_artifact = my_source_artif,
                        whether_to_switch_git_commithash = (tier   not   in constants.STD_TIERS), ### True for developer-branches/ticket-tiers only
                        whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
                        my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt, # type: ignore
                        my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name, # type: ignore
                    )

                build_stage_actions.append(a_build_action)

            ### ---------------
            for subproj_stkname in multiple_stacks:

                if aws_sam_project and not cdk_project:
                    # SAM-DEploy action within CodePipeline
                    a_deploy_action, _ = common.cdk.StandardCodeBuild.standard_CodeBuildDeploy_AWS_SAM(
                        cdk_scope = self,
                        tier = tier,
                        codebase_root_folder = codebase_root_folder,
                        subproj_name = subproj_name,
                        cb_proj_name = f"{common_label}_{subproj_name}",
                        stack_name   = subproj_stkname,
                        source_artifact = my_source_artif,
                        addl_env_vars = { },
                        whether_to_switch_git_commithash = (tier   not   in constants.STD_TIERS), ### True for developer-branches/ticket-tiers only
                        whether_to_use_adv_caching = constants_cdk.use_advanced_codebuild_cache( tier ),
                        my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt, # type: ignore
                        my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name, # type: ignore
                    )

                    deploy_stage_actions.append(a_deploy_action)

                # if cdk_project and not aws_sam_project:

                #     a_template_path=a_build_output.at_path(f'{subproj_stkname}.template.json')

                #     # Deploy action
                #     a_deploy_action = aws_codepipeline_actions.CloudFormationCreateUpdateStackAction(
                #         action_name = f'Deploy_{subproj_stkname}',
                #         template_path = a_template_path,
                #         stack_name = subproj_stkname,
                #         admin_permissions  = True,
                #         replace_on_failure = True,
                #     )

                #     deploy_stage_actions.append(a_deploy_action)

        # Finally, Add build and deploy stages to the CodePipeline
        my_pipeline_v2.add_stage(
            stage_name = f'Build_Synth_{common_label}',
            actions = build_stage_actions,
        )

        my_pipeline_v2.add_stage(
            stage_name = f'Deploy_{common_label}',
            actions = deploy_stage_actions,
        )

        ### -----------------------------------

        add_tags(a_construct=my_pipeline_v2, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch)

### EoF
