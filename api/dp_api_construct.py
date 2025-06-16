"""CDK construct for API Gateway and lambda functions"""

import typing
from typing import Optional

from os import path
import pathlib
from functools import partial

from constructs import Construct
from aws_cdk import (
    Aws,
    Duration,
    Stack,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_lambda_python_alpha as python_lambda,
    RemovalPolicy,
    aws_logs as logs,
    aws_apigateway as apigateway,
    aws_secretsmanager as sm,
    aws_iam as iam,
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_sns,
    aws_sqs,
)

from constants import (
    LAMBDA_PYTHON_RUNTIME,
    LAMBDA_PYTHON_RUNTIME_STR,
    LAMBDA_ADOT_CONFIG,
    LAMBDA_ARCHITECTURE,
    LAMBDA_ARCHITECTURE_X86_64,
    LAMBDA_INSIGHTS_VERSION,
    LOG_RETENTION,
    LOG_LEVEL,
    UPPER_TIER_NAMES,
    C_TIER_PROD,
    C_TIER_STAGE,
    C_TIER_TEST,
    C_ENV_NON_PROD,
    C_ENV_PROD,
)

from data_lake_core import data_lake, athena

from cdk_util.construct_layer import ConstructLayer

from .config import TIMEOUT, api_resources_json


THIS_DIR = path.dirname(__file__)


