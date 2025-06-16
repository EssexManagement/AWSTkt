from aws_cdk import (
    Stack,
    aws_iam,
)
from constructs import Construct

import constants
from common.cdk.StandardCodeBuild import (
    enhance_Common_Shared_CodeBuild_role_for_cdkdeploy,
    simple_short_common_codebuild_role_name,
    common_codebuild_role_name,
)

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

        newrole = aws_iam.Role(
            scope = scope, ### Not "self"!
            id = simple_short_common_codebuild_role_name(),
            role_name = common_codebuild_role_name(stk),
            description = "Unique-per-AWS-Acct - within the DevOps-Pipeline, this is a common/shared Role for ALL CodeBuild-projects, across ALL TIERS",
            assumed_by = aws_iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        enhance_Common_Shared_CodeBuild_role_for_cdkdeploy( newrole, stk )
