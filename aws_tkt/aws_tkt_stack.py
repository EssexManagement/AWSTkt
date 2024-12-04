import os
from aws_cdk import (
    Stack,
    aws_lambda,
    DockerImage,
    DockerVolume,
    BundlingOptions,
    BundlingOutput,
    SymlinkFollowMode,
    RemovalPolicy,
)
from constructs import Construct

import aws_tkt.constants as constants
from .lambda_layer_builder import LambdaLayerBuilder
from pipeline import AppDeployPipelineStack

class AwsTktStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # LambdaLayerBuilder( self, "LambdaLayerBuilder" )

        AppDeployPipelineStack( scope=self,
            stack_id=self.stack_name,
            git_repo_name=constants.git_repo_name,
            git_repo_org_name=constants.git_repo_org_name,
            pipeline_source_gitbranch="main",
            codestar_connection_arn=None,
        )

### EoF