class ApiConstruct(ConstructLayer):
    """CDK construct for NCCR Rest API
    lambda #1 that is the handler for the "PRIVATE API" (http PUT).
    At this point in time, No Authentication implemented (NO Lambda-authorizer.  No Cognito-Authorizer.  NO API-Tokens)
    APIGW will need Access to execute the Lambda function.
    """

    def __init__(
        self,
        scope: "Construct",
        id_: str,
        vpc: ec2.IVpc,
        sg_lambda: ec2.ISecurityGroup,
        ddb_user_tbl: dynamodb.ITable,
        nccr_s3: s3.IBucket,
        nccr_s3_internal: s3.IBucket,
        db_user_tbl_reqid_gsi: str,
        step_func: sfn.StateMachine,
        clean_data_lake: data_lake.DataLake,
        athena_workgroup: athena.WorkGroup,
        enduser_notif_snstopic: aws_sns.ITopic,
        snow_resubmit_sqs: aws_sqs.Queue,
        cohort_count_sqs: aws_sqs.Queue,
    ) -> None:
        super().__init__(scope, id_)

        self._stack = Stack.of(self)
        self._vpc = vpc
        self._sg_lambda = sg_lambda
        self._ddb_user_tbl = ddb_user_tbl
        self._nccr_s3 = nccr_s3
        self._nccr_s3_internal = nccr_s3_internal
        self._clean_data_lake = clean_data_lake
        self._athena_workgroup_name = athena_workgroup.work_group.name
        self._athena_workgroup_result_bucket = athena_workgroup.result_bucket
        self.enduser_notif_snstopic = enduser_notif_snstopic
        self.snow_resubmit_sqs = snow_resubmit_sqs
        self.cohort_count_sqs = cohort_count_sqs
        self._servicenow_submit_lambda = None
        self._api_lambda_env = {
            "NCCR_TABLE_NAME": ddb_user_tbl.table_name,
            "NCCR_USER_BUCKET_NAME": self._nccr_s3.bucket_name,
            "INTERNAL_BUCKET_NAME": self._nccr_s3_internal.bucket_name,
            "NCCR_TABLE_REQID_GSI": db_user_tbl_reqid_gsi,
            "LOG_LEVEL": LOG_LEVEL[self.real_tier],
            "UI_DOMAIN_NAME": self.ui_domain_name,
            "STEPFUNC_ARN": step_func.state_machine_arn,
            "ATHENA_DB": self._clean_data_lake.database.database_name,
            "ATHENA_WORKGROUP": self._athena_workgroup_name,
            "NOTIFY_USER_SNS": self.enduser_notif_snstopic.topic_arn,
            "SNOW_RESUBMIT_SQS": self.snow_resubmit_sqs.queue_url,
            "COHORT_COUNT_SQS": self.cohort_count_sqs.queue_url,
            "TIER": self.tier,
        }

        self.sfn_lambdas: dict[str, lambda_.IFunction] = {}
        print(f"API Gateway for {self.tier}")

        resources = api_resources_json['resources']
        self.public_resources = api_resources_json['public_resources']

        self.secete_manager_info: dict = self.node.try_get_context("secrete_manager")[self.account_type]
        servicenow_api_sm_id = self.secete_manager_info["servicenow_api_sm_id"]
        servicenow_api_sm_name = self.secete_manager_info["servicenow_api_sm_name"]

        self.servicenow_api_sm: sm.ISecret = sm.Secret.from_secret_name_v2(
            self, servicenow_api_sm_id, secret_name=servicenow_api_sm_name
        )

        ### ------------------------------------------------
        allow_methods = self.get_http_methods(child_resources=resources)
        allow_methods.extend(self.get_http_methods(child_resources=self.public_resources))

        # TODO: CORS_origins = [ SERVICENOW_SETTINGS["dev-endpoint-FQDN"] ]

        ### ------------------
        ### From top-most/rootfolder of GitHub project-repo, FILE location = "backend/runtime/src/nccr/handler/servicenow_interface_handler.py"
        path_to_lambda_src_root = pathlib.Path(THIS_DIR) / '../runtime/src'
        rel_path_to_lambda_code = "nccr/handler/servicenow_interface_handler.py"
        fullpath_to_lambda_code = path_to_lambda_src_root / rel_path_to_lambda_code
        if not fullpath_to_lambda_code.exists():
            raise FileNotFoundError(
                f"File not found: fullpath_to_lambda_code={fullpath_to_lambda_code}\npath_to_lambda_src_root={path_to_lambda_src_root}"
            )
        else:
            path_to_lambda_src_root = path_to_lambda_src_root.resolve().absolute()  ### important!
            fullpath_to_lambda_code = fullpath_to_lambda_code.resolve().absolute()
            print(f"FOLDER containing fullpath_to_lambda_code = {fullpath_to_lambda_code.parent}")
            print(f"Just the filename within fullpath_to_lambda_code = {fullpath_to_lambda_code.name}")
            ### debug-only:
            # with open( fullpath_to_lambda_code, 'r' ) as f:
            #     print( '='*80, end='\n\n', flush=True )
            #     print( f.read() )
            #     print( '='*80, end='\n\n', flush=True )
            #     f.close()

        ### ------------------------------------------------
        allow_origins = [
            "https://nccrdataplatform.ccdi.cancer.gov",
            "https://nccrdataplatform-stage.ccdi.cancer.gov",
            "https://nccrdataplatform-test.ccdi.cancer.gov",
        ]
        if self.is_dev_branch or self.is_dev:
            allow_origins = ['*']

        default_cors_preflight_options = apigateway.CorsOptions(
            allow_headers=[
                'Content-Type',
                'X-Amz-Date',
                'Authorization',
                'X-Api-Key',
            ],
            # allow_methods=apigateway.Cors.ALL_METHODS,
            allow_methods=["OPTIONS", "DELETE", "GET", "POST", "PUT"],
            allow_credentials=True,
            allow_origins=allow_origins,
        )

        log_group: logs.ILogGroup = logs.LogGroup(
            scope=self,
            id=f"{self.tier}-ApiGatewayAccessLogs",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.FIVE_DAYS,
        )

        stage_options: apigateway.StageOptions = apigateway.StageOptions(
            tracing_enabled=True,
            data_trace_enabled=True,
            logging_level=apigateway.MethodLoggingLevel.INFO,
            metrics_enabled=True,
            access_log_destination=apigateway.LogGroupLogDestination(log_group),
            access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
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
            stage_name=self.tier,
            cache_cluster_enabled=False,
            caching_enabled=False,
            cache_ttl=Duration.seconds(0),
            throttling_burst_limit=1000,
            throttling_rate_limit=100,
        )

        ### ------------------------------------------------
        public_api_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    principals=[iam.AnyPrincipal()],
                    actions=['execute-api:Invoke'],
                    resources=[
                        "execute-api:/*/GET/*",
                        "execute-api:/*/POST/*",
                        "execute-api:/*/PUT/*",
                        "execute-api:/*/DELETE/*",
                        "execute-api:/*/OPTIONS/*",
                    ],
                    effect=iam.Effect.ALLOW,
                ),
            ]
        )

        self.rest_api = apigateway.RestApi(
            self,
            "rest_api",
            rest_api_name=f"{self.tier}-api",
            description=f"This service serves NCCR dataplatform {self._stack.stack_name}.",
            default_cors_preflight_options=default_cors_preflight_options,
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            # binary_media_types=['application/pdf'],
            deploy_options=stage_options,
            policy=public_api_policy,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
        )

        # base_path: str = "" if self.tier in ["test", "stage", "prod"] else self.tier
        # env: str = self.tier if self.tier in ["test", "stage", "prod"] else "dev"

        # # TODO: need to define api domain name in cdk.json file
        # api_domain_name_attributes = self.node.try_get_context("ui_domain_name")[env]
        # api_domain_name: apigateway.IDomainName = apigateway.DomainName.from_domain_name_attributes(
        #     self,
        #     "ui_domain_name",
        #     domain_name=api_domain_name_attributes["domain_name"],
        #     domain_name_alias_target=api_domain_name_attributes["aliases"],
        #     domain_name_alias_hosted_zone_id=api_domain_name_attributes["domain_name_alias_hosted_zone_id"],
        # )

        # apigateway.BasePathMapping(
        #     self,
        #     "base_path_mapping",
        #     domain_name=api_domain_name,
        #     base_path=base_path,
        #     rest_api=self.rest_api,
        #     stage=self.rest_api.deployment_stage,
        # )

        # TIER = self.node.try_get_context('tier')
        # env: str = TIER if TIER in ["test", "stage", "prod"] else "dev"
        # print(f"tier = {TIER}")
        # print(f"env = {env}")

        # # # csms_vpc_ids: list = self.node.try_get_context("vpc-external-ids")[env]["csms_vpc_ids"]
        # # csms_vpc_ids: list = AWS_VPC_SETTINGS["csms_vpc_ids"]
        # # print(f"csms_vpc_ids = {csms_vpc_ids}")

        # # api_res_arn = f"arn.{Stack.of(scope).partition()}:execute-api:/*/GET/*"
        # ### https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonapigateway.html#amazonapigateway-resources-for-iam-policies
        # api_invoke_arn = Arn.format( ArnComponents( service="execute-api", resource="*/*", resource_name="PUT", arn_format=ArnFormat.SLASH_RESOURCE_NAME ), stack=Stack.of(scope) )

        source_vpc_endpoints: list[str] = self.node.try_get_context("vpc_endpoints")
        vpn_ip_addresses: list[str] = self.node.try_get_context("vpn_ip_addresses")[self.account_type]
        vpc_cidr_block: list[str] = self._vpc.vpc_cidr_block
        service_now_ip_addresses: list[str] = self.node.try_get_context("service_now_ip_addresses")[self.real_tier]

        vpc_source_ip_addresses: list[str] = service_now_ip_addresses + [vpc_cidr_block] + vpn_ip_addresses
        self.provision_concurrency: int = self.node.try_get_context("provision_concurrency")[self.real_tier]

        print(f"IP TIER={self.tier:8} {source_vpc_endpoints=}, {vpc.vpc_id=}")
        print(f"IP TIER={self.tier:8} LOOK={self.account_type:8} {vpn_ip_addresses=}")
        print(f"IP TIER={self.tier:8} LOOK={self.real_tier_uc:8} {vpc_cidr_block=}")
        print(f"IP TIER={self.tier:8} LOOK={self.real_tier:8} {service_now_ip_addresses=}")
        print(f"IP TIER={self.tier:8} LOOK={self.tier:8} {vpc_source_ip_addresses=}")

        api_policy = iam.PolicyDocument(
            statements=[
                # iam.PolicyStatement(
                #     sid="OutsideVPCAccessDenied",
                #     principals=[iam.AnyPrincipal()],
                #     actions=['execute-api:Invoke'],
                #     resources=["execute-api:/*/*/*"],
                #     effect=iam.Effect.DENY,
                #     # conditions={"ForAllValues:StringNotEquals": {"aws:SourceVPC": [vpc.vpc_id] + csms_vpc_ids}},
                #     # conditions={"StringNotEquals": {"aws:SourceVpc": [vpc.vpc_id]}},
                #     # conditions={"StringNotEquals": {"aws:SourceVpce": [ctrp_vpce.vpc_endpoint_id]}},  ## associate ctrp vpce in crri devInt account
                # ),
                # iam.PolicyStatement(
                #     sid="InVPCCanInvokePrivateAPI",
                #     principals=[iam.AnyPrincipal()],
                #     actions=['execute-api:Invoke'],
                #     resources=["execute-api:/*/PUT/*"],
                #     effect=iam.Effect.ALLOW,
                #     conditions={"StringEquals": {"aws:SourceVpc": [vpc.vpc_id]}},
                # ),
                iam.PolicyStatement(
                    sid="APIGWInvokeVpce",
                    principals=[iam.AnyPrincipal()],
                    actions=['execute-api:Invoke'],
                    resources=["execute-api:/*/PUT/*", "execute-api:/*/DELETE/*"],
                    effect=iam.Effect.ALLOW,
                    conditions={
                        "StringEquals": {"aws:SourceVpce": source_vpc_endpoints},
                        "IpAddress": {"aws:VpcSourceIp": vpc_source_ip_addresses},
                    },
                ),
            ]
        )

        # policy has to be created only one time.
        self._athena_policy = self._create_athena_policy()

        self.private_rest_api = apigateway.RestApi(
            self,
            "private_rest_api",
            rest_api_name=f"{self.tier}-internal-api",
            description=f"This private service serves NCCR {self._stack.stack_name}.",
            default_cors_preflight_options=default_cors_preflight_options,
            endpoint_types=[apigateway.EndpointType.PRIVATE],
            # endpoint_configuration=apigateway.EndpointConfiguration(types=[apigateway.EndpointType.PRIVATE], vpc_endpoints=[ctrp_vpce]), ## allow ctrp from crri devInt apigw vpc endpoint
            # binary_media_types=['application/pdf'],
            deploy_options=stage_options,
            policy=api_policy,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
        )
        # base_path: str = "" if tier in ["test", "stage", "prod"] else tier
        # env: str = tier if tier in ["test", "stage", "prod"] else "dev"

        ### Create IAM-Roles common/shared across Lambdas
        self.__role_cache: typing.Dict[str, iam.Role] = {}
        ### Attention! Make sure to match the Key-string to what is in `config.py`
        commonRole_constr = CommonLambdaIAMRole(
            scope=self,
            id="commonDataReqHndl",
            ddb_user_tbl=self._ddb_user_tbl,  ### Only DynamoDB access required for this common-IAM-role.
            nccr_s3=None,
            db_user_tbl_reqid_gsi=None,
            step_func=None,
        )
        self.__role_cache["common_data_request_handler"] = commonRole_constr.common_role

        ### Lambda-layers
        self.lambda_layers = {}

        # lambdalayer_name = "wordsearch-whoosh"
        # cpu_arch = lambda_.Architecture.ARM_64
        # cpu_arch_str = cpu_arch.name.lower() ### === 'arm64'
        # lambdalayer_zip_file_path = f"../lambda_layers/{lambdalayer_name}-layer/build/layer-{lambdalayer_name}-{LAMBDA_PYTHON_RUNTIME_STR}-{cpu_arch_str}.zip"
        # lambdalayer_zip_file_path = path.join( THIS_DIR, lambdalayer_zip_file_path )
        # self.lambda_layers[lambdalayer_name] = lambda_.LayerVersion(
        #     self,
        #     f"layer-{lambdalayer_name}",
        #     layer_version_name=lambdalayer_name,
        #     code=lambda_.Code.from_asset(lambdalayer_zip_file_path),
        #     compatible_runtimes=[LAMBDA_PYTHON_RUNTIME],
        #     compatible_architectures=[cpu_arch],
        # )

        lambdalayer_name = "weasyprint"
        cpu_arch: lambda_.Architecture = LAMBDA_ARCHITECTURE_X86_64
        cpu_arch_str: str = cpu_arch.name.lower()  ### === 'arm64' string
        lambdalayer_zip_file_path = f"../lambda_layers/{lambdalayer_name}-layer/build/layer-{lambdalayer_name}-{LAMBDA_PYTHON_RUNTIME_STR}-{cpu_arch_str}.zip"
        lambdalayer_zip_file_path = path.join(THIS_DIR, lambdalayer_zip_file_path)
        self.lambda_layers[lambdalayer_name] = lambda_.LayerVersion(
            self,
            f"layer-{lambdalayer_name}",
            layer_version_name=Stack.of(self).stack_name + '_' + lambdalayer_name,
            code=lambda_.Code.from_asset(lambdalayer_zip_file_path),
            compatible_runtimes=[LAMBDA_PYTHON_RUNTIME],
            compatible_architectures=[cpu_arch],
        )

        # api_v1_resource = self.rest_api.root.add_resource('api').add_resource('v1')
        # # self.add_resources(api_v1_resource, resources, auth)
        private_api_v1_resource = self.private_rest_api.root.add_resource('api').add_resource('v1')
        self.add_resources([private_api_v1_resource], resources)

        self.aws_apigw_id_header = f'x-apigw-api-id:{self.private_rest_api.rest_api_id}'
        CALLBACK_BASE_URL = self.node.try_get_context('vpc_endpoint_hostname')
        self.private_gw_url = f'{CALLBACK_BASE_URL}/{self.private_rest_api.deployment_stage.stage_name}'
        self.servicenow_callback_url = f'{self.private_gw_url}/api/v1/requests'

    ### ==================================================
    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ### ==================================================

    def add_public_resources(self, auth: apigateway.IAuthorizer):

        api_env = {
            "SECRETE_MANAGER": self.servicenow_api_sm.secret_name,
            "SERVICENOW_CALLBACK_URL": self.servicenow_callback_url,
            "AWS_APIGW_ID_HEADER": self.aws_apigw_id_header,
        }
        self._api_lambda_env.update(api_env)

        public_api_v1_resource = self.rest_api.root.add_resource('api').add_resource('v1')
        self.add_resources([public_api_v1_resource], self.public_resources, auth)

    @staticmethod
    def add_grant_invoke(lambda1, lambda2):
        lambda1.grant_invoke(lambda2)

    ### ==================================================
    def get_http_methods(
        self,
        child_resources: list,
    ) -> list:
        ret_list = ['OPTIONS']  ### Due to CORS,this must be supported ALWAYS.
        for resource in child_resources:
            for resource_item in resource:
                print(f" resource(1): {resource_item}")
                for methods in resource[resource_item]['methods']:
                    for method in methods:
                        ret_list = ret_list + [method]
        return ret_list

    ### ==================================================

    def _create_athena_policy(self):
        athena_lambda_statements = [
            # Athena permissions
            iam.PolicyStatement(
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                ],
                resources=[
                    "arn:aws:athena:{}:{}:workgroup/{}".format(Aws.REGION, Aws.ACCOUNT_ID, self._athena_workgroup_name),
                ],
            ),
            # Glue permissions
            iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetPartitions",
                    "glue:CreateTable",
                    "glue:DeleteTable",
                ],
                resources=[
                    "arn:aws:glue:{}:{}:catalog".format(Aws.REGION, Aws.ACCOUNT_ID),
                    self._clean_data_lake.database.database_arn,
                    "arn:aws:glue:{}:{}:table/{}/*".format(
                        Aws.REGION, Aws.ACCOUNT_ID, self._clean_data_lake.database.database_name
                    ),
                ],
            ),
        ]
        policy = iam.Policy(
            self,
            id=f"Athena-Inline-Policy-backend",
            statements=athena_lambda_statements,
        )
        return policy

    def add_resources(
        self,
        parent_resources: typing.List[apigateway.IResource],
        child_resources: list,
        auth: apigateway.IAuthorizer = None,
    ):

        ### Loop thru items in `config.py` ..
        for resource in child_resources:
            for resource_item in resource:
                print(f" resource: {resource_item}")
                api_resources: typing.List[apigateway.IResource] = list(
                    map(partial(self.add_api_resource, child=resource_item), parent_resources)
                )
                for methods in resource[resource_item]['methods']:
                    for method in methods:
                        only_test = methods[method].get('only_test', False)
                        no_auth = methods[method].get('no_auth', False)
                        # return_mime_type = methods[method].get('return_mime_type', None)
                        if only_test and self.is_prod:
                            # skip creating delete_user_data_lambda in prod
                            continue

                        lambda_id = methods[method].get('lambda_id')

                        index = methods[method]['index']
                        handler = methods[method]['handler']
                        memory_size = methods[method].get('memory_size', 256)
                        print(f"{resource_item} - {method} - {index} - {handler}")
                        handler_id = lambda_id or (index.replace(".py", "").split("/")[-1] + '_' + handler).lower()
                        lambda_name = methods[method].get('lambda_name', handler_id)
                        print(f"handler_id = '{handler_id}' and lambda_name = '{lambda_name}'")
                        function_name = f"{self.tier}_{lambda_name}"
                        lambda_rolename: typing.Optional[str] = methods[method].get('IAMRoleName', None)
                        lambda_layers_names: typing.Optional[list] = methods[method].get('lambda-layers-names', None)
                        override_content_type_to_BINARY: bool = methods[method].get('mime-response', None) is not None
                        # override_content_type_to_BINARY: bool = lambda_name in ["create_pdf_lambda"]
                        cpu_arch = methods[method].get('cpu-arch', LAMBDA_ARCHITECTURE)
                        extra_env_vars = methods[method].get('extra-env-vars')

                        if lambda_rolename:
                            if not self.__role_cache:
                                self.__role_cache: typing.Dict[str, iam.Role] = {}
                            lambda_role = self.__role_cache.get(lambda_rolename, None)
                            if not lambda_role:
                                raise BaseException(
                                    f"!! UN-DEFINED IAM-role '{lambda_rolename}' wtihin config.py for index ='{index}' handler = '{handler}'"
                                )
                        else:
                            lambda_role = None

                        lambda_specific_layers = None
                        if lambda_layers_names:
                            print(f"lambda_layers_names='{lambda_layers_names}'")
                            lambda_specific_layers = []
                            for nm in lambda_layers_names:
                                # print(f"lambda_layers=\n'{lambda_layers}'")
                                lambda_specific_layers.append(self.lambda_layers[nm])
                            print(f"lambda_specific_layer='{lambda_specific_layers}'")

                        handler_func = python_lambda.PythonFunction(
                            scope=self,
                            id=handler_id,
                            function_name=function_name,
                            description=index,
                            entry=path.join(THIS_DIR, '../runtime/src'),
                            index=index,
                            handler=handler,
                            memory_size=memory_size,
                            # TODO: Clean up below - Removed VPC from API lambda
                            # vpc=self._vpc,
                            # security_groups=[self._sg_lambda],
                            # vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                            environment=(
                                {**self._api_lambda_env, **extra_env_vars} if extra_env_vars else self._api_lambda_env
                            ),
                            # TODO: is this the right role to use?
                            role=lambda_role,
                            timeout=TIMEOUT,
                            runtime=LAMBDA_PYTHON_RUNTIME,
                            layers=lambda_specific_layers,
                            tracing=lambda_.Tracing.ACTIVE,
                            architecture=cpu_arch,
                            adot_instrumentation=LAMBDA_ADOT_CONFIG,
                            insights_version=LAMBDA_INSIGHTS_VERSION,
                            log_retention=LOG_RETENTION[self.real_tier],
                        )
                        # add provisioned concurrency
                        # Create and publish a version
                        provision = methods[method].get('provision', False)
                        if provision and self.provision_concurrency:
                            version = lambda_.Version(
                                self,
                                f"APILambdaVersion-{handler_id}",
                                lambda_=handler_func,
                            )

                            # Create alias with provisioned concurrency
                            alias = lambda_.Alias(
                                self,
                                f"APILambdaAlias-{handler_id}",
                                alias_name="provision",
                                version=version,
                                provisioned_concurrent_executions=self.provision_concurrency,
                            )

                        self.enduser_notif_snstopic.grant_publish(handler_func)
                        self._ddb_user_tbl.grant_read_write_data(handler_func)
                        if lambda_specific_layers:
                            for lyr in lambda_specific_layers:
                                handler_func.role.add_to_principal_policy(
                                    iam.PolicyStatement(
                                        actions=["lambda:GetLayerVersion"],
                                        resources=[lyr.layer_version_arn],
                                    )
                                )

                        # TODO: below permission is only needed for submit to service now lambda
                        self.servicenow_api_sm.grant_read(handler_func)
                        if methods[method].get('s3_write', False):
                            self._nccr_s3.grant_read_write(handler_func)
                            self._nccr_s3_internal.grant_read_write(handler_func)
                        else:
                            self._nccr_s3.grant_read(handler_func)
                            self._nccr_s3_internal.grant_read(handler_func)

                        # TODO: Maybe restrict permission to specific lambda
                        self.snow_resubmit_sqs.grant_send_messages(handler_func)
                        self.cohort_count_sqs.grant_send_messages(handler_func)

                        if method == "delete":
                            # give delete permission to S3 when delete_user_data_lambda is created
                            self._nccr_s3.grant_delete(handler_func)
                            self._nccr_s3_internal.grant_delete(handler_func)
                        if no_auth:
                            if not lambda_role:  ### Do NOT touch a COMMON IAM-Role
                                # TODO: need to find the safe bucket
                                self._nccr_s3.grant_read(handler_func)
                            self.add_lambda_int_method(
                                api_resources[0], method, handler_func, None, override_content_type_to_BINARY
                            )
                        else:
                            self.add_lambda_int_method(
                                api_resources[0], method, handler_func, auth, override_content_type_to_BINARY
                            )  ## , return_mime_type)

                        sfn_name = methods[method].get('stepfunc')
                        if sfn_name:
                            self.stepfunc_lambdas = {}
                            self.stepfunc_lambdas[sfn_name] = handler_func

                        use_athena_role = methods[method].get('use_athena_role', False)
                        if not lambda_role:  ### Do NOT touch a COMMON IAM-Role
                            if use_athena_role:
                                handler_func.role.attach_inline_policy(policy=self._athena_policy)
                                self._athena_workgroup_result_bucket.grant_read_write(handler_func)
                                self._clean_data_lake.bucket.grant_read(handler_func)

                        if lambda_name == "submit_request_lambda":
                            self._servicenow_submit_lambda = handler_func

                if 'resources' in resource[resource_item]:
                    self.add_resources(
                        parent_resources=api_resources,
                        child_resources=resource[resource_item]['resources'],
                        auth=auth,
                    )

    @property
    def servicenow_submit_lambda(self) -> lambda_.IFunction:
        return self._servicenow_submit_lambda

    @staticmethod
    def add_api_resource(parent_resource: apigateway.IResource, child: str):
        global match_resource
        child_resource: apigateway.IResource = parent_resource.add_resource(child)
        if child == "match":
            match_resource = child_resource
        return child_resource

    @staticmethod
    def add_lambda_int_method(
        resource: apigateway.IResource,
        method: str,
        handler: lambda_.IFunction,
        auth: apigateway.IAuthorizer,
        override_content_type_to_BINARY: bool,
    ):
        """For use only within this file.
        TODO: prefix/suffix __ to this method-name.
        """
        # apigateway.LambdaIntegrationOptions()
        if override_content_type_to_BINARY:
            integration_responses = [
                apigateway.IntegrationResponse(
                    status_code="200",
                    content_handling=apigateway.ContentHandling.CONVERT_TO_BINARY,
                    selection_pattern=r".*\(statusCode: 200\).*",
                    ### FYI: ALL NCCR-𝜆s have a "wrapper" that returns "statusCode" -- REF: backend/runtime/src/nccr/exceptionhelper/exception_handler.py
                    ### When Lambda-timesout, APIGW will generate JSON that has the exact case-sensitive "statusCode" of 504.
                    ### REF: https://docs.aws.amazon.com/apigateway/latest/developerguide/handle-errors-in-lambda-integration.html
                    # response_parameters={"method.response.header.Content-Type": f"'{return_mime_type}'"}
                ),
                apigateway.IntegrationResponse(
                    status_code="404",
                    selection_pattern=r".*\(statusCode: \d{3}\).*",
                    content_handling=apigateway.ContentHandling.CONVERT_TO_TEXT,
                ),
            ]
        else:
            integration_responses = None

        lambda_int = apigateway.LambdaIntegration(
            allow_test_invoke=True,
            handler=handler,
            request_templates={"application/json": '{ "statusCode": "200" }'},
            ### Following line is ONLY for Lambdas that return BINARY response (example: PDFs, images, ..)
            integration_responses=integration_responses,
        )
        if auth is None:
            resource_method: apigateway.Method = resource.add_method(method, lambda_int)
        else:
            resource_method: apigateway.Method = resource.add_method(
                method, lambda_int, authorization_type=apigateway.AuthorizationType.COGNITO, authorizer=auth
            )
        return resource_method

    @staticmethod
    def get_lambda_int_resource_method(handler, api, resource, method, auth: apigateway.CognitoUserPoolsAuthorizer):
        """
        ATTENTION: Not in use!!!
        ATTENTION: Not in use!!!
        ATTENTION: Not in use!!!
        2023-04-21 added this method
        """
        lambda_int = apigateway.LambdaIntegration(
            handler, request_templates={"application/json": '{ "statusCode": "200" }'}
        )
        resource_method: apigateway.Method = resource.add_method(
            method,
            lambda_int,
            authorizer=auth,
            # TODO: authorization_type=apigateway.AuthorizationType.COGNITO if auth is not None else apigateway.AuthorizationType.NONE,
            # TODO: authorization_scopes=['api/*'],
            # request_parameters={"method.request.header.authorization": True},
        )
        return resource_method


