from os import path
from constructs import Construct
from typing import Optional, Dict, List
import re

from aws_cdk import Stack, aws_logs, Duration, RemovalPolicy, aws_sqs, Size, aws_lambda_event_sources
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda,
    aws_secretsmanager,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam,
    aws_dynamodb,
)

import constants
from cdk_utils.CloudFormation_util import get_cpu_arch_enum
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from common.cdk.mappings import Mappings
from common.cdk.standard_lambda import StandardLambda

from api.config import LambdaConfigs, DEFAULT_LAMBDA_HANDLER
from backend.database.vpc_rds.infrastructure import SqlDatabaseConstruct
# from api.infrastructure import get_lambda_int_resource_method

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class LambdaOnlyConstructs(Construct):

    def __init__( self, scope: Construct, id_: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        vpc: ec2.IVpc,
        rdsSG: ec2.SecurityGroup,
        lambda_configs: LambdaConfigs,
        common_stk :Stack,
        inside_vpc_lambda_factory :StandardLambda,
        emfact_user_unpublished: rds.DatabaseSecret,
        rds_con :SqlDatabaseConstruct,
        search_results_bucket: s3.IBucket,
        dataset_bucket: s3.IBucket,
        trial_criteria_queue: aws_sqs.IQueue,
        make_dataset_queue: aws_sqs.IQueue,
        etl_queue: aws_sqs.IQueue,
        create_report_queue: aws_sqs.IQueue,
        user_data_table :aws_dynamodb.Table,
        # rest_api_id: str,
        # rest_api_root_rsrc :str,
        # rest_api_common_rsrc_path :str,
        # rest_api_lowest_resource_id: str,
        # authorizer_id: str,
        # user_pool: cognito.UserPool,
    ):
        super().__init__(scope, id_)

        stk = Stack.of(self)
        this_dir = path.dirname(__file__)

        # tier = self.node.try_get_context("tier")
        # aws_env = tier if tier in constants.STD_TIERS else constants.DEV_TIER ### ["dev", "int", "uat", "prod"]:
        # git_branch = constants.get_git_branch( tier=tier )
        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        cts_api_v2_unpublished_name = self.node.try_get_context("ctsapi-v2-prod-unpublished-name")
        self.cts_api_v2_unpublished = aws_secretsmanager.Secret.from_secret_name_v2(
            self, "cts_api_v2_unpublished_name", cts_api_v2_unpublished_name
        )

        bing_maps_key_unpublished_name = self.node.try_get_context( "bing-maps-key-unpublished-name" )
        self.bing_maps_key_unpublished = aws_secretsmanager.Secret.from_secret_name_v2(
            self, "bing-maps-key-unpublished-name", bing_maps_key_unpublished_name
        )
        self.trial_criteria_queue = trial_criteria_queue
        self.make_dataset_queue = make_dataset_queue
        self.etl_queue = etl_queue
        self.create_report_queue = create_report_queue
        datadog_destination = Mappings(self).get_dd_subscription_dest( tier=tier, aws_env=aws_env )
        if datadog_destination is None:
            print( f"WARNING !! Datadog's Kinesis-DataStream destination missing for tier='{aws_env}' !!  -- in  DailyEtl(): within ", __file__ )

        ### --------------------------------------------------------
        curated_trigger_folder = 'curated_trigger_folder'

            # scope = self,
            # dbuser_sm_name = emfact_user_unpublished.secret_name,
            # cts_api_v2_unpublished_name = cts_api_v2_unpublished_name,
            # bing_maps_key_unpublished_name=bing_maps_key_unpublished_name,
            # dbuser_sm_name = emfact_user_unpublished.secret_name,
            # SEARCH_RESULTS_BUCKET_NAME = search_results_bucket.bucket_name,
            # TRIAL_CRITERIA_QUEUE_URL = trial_criteria_queue.queue_url,
            # curated_trigger_folder = curated_trigger_folder,

        #     "environment": {
        #         # "AWS_LAMBDA_EXEC_WRAPPER": "/opt/otel-instrument",
        #         "UNPUBLISHED": emfact_user_unpublished.secret_name,
        #         "CT_API_URL": self.node.try_get_context("ctsapi-v1-prod-url"),
        #         "CT_API_URL_V2": self.node.try_get_context("ctsapi-v2-prod-url"),
        #         "CT_API_UNPUBLISHED": self.cts_api_v2_unpublished.secret_name,
        #         "CT_API_VERSION": self.node.try_get_context("ctsapi-version"),
        #         "SEARCH_RESULTS_BUCKET_NAME": search_results_bucket.bucket_name,
        #         "BING_MAPS_UNPUBLISHED": self.bing_maps_key_unpublished.secret_name,
        #         # "BING_MAPS_API_KEY": "removed so that no secrets are hardcoded in the code",
        #         "USE_CONNECTION_POOL": "False",
        #         "CONNECTION_POOL_COUNT": "4",
        #         'UI_UPLOADS_BUCKET': search_results_bucket.bucket_name,
        #         "DATASET_BUCKET": search_results_bucket.bucket_name,
        #         "S3_EVAL_FOLDER": "eval",
        #         'S3_CURATED_FOLDER': 'curated',
        #         'S3_COMPARISON_OUTPUT_FOLDER': 'emfact/comparison',
        #         'TRIAL_CRITERIA_QUEUE_URL': self.trial_criteria_queue.queue_url,
        #         'MAKE_DATASET_QUEUE_URL': self.make_dataset_queue.queue_url,
        #         "ETL_QUEUE_URL": self.etl_queue.queue_url,
        #         'DATASET_S3_FOLDER': 'emfact/datasets'

        ### -------------- create each lambda in config.py -----------------
        a_lambda :dict

        for a_lambda in lambda_configs.list:

            handler = LambdaConfigs.get_handler(a_lambda)

            index = LambdaConfigs.get_lambda_index( a_lambda )
            handler = LambdaConfigs.get_handler(a_lambda)
            entry = LambdaConfigs.get_lambda_entry( a_lambda )
            # TODO: should be fixed to allow lambdas which happen to use api gw to have function name lambda_handler. as is anything using name lambda_handler is assumed to not use gw
            if handler == DEFAULT_LAMBDA_HANDLER:
                ### This is for ETL-Lambdas that can NOT be accessed via APIGW.
                h = re.sub(r"\./", "_", index.replace(".py", ""))
                function_name= aws_names.gen_lambda_name( tier=tier, simple_lambda_name = h )
            else:
                function_name= aws_names.gen_lambda_name( tier=tier, simple_lambda_name=handler )
            http_method = LambdaConfigs.get_http_method(a_lambda)
            print(f"{handler}:\t{http_method}\t-\t{index}\t-\t{handler}")
            print(f"lambda_name = '{function_name}'")

            memory_size = LambdaConfigs.get_memory_size(a_lambda)
            ephemeral_storage_size = LambdaConfigs.get_ephemeral_storage_size(a_lambda)
            cpu_arch_str = LambdaConfigs.get_cpu_arch(a_lambda)
            extra_env_vars = LambdaConfigs.get_extra_env_vars(a_lambda)

            lambda_rolename: Optional[str] = LambdaConfigs.get_lambda_rolename(a_lambda)
            lambda_layers_names: Optional[list] = LambdaConfigs.get_lambda_layers_names(a_lambda)
            # override_content_type_to_BINARY: bool = LambdaConfigs.get_mime-response', None) != None

            if lambda_rolename:
                if not self.__role_cache:
                    self.__role_cache: Dict[str, aws_iam.Role] = {}
                lambda_role = self.__role_cache.get(lambda_rolename, None)
                if not lambda_role:
                    raise BaseException(
                        f"!! UN-DEFINED IAM-role '{lambda_rolename}' wtihin config.py for index ='{index}' handler = '{handler}'"
                    )
            else:
                lambda_role = None

            lambda_specific_layers = None
            if lambda_layers_names:
                lambda_specific_layers = []  ### initialized to None above. Hence.
                for nm in lambda_layers_names:
                    print( f"\tincluding the lambda_layer: '{nm}' for '{function_name}'" )
                    layerobj, _ = LambdaConfigs.lookup_lambda_layer(
                        layer_simple_name = nm,
                        stk_containing_layers = common_stk,
                        cpu_arch_str = cpu_arch_str,
                    )
                    lambda_specific_layers.append( layerobj )
                print(f"lambda_specific_layers are '{lambda_specific_layers}'")

            # env = {**lambda_config.get("environment")}
            # if handler_id in ['validate_curated_for_upload']:
            #     env = {'MAX_EXPRESSION_ERRORS': '0', **lambda_config.get("environment")}
            # if handler_id in ['validate_curated_for_upload']:
            #     env['MAX_EXPRESSION_ERRORS'] = '0'
            # if handler_id in ['process_s3_uploads', 'validate_curated_for_upload']:
            #     env['UI_UPLOADS_BUCKET'] = ui_uploads_bucket.bucket_name
            #     env['CURATED_TRIGGER_FOLDER'] = curated_trigger_folder

            lambda_specific_environment = {
                **lambda_configs.common_env,
                **extra_env_vars,
            }
            my_lambdafn = inside_vpc_lambda_factory.create_lambda(
                scope = self,
                lambda_name = function_name,
                index = index,
                handler = handler,
                # description = None,
                path_to_lambda_src_root = entry,
                environment = lambda_specific_environment,
                memory_size = memory_size,
                ephemeral_storage_size=Size.mebibytes(ephemeral_storage_size),
                timeout = lambda_configs.get_time_out(a_lambda),
                architecture = get_cpu_arch_enum(cpu_arch_str),
                layers=lambda_specific_layers,
            )

            if datadog_destination:
                logs.SubscriptionFilter(scope = self,
                                        id = "logs-subscfilter_" + function_name,
                                        ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_logs/SubscriptionFilter.html
                                        destination = datadog_destination,
                                        log_group = my_lambdafn.log_group,
                                        filter_pattern = logs.FilterPattern.all_events(),
                                        # filter_name= automatically genereated if NOT specified
                                    )

            ### --------------------------------------------------------
            if handler == 'process_s3_uploads':
                filter = s3.NotificationKeyFilter(prefix=f'{curated_trigger_folder}/*')
                ui_uploads_bucket :s3.IBucket = s3.Bucket.from_bucket_name( self, "lkpBkt", search_results_bucket.bucket_name )
                ### Note: This lookup exists to BREAK the cyclical-dependencies between this (Lambda) stack and the Bucket stack.
                ui_uploads_bucket.add_event_notification(
                    s3.EventType.OBJECT_CREATED,
                    s3n.LambdaDestination(my_lambdafn),
                    filter,
                )

            ### --------------------------------------------------------
            ### Grant the lambda - as appropriate - access to other AWS resources.
            if "CT_API_UNPUBLISHED" in lambda_specific_environment:
                self.cts_api_v2_unpublished.grant_read(my_lambdafn)

            # if handler_id in ("get_search_results", "post_search_results"):
            if handler in ('post_search_and_match'):
                create_report_queue.grant_purge(my_lambdafn)
                create_report_queue.grant_send_messages(my_lambdafn)
            if handler in ('create_report_queue_processor'):
                create_report_queue.grant_consume_messages(my_lambdafn)
                search_results_bucket.grant_read_write(my_lambdafn)
                dataset_bucket.grant_read_write(my_lambdafn)
            if handler in (
                    "create_report_queue_processor",
                    "get_search_session_data",
                    "get_subtype_for_maintype",
                    "get_biomarkers",
                    "get_column_info",
                    "get_criteria_type_records",
                    "get_search_results",
                    "get_starred_data",
                    "get_starred_trials",
                    "get_lead_orgs",
                    "get_nct_ids",
                    "get_org_families",
                    "get_possible_disease_trees",
                    "get_primary_cancer",
                    "get_prior_therapy",
                    "post_search_results",
                    "post_search_and_match",
                    "post_stage_for_types",
                    "post_starred_trials",
                    "post_trial_comparisons",
                    "put_presigned_url",
                    "get_sites_from_zip_distance",
                    "process_s3_uploads"
            ):
                search_results_bucket.grant_read_write(my_lambdafn)
                dataset_bucket.grant_read_write(my_lambdafn)
                user_data_table.grant_read_write_data(my_lambdafn)

            if ( "BING_MAPS_UNPUBLISHED" in lambda_specific_environment ):
                self.bing_maps_key_unpublished.grant_read(my_lambdafn)
            if ( "UNPUBLISHED" in lambda_specific_environment ):
                emfact_user_unpublished.grant_read(my_lambdafn)
            if ( "TRIAL_CRITERIA_QUEUE_URL" in lambda_specific_environment ):
                self.trial_criteria_queue.grant_purge(my_lambdafn)
                self.trial_criteria_queue.grant_send_messages(my_lambdafn)
            if ( "MAKE_DATASET_QUEUE_URL" in lambda_specific_environment ):
                self.make_dataset_queue.grant_purge(my_lambdafn)
                self.make_dataset_queue.grant_send_messages(my_lambdafn)
            if ( "CREATE_REPORT_QUEUE_URL" in lambda_specific_environment ):
                self.create_report_queue.grant_purge(my_lambdafn)
                self.create_report_queue.grant_send_messages(my_lambdafn)
            #
            if handler=='create_report_queue_processor':
                create_report_queue.grant_consume_messages(my_lambdafn)
                event_source = aws_lambda_event_sources.SqsEventSource(create_report_queue)
                my_lambdafn.add_event_source(event_source)
            #
            if ( "DBA" in lambda_specific_environment ):
                rds_con.db.secret.grant_read(my_lambdafn)
            if ( "DBU" in lambda_specific_environment ):
                rds_con.emfact_user_hush.grant_read(my_lambdafn)

            ### ---------------------------------
            LambdaConfigs.lambda_construct_list().append( my_lambdafn )
            if handler == DEFAULT_LAMBDA_HANDLER:
                LambdaConfigs.lambda_construct_map()[ function_name ] = my_lambdafn
            else:
                LambdaConfigs.lambda_construct_map()[ handler ] = my_lambdafn

### EoF
