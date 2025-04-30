from aws_cdk import (
    Stack,
    aws_iam,
)
from constructs import Construct

from common.cdk.StandardCodeBuild import enhance_CodeBuild_role_for_cdkdeploy

class CommonRoleForAwsCodeBuild(Construct):

    def __init__(self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(
            scope = scope,
            id = construct_id,
            **kwargs
        )
        stk = Stack.of(scope)
        id = "CommonRoleForAwsCodeBuild"
        role_name = stk.stack_name +'-'+ id
        newrole = aws_iam.Role(
            scope = scope, ### Not "self"!
            id = id,
            role_name = role_name,
            description = "Unique-per-AWS-Acct - within the DevOps-Pipeline, this is a common/shared Role for ALL CodeBuild-projects, across ALL TIERS",
            assumed_by = aws_iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        enhance_CodeBuild_role_for_cdkdeploy( newrole, stk )
