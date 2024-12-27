import re
import copy
import json
from typing import Optional, List, Dict
from jsonschema import validate
import jsonschema

from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_lambda,
    Size,
)

import constants
import common.cdk.constants_cdk as constants_cdk

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

DEFAULT_LAMBDA_HANDLER = "lambda_handler"

DEFAULT_API_LAMBDAS_ENTRY = "api/runtime"  ### folderpath
PANDAS_LAMBDA_ENTRY       = 'api/runtime_pandas' ### folderpath
ETL_LAMBDA_ENTRY          = 'backend/etl/runtime'   ### folderpath

DEFAULT_LAMBDA_LAYER = "psycopg3"
DEFAULT_CPU_ARCH         = aws_lambda.Architecture.ARM_64
DEFAULT_CPU_ARCH_NAMESTR = aws_lambda.Architecture.ARM_64.name
# runtime = constants_cdk.LAMBDA_PYTHON_RUNTIME

MIN_MEMORY = 512 ### CDK-Deploy error: Function code combined with layers exceeds the maximum allowed size of 262144000 bytes. The actual size is 375883658 bytes
DEFAULT_API_TIMEOUT = Duration.seconds(60)  ### Lambda-timeout for Lambdas BEHIND the APIGW.
LOG_LEVEL = "INFO" ### "DEBUG" "WARN"

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

_lambda_construct_list :List[aws_lambda.IFunction]     = []
_lambda_construct_map  :Dict[str,aws_lambda.IFunction] = {}

_cache_of_layers          :Dict[str, aws_lambda.ILayerVersion] = {}
_cache_of_layers_arns     :Dict[str, str]                      = {}
_cache_of_layers_assets   :Dict[str, aws_lambda.AssetCode]     = {}
# _cache_of_layers_zipfiles :Dict[str, pathlib.Path]             = {}

### AWS official Lambda-Layers for Pandas
###         https://aws-sdk-pandas.readthedocs.io/en/stable/layers.html
### FYI only: 3rd party https://github.com/keithrozario/Klayers/tree/master/deployments/python3.12
_cache_of_layers_arns["pandas-ext-arm64"] = "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312-Arm64"
_cache_of_layers_arns["pandas-ext-amd64"] = "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312"

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

class MyLambdaConfigException(Exception):
    pass

class LambdaConfigs():

    @property
    def list(self) -> List[dict]:             return self.__list

    @property
    def common_env(self) -> dict:       return self._common_env

    def append_addl_api(self, entry: dict) -> None:
        self.__list.append(entry)

    @staticmethod
    def lambda_construct_list() -> List[aws_lambda.Function]:
        return _lambda_construct_list

    @staticmethod
    def lambda_construct_map()  -> Dict[str,aws_lambda.Function]:
        return _lambda_construct_map

    @property
    def num_of_lambdas( self ) -> int:  return len( self.list )

    ### =========================================================================

    @staticmethod
    def num_of_lambdas() -> int:
        return 55

    @staticmethod
    def get_lambda_entry(item :dict) -> Optional[str]: return item["entry"] if "entry" in item else DEFAULT_API_LAMBDAS_ENTRY
    @staticmethod
    def get_lambda_index(item :dict) -> Optional[str]: return item['handler_file'] if 'handler_file' in item else f"{item['handler']}.py"
    # @staticmethod
    # def get_handler_file(item :dict) -> Optional[str]: return item.get('handler_file', LambdaConfigs.get_handler_id(item=item))
    @staticmethod
    def get_handler(item :dict) -> Optional[str]: return item.get('handler')   or   DEFAULT_LAMBDA_HANDLER
    @staticmethod
    def get_http_method(item :dict) -> Optional[str]: return item.get('http_method', None)
    @staticmethod
    def get_apigw_path(item :dict) -> Optional[str]: return item.get("apigw-path", None)
    @staticmethod
    def get_memory_size(item :dict) -> Optional[str]: return item.get('memory')
    @staticmethod
    def get_cpu_arch(item :dict) -> Optional[str]: return item.get('cpu-arch', None) or DEFAULT_CPU_ARCH_NAMESTR
    @staticmethod
    def get_extra_env_vars(item :dict) -> Optional[str]: return item.get('extra-env-vars', {})
    @staticmethod
    def get_lambda_rolename(item :dict) -> Optional[str]: return item.get('IAM-role-name', None)
    @staticmethod
    def get_lambda_layers_names(item :dict) -> Optional[List[str]]:
        v = item.get('lambda-layers-names', None)
        return v if v else [ DEFAULT_LAMBDA_LAYER ]
        # return [DEFAULT_LAMBDA_LAYER] if v == None else v
        # retval = [ DEFAULT_LAMBDA_LAYER ]
        # if v: retval.extend( v )
    @staticmethod
    def get_time_out(item :str) -> Duration:
        if "timeout" in item:
            return item["timeout"]
        else:
            if LambdaConfigs.get_http_method(item) == None:
                return Duration.minutes(15) ### Non-API Lambdas.  Should be the maximum possible.
            else:
                return DEFAULT_API_TIMEOUT ### for all API-Lambdas
    # override_content_type_to_BINARY: bool = a_lambda.get('mime-response', None) != None

