from aws_cdk import (
    Stack,
)
from constructs import Construct

from .lambda_layer_builder import LambdaLayerBuilder

class AwsTktStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        LambdaLayerBuilder( self, "LambdaLayerBuilder" )

### EoF
