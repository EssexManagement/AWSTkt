import pathlib
from typing import Optional

from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_cognito as cognito,
    aws_iam,
    aws_wafv2,
)
from constructs import Construct

import constants
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from common.cdk.standard_lambda import StandardLambda

THIS_DIR = pathlib.Path(__file__).parent

class MyUserPool(Construct):
    def __init__(self, scope: "Construct", id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
    ) -> None:
        super().__init__(scope, id_)
        stk = Stack.of(self)

        print( f"tier = '{tier}' within "+ __file__ )
        print( f"git_branch = '{git_branch}' within "+ __file__ )
        print( f"aws_env = '{aws_env}' within "+ __file__ )
        effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER ### ["dev", "int", "uat", "prod"]

        root_domain :str  = self.node.try_get_context("root_domain")
        print( f"root_domain = '{root_domain}' within "+ __file__ )

        _, frontend_domain, _ = CdkDotJson_util.lkp_website_details( scope, tier )

        web_acl_arn = CdkDotJson_util.lkp_waf_acl_for_cognito( self, effective_tier )
        print( f"COGNITO's WAF-ACL arn = '{web_acl_arn}'")

        from_emailaddr = constants.get_COGNITO_FROM_EMAIL( tier=tier, aws_env=aws_env )
        replyto_emailaddr = constants.get_COGNITO_REPLY_TO_EMAIL( tier=tier, aws_env=aws_env )
        print( f"COGNITO's from_emailaddr = '{from_emailaddr}'")
        print( f"COGNITO's replyto_emailaddr = '{replyto_emailaddr}'")

        user_pool: cognito.IUserPool = cognito.UserPool( scope=self,
            id=f"{constants.CDK_APP_NAME}-{constants.CDK_BACKEND_COMPONENT_NAME}-{tier}",
            # sign in
            sign_in_aliases=cognito.SignInAliases(username=True, email=True),
            # auto_verify=cognito.AutoVerifiedAttrs(email=True, phone=True),
            # Attributes
            standard_attributes=cognito.StandardAttributes(
                # fullname=cognito.StandardAttribute(
                #  required=True,
                #  mutable=False
                # ),
                # address=cognito.StandardAttribute(
                #  required=False,
                #  mutable=True
                # )
            ),
            custom_attributes={
                "my_app_id": cognito.StringAttribute(
                    min_len=5, max_len=15, mutable=False
                ),
                "callingcode": cognito.NumberAttribute(min=1, max=3, mutable=True),
                "is_employee": cognito.BooleanAttribute(mutable=True),
                "joined_on": cognito.DateTimeAttribute(),
                "login_count": cognito.NumberAttribute(min=0,mutable=True)
            },
            # Policies
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(1),
            ),
            # email
            email=cognito.UserPoolEmail.with_ses(
                from_email=from_emailaddr,
                from_name=constants.CDK_APP_NAME +" support",
                reply_to=replyto_emailaddr,
            ),
            user_invitation=cognito.UserInvitationConfig(
                email_subject=constants.CDK_APP_NAME +" temporary password",
                email_body="Your account for "+ constants.CDK_APP_NAME +" has been created.\n\n"+
                    "Your username is {username} and temporary password is {####} \n\n" +        ### ATTENTION !! THIS lines use '{}' in a DIFFERENT WAY!!!
                    "You will be required to change your password when you first login to "+ constants.CDK_APP_NAME +". \n\n" +
                    "The "+ constants.CDK_APP_NAME +" app is available at https://"+ (frontend_domain or "undefined-in-cdk.json") +"/ \n\n" +
                    "If you have any questions, please send email to "+ replyto_emailaddr +" \n\nThank you ! \n\n" +
                    constants.CDK_APP_NAME +"Team",
                sms_message="Your account for "+ constants.CDK_APP_NAME +" has been created.\nYour username is {username} and temporary password is {####} ",
            ),
            user_verification=cognito.UserVerificationConfig(
                email_style=cognito.VerificationEmailStyle.LINK,
                email_subject=constants.CDK_APP_NAME +" account request verification - Please take action!",
                email_body="Hello,\nThank you for registering for "+ constants.HUMAN_FRIENDLY_APP_NAME + "." +
                        "To use our site, please use the link below to verify your identity:\n{##Verify Email##} \n\n" +
                        "If you cannot access the link or did not make this request, contact us at "+ from_emailaddr +"\n"+
                        "Thank you ! \nThe "+ constants.HUMAN_FRIENDLY_APP_NAME +" Support team\n",
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            self_sign_up_enabled=True,
            removal_policy=RemovalPolicy.RETAIN if tier in ["uat", "prod"] else RemovalPolicy.DESTROY,
        )

        # UI App Clients
        self.ui_client = user_pool.add_client(
            "customer-app-client",
            auth_flows=cognito.AuthFlow(user_srp=True, user_password=True),
            id_token_validity=Duration.minutes(20),
            access_token_validity=Duration.minutes(20),
            refresh_token_validity=Duration.days(1),
            generate_secret=False, ### Attention: Must be False.  For QE-team, MANUALLY create a 2nd App-Client-Integration (that contains a Client-Secret)
        )

        # Resource Server
        scope_name = "*"
        full_access_scope: cognito.ResourceServerScope = cognito.ResourceServerScope(
            scope_name=scope_name, scope_description="Full access"
        )

        resource_path = "api"
        resource_server: cognito.IUserPoolResourceServer = (
            user_pool.add_resource_server(
                "ResourceServer", identifier=resource_path, scopes=[full_access_scope]
            )
        )

        # domain_prefix=f"{constants.CDK_APP_NAME}-{tier}".lower()
        # domain_prefix=f"{constants.CDK_APP_NAME}-{stage}".lower()
        domain_prefix = frontend_domain.lower().replace(".", "-") if frontend_domain else None
        ### It must be unique GLOBALLY as: https://{domain_prefix}.auth.us-east-1.amazoncognito.com

        self.user_pool_domain: Optional[cognito.IUserPoolDomain] = user_pool.add_domain(
            "cognito-domain",
            cognito_domain=cognito.CognitoDomainOptions( domain_prefix=domain_prefix ),
            # cognito_domain=cognito.CustomDomainOptions()
        ) if domain_prefix else None

        # API App Client

        self.api_client: cognito.IUserPoolClient = user_pool.add_client(
            "api-app-client",
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    cognito.OAuthScope.resource_server(
                        resource_server, full_access_scope
                    )
                ],
            ),
            access_token_validity=Duration.minutes(20),
            refresh_token_validity=Duration.minutes(60),
            generate_secret=True,
            enable_token_revocation=True,
        )

        if web_acl_arn:
            wafaclass = aws_wafv2.CfnWebACLAssociation(
                scope=self,
                id="wafv2ForCognito",
                web_acl_arn = web_acl_arn,
                resource_arn = user_pool.user_pool_arn,
            )
            wafaclass.add_dependency(user_pool.node.default_child) # type: ignore
            if self.user_pool_domain: wafaclass.add_dependency(self.user_pool_domain.node.default_child) # type: ignore

        # # create a new Lambda function using aws_lambda_python_alpha that is based on the file at: ./src/cognito_custom_msg_handler.py
        # lambda_file_name = "cognito_custom_msg_handler"
        # lambda_name = f"{APP_NAME}-{COMPONENT_NAME}-{tier}-{lambda_file_name}"

        # cog_lambda = StandardLambda(
        #     scope=self, vpc=None, sg_lambda=None, real_tier=tier
        # ).create_lambda(
        #     scope=self,
        #     lambda_name = lambda_name,
        #     index=lambda_file_name +".py",
        #     handler="lambda_handler",
        #     description=f"{tier} Cognito Custom-Event Handler for {constants.CDK_APP_NAME}",
        #     path_to_lambda_src_root = THIS_DIR / "src",
        # )
        # cog_lambda.add_to_role_policy(
        #     statement=aws_iam.PolicyStatement(
        #         actions=["cognito-idp:List*", "cognito-idp:Describe*",
        #                  "cognito-idp:AdminAddUserToGroup",
        #                  "cognito-idp:GetGroup", "cognito-idp:CreateGroup", "cognito-idp:UpdateGroup",
        #                  "cognito-idp:GetUser*", ### "cognito-idp:ChangePassword", "cognito-idp:ForgotPassword", "cognito-idp:ResendConfirmationCode",
        #         ],
        #         resources=[ f"arn:{Stack.of(self).partition}:cognito-idp:*:{Stack.of(self).account}:userpool/*" ],
        #     )
        # )

        # user_pool.add_trigger(
        #     operation=cognito.UserPoolOperation.POST_CONFIRMATION,
        #     fn=cog_lambda,
        # )

        self.user_pool: cognito.IUserPool = user_pool
