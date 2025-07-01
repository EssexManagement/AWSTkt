from pathlib import Path
from typing import Optional
import re

from constructs import Construct

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda,
    aws_apigateway,
    aws_cognito,
    aws_logs,
    aws_wafv2,
)

import constants
import cdk_utils.CdkDotJson_util as CdkDotJson_util
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from common.cdk.mappings import Mappings
from common.cdk.standard_lambda import StandardLambda
from common.cdk.standard_logging import get_log_grp, LogGroupType

from api import config

class Api(Construct):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        vpc: ec2.IVpc,
        emfact_user_unpublished: rds.DatabaseSecret,
        rdsSG: ec2.SecurityGroup,
        user_pool: aws_cognito.UserPool,
        lambda_configs: config.LambdaConfigs,
        # inside_vpc_lambda_factory :StandardLambda,
        **kwargs,
    ):
        super().__init__(scope, id_)

        stk = Stack.of(self)
        this_dir = Path(__file__).parent

        effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER ### ["dev", "int", "uat", "prod"]
        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        datadog_destination = Mappings(self).get_dd_subscription_dest( tier=effective_tier, aws_env=aws_env ) ### TODO
        if datadog_destination is None:
            print( f"WARNING !! Datadog's Kinesis-DataStream destination missing for tier='{aws_env}' !!  -- in  Api(): within ", __file__ )

        ### Configuration for APIGW ---------------------
        default_cors_preflight_options = aws_apigateway.CorsOptions(
            allow_headers=[
                "Content-Type",
                "X-Amz-Date",
                "Authorization",
                "X-Api-Key",
            ],
            allow_methods=["OPTIONS", "GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_credentials=True,
            allow_origins=["*"],
        )

        loggrp = get_log_grp(
            scope = self,
            tier = tier,
            loggrp_type = LogGroupType.APIGW,
            what_is_being_logged = aws_names.gen_awsresource_name( tier, constants.CDK_BACKEND_COMPONENT_NAME, f"APIGW-AccessLogs" ),
            # loggrp_name = ...
        )

        ## APIGW ---------------------------------
        stage_options: aws_apigateway.StageOptions = aws_apigateway.StageOptions(
            stage_name="prod",  ### always "prod" for ALL tiers (which, BTW is AWS-default, if left unnamed)
            tracing_enabled=True,
            data_trace_enabled=True,
            logging_level=aws_apigateway.MethodLoggingLevel.INFO,
            metrics_enabled=True,
            access_log_destination=aws_apigateway.LogGroupLogDestination(loggrp), # type: ignore
            access_log_format=aws_apigateway.AccessLogFormat.json_with_standard_fields(
                caller=True,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True,
            ),
            cache_cluster_enabled=False,
            cache_ttl=Duration.seconds(0),
        )

        ### APIGW & the only RESTAPI constructor -----------------------------------------
        _, fqdn, _ = CdkDotJson_util.lkp_website_details( scope, tier )
        description=f"This service serves {constants.HUMAN_FRIENDLY_APP_NAME} at {fqdn} -- created by Stack: {stk.stack_name}."
        self.api = aws_apigateway.RestApi( self, "emfact-api",
            rest_api_name = f"{stk.stack_name}-emfact-api",
            description = description,
            default_cors_preflight_options = default_cors_preflight_options,
            endpoint_types = [aws_apigateway.EndpointType.REGIONAL],
            binary_media_types = ["application/pdf"],
            deploy_options = stage_options,
            cloud_watch_role_removal_policy = constants_cdk.get_stateful_removal_policy( construct=scope, tier=tier ),
        )

        self.api_v1_resource = self.api.root.add_resource("api").add_resource("v1")

        ### Security & Audit-Compliance configuration -------------------------
        if datadog_destination:
            aws_logs.SubscriptionFilter( scope=self, id="_logs-subscfilter_"+ loggrp.node.id,                           ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_logs/SubscriptionFilter.html
                destination = datadog_destination, # type: ignore
                log_group = loggrp,
                filter_pattern = aws_logs.FilterPattern.all_events(),
                # filter_name= automatically genereated if NOT specified
            )

        web_acl_arn = CdkDotJson_util.lkp_waf_acl_for_apigw( self, effective_tier )
        print( f"APIGW's WAF-ACL arn = '{web_acl_arn}'")
        if web_acl_arn:
            # given the ARN to a WAF-ACL, apply it to the above APIGW
            apigw_stage_arn = f"arn:{stk.partition}:apigateway:{stk.region}::/restapis/{self.api.rest_api_id}/stages/{stage_options.stage_name}"
            wafaclass = aws_wafv2.CfnWebACLAssociation(
                scope=self,
                id="wafv2ForAPIGW",
                web_acl_arn=web_acl_arn,
                resource_arn=apigw_stage_arn,
            )
            wafaclass.add_dependency(self.api.node.default_child) # type: ignore
            wafaclass.add_dependency(self.api.deployment_stage.node.default_child) # type: ignore

        ### common authorizer for all Lambdas ------------------------------------
        self.my_authorizer = aws_apigateway.CognitoUserPoolsAuthorizer( self, "emFactAuthorizer",
            authorizer_name=f"{stk.stack_name}-api-auth",
            cognito_user_pools=[user_pool],
            identity_source=aws_apigateway.IdentitySource.header("Authorization"),
        )

        ### ------------- OLD CODE ----------
        ### ------------- OLD CODE ----------
        ### ------------- OLD CODE ----------
        # beg :int = 0
        # ### ----- following code should be __SIMILAR__ (NOT identical)  to the lines 111-124 of `deployment.py`
        # for chunk_num in range(0,constants.NUM_OF_CHUNKS):
        #     enddd :int = beg + CHUNK_SIZE
        #     # beg = int( chunk_num*CHUNK_SIZE )
        #     # enddd = int( (chunk_num+1)*CHUNK_SIZE )
        #     print( f"Chunk is from '{beg}' to '{enddd}' --- in StatelessStackLambdas() within "+ __file__ )
        #     chunk = config.api_resources[ beg : enddd ]
        #     # config_api_resources = chunk,
        #     print( f"CHUNK is of len = '{len(chunk)}' in StatelessStackLambdas() within "+ __file__ )
        #     if ( len(chunk) == 0 ):
        #         return
        #     print( f"INTEGRATING(with-APIGW) Lambdas for Chunk # {chunk_num}: from {beg} to {enddd} --- inside Api(constructor) within "+ __file__ )

        #     id_ = f"{APP_NAME}-{COMPONENT_NAME}-{tier}-Lambdas-{chunk_num}",
        #     id_=f"{beg}-{enddd}"

        ### ------------------------- integrate ALL 𝜆s from config.py ---------------------------
        a_lambda :dict
        for a_lambda in lambda_configs.list:

            index :str = config.LambdaConfigs.get_lambda_index( a_lambda ) # type: ignore
            handler = config.LambdaConfigs.get_handler(a_lambda)
            entry   = config.LambdaConfigs.get_lambda_entry( a_lambda )
            apigw_res_path :Optional[str] = config.LambdaConfigs.get_apigw_path(a_lambda)
            simple_name = config.LambdaConfigs.get_simple_name(a_lambda)
            print(f'simple_name={simple_name}:index={index}:apigw_res_path={apigw_res_path}:handler={handler}:entry={entry}')
            # TODO: Should fix this more
            # now the criteria for ETL Lambda is not having api_gw_path and having default handler name
            """ SCENARIO:
                When .. for this item, the name of the python-handler is the worldwide default (`lambda_handler`).
                .. and the name of the PY-module is --NO-- good to be used as the Lambda's name (for whatever reason)
                that's when you use the "simple-name" of a lambda (without CDK_APP_NAME and TIER) .. ..
                It defaults to the value returned by `get_handler(item)` ONLY if that is a unique-value.
                ELSE it next defaults to the value returned by `get_apigw_path(item)` which better be Not `None`.
                Else, an exception is raised.
            """
            if not simple_name:
                if (not handler or handler == config.DEFAULT_LAMBDA_HANDLER):
                    if not apigw_res_path:
                        simple_name = re.sub(r"\./", "_", index.replace(".py", ""))
                        # raise Exception(f"get_simple_name() is not defined, when the Handler-method is the generic '{DEFAULT_LAMBDA_HANDLER}' for item = '{a_lambda}'")
                    else:
                        simple_name = apigw_res_path
                else:
                    if not apigw_res_path:
                        simple_name = handler
                    else:
                        simple_name = apigw_res_path

            # if not apigw_res_path and handler == DEFAULT_LAMBDA_HANDLER:
            #     ### This is for ETL-Lambdas that can NOT be accessed via APIGW.
            #     h = re.sub(r"\./", "_", index.replace(".py", ""))
            #     function_name= aws_names.gen_lambda_name( tier=tier, simple_lambda_name = h )
            # else:
            #     function_name= aws_names.gen_lambda_name( tier=tier, simple_lambda_name=simple_name )
            function_name= aws_names.gen_lambda_name( tier=tier, simple_lambda_name=simple_name )
            http_method :Optional[str] = config.LambdaConfigs.get_http_method(a_lambda)

            ### -------
            # for (simple_resource_name, http_method, handler_id, handler_file) in config.api_resources:
            print( f"INTEGRATING(with-APIGW) Lambda {function_name}: http-{http_method} --- inside Api(constructor) within "+ __file__ )

            ### Do Not create APIs for these Lambdas
            # if function_name in ['wakeup_db']:
            # if function_name == 'process_s3_uploads':
            if not http_method or http_method.lower() == "n/a" or http_method.lower() == "none":
                continue

            is_auth_needed = True
            if handler in ("get_search_results", "post_search_results", "post_wakeup_db", "approve_or_decline_curated"):
                is_auth_needed = False
                # authorizer_id = None

            fn :aws_lambda.IFunction = aws_lambda.Function.from_function_name( scope=self,
                    # id = "lkp-"+(handler if handler else "None"),
                    id="lkp-"+simple_name,
                    function_name=function_name,
            )

            if apigw_res_path:
                ### Integrate pre-existing/previously-deployed Lambda with APIGW
                get_lambda_int_resource_method(
                    fn = fn,
                    api_resource = self.api_v1_resource,
                    resource_name = apigw_res_path,
                    method = http_method,
                    authorizer = self.my_authorizer if is_auth_needed else None, # type: ignore
                    # authorizer_id = self.my_authorizer.authorizer_id if self.my_authorizer else None,
                )

        self.public_api_FQDN = self.api.rest_api_id + f".execute-api.{stk.region}.{stk.url_suffix}"
        print( f"public_api_FQDN = '{self.public_api_FQDN}'")

### ====================================================================================================
def get_lambda_int_resource_method(
    fn :aws_lambda.IFunction,
    api_resource :aws_apigateway.Resource,
    resource_name :str,
    method :str,
    authorizer: aws_apigateway.CognitoUserPoolsAuthorizer,
    # authorizer_id: str,
):
    lambda_int = aws_apigateway.LambdaIntegration(
        handler = fn,
        request_templates={"application/json": '{ "statusCode": "200" }'}
    )
    resource :aws_apigateway.Resource = api_resource.add_resource(resource_name)
    mthd = resource.add_method(
        http_method = method,
        integration = lambda_int,
        authorizer=authorizer,  ### Since we want to SHARE CognitoAuthorizer ACROSS multiple STACKS, we will NOT specify it here.  See 6 lines below!!!
        authorization_type=aws_apigateway.AuthorizationType.COGNITO if authorizer is not None else aws_apigateway.AuthorizationType.NONE,
        # authorization_scopes=['api/*'],
        request_parameters={"method.request.header.authorization": (authorizer is not None)},
        # request_parameters={"method.request.header.authorization": (authorizer_id is not None)},
    )
    # if authorizer_id:
    #     mthd_resource = mthd.node.find_child('Resource')
    #     mthd_resource.add_property_override('AuthorizationType', aws_apigateway.AuthorizationType.COGNITO ) ### 'COGNITO_USER_POOLS'
    #     mthd_resource.add_property_override('AuthorizerId', {"Ref": authorizer_id})
    mthd.node.add_dependency( fn )
    # mthd.node.add_dependency( fn.role )
    return (lambda_int, resource)
