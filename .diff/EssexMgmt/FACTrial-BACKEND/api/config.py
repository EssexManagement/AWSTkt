138,159c138,140
<                  tier: str,
<                  scope :Construct,
<                  dbuser_sm_name :str,
<                  dbuser_sm_arn :str,
<                  dbadmin_sm_arn :str,
<                  user_data_table_name: str,
<                  process_status_table_name :str,
<                  cts_api_v2_unpublished_name :str,
<                  bing_maps_key_unpublished_name :str,
<                  SEARCH_RESULTS_BUCKET_NAME :str,
<                  UI_UPLOADS_BUCKET_NAME :str,
<                  DATASET_BUCKET_NAME: str,
<                  TRIAL_CRITERIA_QUEUE_URL: str,
<                  MAKE_DATASET_QUEUE_URL :str,
<                  ETL_QUEUE_URL :str,
<                  CREATE_REPORT_QUEUE_URL: str,
<                  ETL_TOPIC_ARN :str,
<                  CT_API_URL :str,
<                  CT_API_URL_V2 :str,
<                  CT_API_VERSION :str,
<                  curated_trigger_folder :str,
<                  ):
---
>         scope :Construct,
>         dbuser_sm_name :str,
>     ):
163d143
<         self.tier = tier
166,183c146
<         self.dbuser_sm_arn = dbuser_sm_arn
<         self.dbadmin_sm_arn = dbadmin_sm_arn
<         self.user_data_table_name = user_data_table_name
<         self.process_status_table_name = process_status_table_name
<         self.cts_api_v2_unpublished_name = cts_api_v2_unpublished_name
<         self.bing_maps_key_unpublished_name = bing_maps_key_unpublished_name
<         self.SEARCH_RESULTS_BUCKET_NAME = SEARCH_RESULTS_BUCKET_NAME
<         self.UI_UPLOADS_BUCKET_NAME = UI_UPLOADS_BUCKET_NAME
<         self.TRIAL_CRITERIA_QUEUE_URL = TRIAL_CRITERIA_QUEUE_URL
<         self.MAKE_DATASET_QUEUE_URL = MAKE_DATASET_QUEUE_URL
<         self.ETL_QUEUE_URL = ETL_QUEUE_URL
<         self.CREATE_REPORT_QUEUE_URL = CREATE_REPORT_QUEUE_URL
<         self.ETL_TOPIC_ARN = ETL_TOPIC_ARN
<         self.CT_API_URL = CT_API_URL
<         self.CT_API_URL_V2 = CT_API_URL_V2
<         self.CT_API_VERSION = CT_API_VERSION
<         self.curated_trigger_folder = curated_trigger_folder
<         self.DATASET_BUCKET_NAME = DATASET_BUCKET_NAME # f'nih-nci-fact-backend-{tier.lower()}-etl-data-sets'
---
> 
185a149
> 
189,203d152
<             "BING_MAPS_UNPUBLISHED": bing_maps_key_unpublished_name,
<             "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<             "CT_API_URL"    : CT_API_URL,
<             "CT_API_URL_V2" : CT_API_URL_V2,
<             "CT_API_VERSION": CT_API_VERSION,
<             'UI_UPLOADS_BUCKET' : UI_UPLOADS_BUCKET_NAME,
<             "DATASET_BUCKET": self.DATASET_BUCKET_NAME,
<             # TODO remove
<             #"DATASET_BUCKET2":
<             'S3_CURATED_FOLDER' : 'curated',
<             'S3_COMPARISON_OUTPUT_FOLDER': 'emfact/comparison',
<             "S3_EVAL_FOLDER": "eval",
<             "TRIAL_CRITERIA_QUEUE_URL": TRIAL_CRITERIA_QUEUE_URL,
<             "MAKE_DATASET_QUEUE_URL": MAKE_DATASET_QUEUE_URL,
<             "ETL_QUEUE_URL": ETL_QUEUE_URL,
210c159
<             { 'http_method': 'GET',  "handler": 'get_filtering_criteria',        "apigw-path": 'filtering_criteria', },
---
>             { 'http_method': 'GET',  "handler": 'get_prior_therapy',             "apigw-path": 'prior_therapy', },
213,286d161
<                 'memory': 4096,
<                 'lambda-layers-names': [ 'numpy_etc' ],
<                 'extra-env-vars': dict(
<                     USER_DATA_TABLE_NAME=user_data_table_name,
<                     CREATE_REPORT_QUEUE_URL=CREATE_REPORT_QUEUE_URL,
<                 )
<             },
<             { 'http_method': 'GET',  "handler": 'get_prior_therapy',             "apigw-path": 'prior_therapy',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_primary_cancer',            "apigw-path": 'primary_cancer',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_subtype_for_maintype',      "apigw-path": 'subtype_for_maintype',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_stage_for_types',          "apigw-path": 'stage_for_types',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_biomarkers',                "apigw-path": 'biomarkers',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_column_info',               "apigw-path": 'column_info',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_ccodes_from_display_names',    "apigw-path": 'ccodes_from_display_names',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_studies_for_lat_lon_distance', "apigw-path": 'studies_for_lat_lon_distance',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_org_families',              "apigw-path": 'org_families',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_report_data',              "apigw-path": 'report_data',
<               'extra-env-vars': dict(
<                   USER_DATA_TABLE_NAME=user_data_table_name
<               )
<               },
<             { 'http_method': 'POST', "handler": 'post_studies_for_cancer_ctrs', "apigw-path": 'studies_for_cancer_centers',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_lead_orgs',                 "apigw-path": 'lead_orgs',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_studies_for_lead_orgs',    "apigw-path": 'studies_for_lead_orgs',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_disease_tree_data',        "apigw-path": 'disease_tree_data', },
<             { 'http_method': 'GET',  "handler": 'get_possible_disease_trees',    "apigw-path": 'possible_disease_trees',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_search_session_data',       "apigw-path": 'search_session_data', },
<             { 'http_method': 'GET',  "handler": 'get_starred_trials',            "apigw-path": 'get_starred_trials',
<               'lambda-layers-names': ['numpy_etc'],
<               'extra-env-vars': dict(
<                   USER_DATA_TABLE_NAME=user_data_table_name
<               )
<               },
<             { 'http_method': 'POST', "handler": 'post_starred_trials',           "apigw-path": 'post_starred_trials',
<               'lambda-layers-names': ['numpy_etc'],
<               'extra-env-vars': dict(
<                   USER_DATA_TABLE_NAME=user_data_table_name
<               )
<               },
<             { 'http_method': 'PUT',  "handler": 'put_rename_search_sessions',    "apigw-path": 'rename_search_sessions', },
<             { 'http_method': 'DELETE', "handler": 'delete_search_sessions',      "apigw-path": 'delete_search_sessions', },
<             { 'http_method': 'GET',  "handler": 'get_criteria_type_records',     "apigw-path": 'get_criteria_type_records',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET',  "handler": 'get_starred_data',              "apigw-path": 'get_starred_data',
<               'extra-env-vars': dict(
<                   USER_DATA_TABLE_NAME=user_data_table_name
<               )
<               },
<             { 'http_method': 'POST', "handler": 'post_create_criteria_type',     "apigw-path": 'post_create_criteria_type', },
<             { 'http_method': 'GET',  "handler": 'get_trial_criteria_count_by_id', "apigw-path": 'get_trial_criteria_count_by_id', },
<             { 'http_method': 'DELETE', "handler": 'delete_criteria_type',        "apigw-path": 'delete_criteria_type', },
<             { 'http_method': 'PUT',  "handler": 'put_update_criteria_type',      "apigw-path": 'put_update_criteria_type', },
<             { 'http_method': 'GET',  "handler": 'get_trial_criteria_by_type',    "apigw-path": 'get_trial_criteria_by_type', },
<             { 'http_method': 'GET',  "handler": 'get_trial_criteria_by_nct_id',  "apigw-path": 'get_trial_criteria_by_nct_id', },
<             { 'http_method': 'GET',  "handler": 'get_nct_ids',                   "apigw-path": 'get_nct_ids',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'POST', "handler": 'post_create_trial_criteria',    "apigw-path": 'post_create_trial_criteria', },
<             { 'http_method': 'PUT',  "handler": 'put_update_trial_criteria',     "apigw-path": 'put_update_trial_criteria', },
<             { 'http_method': 'DELETE', "handler": 'delete_trial_criteria',       "apigw-path": 'delete_trial_criteria', },
<             { 'http_method': 'GET',  "handler": 'get_trial_criteria_by_nct_type',"apigw-path": 'get_trial_criteria_by_nct_type', },
<             { 'http_method': 'POST', "handler": 'post_eval_expression',          "apigw-path": 'post_eval_expression',
288c163
<                 'lambda-layers-names': [ 'numpy_etc' ],
---
>                 'entry': PANDAS_LAMBDA_ENTRY, 'lambda-layers-names': [ 'psycopg3-pandas' ],
290,315d164
<             { 'http_method': 'GET', "handler": 'get_emfact_programs_for_user',   "apigw-path": 'get_emfact_programs_for_user',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET', "handler": 'get_lat_lon_from_address',       "apigw-path": 'get_lat_lon_from_address',
<               'lambda-layers-names': [ 'numpy_etc' ],},
<             { 'http_method': 'GET', "handler": 'get_search_results',             "apigw-path": 'get_search_results',
<               'lambda-layers-names': ['numpy_etc'],
<               'extra-env-vars': {
<                 'SEARCH_RESULTS_BUCKET_NAME': SEARCH_RESULTS_BUCKET_NAME,
<             }},
<             { 'http_method': 'POST', "handler": 'post_search_results',           "apigw-path": 'post_search_results', 'extra-env-vars':
<                 {
<                 'SEARCH_RESULTS_BUCKET_NAME':SEARCH_RESULTS_BUCKET_NAME,
<                 'USER_DATA_TABLE_NAME' : user_data_table_name,
<                 'MAKE_DATASET_QUEUE_URL': MAKE_DATASET_QUEUE_URL
< 
<             },
<               },
<             { 'http_method': 'POST', "handler": 'post_process_nct_data',         "apigw-path": 'post_process_nct_data', },
<             { 'http_method': 'GET',  "handler": 'get_sites_from_zip_distance',   "apigw-path": 'get_sites_from_zip_distance',
<                 'memory': 1024,
<                 'lambda-layers-names': [ 'numpy_etc' ],
<             },
<             { 'http_method': 'GET',  "handler": 'get_sites',                     "apigw-path": 'get_sites', },
<             { 'http_method': 'POST', "handler": 'post_lat_lon_from_addresses',   "apigw-path": 'post_lat_lon_from_addresses', },
<             { 'http_method': 'PUT',  "handler": 'put_presigned_url',             "apigw-path": 'put_presigned_url',
<               'lambda-layers-names': [ 'numpy_etc' ],},
317c166
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
---
>                 'entry': PANDAS_LAMBDA_ENTRY, 'lambda-layers-names': [ 'psycopg3-pandas' ],
320,322d168
<                     'UI_UPLOADS_BUCKET'      : UI_UPLOADS_BUCKET_NAME,
<                     'CURATED_TRIGGER_FOLDER' : curated_trigger_folder,
<                     'TRIAL_CRITERIA_QUEUE_URL': TRIAL_CRITERIA_QUEUE_URL,
324,344d169
<             { 'http_method': 'POST', "handler": 'post_wakeup_db',                "apigw-path": 'wakeup_db', },
<             { 'http_method': None,   "handler": 'process_s3_uploads',
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'extra-env-vars': {
<                     'TRIAL_CRITERIA_QUEUE_URL': TRIAL_CRITERIA_QUEUE_URL,
<                     'UI_UPLOADS_BUCKET'      : UI_UPLOADS_BUCKET_NAME,
<                     'CURATED_TRIGGER_FOLDER' : curated_trigger_folder,
<             }},
<             { 'http_method': 'POST', "handler": 'post_trial_comparisons',        "apigw-path": 'post_trial_comparisons', },
<             {'http_method': 'POST', "handler": 'create_report_queue_processor',
<              "apigw-path": 'create_report_queue_processor',
<              'handler_file': 'create_report_queue_processor.py',
<              'lambda-layers-names': ['psycopg3-pandas'],
<              'memory': 1024,
<              'ephemeral_storage_size': 2048,
<              'extra-env-vars': {
<                  "S3_COMPARISON_OUTPUT_FOLDER": "fact/comparison",
<                  "S3_EXCEL_REPORTS_FOLDER": "fact/excel_reports",
<                  "PROCESS_STATUS_TABLE": process_status_table_name,
<                  "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<              }},
352,359d176
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     # "DATASET_S3_FOLDER": 'emfact/datasets',
<                     "ETL_QUEUE_URL": ETL_QUEUE_URL,
<                     "ETL_TOPIC_ARN": ETL_TOPIC_ARN,
362,427d178
<                     "count_per_thread": "50",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'refresh_ncit.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 2048,
<                 'ephemeral_storage_size': 2048,
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     "NCIT_VERSION": "",
<                     "NUM_CONCEPTS_PER_EVS_CALL": "575",
<                     "EVS_THREAD_COUNT": "10",
<                     "USE_EVS_FOR_PREF_NAMES": "false",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'etl_start.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 10240,
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     # "DATASET_S3_FOLDER": 'emfact/datasets',
<                     "ETL_QUEUE_URL": ETL_QUEUE_URL,
<                     "ETL_TOPIC_ARN": ETL_TOPIC_ARN,
<                     'S3_EVAL_FOLDER': 'eval',
<                     "thread_count": "25",
<                     "count_per_thread": "50",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'etl_start_mp.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 10240,
<                 'ephemeral_storage_size': 4096,
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     # "DATASET_S3_FOLDER": 'emfact/datasets',
<                     "ETL_QUEUE_URL": ETL_QUEUE_URL,
<                     'S3_EVAL_FOLDER': 'eval',
<                     "thread_count": "25",
<                     "count_per_thread": "50",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<                     "DB_THREAD_COUNT": "1",
<                     "DB_COUNT_PER_THREAD": "200",
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'etl_sqs_processor.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 1024,
<                 'extra-env-vars': {
<                     "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     "DATASET_S3_BUCKET": "emfact/datasets",
<                     'S3_EVAL_FOLDER': 'eval',
<                     "thread_count": "10",
429,487d179
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'post_make_comparison_report.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 2048,
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     "NCIT_VERSION": "",
<                     "CTS_DOWNLOAD_DIR": "/tmp/cts_download_dir",
<                     "NCIT_DOWNLOAD_DIR": "/tmp/NCIT_download_dir",
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     'S3_EVAL_FOLDER': 'eval',
<                     # "DATASET_S3_FOLDER": "emfact/datasets",
<                     "COMPARE_TYPE": "cartesian",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<             }},
<             { 'http_method': None,   "handler": None,     'handler_file': 'post_make_datasets.py',    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     "NCIT_VERSION": "",
<                     "CTS_DOWNLOAD_DIR": "/tmp/cts_download_dir",
<                     "NCIT_DOWNLOAD_DIR": "/tmp/NCIT_download_dir",
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     # "DATASET_S3_FOLDER": "emfact/datasets",
<                     # "MAKE_REPORT_LAMBDA": make_comparison_report_lambda.function_name,
<                     ### ATTENTION: This above env-var is added DYNAMICALLY within `etl/infrastructure.py`
<                     "COMPARISON_COUNT": '5',
<                     "S3_COMPARISON_OUTPUT_FOLDER": "fact/comparison",
<                     "S3_EXCEL_REPORTS_FOLDER": "fact/excel_reports",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
<                     "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<             }},
<             { 'http_method': None,   "handler": "process_trial_criteria_queue",    'entry': ETL_LAMBDA_ENTRY,
<                 'lambda-layers-names': [ 'psycopg3-pandas' ],
<                 'memory': 2048,
<                 # "timeout": 300 ### Queue visibility timeout: 300 seconds is less than Function timeout: 900 (Default for all API-lambdas)
<                 'extra-env-vars': {
<                     # "UNPUBLISHED": dbuser_sm_name,
<                     # "CT_API_UNPUBLISHED": cts_api_v2_unpublished_name,
<                     # "CT_API_URL"    : CT_API_URL,
<                     # "CT_API_URL_V2" : CT_API_URL_V2,
<                     # "CT_API_VERSION": CT_API_VERSION,
<                     "NCIT_VERSION": "",
<                     "CTS_DOWNLOAD_DIR": "/tmp/cts_download_dir",
<                     "NCIT_DOWNLOAD_DIR": "/tmp/NCIT_download_dir",
<                     # "DATASET_BUCKET": SEARCH_RESULTS_BUCKET_NAME,
<                     'S3_EVAL_FOLDER': 'eval',
<                     # "DATASET_S3_FOLDER": "emfact/datasets",
<                     "COMPARE_TYPE": "cartesian",
<                     "PROCESS_STATUS_TABLE": process_status_table_name,
489,498d180
< 
<             ### --------- devops-related Lambdas -----------
< 
<             {   'http_method': None,   'handler_file': 'devops_RDSInstanceSetup.py',
<                 'handler': DEFAULT_LAMBDA_HANDLER,
<                 'lambda-layers-names': [ 'psycopg3' ],
<                 'extra-env-vars': {
<                     "DBA": dbadmin_sm_arn,
<                     "DBU": dbuser_sm_arn,
<             }},
516d197
<             tier=self.tier,
519,536d199
<             dbuser_sm_arn=self.dbuser_sm_arn,
<             dbadmin_sm_arn=self.dbadmin_sm_arn,
<             user_data_table_name=self.user_data_table_name,
<             process_status_table_name=self.process_status_table_name,
<             cts_api_v2_unpublished_name=self.cts_api_v2_unpublished_name,
<             bing_maps_key_unpublished_name=self.bing_maps_key_unpublished_name,
<             SEARCH_RESULTS_BUCKET_NAME=self.SEARCH_RESULTS_BUCKET_NAME,
<             DATASET_BUCKET_NAME=self.DATASET_BUCKET_NAME,
<             UI_UPLOADS_BUCKET_NAME=self.UI_UPLOADS_BUCKET_NAME,
<             TRIAL_CRITERIA_QUEUE_URL=self.TRIAL_CRITERIA_QUEUE_URL,
<             MAKE_DATASET_QUEUE_URL=self.MAKE_DATASET_QUEUE_URL,
<             ETL_QUEUE_URL=self.ETL_QUEUE_URL,
<             CREATE_REPORT_QUEUE_URL=self.CREATE_REPORT_QUEUE_URL,
<             ETL_TOPIC_ARN=self.ETL_TOPIC_ARN,
<             CT_API_URL=self.CT_API_URL,
<             CT_API_URL_V2=self.CT_API_URL_V2,
<             CT_API_VERSION=self.CT_API_VERSION,
<             curated_trigger_folder=self.curated_trigger_folder
