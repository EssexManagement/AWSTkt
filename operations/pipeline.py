import os
import re
import sys

from constructs import Construct
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_cloudformation,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
    aws_s3_assets,
    aws_iam,
    aws_secretsmanager,
    SecretValue,
    aws_codepipeline_actions as codepipeline_actions,
)

from cdk_utils.CloudFormation_util import add_tags
import cdk_utils.CdkDotJson_util
import common.cdk.StandardCodePipeline
import common.cdk.StandardCodeBuild

import constants
import common.cdk.constants_cdk as constants_cdk

### ---------------------------------------------------------------------------------

THIS_COMPONENT = "operations"

CloudEngg_GIT_REPO_URL = "https://github.com/BIAD/cloud_eng.git"
CloudEngg_GIT_BRANCH   = "main"

### ---------------------------------------------------------------------------------
class OperationsPipelineStack(Stack):
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

        # tier = self.node.try_get_context("tier")
        # aws_env = tier if tier in constants.STD_TIERS else constants.DEV_TIER ### ["dev", "int", "uat", "prod"]:
        # git_branch = constants.get_git_branch( tier=tier )

        SNSTopicName=f"{constants.CDK_APP_NAME}-{tier}"
        supportTeamEmails = self.node.try_get_context("support-email")
        if supportTeamEmails is None:
            supportTeamEmails = []
        elif type(supportTeamEmails).__name__ != "list":
            print( f"ERROR: support-email should be a list. Found '{type(supportTeamEmails).__name__}'" )
            print( supportTeamEmails )
            sys.exit(1)

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

        OperationsPipeline( scope=self,
            construct_id="Cdks",
            pipeline_name=stack_id,
            tier=tier,
            aws_env=aws_env,
            codestar_connection_arn=codestar_connection_arn,
            codebase_root_folder=".",
            sns_topic_name=SNSTopicName,
            sns_subscriber=supportTeamEmails[0],
        )

        add_tags(a_construct=self, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch)