class CommonLambdaIAMRole(ConstructLayer):
    def __init__(
        self,
        scope: "Construct",
        id: str,
        ddb_user_tbl: Optional[dynamodb.ITable],
        nccr_s3: Optional[s3.IBucket],
        db_user_tbl_reqid_gsi: Optional[str],
        step_func: Optional[sfn.StateMachine],
    ) -> None:
        super().__init__(scope=scope, id_=id)

        self._ddb_user_tbl = ddb_user_tbl
        self._db_user_tbl_reqid_gsi = db_user_tbl_reqid_gsi
        self._nccr_s3 = nccr_s3
        self._step_func = step_func

        self._managed_policies = [
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLambdaInsightsExecutionRolePolicy"),
        ]

        self.common_role = iam.Role(
            scope=self,
            id="Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=self._managed_policies,
            description="Common IAM-Role for Project-Lambdas",
        )
        if self._ddb_user_tbl:
            self._ddb_user_tbl.grant_read_write_data(self.common_role)
        if self._nccr_s3:
            self._nccr_s3.grant_read_write(self.common_role)
        if self._step_func:
            self._step_func.grant_start_execution(self.common_role)

        # Attach an inline-policy to the above IAM-Role, for actions "xray:PutTraceSegments"
        self._xray_policy = iam.Policy(
            scope=self,
            id="XrayPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                    resources=["*"],
                )
            ],
        )
        self.common_role.attach_inline_policy(self._xray_policy)


# EoF
