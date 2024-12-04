#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws_tkt.application_stack import AwsTktApplicationStack

app = cdk.App()
AwsTktApplicationStack( app, "AwsTkt-Sarma-Appl", )

app.synth()
