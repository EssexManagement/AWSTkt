#!/usr/bin/env python3
import os

import aws_cdk as cdk

import app_pipeline.constants as constants
from app_pipeline.pipeline_stack import AwsTktPipelineStack

app = cdk.App()
AwsTktPipelineStack( app, f"{constants.CDK_APP_NAME}-PIPELINE", )

app.synth()
