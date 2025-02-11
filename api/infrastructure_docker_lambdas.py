from pathlib import Path
from typing import Optional
from constructs import Construct

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_cognito,
    aws_logs,
    aws_secretsmanager,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from common.cdk.standard_lambda import StandardLambda
from common.cdk.custom_ECRRepo_lambda_construct import CustomECRRepoLambdaConstruct

from common.cdk.mappings import Mappings
from api import config

THIS_DIR = Path(__file__).parent

### --------------------------------------------------------------------------------------
class DockerLambdaConstruct(Construct):
    def __init__( self, scope: Construct,
        tier :str,
        git_branch :str,
        aws_env :str,
        emfact_user_unpublished: rds.DatabaseSecret,
        cts_api_v2_unpublished :aws_secretsmanager.Secret,
        inside_vpc_lambda_factory :StandardLambda,
    ):
        super().__init__(scope, "DockerLambdas")

        stk = Stack.of(self)

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        datadog_destination = Mappings(self).get_dd_subscription_dest( tier=tier, aws_env=aws_env ) ### TODO
        if datadog_destination is None:
            print( f"WARNING !! Datadog's Kinesis-DataStream destination missing for tier='{aws_env}' !!  -- in  Api(): within ", __file__ )

        ### ---------------------

        function_name="reportLambda"
        # function_full_name=f"{stk.stack_name}-{function_name}"
        function_full_name = aws_names.gen_lambda_name( tier=tier, simple_lambda_name=function_name )

        ### Create a Lambda-specific ECR-Repo, store the Container-Image in it, and then create a new Lambda per project-standards.
        self.rpt_constr = CustomECRRepoLambdaConstruct(
            scope = scope,
            construct_id = function_name,
            tier = tier,
            git_branch = git_branch,
            aws_env = aws_env,

            lambda_fullname = function_full_name,
            container_img_codebase = str(THIS_DIR / "runtime_report"),
            lambda_factory = inside_vpc_lambda_factory,
            memory_size = 2048,
            # description = None
            environment={
                "UNPUBLISHED": emfact_user_unpublished.secret_name,
                "CT_API_UNPUBLISHED": cts_api_v2_unpublished.secret_name,
                "CT_API_URL": self.node.try_get_context("ctsapi-v1-prod-url"),
                "CT_API_URL_V2": self.node.try_get_context("ctsapi-v2-prod-url"),
                "CT_API_VERSION": self.node.try_get_context("ctsapi-version"),
            },
        )
        # rpt_constr = aws_lambda.DockerImageFunction( scope=scope,
        #     id=function_name,
        #     # function_name=f"{stk.stack_name}-report-lambda",
        #     timeout=Duration.minutes(15),
        #     vpc=vpc,
        #     security_groups=[rdsSG],
        #     vpc_subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        #     ),
        #     code=aws_lambda.DockerImageCode.from_image_asset(

        #         directory=path.join(this_dir, "./runtime_report"),
        #         asset_name=function_full_name,
        #     ),
        #     tracing=aws_lambda.Tracing.ACTIVE,
        #     log_group=loggrp_2,
        #     # log_retention=aws_logs.RetentionDays.FIVE_DAYS if tier not in ["prod"] else aws_logs.RetentionDays.ONE_YEAR,
        # )
        cts_api_v2_unpublished.grant_read(  self.rpt_constr.lambda_function )
        emfact_user_unpublished.grant_read( self.rpt_constr.lambda_function )

        if datadog_destination:
            aws_logs.SubscriptionFilter(
                ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_logs/SubscriptionFilter.html
                scope = self,
                id = "logs-subscfilter_" + function_full_name,
                destination = datadog_destination,
                log_group = self.rpt_constr.log_group,
                filter_pattern = aws_logs.FilterPattern.all_events(),
                # filter_name= automatically genereated if NOT specified
            )

