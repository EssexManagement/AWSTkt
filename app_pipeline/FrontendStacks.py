from aws_cdk import (
    Stack,
    Fn,
    CfnOutput,
    Duration,
    aws_logs,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3,
    aws_sns_subscriptions,
    aws_cognito as cognito,
    aws_apigateway,
    aws_sns,
    aws_sqs,
    aws_stepfunctions as aws_sfn,
    aws_stepfunctions_tasks as aws_sfn_tasks,
)
from constructs import Construct

from cdk_utils.CloudFormation_util import add_tags
import cdk_utils.CdkDotJson_util
import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names

# from vpc_rds.vpc_stack import VpcStack
from frontend.infrastructure import Frontend
from observe.infrastructure import Monitoring



"""
    @param scope: standard CDK arg
    @param id_: standard CDK arg
    @param git_branch:
    @param aws_env: deployment-environment;  Example: various DEVELOPER-git-branches may all be deployed into SHARED `DEV` environment.
    @param env:  This is of type `aws_cdk.Environment` containing AWS_REGION, AWS_ACCOUNT_ID, etc..
    @param kwargs:
"""
class Gen_AllFrontendApplicationStacks():
#     def user_pool_id(self):
#         return self._user_pool_id

#     def user_pool_client_id(self):
#         return self._user_pool_client_id

    def __init__( self,
        scope: Construct,
        id_: str,
        stack_prefix :str,
        tier: str,
        aws_env :str,
        git_branch :str,
        **kwargs: any
    ):
        super().__init__()
        # super().__init__(scope, id_, **kwargs)   ### Within this App's framework, Do NOT pass kwargs into Constructs!

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        self.stack_prefix = stack_prefix

        backend_stateless_stkname = aws_names.gen_awsresource_name(
                    tier=tier,
                    cdk_component_name = constants.CDK_BACKEND_COMPONENT_NAME, ### Backend's component-name
                    simple_resource_name = f"StatelessAPIGW"
        )
        frontend_stkname = aws_names.gen_awsresource_name_prefix(
                    tier=tier,
                    cdk_component_name = constants.CDK_FRONTEND_COMPONENT_NAME,
        )
        # backend_stateless_stkname = constants.CDK_APP_NAME +'-'+ constants.CDK_BACKEND_COMPONENT_NAME + \
        #                         f"-{tier}-StatelessAPIGW"
        imported_api_url = Fn.import_value(f"{backend_stateless_stkname}-APIEndpointURL") ### Example: `https://o1a2b3c4d5f.execute-api.us-east-1.amazonaws.com/${StageName}/`
        api_domain = Fn.parse_domain_name(imported_api_url)  ### removes the stage_name and any '/'

        backend_cognito_stkname = (
            constants.CDK_APP_NAME +'-'+ constants.CDK_BACKEND_COMPONENT_NAME
            + f"-{tier}-Cognito"
        )

        import_ui_client_id = Fn.import_value(f"{backend_cognito_stkname}-UIClientID")
        import_user_pool_domain = Fn.import_value(
            f"{backend_cognito_stkname}-UserPoolDomain"
        )
        import_user_pool_id = Fn.import_value(f"{backend_cognito_stkname}-UserPoolID")
        import_user_pool_id = Fn.import_value(f"{backend_cognito_stkname}-UserPoolID")

        # this_dir = pathlib.Path.dirname(__file__)
        # with open( this_dir / "frontend/ui/cognito_ids", "w+", encoding="utf-8") as build_fp:
        #     build_fp.write(
        #         f"ui_client_id: {import_ui_client_id}, api_client_id: {import_api_client_id}, user_pool_id: {import_user_pool_id}"
        #     )
        #
        # system(f"cat {this_dir}/frontend/ui/cognito_ids")

        root_domain, frontend_website_FQDN = cdk_utils.CdkDotJson_util.lkp_website_details( cdk_scope=scope, tier=tier )

        # if tier == "prod":
        #     domain_name = root_domain
        # else:
        #     if branch in constants.GIT_STD_BRANCHES:
        #         domain_name = f"{tier}.{root_domain}"
        #     else:  ### developer specific branch
        #         domain_name = f"dev.{root_domain}"

        ### (dev|int|uat).<ROOTDOMAIN>.com   --versus--   production uses <ROOTDOMAIN>.com
        # print( f"!!!!!!! ATTENTION !!!!!!!! domain_name='{domain_name}' in "+ __file__ )

        # public_api_FQDN = stateless_stack.api_construct.rest_api.deployment_stage.url_for_path(),
        # stkSL = Stack.of(stateless_stack)
        # public_api_FQDN = stateless_stack.api_construct.rest_api.rest_api_id + f".execute-api.{stkSL.region}.{stkSL.url_suffix}"
        # print( f"public_api_FQDN = '{public_api_FQDN}'")
        frontend_stack = FrontendStack(
            scope=scope,
            id_=frontend_stkname,
            api_domain=api_domain,
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            stack_name=frontend_stkname,
            root_domain=root_domain,
            frontend_domain_name=frontend_website_FQDN,
            public_api_FQDN = api_domain, ### stateless_stack.api_construct.public_api_FQDN,
            **kwargs
        )

        if tier in constants.STD_TIERS:
            ObserveStack(
                scope=scope,
                id_=f"{frontend_stkname}-observe",
                tier=tier,
                aws_env=aws_env,
                git_branch=git_branch,
                api_name=(
                    constants.CDK_APP_NAME +'-'+ constants.CDK_FRONTEND_COMPONENT_NAME
                    + f"-{tier}-Stateless-{constants.CDK_APP_NAME}-api"
                ),
                user_pool_id=import_user_pool_id,
                user_pool_client_id=import_ui_client_id,
                ui_domain_name=frontend_website_FQDN,
                # ui_domain_name=domain_name,
                stack_name=f"{id_}-observe",  ### kwargs
                **kwargs
            )
        else:  ### developer specific branch
            pass ### Cuz, the DEV-git-branch's pipeline already took care of this.  ASSUMPTION: Before ANY Developer-Git-Branch got deployed into DEV-AWS-Account, `dev` Git-Branch got deployed already.

        self._url = frontend_stack._url



class FrontendStack(Stack):
    def __init__( self, scope: Construct,
        id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        stack_name :str,
        api_domain: str,
        root_domain :str,
        frontend_domain_name :str,
        public_api_FQDN :str,
        **kwargs,
    ) -> None:
        super().__init__(
            scope=scope,
            id=id_,
            stack_name=stack_name,
            **kwargs
        )

        print( f"tier='{tier}' within FrontendStack: "+ __file__ )
        print( f"aws_env='{aws_env}' within FrontendStack: "+ __file__ )
        print( f"git_branch='{git_branch}' within FrontendStack: "+ __file__ )

        self.frontend_construct = Frontend(
            scope = self,
            id_ = "frontend",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            api_domain=api_domain,
            root_domain=root_domain,
            frontend_domain_name=frontend_domain_name,
            public_api_FQDN = public_api_FQDN,
        )

        self._url = CfnOutput(
            self,
            id="FrontendURL",
            export_name=f"{self.stack_name}-Frontend-URL",
            value=self.frontend_construct.frontend_url,
        )


class ObserveStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        api_name: str,
        user_pool_id: str,
        user_pool_client_id: str,
        ui_domain_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, **kwargs)

        monitor = Monitoring(
            self,
            "monitoring",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            user_pool_id=user_pool_id,
            user_pool_client_id=user_pool_client_id,
            api_name=api_name,
            ui_domain_name=ui_domain_name,
        )
