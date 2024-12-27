#!/usr/bin/env python3
import os

import aws_cdk as cdk

import app_pipeline.constants as constants
from app_pipeline.application_stack import AwsTktApplicationStack

app = cdk.App()
AwsTktApplicationStack( app, f"{constants.CDK_APP_NAME}-Appl", )

app.synth()