### ---------------------------------------------------------------------------------
class OperationsPipeline(Construct):
    """
        1st param:  typical CDK scope (parent Construct/stack)
        2nd param:  typical CDK construct_id
        3rd param:  pipeline_name :str  => Usually, pass in the stack_id as
        4th param:  tier :str           => (dev|int|uat|tier)
        5th param:  aws_env :str        => typically the AWS_ACCOUNT AWSPROFILE; Example: DEVINT_SHARED|UAT|PROD
        6th param:  codestar_connection_arn :str => (ideally lookup it up from cdk.json and pass it in here)
        7th param:  codebase_root_folder :str => SubFolder within which to find the various "subprojects".
                        Example-Values: "devops/"  "Operations/"
        8th param:  sns_topic_name :str => example "FACT-dev"
        9th param:  sns_subscriber :str => an email-address (just one)
    """
    def __init__(self,
        scope: Construct,
        construct_id: str,
        pipeline_name: str,
        tier :str,
        aws_env :str,
        codestar_connection_arn :str,
        codebase_root_folder :str,
        sns_topic_name :str,
        sns_subscriber :str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        stk = Stack.of(self)

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )

        ### ------------------------------------
        ### Connect to a DIFFERENT 2nd Git-Repo -- a common git-repo belonging to entire CRRI-CloudEngg Team

        CloudEngg_git_repo_name, CloudEngg_git_repo_org_name = cdk_utils.CdkDotJson_util.parse_gitrepo_details( CloudEngg_GIT_REPO_URL )

        CloudEngg_source_artif = codepipeline.Artifact()
        CloudEngg_source_artif.set_metadata( key="git_repo_org_name", value=CloudEngg_git_repo_org_name )
        CloudEngg_source_artif.set_metadata( key="git_repo_name",     value=CloudEngg_git_repo_name )

        ### -----------------------------------

        my_pipeline_v2 = common.cdk.StandardCodePipeline.createStandardPipeline(
            cdk_scope = self,
            pipeline_name = pipeline_name,
            stack_id = None,
            tier = tier,
            aws_env = aws_env,
            source_artifact   = CloudEngg_source_artif,
            git_repo_org_name = CloudEngg_git_repo_org_name,
            git_repo_name     = CloudEngg_git_repo_name,
            pipeline_source_gitbranch = CloudEngg_GIT_BRANCH,
            codestar_connection_arn   = codestar_connection_arn,
            # codebase_folders_that_trigger_pipeline = [ ### Could be ANY folder within the CRRI-CloudEngg git-repo (see above) !!!!!!!
            #     "operations",
            #     "common", "cdk_utils",
            # ],
            codebase_root_folder=codebase_root_folder,
        )

        ### -----------------------------------
        ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        ### -----------------------------------

        subprojects_cdk = {
            ### FORMAT of each entry here is:-
            ### "Any-Random-Name": { "dir": <relative-path to `codebase_root)_folder`> , "stks": [ "Stk1", "Stk2" ] }
            "CDK_deleteManyStacks":     { "dir": "./CDK/deleteManyStacks/",     "stks": [ "StepFn-DeleteStacksInSequence", "StepFn-DeleteStacksInParallel" ] },
            "CDK_cleanup-FailedStacks": { "dir": "./CDK/cleanup-FailedStacks/", "stks": [ "StepFn-CleanupFailedStacksInSequence", "StepFn-CleanupFailedStacksInParallel" ] },
        }

        ### -----------------------------------
        common_label = f"CloudEngg_CDKProjs"
        build_stage_actions  = []
        deploy_stage_actions = []

        for subproj_userfriendly_name in subprojects_cdk.keys():
            subproj_details = subprojects_cdk[subproj_userfriendly_name]

            subproj_rel_path = subproj_details["dir"] ### relative-path to `codebase_root)_folder`
            multiple_stacks = subproj_details["stks"]

            # Build action
            a_build_action, a_build_output = common.cdk.StandardCodeBuild.standard_CodeBuildSynth_NodeJS(
                cdk_scope = self,
                tier = tier,
                codebase_root_folder = codebase_root_folder,
                subproj_name = subproj_rel_path,
                cb_proj_name = f"{common_label}_{subproj_userfriendly_name}",
                source_artifact = CloudEngg_source_artif,
                whether_to_use_adv_caching = constants_cdk.USE_ADVANCED_CODEBUILD_CACHE,
                my_pipeline_artifact_bkt = my_pipeline_v2.my_pipeline_artifact_bkt,
                my_pipeline_artifact_bkt_name = my_pipeline_v2.my_pipeline_artifact_bkt_name,
            )

            build_stage_actions.append(a_build_action)

            for subproj_stkname in multiple_stacks:

                a_path = f'{subproj_stkname}.template.json'
                uniq_name = re.sub(r'[^\w\s]', '', a_path)
                print( f"uniq_name = '{uniq_name}' !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" )
                a_template_path = a_build_output.at_path( a_path )

                # Deploy-Raw-CloudFormation action
                a_deploy_action = codepipeline_actions.CloudFormationCreateUpdateStackAction(
                    action_name = f'Deploy_{uniq_name}',
                    template_path = a_template_path,
                    stack_name = subproj_stkname,
                    admin_permissions  = True,
                    replace_on_failure = True,
                )

                deploy_stage_actions.append(a_deploy_action)

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
        ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        ### -----------------------------------
        subprojects_awssam = {
            "AWS_SAM_WipeoutBucket": { "dir": "./AWS-SAM/lambdas/wipeout-bucket/", "stks": [ f"wipeout-bucket-{tier}" ] },
        }

        ### -----------------------------------
        common_label = f"CloudEngg_AWS_SAM"
        # build_stage_actions  = []
        # deploy_stage_actions = []

        # # Finally, Add build and deploy stages to the CodePipeline
        # my_pipeline_v2.add_stage(
        #     stage_name=f'Build_Synth_{common_label}',
        #     actions=build_stage_actions,
        # )
        # my_pipeline_v2.add_stage(
        #     stage_name=f'Deploy_{common_label}',
        #     actions=deploy_stage_actions,
        # )

        ### -----------------------------------
        ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        ### -----------------------------------
        subprojects_raw_CFT = {}
        # subprojects_raw_CFT = {
        #     ### format:  path2CloudFormationTEMPLATE.yaml     a-dictionary-of-CFT-KeyValuePairs
        #     f"./operations/CloudFormation/{constants.CDK_APP_NAME}-SNS-Topic-CFT.yaml": {
        #         "TopicName":     sns_topic_name,
        #         "EmailAddress":  sns_subscriber,
        #     }
        # }

        ### -----------------------------------
        common_label = f"CloudEngg_RawCFT"
        deploy_stage_actions = []
        rawcft_artifacts = codepipeline.Artifact(common_label)

        for cft_filename, cft_params in subprojects_raw_CFT.items():

            # Deploy-Raw-CloudFormation action
            a_deploy_action = codepipeline_actions.CloudFormationCreateUpdateStackAction(
                action_name = f'Deploy_{subproj_stkname}',
                template_path = CloudEngg_source_artif.at_path(cft_filename),
                parameter_overrides = cft_params,
                stack_name = subproj_stkname,
                admin_permissions = True,
                replace_on_failure = True,
            )

            deploy_stage_actions.append(a_deploy_action)

        if len(deploy_stage_actions) > 0:
            my_pipeline_v2.add_stage(
                stage_name = f'Deploy_{common_label}',
                actions = deploy_stage_actions,
            )

### ---------------------------------------------------------------------------------

### EoF
