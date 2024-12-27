from aws_cdk import (
    Stack,
    RemovalPolicy,
)

from constructs import Construct
from backend.common_aws_resources_stack import CommonAWSResourcesStack

class AwsTktApplicationStack(Stack):

    def __init__(self,
        scope: Construct,
        construct_id: str,
        tier: str,
        aws_env :str,
        git_branch :str,
        **kwargs
    ) -> None:
        super().__init__( scope, construct_id,
            stack_name=construct_id,
            **kwargs
        )

        CommonAWSResourcesStack( scope=self, id_="CommonAWSRrcs",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            # lambda_configs = lambda_configs,
            **kwargs,
        )

### EoF
