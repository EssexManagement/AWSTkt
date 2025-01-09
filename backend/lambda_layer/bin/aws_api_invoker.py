### This file has a Utility class to make it easy to write COOKIE-CUTTER python-scripts that replace my complicated AWS-CLI.
### This file also has the wonderful ability to CACHE the responses from AWS-SDK/boto3, so that scripts are incredibly fast.

from typing import Tuple, Sequence
import sys
import boto3
import os
import pathlib
import json
import time
import regex
import traceback
from datetime import datetime, timedelta

class MyException(Exception):
    pass

class InvokeAWSApi():
    debug: bool = False

    def __init__(self,
        aws_profile :str = None,
        aws_region :str = "us-east-1",
        session: boto3.Session = None,
        debug: bool = False
    ) -> None:

        self.debug = debug

        self.aws_profile = aws_profile
        self.session = session
        self.aws_region = aws_region
        self.sanity_check_awsprofile()

    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    def sanity_check_awsprofile(self,
        # aws_profile: str,
    ) -> boto3.Session:
        CTX = "sanity_check_awsprofile() in "+__file__
        ### if instance-variables are UN-defined, define them.
        if self.aws_profile and self.aws_profile.strip().lower() not in [ "", "none", "n/a", "undefined" ]:
            if self.session is None:
                if hasattr(self, "aws_region"):
                    self.session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                else:
                    self.session = boto3.Session(profile_name=self.aws_profile)
        else:
            if self.session is None:
                if hasattr(self, "aws_region"):
                    self.session = boto3.Session(region_name=self.aws_region)
                else:
                    self.session = boto3.Session()
            # raise MyException("!!ERROR!! Constructor-param AWS-Profile is missing!! Context="+CTX)

        ### Sanity-check
        if not self.session:
            raise MyException("!!ERROR!! Session(AWS) is STILL undefined!! Context="+CTX)

        ### Section: AWS SDK initialization (for API/SDK calls)
        client = self.session.client('sts')
        account_id = client.get_caller_identity()["Account"]
        default_region_in_awsprofile = self.session.region_name
        if self.debug: print(f"\nAWS Account ID: {account_id}")
        if self.debug: print(f"Default AWS Region: {default_region_in_awsprofile}\n")
        if not hasattr(self, "aws_region"):
            self.aws_region = default_region_in_awsprofile

        return self.session
    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    """ 1st param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        The 2nd-param is # of days (how old can the Cache-file be)
        The 2nd-param represents the maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    """
    def is_cache_too_old(
        self,
        json_output_filepath: str,
        cache_no_older_than: int,
    ) -> bool:
        if not json_output_filepath.exists():
            print(f"Cache is missing!! a.k.a. File '{json_output_filepath}' is missing!!")
            re_run_aws_sdk_call = True
        else:
            # Check if the file was last modified over a week ago
            cache_no_older_than__in_secs = cache_no_older_than * 24 * 60 * 60  # 7 days
            file_modified_time = json_output_filepath.stat().st_mtime
            current_time = time.time()

            if current_time - file_modified_time > cache_no_older_than__in_secs:
                re_run_aws_sdk_call = True
                print(f"The CACHE/file '{json_output_filepath}' is too old by at least {cache_no_older_than} days !!! ")
            else:
                re_run_aws_sdk_call = False
                print(f"The CACHE/file '{json_output_filepath}' is still fresh enough.\n", '_'*80,"\n\n")
        return re_run_aws_sdk_call


    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    """ 1st param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        The 2nd-param is the AWS-Profile to use.
        The 3rd-OPTIONAL-param is # of days (how old can the Cache-file be).  Defaults to 7-days
    """
    def list_lambdas( self,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:
        return self.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'lambda',
            api_method_name = "list_functions",
            additional_params={},
            response_key = 'Functions',
            json_output_filepath = json_output_filepath,
            cache_no_older_than = cache_no_older_than,
        )

    ### ----------------------------------------------------------

    """ 1st param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        The 2nd-param is the AWS-Profile to use.
        The 3rd-OPTIONAL-param is # of days (how old can the Cache-file be).  Defaults to 7-days
    """
    def list_stacks( self,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:
        return self.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'cloudformation',
            api_method_name = "list_stacks",
            additional_params={
                "StackStatusFilter": ['CREATE_IN_PROGRESS', 'CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',                     'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_COMPLETE', 'UPDATE_FAILED', 'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE', 'REVIEW_IN_PROGRESS', 'IMPORT_IN_PROGRESS', 'IMPORT_COMPLETE', 'IMPORT_ROLLBACK_IN_PROGRESS', 'IMPORT_ROLLBACK_FAILED', 'IMPORT_ROLLBACK_COMPLETE'],
                # "StackStatusFilter": ['CREATE_IN_PROGRESS', 'CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED', 'DELETE_COMPLETE', 'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_COMPLETE', 'UPDATE_FAILED', 'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE', 'REVIEW_IN_PROGRESS', 'IMPORT_IN_PROGRESS', 'IMPORT_COMPLETE', 'IMPORT_ROLLBACK_IN_PROGRESS', 'IMPORT_ROLLBACK_FAILED', 'IMPORT_ROLLBACK_COMPLETE'],
            },
            response_key = 'StackSummaries',
            json_output_filepath = json_output_filepath,
            cache_no_older_than = cache_no_older_than,
        )

    ### ----------------------------------------------------------

    """ Returns a JSON + latest-VersionId-as-String.
        The returned-JSON is as list (containing full details of each version)
    """
    def get_all_versions_of_lambda( self,
        lambda_name :str,
    ) -> Tuple[list,str]:
        try:
            lambda_client = self.session.client('lambda')

            all_versions = []
            marker = None

            while True:
                params = {'FunctionName': lambda_name}
                if marker:
                    params['Marker'] = marker
                print("↓", end="", flush=True)
                lambda_versions = lambda_client.list_versions_by_function(**params)
                all_versions.extend(lambda_versions['Versions'])

                marker = lambda_versions.get('NextMarker')
                if not marker:
                    break

            # Sort by LastModified to ensure we get the truly latest version
            all_versions.sort(key=lambda x: x['LastModified'])
            if self.debug > 4: print(json.dumps(all_versions, indent=4, default=str))

            latest_version_id :str = all_versions[-1]['Version']
            if latest_version_id == "$LATEST" and len(all_versions) > 1:
                latest_version_id = all_versions[-2]['Version']
            else:
                if self.debug > 1:
                    print("\n\n"); print(all_versions)
                if self.debug: print(f"\n! No PROPER-NUMERICAL versionIds exist for {lambda_name} !  Very likely just DEFAULT-VERSION only for this lambda !")
                # print(f"\t! 👎🏾{lambda_name}👎🏾 ", end="", flush=True)
                return all_versions, None

            if self.debug > 4: print(json.dumps(lambda_versions, indent=4, default=str))
            if self.debug > 1: print(f"Latest out of {len(all_versions)} versions, LATEST-Version: {latest_version_id}")

            return all_versions, latest_version_id

        except Exception as e:
            print(f"!! ERROR !! getting versions for {lambda_name}: {str(e)}")
            traceback.print_exc()
            time.sleep(30)

    ### ----------------------------------------------------------
    def get_all_lambdas_full_details( self,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:
        CTX = f"get_all_lambdas_full_details('{json_output_filepath}'): "
        ### Note: `aws-cli` command `list-function` and the corresponding `boto3 list_function()` on respond with SOME of the Lambda-attributes/configuration.
        all_lambdas_w_props = self.list_lambdas(
            json_output_filepath = json_output_filepath,
            # aws_profile = aws_profile,
            cache_no_older_than = cache_no_older_than,
        )

        if self.debug: print(f"\nInvoking `lambda_client.get_function()` and `lambda_client.get_concurrency()` for each Lambda within {CTX}\n")
        ### Load additional details on each Lambda, like ProvisionedConcurrency, and merge that detail into the `all_lambdas_w_props`
        lambda_client = self.session.client('lambda')
        lambda_details :dict = None
        for lambda_details in all_lambdas_w_props:
            lambda_name = lambda_details['FunctionName']
            # lambda_arn = lambda_details['FunctionArn']

            ### Check whether .. the Cache has already invoked `lambda_client.get_function()` and `lambda_client.get_concurrency()`
            # if "Tags" in lambda_details and "ProvisionedConcurrency" in lambda_details:
            if 'ProvisionedConcurrency' in lambda_details:
                if self.debug: print("⏩", end="", flush=True)
                continue
            else:
                lambda_details['ProvisionedConcurrency'] = None
                ### Initialize any missing values, so repeated AWS-Boto3 invocations do Not happen (below)

            # print(lambda_details)
            # print(lambda_name)
            # time.sleep(15)


            try:
                print("↓", end="", flush=True)
                addl_details = lambda_client.get_function(
                    FunctionName=lambda_name,
                    # Qualifier='version#'
                )
                if self.debug > 4:
                    print("\n", '.'*80, "\n")
                    print(json.dumps(lambda_details, indent=4, default=str))

                ### Now copy Tags, Code and other Configuration elements into the main-cache for Lambdas
                lambda_details["Code"] = addl_details["Code"]

                if "Tags" in addl_details:
                    lambda_details["Tags"] = addl_details["Tags"]
                else:
                    if self.debug: print(f"\n\n!! WARNING !! {lambda_name} does NOT have a Tags !!\n")
                    print(f"\t! ⚠️{lambda_name}⚠️ ", end="", flush=True)

                addl_details = addl_details['Configuration']
                for k in addl_details.keys():
                    if self.debug > 1: print(f"Lambda-Configuration-KEY = {k} within {CTX}")
                    v = addl_details[k]
                    if self.debug > 1: print(v)
                    if not k in lambda_details:
                        lambda_details[k] = v

                try:
                    latest_versionid :str = None
                    ### Get the latest version of this lambda, by invoking lambda_client.list_versions_by_function()
                    lambda_versions, latest_versionid = self.get_all_versions_of_lambda( lambda_name=lambda_name )
                    lambda_details['Versions'] = lambda_versions

                    # print(lambda_versions)
                    if self.debug: print(f"\nLatest Version: {latest_versionid}]\tfor {lambda_name} ..", end="", flush=True)
                    if self.debug > 1: print(f"\nLatest Version: {latest_versionid} for {lambda_name} within {CTX}\n")
                    ### For this "lambda_name", get provisioned-concurrency information -- for latest version at least.
                    if latest_versionid:
                        print("↓", end="", flush=True)
                        lambda_provisioned_concurrency :dict = lambda_client.get_provisioned_concurrency_config(
                            FunctionName=lambda_name,
                            Qualifier=latest_versionid,
                            # Qualifier="$LATEST", ### will throw an error/exception. Need actual Numerical VersionId of Lambda!!!
                        )
                        lambda_provisioned_concurrency.pop('ResponseMetadata', None) ### delete this entry from JSON.
                        lambda_details['ProvisionedConcurrency'] = lambda_provisioned_concurrency

                except Exception as e:
                    # print(f"!! ERROR !! getting provisioned-concurrency for {lambda_name}: {str(e)}")
                    if self.debug > 1: print(f" --NO-- provisioned-concurrency for {lambda_name} VersionId={latest_versionid}\n{str(e)}\n")

                # time.sleep(1)

                if self.debug > 2: print(json.dumps(lambda_details, indent=4, default=str))
                print(".", end="", flush=True)

            except Exception as e:
                print(f"!! ERROR !! getting provisioned-concurrency for {lambda_name}: {str(e)}")
                traceback.print_exc(limit=None, file=sys.stderr)
                sys.exit(71)

        self.update_diskfile_cache(
            json_output_filepath = json_output_filepath,
            inmemory_cache = all_lambdas_w_props,
        )
        return all_lambdas_w_props

    ### ----------------------------------------------------------
    def get_all_stacks_full_details( self,
        app_name :str,
        json_output_filepath: str,
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:
        CTX = f"get_all_stacks_full_details('{app_name}'): '{json_output_filepath}'"
        if not self.is_cache_too_old( json_output_filepath=json_output_filepath, cache_no_older_than=cache_no_older_than ):
            # Use the cached response (previously invoked perhaps a few days back)
            with open(str(json_output_filepath)) as f:
                complete_results = json.load(f)
            cnt = len(complete_results)
            print(f"File {json_output_filepath} is present. Context={CTX}.\nSo .. using {cnt} rows of cached AWS-SDK complete_response.. ..\n")
            return complete_results

        CTX = f"get_all_STACKS_full_details('{json_output_filepath}'): "
        ### Note: `aws-cli` command `list-function` and the corresponding `boto3 list_function()` on respond with SOME of the Lambda-attributes/configuration.
        all_stk_list = self.list_stacks(
            json_output_filepath = json_output_filepath,
            # aws_profile = aws_profile,
            cache_no_older_than = cache_no_older_than,
        )

        if self.debug: print(f"\nInvoking `cloudFormation_client.get_stack()` for each Lambda within {CTX}\n")
        ### Load additional details on each Lambda, like ProvisionedConcurrency, and merge that detail into the `all_lambdas_w_props`
        cft_client = self.session.client('cloudformation')
        for stk_props in all_stk_list:
            stk_name :str = stk_props['StackName']
            # stk_id :str = stk_props['StackId']

            # print(stk_props)
            # print(stk_name)
            # time.sleep(15)
            if not stk_name.startswith( app_name ):
                if self.debug: print(f"Skipping Stack {stk_name} as it does NOT start with {app_name} ..")
                print("⏩", end="", flush=True)
                continue

            try:
                print("↓", end="", flush=True)
                addl_details = cft_client.describe_stacks(
                    StackName = stk_name,
                    # Qualifier='version#'
                )
                if len(addl_details['Stacks']) > 1:
                    raise MyException(f"!! ERROR !! More than 1 Stack returned for '{stk_name}' !")
                addl_details = addl_details['Stacks'][0]
                if self.debug > 4:
                    print("\n", '.'*80, "\n")
                    print(json.dumps(stk_props, indent=4, default=str))

                key = "Parameters"
                stk_props[ key ] = addl_details[ key ]
                key = "Outputs"
                if key in addl_details:
                    stk_props[ key ] = addl_details[ key ]
                key = "RoleARN"
                if key in addl_details:
                    stk_props[ key ] = addl_details[ key ]

                resp = cft_client.get_template(
                    ### https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/client/get_template.html
                    StackName = stk_name,
                    TemplateStage = 'Original' ### | 'Processed'
                )
                key = "TemplateBody"
                stk_props[ key ] = resp[ key ]

                if "Tags" in addl_details:
                    stk_props["Tags"] = addl_details["Tags"]
                else:
                    if self.debug: print(f"\n\n!! WARNING !! {stk_name} does NOT have a Tags !!\n")
                    print(f"\t! ⚠️{stk_name}⚠️ ", end="", flush=True)

                # addl_details = addl_details['Parameters']
                # for k in addl_details.keys():
                #     if self.debug > 1: print(f"Stack-PARAMETER-KEY = {k} within {CTX}")
                #     v = addl_details[k]
                #     if self.debug > 1: print(v)
                #     if not k in stk_props:
                #         stk_props[k] = v

                if self.debug > 2: print(json.dumps(stk_props, indent=4, default=str))
                print(".", end="", flush=True)

            except Exception as e:
                print(f"!! ERROR !! getting additional-details for Stack '{stk_name}': {str(e)}")
                traceback.print_exc(limit=None, file=sys.stderr)
                sys.exit(71)

        self.update_diskfile_cache(
            json_output_filepath = json_output_filepath,
            inmemory_cache = all_stk_list,
        )
        return all_stk_list

    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    """ 1st param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        The 2nd-param is the AWS-Profile to use.
        The 3rd-OPTIONAL-param is # of days (how old can the Cache-file be).  Defaults to 7-days
    """
    def list_iam_roles( self,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:

        ### ----------------------------------------------------------------------
        # session = self.sanity_check_awsprofile(aws_profile=aws_profile)

        return self.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'iam',
            api_method_name = "list_roles",
            additional_params={},
            response_key = 'Roles',
            json_output_filepath = json_output_filepath,
            cache_no_older_than = cache_no_older_than,
        )

    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    """ 1st param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        The 2nd-param is the AWS-Profile to use.
        The 3rd-OPTIONAL-param is # of days (how old can the Cache-file be).  Defaults to 7-days
    """
    def list_iam_policies( self,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        # aws_profile: str,
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:

        CTX = "list_iam_POLICIES(): "
        json_output_filepath = pathlib.Path(json_output_filepath) ### convert a string into a Path object.

        ### ----------------------------------------------------------------------
        ### Logic to --Cache-- the output of AWS-SDK API-calls (into temporary files)
        ### As necessary invoke AWS SDK API calls.

        if self.is_cache_too_old( json_output_filepath=json_output_filepath, cache_no_older_than=cache_no_older_than ):
            print(f"{CTX} Invoking the massive AWS-SDK API to update the file ${json_output_filepath}...")
            client = self.session.client('iam')
            all_iam_Policies = []
            marker = None

            while True:
                if marker:
                    response = client.list_policies(Marker=marker)
                else:
                    response = client.list_policies()

                print("↓", end="", flush=True)
                all_iam_Policies.extend(response.get('Policies'))
                marker = response.get('Marker')
                # print(f"nextToken='{marker}'")

                if not marker:
                    break

            # Write the final complete-response as JSON to the file
            with open(str(json_output_filepath), "w") as f:
                json.dump(all_iam_Policies, f, indent=4, default=str)

            print(f"{CTX} Retrieved {len(all_iam_Policies)} in total.")
        else:
            # Use the cached complete-response
            with open(str(json_output_filepath)) as f:
                all_iam_Policies = json.load(f)
            cnt = len(all_iam_Policies)
            print(f"File {json_output_filepath} is present. Context={CTX}.\nSo .. using {cnt} rows of cached AWS-SDK complete_response.. ..\n")

        return all_iam_Policies


    def load_role_associated_inline_policy_cache(
        self,
        json_output_filepath: str,
    ) -> dict:
        CTX = "LOAD_role_associated_inline_policy_cache(): "
        try:
            # Use the cached complete-response
            with open(str(json_output_filepath)) as f:
                inmemory_cache = json.load(f)
            cnt = len(inmemory_cache)
            print(f"File {json_output_filepath} is present. Context={CTX}.\nSo .. using {cnt} rows of cached AWS-SDK complete_response.. ..\n")
        except Exception as e:
            inmemory_cache = {}

        return inmemory_cache

    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    ### This is information that needs to be PAINFULLY gathered via INNUMERABLE API invocations!
    def update_diskfile_cache(self,
        json_output_filepath: str,
        inmemory_cache: dict,
    ):
        CTX = "update_diskfile_cache(): "
        # Write the final complete-response as JSON to the file
        with open(str(json_output_filepath), "w") as f:
            json.dump(inmemory_cache, f, indent=4, default=str)

        cnt = len(inmemory_cache)
        if self.debug: print(f"\n\nFile {json_output_filepath} Saved with {cnt} rows of **DERIVED** data. Context={CTX}.\n\n")

        return inmemory_cache


    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ### *************************************************************************************************************************
    ### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    """ Generic Template-based Utility Function.
        Since All AWS-APIs will respond via Pagination, this can invoke -ANY- AWS-API repeatedly, until all "pagination" is complete.

        1st param is pre-defined string-value that you pass to boto3.client() call.
        2nd param is the method's-NAME for the above specified boto3-client.
        3rd param is a dict of Non-Default additional-params to pass to the above method.
        4th param is the json-key in the boto3-call's response-dict that you are interested in.
        5th param is a path like '/tmp/aws-cli-cmd-xyz.json'.
        6th-OPTIONAL-param is # of days (how old can the Cache-file be).  Defaults to 7-days
    """
    def invoke_aws_GenericAWSApi_for_complete_response( self,
        aws_client_type :str,
        api_method_name: str,
        additional_params :dict,
        response_key :str,
        json_output_filepath: str, ## f"{TMPDIR}/all-iam-roles.json"
        cache_no_older_than: int = 7,     ### maximum _ days old before invoking SDK-APIs to refresh the json_output_filepath
    ) -> any:

        CTX = f"invoke_aws_GenericAWSApi_for_complete_response('{api_method_name}'): '{json_output_filepath}'"
        json_output_filepath = pathlib.Path(json_output_filepath) ### convert a string into a Path object.

        ### ----------------------------------------------------------------------
        ### generic-logic to --Cache-- the output of AWS-SDK API-calls (into temporary files)
        ### As necessary invoke AWS SDK API calls.

        if self.is_cache_too_old( json_output_filepath=json_output_filepath, cache_no_older_than=cache_no_older_than ):

            print(f"Invoking the massive AWS-SDK API to update the CACHE-file... {CTX} ")
            client = self.session.client(aws_client_type)
            if not hasattr(client, api_method_name):
                raise MyException(f"Error: '{api_method_name}' is not a valid Method of AWS-API-SDK.")
            api_call_ref = getattr(client, api_method_name)

            complete_results = []
            Marker = None
            NextMarker = None
            nextToken = None
            NextToken = None
            KeyMarker = None ### S3
            ContinuationToken = None ### S3

            awsapi_pagination_params = {}
            # additional_params = {additional_param_name: additional_param_value}

            while True:
                print("↓", end="", flush=True)
                awsapi_all_params = { **awsapi_pagination_params, **additional_params }
                if self.debug > 2: print(f"\n\nawsapi_all_params={awsapi_all_params}\n")
                if Marker or NextMarker or nextToken or NextToken or KeyMarker or ContinuationToken:
                    response = api_call_ref(**awsapi_all_params)
                else:
                    response = api_call_ref(**additional_params)
                # if Marker or NextMarker oe nextToken or NextToken or KeyMarker or ContinuationToken:
                #     if additional_param_name:
                #         response = api_call_ref(Marker=Marker, nextToken=nextToken, NextToken=NextToken, **{additional_param_name: additional_param_value})
                #     else:
                #         response = api_call_ref(Marker=Marker, nextToken=nextToken, NextToken=NextToken)
                # else:
                #     if additional_param_name:
                #         response = api_call_ref(**{additional_param_name: additional_param_value})
                #     else:
                #         response = api_call_ref()
                if self.debug > 2: print(json.dumps(response, indent=4, default=str))

                if response.get(response_key) is not None:
                    complete_results.extend(response.get(response_key))

                ### Some AWS APIs use 'Marker' and some use 'nextToken'
                Marker = response.get('Marker')
                # if self.debug: print(f"Marker='{Marker}'")
                NextMarker = response.get('NextMarker')
                # if self.debug: print(f"NextMarker='{NextMarker}'")
                nextToken = response.get('nextToken')
                # if self.debug: print(f"nextToken='{nextToken}'")
                NextToken = response.get('NextToken')
                # if self.debug: print(f"NextToken='{NextToken}'")
                KeyMarker = response.get('NextKeyMarker')
                # if self.debug: print(f"KeyMarker='{KeyMarker}'")
                ContinuationToken = response.get('NextContinuationToken')
                # if self.debug: print(f"ContinuationToken='{ContinuationToken}'")

                if Marker:
                    awsapi_pagination_params = {"Marker": Marker}
                if NextMarker:
                    awsapi_pagination_params = {"Marker": NextMarker}
                elif nextToken:
                    awsapi_pagination_params = {"nextToken": nextToken}
                elif NextToken:
                    awsapi_pagination_params = {"NextToken": NextToken}
                elif KeyMarker:
                    awsapi_pagination_params = {"KeyMarker": KeyMarker}
                elif ContinuationToken:
                    awsapi_pagination_params = {"ContinuationToken": ContinuationToken}
                # else:
                #     break

                if self.debug > 2: print(f"\n\nawsapi_all_params={awsapi_pagination_params}\n")

                if Marker == None and NextMarker == None and nextToken == None and NextToken == None and KeyMarker == None and ContinuationToken == None:
                    break ### duplicate of above 'break'

            # Write the final complete-response as JSON to the file
            with open(str(json_output_filepath), "w") as f:
                json.dump(complete_results, f, indent=4, default=str)

            if self.debug: print(f"Retrieved {len(complete_results)} in total. {CTX} ")
        else:
            # Use the cached response (previously invoked perhaps a few days back)
            with open(str(json_output_filepath)) as f:
                complete_results = json.load(f)
            cnt = len(complete_results)
            print(f"File {json_output_filepath} is present. Context={CTX}.\nSo .. using {cnt} rows of cached AWS-SDK complete_response.. ..\n")

        return complete_results


### EoScript