### ===========================================================================================================
### -----------------------------------------------------------------------------------------------------------
### ===========================================================================================================

    def __init__(self,
        scope :Construct,
        dbuser_sm_name :str,
    ):
        super().__init__()

        ### Attention: Must save all params, so that `deep_clone()` can utilize it.
        self._scope = scope
        self.dbuser_sm_name = dbuser_sm_name

        self._common_env = {
            "LOG_LEVEL": LOG_LEVEL,

            "USE_CONNECTION_POOL": "False",
            "CONNECTION_POOL_COUNT": "4",
            "UNPUBLISHED": dbuser_sm_name,
            "DATASET_S3_FOLDER": "emfact/datasets",
        }

        ### -----------------------------------------------------------------------

        self.__list = [
            { 'http_method': 'GET',  "handler": 'get_prior_therapy',             "apigw-path": 'prior_therapy', },
            { 'http_method': 'POST', "handler": 'post_search_and_match',         "apigw-path": 'search_and_match',
                'handler_file': 'handler.py',
                'memory': 1024,
                'entry': PANDAS_LAMBDA_ENTRY, 'lambda-layers-names': [ 'psycopg3-pandas' ],
            },
            { 'http_method': 'POST', "handler": 'validate_curated_for_upload',   "apigw-path": 'validate_curated_for_upload',
                'entry': PANDAS_LAMBDA_ENTRY, 'lambda-layers-names': [ 'psycopg3-pandas' ],
                'extra-env-vars': {
                    'MAX_EXPRESSION_ERRORS'  : '0',
            }},
            ### ! ATTENTION ! the following are ETL-related, and SHOULD NOT be accessible via APIGW.
            { 'http_method': None,   "handler": None,     'handler_file': 'api_etl.py',    'entry': ETL_LAMBDA_ENTRY,
                'lambda-layers-names': [ 'psycopg3-pandas' ],
                'memory': 2048,
                # ephemeral_storage_size=Size.mebibytes(8192),
                'extra-env-vars': {
                    # "UNPUBLISHED": dbuser_sm_name,
                    'S3_EVAL_FOLDER': 'eval',
                    "thread_count": "25",
                    "count_per_thread": "50",
            }},
        ]

        LambdaConfigs.validate_lambda_config_list( self.list )


### ===========================================================================================================
### -----------------------------------------------------------------------------------------------------------
### ===========================================================================================================

    def deep_clone(self):
        """
        Create a deep clone of the "self"(thereby creating a completely-isolated no-shared but new LambdaConfigs object).
        :param config: The LambdaConfigs object to clone
        :return: A new LambdaConfigs object with deeply copied attributes
        """
        # Create a new instance of LambdaConfigs
        new_config = LambdaConfigs(
            scope=self._scope,
            dbuser_sm_name=self.dbuser_sm_name,
        )

        # Perform a deep copy of all attributes
        for attr, value in self.__dict__.items():
            setattr(new_config, attr, copy.deepcopy(value))

        return new_config

### -----------------------------------

    """ only keep items in self.list .. whose array-indices are between 'begg' & 'endd' (NOT-inclusive)
    """
    def keep_only_items_between( self,
        begg :int,
        endd :int
    ):
        """
        Modifies the list list in-place, keeping only the items whose indices fall within the specified range.
        :param begg: The beginning index (inclusive)
        :param endd: The ending index (inclusive)
        """
        if begg < 0 or begg > endd:
            raise ValueError(f"Invalid range specified -- begg='{begg}' and endd='{endd}' -- within LambdaConfigs.self.keep_only_items_between() within "+ __file__)

        self.__list = self.__list[ begg:endd ]

