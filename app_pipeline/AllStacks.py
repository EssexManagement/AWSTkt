from typing import Dict
import math
from constructs import Construct
from aws_cdk import (
    Stack,
    Fn,
    CfnOutput,
    CfnParameter,
    Duration,
    aws_logs,
    RemovalPolicy,
    aws_ec2,
    aws_rds,
    aws_iam,
    aws_s3,
    aws_secretsmanager,
    aws_lambda,
    aws_sns,
    aws_sqs,
    aws_cognito,
    aws_dynamodb,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import add_tags

from common.cdk.standard_lambda import StandardLambda
from common.cdk.standard_ddbtbl import standard_dynamodb_table
from common.cdk.retention_base import (
    DATA_CLASSIFICATION_TYPES,
    S3_LIFECYCLE_RULES,
)
from common.cdk.StandardBucket import (
    create_std_bucket,
    gen_bucket_lifecycle,
    add_lifecycle_rules_to_bucket,
)

from backend.common_aws_resources_stack import CommonAWSResourcesStack
from cognito.infrastructure import MyUserPool
from api import config
from backend.vpc_w_subnets import VpcWithSubnetsConstruct
from backend.database.vpc_rds.infrastructure import SqlDatabaseConstruct
from backend.database.rds_init.infrastructure import RdsInit
from backend.etl.infrastructure import DailyETL
from api.infrastructure import Api
from api.infrastructure_lambdas import LambdaOnlyConstructs

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

print( f"Est. of # of Lambdas in config.py = '{config.LambdaConfigs.num_of_lambdas()}' - a GLOBAL-CONSTANT within "+ __file__ )
CHUNK_SIZE = math.ceil( config.LambdaConfigs.num_of_lambdas() / constants.NUM_OF_CHUNKS )
print( f"CHUNK_SIZE = '{CHUNK_SIZE}' -- a GLOBAL-CONSTANT within "+ __file__ )

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

class StackReferences:
    def __init__(self):
        pass

stk_refs = StackReferences()


"""
    @param scope: standard CDK arg
    @param id_: standard CDK arg
    @param git_branch:
    @param aws_env: deployment-environment;  Example: various DEVELOPER-git-branches may all be deployed into SHARED `DEV` environment.
    @param env:  This is of type `aws_cdk.Environment` containing AWS_REGION, AWS_ACCOUNT_ID, etc..
    @param kwargs:
"""
class Gen_AllApplicationStacks(Construct):
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
        super().__init__(scope, id_)   ### This is --NOT-- as stack; So, Do NOT pass kwargs (into Constructs)!

        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        self.stack_prefix = stack_prefix
        cts_api_v2_unpublished_name = self.node.try_get_context("ctsapi-v2-prod-unpublished-name")
        bing_maps_key_unpublished_name = self.node.try_get_context( "bing-maps-key-unpublished-name" )

        ### ----------------------------------------------
        bundling_stks :list[str] = self.node.try_get_context("aws:cdk:bundling-stacks")
        bundlings_all_stks = bundling_stks.index("**") >= 0

        ### ----------------------------------------------
        id_ = stack_prefix+ "-AWSLandingZone"
        # if bundlings_all_stks or (bundling_stks.index(id_) >= 0):
        aws_landingzone = AWSLandingZoneStack(  ### Do nothing Stack-construct.  Acts as "scope" construct below.
            scope = self,
            id_ = id_,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            **kwargs
        )

        common_stk = CommonAWSResourcesStack(
            scope = None,
            simple_id = "CommonRsrcs",
            stk_prefix = stack_prefix,
            tier = tier,
            aws_env = aws_env,
            git_branch = git_branch,
            **kwargs
        )

        stateful = StatefulStack(  ### Do nothing Stack-construct.  Acts as "scope" construct below.
            scope = self,
            id_ = stack_prefix+ "-Stateful",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc = aws_landingzone.vpc,
            **kwargs
        )
        stk_refs.stateful_stk = stateful

        inside_vpc_lambda_factory = StandardLambda(
            vpc       = aws_landingzone.vpc,
            sg_lambda = stateful.rds_security_group,
            tier = tier,
            min_memory = config.MIN_MEMORY,
            default_timeout = config.DEFAULT_API_TIMEOUT,
        )
        no_vpc_lambda_factory = StandardLambda(
            vpc = None,
            sg_lambda = None,
            tier = tier,
            min_memory = config.MIN_MEMORY,
            default_timeout = config.DEFAULT_API_TIMEOUT,
        )

        cognito = CognitoStack( scope=self,
            id_ = stack_prefix + "-Cognito",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            **kwargs
        )
        print(f"cognito--${cognito.user_pool}")
        stk_refs.cognito_stk = cognito

        buckets_stk = BucketsStack( scope=self,
            id_ = stack_prefix + "-Buckets",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            **kwargs,
        )
        stk_refs.buckets_stk = buckets_stk

        sqs_stack = SqsStack(scope=self,
            id_ = stack_prefix + "-SqsStack",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            **kwargs,
        )
        trial_criteria_queue = sqs_stack.trial_criteria_queue
        make_dataset_queue = sqs_stack.make_dataset_queue
        create_report_queue = sqs_stack.create_report_queue
        stk_refs.sqs_stack = sqs_stack

        sns_stack = SnsStack(scope=self,
            id_ = stack_prefix + "-SNSStack",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            **kwargs,
        )

        ddbtbl_stk = DynamoDBStack(scope=self,
            id_ = stack_prefix + "-DynamoDB",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            **kwargs,
        )
        stk_refs.ddbtbl_stk = ddbtbl_stk

        ### ----------------------------------------------------------------
        lambda_configs = config.LambdaConfigs(
            tier = tier,
            scope = self,
            dbuser_sm_name = stateful.rds_con.emfact_user_hush.secret_name,
            dbuser_sm_arn = stateful.rds_con.emfact_user_hush.secret_full_arn,
            dbadmin_sm_arn = stateful.rds_con.db.secret.secret_full_arn,
            user_data_table_name = ddbtbl_stk.user_data_table.table_name,
            process_status_table_name = ddbtbl_stk.process_status_table.table_name,
            cts_api_v2_unpublished_name = cts_api_v2_unpublished_name,
            bing_maps_key_unpublished_name = bing_maps_key_unpublished_name,
            SEARCH_RESULTS_BUCKET_NAME = buckets_stk.search_results_bucket.bucket_name,
            UI_UPLOADS_BUCKET_NAME = buckets_stk.search_results_bucket.bucket_name,
            DATASET_BUCKET_NAME=buckets_stk.etl_data_sets_bucket.bucket_name,
            TRIAL_CRITERIA_QUEUE_URL = trial_criteria_queue.queue_url,
            MAKE_DATASET_QUEUE_URL = make_dataset_queue.queue_url,
            ETL_QUEUE_URL = sqs_stack.etl_queue.queue_url,
            CREATE_REPORT_QUEUE_URL=create_report_queue.queue_url,
            ETL_TOPIC_ARN = sns_stack.etl_topic.topic_arn,
            CT_API_URL = self.node.try_get_context("ctsapi-v1-prod-url"),
            CT_API_URL_V2 = self.node.try_get_context("ctsapi-v2-prod-url"),
            CT_API_VERSION = self.node.try_get_context("ctsapi-version"),
            curated_trigger_folder = "curated_trigger_folder",
        )

        stk_refs.list_of_lambda_stks = []
        beg :int = 0
        for chunk_num in range(0,constants.NUM_OF_CHUNKS):
            enddd :int = beg + CHUNK_SIZE
            print( f"New Stack of Lambdas for Chunk # {chunk_num}: from {beg} to {enddd} --- inside BackendStage() within "+ __file__ )
            a_stk = StatelessStackLambdas( scope=self,
                id_ = f"{stack_prefix}-Lambdas-{chunk_num}",
                tier=tier,
                aws_env=aws_env,
                git_branch=git_branch,
                # chunk_num = chunk_num,
                beg = beg,
                enddd = enddd,
                inside_vpc_lambda_factory=inside_vpc_lambda_factory,
                common_stk = common_stk,
                user_pool = cognito.user_pool,
                emfact_user_hush = stateful.rds_con.emfact_user_hush,
                rds_con = stateful.rds_con,
                vpc=aws_landingzone.vpc,
                db=stateful.rds,
                rds_security_group=stateful.rds_security_group,
                user_data_table=ddbtbl_stk.user_data_table,
                search_results_bucket=buckets_stk.search_results_bucket,
                dataset_bucket=buckets_stk.etl_data_sets_bucket,
                trial_criteria_queue=trial_criteria_queue,
                make_dataset_queue=make_dataset_queue,
                etl_queue=sqs_stack.etl_queue,
                create_report_queue=create_report_queue,
                lambda_configs = lambda_configs,
                # api_construct = stateless_apigw.api,
                # restapi     = stateless_apigw.api.api,
                # api_v1_resource = stateless_apigw.api.api_v1_resource,
                # search_results_bucket = stateless_apigw.search_results_bucket,
                # user_pool = imported_stack.user_pool,
                **kwargs,
            )
            beg = enddd
            stk_refs.list_of_lambda_stks.append( a_stk )

        # self._user_pool_id = cognito._user_pool_id
        # self._user_pool_client_id = cognito._user_pool_client_id
        # self._user_pool_client_secret = cognito._user_pool_client_secret


        ### ------------
        # ### report lambda -- should be PART of the LAST of the Lambda-stacks above !!
        # last_lambda_stk = stk_refs.list_of_lambda_stks[-1]
        # cts_api_v2_unpublished = aws_secretsmanager.Secret.from_secret_name_v2(
        #     last_lambda_stk, "cts_api_v2_unpublished_name", cts_api_v2_unpublished_name
        # )
        # dckr_con = DockerLambdaConstruct(
        #     scope = last_lambda_stk,    ### Reference to the last stack above.
        #     tier = tier,
        #     aws_env = aws_env,
        #     git_branch = git_branch,
        #     inside_vpc_lambda_factory = inside_vpc_lambda_factory,
        #     cts_api_v2_unpublished = cts_api_v2_unpublished,
        #     emfact_user_hush = stateful.rds_con.emfact_user_hush,
        # )
        # ### Note: Above, we ONLY JUST created the Lambda.  Now .. we will associate the Lambda with the APIGW.
        # addl_entry = { 'http_method': 'POST',    "handler": 'report',     "apigw-path": 'report' }
        # lambda_configs.append_addl_api( addl_entry )


        stateless_apigw = StatelessStackAPIGW( scope=self,
            id_ = stack_prefix + "-StatelessAPIGW",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc=aws_landingzone.vpc,
            db=stateful.rds,
            rds_security_group=stateful.rds_security_group,
            emfact_user_hush = stateful.rds_con.emfact_user_hush,
            user_pool=cognito.user_pool,
            lambda_configs = lambda_configs,
            inside_vpc_lambda_factory = inside_vpc_lambda_factory,
            **kwargs,
        )
        for a_stk in stk_refs.list_of_lambda_stks:
            stateless_apigw.add_dependency( a_stk )  ### Wait for Lambda-stacks to finish deploying before deploying APIGW-stack.

        # ### Integrate above "rpt_lmbda" with APIGW
        # get_lambda_int_resource_method(
        #     handler = dckr_con.rpt_constr.lambda_function,
        #     api_resource = stateless_apigw.apigw.api_v1_resource,
        #     resource_name="report",
        #     method="POST",
        #     authorizer = self.my_authorizer,
        #     # authorizer_id = self.my_authorizer.authorizer_id if self.my_authorizer else None,
        # )

        stateless_etl = StatelessStackETL( scope=self,
            id_ = stack_prefix + "-StatelessETL",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            db = stateful.rds,
            dynamo_stack = ddbtbl_stk,
            inside_vpc_lambda_factory = inside_vpc_lambda_factory,
            lambda_construct_map = lambda_configs.lambda_construct_map(),
            common_stk = common_stk,
            emfact_user_hush = stateful.rds_con.emfact_user_hush,
            buckets_stk = buckets_stk,
            trial_criteria_queue = trial_criteria_queue,
            make_dataset_queue = make_dataset_queue,
            etl_queue = sqs_stack.etl_queue,
            etl_topic = sns_stack.etl_topic,
            **kwargs,
        )

        stateless_apigw.add_dependency( stateless_etl )  ### Wait for Lambda-stacks to finish deploying before deploying APIGW-stack.

        ### TODO -- create a new stack called "misc" ??? and move this construct into that.  -NOT- in `ETL` stack.
        rds_initializer = RdsInit(
            scope = stateless_etl, ### !!! ATTENTION !!! scope can -NOT- be 'self' and can -NOT- be 'scope'
            id_="RdsInit",
            fnMemorySize = 256,
            fnLogRetention = aws_logs.RetentionDays.ONE_DAY,
            fnTimeout = Duration.minutes(10),
            emfact_user_hush = stateful.rds_con.emfact_user_hush,
            db = stateful.rds,
            vpc = aws_landingzone.vpc,
            rdsSG = stateful.rds_security_group,
            inside_vpc_lambda_factory = inside_vpc_lambda_factory ,
            common_stk = common_stk,
        )

        rds_initializer.customResource.node.add_dependency(stateful.rds)



### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class AWSLandingZoneStack(Stack):
    """ Has 3 properties: vpc_con, vpc and rds_security_group
    """

    def __init__(self,
        scope: Construct,
        id_: str,
        tier: str,
        aws_env: str,
        git_branch: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id_, stack_name=id_, **kwargs)

        # define stack-cloudformation-param named "cdkAppName"
        cdk_app_name_cfnp = CfnParameter(self, "cdkAppName",
            type="String",
            description="The name of the CDK app",
            default=constants.CDK_APP_NAME,
        )

        self.vpc_con = VpcWithSubnetsConstruct( scope = self,
            construct_id = "vpc-only",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            cdk_app_name = cdk_app_name_cfnp,
        )

        self.vpc = self.vpc_con.vpc

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class StatefulStack(Stack):
    """ Just the RDS Aurora and Stack-Outputs.
        Has 2 RDS-related properties: self.rds_con and self.rds;
            The former is a CDK-construct SqlDatabaseConstruct, while the latter is aws_cdk.aws_rds.DatabaseCluster instance.
        Also, has a Security-Group property named `rds_security_group`
    """

    @property
    def rds(self) -> aws_rds.DatabaseCluster:
        return self._rds

    @property
    def rds_security_group(self) -> aws_ec2.ISecurityGroup:
        return self._rds_security_group

    def __init__(self,
        scope: Construct,
        id_: str,
        tier: str,
        aws_env: str,
        git_branch: str,
        vpc :aws_ec2.Vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, id_, stack_name=id_, **kwargs)

        self.rds_con = SqlDatabaseConstruct(scope = self,
            id_ = "AuroraV2PG",
            tier = tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc = vpc,
        )
        self._rds = self.rds_con.db
        self._rds_security_group  = self.rds_con.rds_security_group

        CfnOutput(self, id=f"vpc-{tier}", export_name=f"vpc-{tier}", value=vpc.vpc_id)

        CfnOutput( self,
            id="emfact-user-secret",
            export_name=f"{self.stack_name}-emfact-user-secret-name",
            value=self.rds_con.emfact_user_hush.secret_name,
        )

        CfnOutput( self,
            id="rds_security_group",
            export_name=f"{self.stack_name}-rds-security-group-id",
            value=self.rds_security_group.security_group_id,
        )

        CfnOutput( self,
            id="db",
            export_name=f"{self.stack_name}-db-cluster-id",
            value=self.rds.cluster_identifier,
        )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class CognitoStack(Stack):
    def __init__(self, scope: Construct, id_: str,
            tier :str,
            git_branch :str,
            aws_env :str,
            **kwargs
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        _user_pool = MyUserPool(self, "user pool",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
        )
        self.user_pool = _user_pool.user_pool
        self.api_client = _user_pool.api_client

        self._user_pool_id = CfnOutput(
            self,
            id="UserPoolID",
            export_name=f"{self.stack_name}-UserPoolID",
            value=self.user_pool.user_pool_id,
        )

        self._domain_name = CfnOutput(
            self,
            id="UserPoolDomain",
            export_name=f"{self.stack_name}-UserPoolDomain",
            value=_user_pool.user_pool_domain.domain_name,
        )

        self._user_pool_client_id = CfnOutput(
            self,
            id="UIClientID",
            export_name=f"{self.stack_name}-UIClientID",
            value=_user_pool.ui_client.user_pool_client_id,
        )

        # self._user_pool_client_secret = CfnOutput(
        #     self,
        #     id="APIClientID",
        #     export_name=f"{self.stack_name}-APIClientID",
        #     value=_user_pool.api_client.user_pool_client_secret,
        # )
        print('&'* 200)
        print(dict(tier=tier, aws_env=aws_env, git_branch=git_branch))
        print('&' * 200)
        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)

class BucketsStack(Stack):
    def __init__(self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)


        data_classification_type: DATA_CLASSIFICATION_TYPES = DATA_CLASSIFICATION_TYPES.INTERNAL_DATA
        all_lifecycle_rules: dict[str, aws_s3.LifecycleRule] = gen_bucket_lifecycle(
            tier=tier,
            data_classification_type=data_classification_type, enabled=True
        )

        self.etl_data_sets_bucket: aws_s3.Bucket = create_std_bucket(
            scope = self,
            id = 'etl_data_sets',
            bucket_name = aws_names.gen_bucket_name( tier=tier, simple_bucket_name="etl-data-sets" ).lower(),
            tier = tier,
            data_classification_type = data_classification_type,
            enable_S3PreSignedURLs = True,
            lifecycle_rules=all_lifecycle_rules[S3_LIFECYCLE_RULES.LOW_COST.name],
            # cors_rule_list=[cors_rule],
        )

        data_classification_type: DATA_CLASSIFICATION_TYPES = DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY
        all_lifecycle_rules: dict[str, aws_s3.LifecycleRule] = gen_bucket_lifecycle(
            tier=tier,
            data_classification_type=data_classification_type, enabled=True
        )

        self.search_results_bucket: aws_s3.Bucket = create_std_bucket(
            scope = self,
            id = 'buckets',
            bucket_name = aws_names.gen_bucket_name( tier=tier, simple_bucket_name="session-results" ).lower(),
            tier = tier,
            data_classification_type = data_classification_type,
            enable_S3PreSignedURLs = True,
            lifecycle_rules=all_lifecycle_rules[S3_LIFECYCLE_RULES.SCRATCH.name],
            # cors_rule_list=[cors_rule],
        )
        # ### Support S3PreSignedURL for this bucket.
        # self.search_results_bucket.add_to_resource_policy(
        #     aws_iam.PolicyStatement(
        #         effect=aws_iam.Effect.ALLOW,
        #         principals=[aws_iam.AnyPrincipal()],
        #         actions = ["s3:GetObject"], ### ["s3:GetObject", "s3:PutObject"],
        #         resources=[
        #             f"{self.search_results_bucket.bucket_arn}/*",
        #             # f"{self.search_results_bucket.bucket_arn}", ### Public users should -NOT- be able to list objects
        #         ],
        #         conditions = {
        #             "StringEquals": {
        #                 "aws:ResourceAccount": self.account,
        #             },
        #             "Bool": {
        #                 "aws:SecureTransport": "true"
        #             }
        #         }
        #     )
        # )
        # ### Then add the DENY policy for all other S3 actions
        # self.search_results_bucket.add_to_resource_policy(
        #     aws_iam.PolicyStatement(
        #         effect = aws_iam.Effect.DENY, ### <--------- DENY !!!
        #         principals = [aws_iam.AnyPrincipal()],
        #         not_actions = ["s3:GetObject"],  ### Deny --Everything-EXCEPT-- s3:GetObject action
        #         resources = [
        #             f"{self.search_results_bucket.bucket_arn}/*",
        #             f"{self.search_results_bucket.bucket_arn}"
        #         ],
        #         conditions = {
        #             "StringNotLike": {
        #                 "aws:userId": [
        #                     "*:*",  # IAM users/roles
        #                     "AROA*",  # IAM roles
        #                     "AIDA*",  # IAM users
        #                     "AROD*"   # Root users
        #                 ]
        #             }
        #         }
        #     )
        # )




class DynamoDBStack(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)
        stk = Stack.of(self)

        self.process_status_table = standard_dynamodb_table(
            scope=self,
            id="prcoess-status",
            tier = tier,
            data_classification_type = DATA_CLASSIFICATION_TYPES.USER_REQUESTS,
            ddbtbl_name = f"{stk.stack_name}-fact_process_status",
            # ddbtbl_name=aws_names.gen_dynamo_table_name(tier, 'fact_process_status'),
            partition_key=aws_dynamodb.Attribute(name="execution_id", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="step", type=aws_dynamodb.AttributeType.STRING),
            global_secondary_indexes=[
                aws_dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="gsi",
                    partition_key=aws_dynamodb.Attribute(name="aws_request_id", type=aws_dynamodb.AttributeType.STRING),
                    sort_key=aws_dynamodb.Attribute(name="step", type=aws_dynamodb.AttributeType.STRING))
            ],
            local_secondary_indexes=[aws_dynamodb.LocalSecondaryIndexProps(
                index_name="lsi",
                sort_key=aws_dynamodb.Attribute(name="aws_request_id", type=aws_dynamodb.AttributeType.STRING))
            ],
        )
        self.user_data_table = standard_dynamodb_table(
            scope=self,
            id="user_data",
            tier=tier,
            data_classification_type=DATA_CLASSIFICATION_TYPES.USER_REQUESTS,
            ddbtbl_name = f"{stk.stack_name}-user_data",
            # ddbtbl_name=aws_names.gen_dynamo_table_name(tier, 'user_data'),
            partition_key=aws_dynamodb.Attribute(name="user_id", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="record_type", type=aws_dynamodb.AttributeType.STRING),
        )

