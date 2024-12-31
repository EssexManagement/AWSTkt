#!/usr/bin/env python3
import os

import aws_cdk as cdk

import constants as constants
from app_pipeline.application_stack import AwsTktApplicationStacks

tier=constants.DEV_TIER

app = cdk.App()
AwsTktApplicationStacks( scope=app,
    construct_id=f"Appl", ### Keep this simple, cuz this Constructor will be automatically prefixing the stack-names appropriately.
    tier=tier,
    aws_env=constants.DEV_TIER,
    git_branch=constants.get_git_branch(tier),
)

app.synth()