### -----------------------------------------------------------------------------------------------------------

    # @staticmethod
    # def num_of_lambdas_in_file(file_path=__file__):
    #     """
    #     Reads the specified file, counts occurrences of 'http_method' and 'handler_id',
    #     and returns the maximum of the two counts.
    #     :param file_path: Path to the file to analyze (default is the ./api/config.py)
    #     """
    #     try:
    #         with open(file_path, 'r') as file:
    #             content = file.read()
    #         # Count occurrences using regex
    #         http_method_count = len(re.findall(r"'http_method'", content))
    #         handler_id_count = len(re.findall(r"'handler_id'", content))
    #         return max(http_method_count, handler_id_count)
    #     except FileNotFoundError:
    #         print(f"Error: File not found at {file_path}")
    #         return None
    #     except IOError:
    #         print(f"Error: Unable to read file at {file_path}")
    #         return None

### ===========================================================================================================
### -----------------------------------------------------------------------------------------------------------
### ===========================================================================================================

    @staticmethod
    def cache_lambda_layer_asset(
        layer_name :str,
        cpu_arch_str :str,
        layer_asset :aws_lambda.AssetCode,
        overwrite :bool = False,
    ) -> None:
        """ Caches the specified Lambda-layer's Zip-file artifact -- allowing it to be used ANYWHERE in cdk.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :param layer_zip_file :Path -- to the Lambda layer zip file
        :param overwrite :bool -- Whether to overwrite the layer if it already exists (default: False)
        """
        ### SANITY CHECK: if the layer is valid
        if not layer_asset:
            raise MyLambdaConfigException( f"!! ERROR !! For Lambda-Layer '{layer_name}-{cpu_arch_str}' .. 'layer_asset' is None !!" )
        if not overwrite and f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_assets:
            raise MyLambdaConfigException( f"!! ERROR !! Layer-Asset '{layer_name}-{cpu_arch_str}' is already cached (FYI: overwrite='{overwrite}')!!" )

        _cache_of_layers_assets[ f"{layer_name}-{cpu_arch_str}" ] = layer_asset
        print( f"Saved to _cache_of_layers_assets for '{layer_name}-{cpu_arch_str}' = {layer_asset.path}" )
        print( layer_asset )


    @staticmethod
    def lookup_lambda_layer_asset(
        layer_name :str,
        cpu_arch_str :str,
    ) -> aws_lambda.AssetCode:
        """ Looks up the path to the cached Lambda-layer's Zip-file artifact.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :return: pathlib.Path object to the Lambda-layer's zip-file
        """
        if f"{layer_name}-{cpu_arch_str}" not in _cache_of_layers_assets:
            raise MyLambdaConfigException( f"!! ERROR !! Layer '{layer_name}-{cpu_arch_str}' is NOT cached.  Perhaps you are looking it up BEFORE it has been created (within api/infrastructure.py) !!" )
        return _cache_of_layers_assets[ f"{layer_name}-{cpu_arch_str}" ]

### -----------------------------------------------------------------------------------------------------------

    @staticmethod
    def cache_lambda_layer(
        layer_name :str,
        cpu_arch_str :str,
        stk :Stack,
        layer :aws_lambda.ILayerVersion,
        overwrite :bool = False,
    ) -> None:
        """ Caches the specified Lambda layer -- allowing it to be used ANYWHERE in cdk.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :param layer :aws_lambda.ILayerVersion -- cdk-construct-resource already created.
        :param overwrite :bool -- Whether to overwrite the layer if it already exists (default: False)
        """
        ### SANITY CHECK: if the layer is valid
        if not overwrite and ( f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_arns or f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" in _cache_of_layers ):
            raise MyLambdaConfigException( f"!! ERROR !! Layer-CDK-Object '{layer_name}-{cpu_arch_str}' is already cached (FYI: overwrite='{overwrite}')!!" )

        _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ] = layer
        _cache_of_layers_arns[ f"{layer_name}-{cpu_arch_str}" ] = layer.layer_version_arn
        print( f"_cache_of_layers for '{stk.stack_name}-{layer_name}-{cpu_arch_str}' = {layer.node.addr} // layer-arn={layer.layer_version_arn}" )


    @staticmethod
    def lookup_lambda_layer(
        layer_name :str,
        stk :Stack,
        cpu_arch_str :str,
    ) -> aws_lambda.ILayerVersion:
        """ Looks up the path to the cached Lambda layer.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :return: aws_lambda.ILayerVersion object
        """
        if f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" in _cache_of_layers:
            return _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ]
        else:
            if f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_arns:
                ilayer_obj = aws_lambda.LayerVersion.from_layer_version_arn(
                    scope = stk,
                    id = f"{layer_name}-{cpu_arch_str}",
                    layer_version_arn = _cache_of_layers_arns[ f"{layer_name}-{cpu_arch_str}" ],
                )
                _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ] = ilayer_obj
                return ilayer_obj
            else:
                raise MyLambdaConfigException( f"!! ERROR !! Layer/Layer-ARN for '{layer_name}-{cpu_arch_str}' is NOT cached.  Perhaps you are looking it up BEFORE it has been created (within api/infrastructure.py) !!" )


    @staticmethod
    def num_of_lambdas(file_path=__file__):
        """
        Reads the specified file, counts occurrences of 'http_method' and 'handler_id',
        and returns the maximum of the two counts.
        :param file_path: Path to the file to analyze (default is the ./api/config.py)
        """
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            # Count occurrences using regex
            http_method_count = len(re.findall(r"'http_method'", content))
            handler_id_count = len(re.findall(r"'handler_id'", content))
            return max(http_method_count, handler_id_count)
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return None
        except IOError:
            print(f"Error: Unable to read file at {file_path}")
            return None