class SqsStack(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        queue = aws_sqs.Queue(scope=self, id='fact_trial_criteria_queue',
                          visibility_timeout=Duration.seconds(900))
            ### !! ATTENTION !! CDK-deploy ERROR = Queue visibility timeout: 180 seconds is less than Function timeout: 900 seconds
        self.trial_criteria_queue = queue

        queue = aws_sqs.Queue(scope=self, id='fact_make_dataset_queue',
                              visibility_timeout=Duration.seconds(900))
        self.make_dataset_queue = queue

        queue = aws_sqs.Queue(scope=self, id='create_report_queue',
                              visibility_timeout=Duration.seconds(60))
        self.create_report_queue = queue

        queue = aws_sqs.Queue(scope=self, id='fact_etl_queue',
                              visibility_timeout=Duration.seconds(900))
        self.etl_queue = queue
        # tier = self.node.try_get


class SnsStack(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        id = 'etl_topic'
        full_name = f"{self.stack_name}-{id_}"
        # full_name = f"{constants.CDK_APP_NAME}-{tier}-{id}"
        # full_name = aws_names.gen_awsresource_name( tier, constants.CDK_COMPONENT_NAME, id_ )
        self.etl_topic = aws_sns.Topic(
            scope=self,
            id = id,
            display_name = full_name,
            topic_name = full_name,
            enforce_ssl=True,
        )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class StatelessStackLambdas(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        lambda_configs: config.LambdaConfigs,
        beg: int,
        enddd: int,
        # chunk_num: int,
        inside_vpc_lambda_factory: StandardLambda,
        common_stk :Stack,
        user_pool: aws_cognito.UserPool,
        emfact_user_hush: aws_rds.DatabaseSecret,
        rds_con :SqlDatabaseConstruct,
        vpc: aws_ec2.Vpc,
        db: aws_rds.ServerlessCluster,
        rds_security_group: aws_ec2.SecurityGroup,
        user_data_table,
        search_results_bucket: aws_s3.IBucket,
        dataset_bucket: aws_s3.IBucket,
        trial_criteria_queue: aws_sqs.IQueue,
        make_dataset_queue: aws_sqs.IQueue,
        etl_queue: aws_sqs.IQueue,
        create_report_queue: aws_sqs.IQueue,
        # api_construct: Api,
        # rest api: aws_apigateway.RestApi,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        # beg = int( chunk_num*CHUNK_SIZE )
        # enddd = int( (chunk_num+1)*CHUNK_SIZE )
        print( f"Chunk is from '{beg}' to '{enddd}' --- in StatelessStackLambdas() within "+ __file__ )
        # lambda_configs_chunk = config.list[ beg : enddd ]
        lambda_configs_chunk :config.LambdaConfigs = lambda_configs.deep_clone()
        lambda_configs_chunk.keep_only_items_between( beg, enddd )
        print( f"CHUNK is of len = '{len(lambda_configs_chunk.list)}' in StatelessStackLambdas() within "+ __file__ )
        if ( len(lambda_configs_chunk.list) == 0 ):
            return

        self.lambdas = LambdaOnlyConstructs( scope=self,
            id_=f"{beg}-{enddd}",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc=vpc,
            rdsSG=rds_security_group,
            lambda_configs = lambda_configs_chunk,
            common_stk = common_stk,
            inside_vpc_lambda_factory=inside_vpc_lambda_factory,
            # user_pool=user_pool,
            emfact_user_unpublished=emfact_user_hush,
            rds_con = rds_con,
            user_data_table=user_data_table,
            search_results_bucket=search_results_bucket,
            dataset_bucket=dataset_bucket,
            trial_criteria_queue=trial_criteria_queue,
            make_dataset_queue=make_dataset_queue,
            create_report_queue=create_report_queue,
            etl_queue=etl_queue,
            # db=db,
            # rest_api_id = api_construct.api.rest_api_id,
            # rest_api_root_rsrc = api_construct.api.rest_api_root_resource_id,
            # rest_api_common_rsrc_path = api_construct.api_v1_resource.path,
            # rest_api_lowest_resource_id
            # authorizer_id = api_construct.my_authorizer.authorizer_id,
        )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)


class StatelessStackETL(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        db: aws_rds.ServerlessCluster,
        dynamo_stack ,
        inside_vpc_lambda_factory :StandardLambda,
        lambda_construct_map :Dict[str, aws_lambda.Function],
        common_stk :Stack,
        emfact_user_hush: aws_rds.DatabaseSecret,
        buckets_stk,
        trial_criteria_queue,
        make_dataset_queue,
        etl_queue,
        etl_topic,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        DailyETL( self, id_="ETL",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            db=db,
            dynamo_stack = dynamo_stack,
            buckets_stk=buckets_stk,
            lambda_construct_map = lambda_construct_map,
            common_stk=common_stk,
            emfact_user_unpublished=emfact_user_hush,
            trial_criteria_queue=trial_criteria_queue,
            make_dataset_queue=make_dataset_queue,
            etl_queue=etl_queue,
            etl_topic=etl_topic,
        )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class StatelessStackAPIGW(Stack):
    def __init__( self, scope: Construct, id_: str,
        tier :str,
        git_branch :str,
        aws_env :str,
        vpc: aws_ec2.Vpc,
        db: aws_rds.ServerlessCluster,
        rds_security_group: aws_ec2.SecurityGroup,
        emfact_user_hush: aws_rds.DatabaseSecret,
        user_pool: aws_cognito.UserPool,
        lambda_configs: config.LambdaConfigs,
        inside_vpc_lambda_factory :StandardLambda,
        **kwargs,
    ) -> None:
        super().__init__(scope=scope, id=id_, stack_name=id_, **kwargs)

        self.apigw = Api( self, "api",
            tier=tier,
            aws_env=aws_env,
            git_branch=git_branch,
            vpc=vpc,
            emfact_user_unpublished=emfact_user_hush,
            db=db,
            rdsSG=rds_security_group,
            user_pool=user_pool,
            lambda_configs = lambda_configs,
            inside_vpc_lambda_factory = inside_vpc_lambda_factory,
            **kwargs,
        )
        CfnOutput( self, id="APIEndpointURL",
            export_name=f"{self.stack_name}-APIEndpointURL",
            value = self.apigw.api.url,
        )

        add_tags(self, tier=tier, aws_env=aws_env, git_branch=git_branch)
