#!/usr/bin/env python3
import os

import aws_cdk as cdk

import aws_tkt.constants as constants
from aws_tkt.pipeline_stack import AwsTktPipelineStack

app = cdk.App()
AwsTktPipelineStack( app, f"{constants.CDK_APP_NAME}-PIPELINE", )

app.synth()