### ===========================================================================================================
### -----------------------------------------------------------------------------------------------------------
### ===========================================================================================================

    @staticmethod
    def cache_lambda_layer_asset(
        layer_name :str,
        cpu_arch_str :str,
        layer_asset :aws_lambda.AssetCode,
        overwrite :bool = False,
    ) -> None:
        """ Caches the specified Lambda-layer's Zip-file artifact -- allowing it to be used ANYWHERE in cdk.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :param layer_zip_file :Path -- to the Lambda layer zip file
        :param overwrite :bool -- Whether to overwrite the layer if it already exists (default: False)
        """
        ### SANITY CHECK: if the layer is valid
        if not layer_asset:
            raise MyLambdaConfigException( f"!! ERROR !! For Lambda-Layer '{layer_name}-{cpu_arch_str}' .. 'layer_asset' is None !!" )
        if not overwrite and f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_assets:
            raise MyLambdaConfigException( f"!! ERROR !! Layer-Asset '{layer_name}-{cpu_arch_str}' is already cached (FYI: overwrite='{overwrite}')!!" )

        _cache_of_layers_assets[ f"{layer_name}-{cpu_arch_str}" ] = layer_asset
        print( f"Saved to _cache_of_layers_assets for '{layer_name}-{cpu_arch_str}' = {layer_asset.path}" )
        print( layer_asset )


    @staticmethod
    def lookup_lambda_layer_asset(
        layer_name :str,
        cpu_arch_str :str,
    ) -> aws_lambda.AssetCode:
        """ Looks up the path to the cached Lambda-layer's Zip-file artifact.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :return: pathlib.Path object to the Lambda-layer's zip-file
        """
        if f"{layer_name}-{cpu_arch_str}" not in _cache_of_layers_assets:
            raise MyLambdaConfigException( f"!! ERROR !! Layer '{layer_name}-{cpu_arch_str}' is NOT cached.  Perhaps you are looking it up BEFORE it has been created (within api/infrastructure.py) !!" )
        return _cache_of_layers_assets[ f"{layer_name}-{cpu_arch_str}" ]

