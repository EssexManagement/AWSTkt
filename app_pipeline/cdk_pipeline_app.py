#!/usr/bin/env python3
import os

import aws_cdk as cdk

import constants as constants
from app_pipeline.pipeline_stack import AwsTktPipelineStack

tier=constants.DEV_TIER

app = cdk.App()
AwsTktPipelineStack( scope=app,
    construct_id=f"{constants.CDK_APP_NAME}-PIPELINE",
    tier=tier,
    aws_env=constants.DEV_TIER,
    git_branch=constants.get_git_branch(tier),
)

app.synth()
