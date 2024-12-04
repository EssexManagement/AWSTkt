#!/usr/bin/env python3
import os

import aws_cdk as cdk

import aws_tkt.constants as constants
from aws_tkt.application_stack import AwsTktApplicationStack

app = cdk.App()
AwsTktApplicationStack( app, f"{constants.CDK_APP_NAME}-Appl", )

app.synth()