### -----------------------------------------------------------------------------------------------------------

    @staticmethod
    def cache_lambda_layer(
        layer_name :str,
        cpu_arch_str :str,
        stk :Stack,
        layer :aws_lambda.ILayerVersion,
        overwrite :bool = False,
    ) -> None:
        """ Caches the specified Lambda layer -- allowing it to be used ANYWHERE in cdk.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :param layer :aws_lambda.ILayerVersion -- cdk-construct-resource already created.
        :param overwrite :bool -- Whether to overwrite the layer if it already exists (default: False)
        """
        ### SANITY CHECK: if the layer is valid
        if not overwrite and ( f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_arns or f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" in _cache_of_layers ):
            raise MyLambdaConfigException( f"!! ERROR !! Layer-CDK-Object '{layer_name}-{cpu_arch_str}' is already cached (FYI: overwrite='{overwrite}')!!" )

        _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ] = layer
        _cache_of_layers_arns[ f"{layer_name}-{cpu_arch_str}" ] = layer.layer_version_arn
        print( f"_cache_of_layers for '{stk.stack_name}-{layer_name}-{cpu_arch_str}' = {layer.node.addr} // layer-arn={layer.layer_version_arn}" )


    @staticmethod
    def lookup_lambda_layer(
        layer_name :str,
        stk :Stack,
        cpu_arch_str :str,
    ) -> aws_lambda.ILayerVersion:
        """ Looks up the path to the cached Lambda layer.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :return: aws_lambda.ILayerVersion object
        """
        if f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" in _cache_of_layers:
            return _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ]
        else:
            if f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_arns:
                ilayer_obj = aws_lambda.LayerVersion.from_layer_version_arn(
                    scope = stk,
                    id = f"{layer_name}-{cpu_arch_str}",
                    layer_version_arn = _cache_of_layers_arns[ f"{layer_name}-{cpu_arch_str}" ],
                )
                _cache_of_layers[ f"{stk.stack_name}-{layer_name}-{cpu_arch_str}" ] = ilayer_obj
                return ilayer_obj
            else:
                raise MyLambdaConfigException( f"!! ERROR !! Layer/Layer-ARN for '{layer_name}-{cpu_arch_str}' is NOT cached.  Perhaps you are looking it up BEFORE it has been created (within api/infrastructure.py) !!" )


    @staticmethod
    def validate_lambda_config_list( a_list :list):
        """
        Validates self.__list against the Lambda configuration schema.
        Raises ValidationError if the configuration is invalid.
        Returns True if validation passes.
        """
        lambda_config_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "http_method",
                    "handler",
                ],
                "properties": {
                    "apigw-path":   { "type": "string" },
                    "http_method":  {
                        "type": ["string", "null"],
                        "enum": ["GET", "POST", "PUT", "DELETE", None]
                    },
                    "handler":      { "type": ["string", "null"] },
                    "handler_file": { "type": "string" },
                    "apigw-path":   { "type": "string" },
                    "ephemeral_storage_size": { "type": "integer", "minimum": 512 },
                    "memory":       { "type": "integer", "minimum": 128 },
                    "timeout":      { "type": "object" },
                    "entry":        { "type": "string" },
                    "lambda-layers-names": { "type": "array", "items": { "type": "string" } },
                    "extra-env-vars": { "type": "object" },
                },
                "additionalProperties": False
            }
        }

        try:
            validate( instance = a_list, schema = lambda_config_schema )
        except jsonschema.exceptions.ValidationError as err:
            error_path = " -> ".join(str(p) for p in err.path)
            error_message = f"Configuration validation failed at {error_path}: {err.message}"
            raise ValueError(error_message) from err
        except Exception as err:
            raise ValueError(f"Unexpected error during configuration validation: {str(err)}") from err

### -----------------------------------------------------------------------------------------------------------

"""
    @staticmethod
    def cache_lambda_layer_zipfile_path(
        layer_name :str,
        cpu_arch_str :str,
        layer_zip_file :pathlib.Path,
        overwrite :bool = False,
    ) -> None:
        " " " Caches the specified Lambda-layer's Zip-file artifact -- allowing it to be used ANYWHERE in cdk.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :param layer_zip_file :Path -- to the Lambda layer zip file
        :param overwrite :bool -- Whether to overwrite the layer if it already exists (default: False)
        " " "
        ### SANITY CHECK: if the layer is valid
        if not layer_zip_file.exists():
            raise MyLambdaConfigException( f"!! ERROR !! For Lambda-Layer '{layer_name}-{cpu_arch_str}' .. {layer_zip_file} does NOT exist !!" )
        if not overwrite and f"{layer_name}-{cpu_arch_str}" in _cache_of_layers_zipfiles:
            raise MyLambdaConfigException( f"!! ERROR !! Layer-ZIP-file '{layer_name}-{cpu_arch_str}' is already cached (FYI: overwrite='{overwrite}')!!" )

        _cache_of_layers_zipfiles[ f"{layer_name}-{cpu_arch_str}" ] = layer_zip_file
        print( f"_cache_of_layers_zipfiles for '{layer_name}-{cpu_arch_str}' = {layer_zip_file}" )


    @staticmethod
    def lookup_lambda_layer_zipfile_path(
        layer_name :str,
        cpu_arch_str :str,
    ) -> pathlib.Path:
         " " " Looks up the path to the cached Lambda-layer's Zip-file artifact.
        :param layer_name :str -- Unique Name of the Lambda layer (not incl. CPU_ARCH)
        :param cpu_arch_str :str -- amd64|arm64
        :return: pathlib.Path object to the Lambda-layer's zip-file
        " " "
        if f"{layer_name}-{cpu_arch_str}" not in _cache_of_layers_zipfiles:
            raise MyLambdaConfigException( f"!! ERROR !! Layer '{layer_name}-{cpu_arch_str}' is NOT cached.  Perhaps you are looking it up BEFORE it has been created (within api/infrastructure.py) !!" )
        return _cache_of_layers_zipfiles[ f"{layer_name}-{cpu_arch_str}" ]
"""

### ===========================================================================================================
### -----------------------------------------------------------------------------------------------------------
### ===========================================================================================================


""" print out the above list in alphabetically-sorted order
python3 <<EOTXT
from api.config import list
nl=[]
for ar in list:
    nl.append( ar[0] )
nl.sort()
print( nl )
EOTXT
"""
