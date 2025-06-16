import os
from typing import Union, Optional
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2,
    aws_rds,
    aws_lambda,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
)
from constructs import Construct

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from cdk_utils.CloudFormation_util import get_vpc_privatesubnet_type

import common.cdk.StandardCodePipeline
import common.cdk.StandardCodeBuild
from backend.database.vpc_rds.infrastructure import SqlDatabaseConstruct

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
        stk = Stack.of(self)
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
        ### We need VPC, Subnets, SGs and perhaps RDS info, to allow CodeBuild to use these AWS resources.

        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
        [ acct_wide_vpc_details, vpc_details_for_tier ] = CdkDotJson_util.get_cdk_json_vpc_details( scope, aws_env, tier )
        SG_IDs_for_vpc_endpts :Optional[list[str]] = vpc_details_for_tier["VPCEndPts-SG"]
        print( f"SGs for vpc_endpts = '{SG_IDs_for_vpc_endpts}'")
        SG_IDs_for_vpc_endpts = SG_IDs_for_vpc_endpts if SG_IDs_for_vpc_endpts else []
        SGs_for_vpc_endpts :list[aws_ec2.ISecurityGroup] = []
        for sgid in SG_IDs_for_vpc_endpts:
            sg_con = aws_ec2.SecurityGroup.from_lookup_by_id( scope=self, id="lkpSg-"+sgid, security_group_id=sgid )
            if sg_con:
                SGs_for_vpc_endpts.append(sg_con)

        vpc_name = aws_names.get_vpc_name( tier=tier, aws_region=stk.region )
        print( f"vpc_name = '{vpc_name}'" )
        vpc = aws_ec2.Vpc.from_lookup(self, f"vpcLookup", vpc_name=vpc_name)

        vpc_subnet_sel = aws_ec2.SubnetSelection( one_per_az=True, subnet_type=get_vpc_privatesubnet_type(vpc) )

        stack_prefix = f"{constants.CDK_APP_NAME}-{constants.CDK_BACKEND_COMPONENT_NAME}-{tier}"
                ### Make sure this/ABOVE matches the defn within `cdk_backend_app.py`
        stateFUL_stack_name = stack_prefix + "-Stateful"
                ### Make sure this/ABOVE matches the Constructor-invocation for `StatefulStack` within `BackendStacks.py`
        rds_aurora_cluster_identifier = SqlDatabaseConstruct.get_rds_cluster_identifier(
            stateFUL_stack_name,
            SqlDatabaseConstruct.get_engine_ver_as_str( self, tier )
        )
        print( f"rds_aurora_cluster_identifier = '{rds_aurora_cluster_identifier}'" )
        # rds_aurora_cluster = aws_rds.DatabaseCluster.from_database_cluster_attributes(
        #     scope = self,
        #     id = "rdsLkp-" + rds_aurora_cluster_identifier,
        #     cluster_identifier = rds_aurora_cluster_identifier,
        # )
        # print( f"rds_aurora_cluster = '{rds_aurora_cluster.cluster_arn}'" )
        # rds_sg_list = rds_aurora_cluster.connections.security_groups if rds_aurora_cluster else []
        ### Note: Since `rds_aurora_cluster` is of type `IDatabaseCluster` it will give EMPTY values always!
        ### Luckily, RDS-Aurora-cluster's SG's name is IDENTICAL to the Aurora-cluster's ID

        rds_sg_list = []
        # rds_sg_list = [ aws_ec2.SecurityGroup.from_lookup_by_name(self, id="rdsSgLkp",
        #     vpc = vpc,
        #     security_group_name = rds_aurora_cluster_identifier
        # ) ]
        print( f"rds_sg_list = '{rds_sg_list}'" )

        ### Create a new SG with just one SG-Rule for All Outbound-Traffic only, and NO inbound traffic.
        outbound_only_sg = aws_ec2.SecurityGroup( self, "OutboundOnlySG",
            vpc=vpc,
            security_group_name=f"{constants.CDK_APP_NAME}-{constants.CDK_BDD_COMPONENT_NAME}-{tier}-outbound-only",
            description="For BDDs running inside CodeBuild, SG allowing only outbound-traffic. NO inbound",
            allow_all_outbound=True,  # Allow all outbound traffic
            # disable_inline_rules=True,
        )
        SGs_for_vpc_endpts.append(outbound_only_sg)

        vpc_info = constants_cdk.VpcInfo(
            vpc_name = vpc_name,
            vpc_con = vpc,
            subnet_selection = vpc_subnet_sel,
            security_groups = rds_sg_list + SGs_for_vpc_endpts,
            # security_group_ids = [ sg.security_group_id for sg in rds_sg_list ]
        )

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

        _, frontend_website_FQDN, _ = CdkDotJson_util.lkp_website_details( cdk_scope=self, tier=tier )

        codebuild_projname = f"{constants.CDK_BDD_COMPONENT_NAME}s"

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
            vpc_info = vpc_info,
            # rds_aurora_cluster_identifier = rds_aurora_cluster_identifier,
            # rds_aurora_cluster = rds_aurora_cluster,
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
