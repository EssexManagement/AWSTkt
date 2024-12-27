#!/usr/bin/env python3
import os

import aws_cdk as cdk

import constants as constants
from app_pipeline.application_stack import AwsTktApplicationStack

tier=constants.DEV_TIER

app = cdk.App()
AwsTktApplicationStack( scope=app,
    construct_id=f"{constants.CDK_APP_NAME}-Appl",
    tier=tier,
    aws_env=constants.DEV_TIER,
    git_branch=constants.get_git_branch(tier),
)

app.synth()
