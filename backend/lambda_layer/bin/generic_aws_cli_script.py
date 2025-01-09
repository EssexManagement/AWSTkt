### Using this script, to drastically simplify creating a NEW python-tool to interact with AWS-APIs.

import sys
import boto3
import os
import pathlib
import json
import time
import regex
from typing import Sequence
from datetime import datetime, timedelta
import traceback

from .aws_api_invoker import (
    InvokeAWSApi,
    MyException,
)

### Manually configurable constants.

all_tiers = [
    regex.regex.Regex("dev"),
    regex.regex.Regex("test"),
    regex.regex.Regex("uat"),
    regex.regex.Regex("prod"),
    regex.regex.Regex("nccr-[a-z0-9A-Z-]+"),
]
lambdaname_extract_regex = regex.regex.Regex("nccr-[a-z0-9A-Z-]+-stateless-(.*)-[a-z0-9A-Z]+")

aws_managed_policies :list = [
    "arn:aws:iam::aws:policy/ReadOnlyAccess",
    "arn:aws:iam::aws:policy/AWSSupportAccess",
    "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
    "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
]

global__cache_no_older_than = 60

### ----------------------------------------------------------------------
""" 1st param is your application-name (whether an FQDN or simple-string)
    2nd param is typically "iam-roles" "iam-policies" or .. "policies-for-role_abc_xyz"
    3rd param is OPTIONAL, defining how old the "cache" is, before re-invoking AWS-APIs to get latest data from AWS
    4th param is OPTIONAL, default FALSE.  Set it to true, for verbose debug-dumps.
"""
class GenericAWSCLIScript():

    inmemory_cache :dict = {}
    debug = False
    TMPDIR    = '/tmp'

    ### ---------------------------------------------------

    def gen_name_of_json_outp_file(self,
        purpose :str,
        suffix :str = None
    ) -> str:
        if self.aws_profile:
            ### on developer-laptops
            return f"{self.TMPDIR}/{self.aws_profile}-{self.session.region_name}-all-{purpose}{suffix if suffix else ''}.json"
        else:
            ### when running inside GitHub-Actions/Workflows
            return f"{self.TMPDIR}/all-{purpose}{suffix if suffix else ''}.json"

    ### ---------------------------------------------------

    def __init__(self,
        appl_name :str,
        purpose :str,
        _cache_no_older_than :int = global__cache_no_older_than,
        debug :bool = False,
    ):
        if len(sys.argv) < 3:
            print("Usage: python script.py <AWS_PROFILE> <TIER>")
            sys.exit(1)

        self.aws_profile = sys.argv[1]
        self.tier        = sys.argv[2]
        self.appl_name   = appl_name
        self.purpose     = purpose
        self.cache_no_older_than = _cache_no_older_than
        self.debug       = debug

        if self.aws_profile and self.aws_profile.strip().lower() in [ "", "none", "n/a", "undefined" ]:
            self.aws_profile = None

        ### ------------------------------
        ### AWS APIs
        self.awsapi_invoker = InvokeAWSApi(
            aws_profile=self.aws_profile,
            debug=self.debug
        )

        self.session = self.awsapi_invoker.sanity_check_awsprofile()

        self.client = self.session.client('iam')

        ### ------------------------------
        ### Section: Derived variables and constants

        self.json_output_filepath = self.gen_name_of_json_outp_file( purpose )
        self.json_output_filepath = pathlib.Path(self.json_output_filepath) ### convert a string into a Path object.

    ### ----------------------------------------------------------------------
    """ The only parameter is the -NAME- of the CUSTOM-method of the class "InvokeAWSApi" (See file: ./aws_invoker_api.py).
        Assumption: That☝🏾 method takes 2 parameters: (1) json_output_filepath (2) cache_no_older_than
    """
    def load_aws_api_data(self, aws_api_name :str):
        if hasattr(self.awsapi_invoker, aws_api_name):
            dynamic_method_ref = getattr(self.awsapi_invoker, aws_api_name)
            self.inmemory_cache[aws_api_name] = dynamic_method_ref(
                json_output_filepath = self.json_output_filepath,
                aws_profile = self.aws_profile,
                cache_no_older_than = self.cache_no_older_than,
            )
        else:
            raise MyException(f"Error: {aws_api_name} is not a valid Method of InvokeAWSApi custom-class.")

        # print("Loading Cache for DERIVED-Info re: Policies-ASSOCIATED-with-Roles.. ..", end="")
        # iam_Policy_lookup = {}
        # iam_role_associated_inline_policy_lookup = self.awsapi_invoker.load_role_associated_inline_policy_cache(
        #     json_output_filepath=json_output_filepath_RoleAssociatedPolicies,
        # )
        # print(".. Done")


    ### ----------------------------------------------------------------------
    def invalid_code_snippets(self, iamrole_name :str):
        # Get --ALL-- the Policy Statements associated with this IAM-Role
        # Get inline policies
        inline_policies = []
        try:
            if iamrole_name in iam_role_associated_inline_policy_lookup:
                response = iam_role_associated_inline_policy_lookup[iamrole_name]
            else:
                print(f"!!!!!! Policy IN-MEMORY Lookup = None.  Invoking AWS-API list_role_policies() for {iamrole_name} !!!!!!")
                response = self.client.list_role_policies(RoleName=iamrole_name)
                iam_role_associated_inline_policy_lookup[iamrole_name] = response
                # print(response)

            for policy_name in response['PolicyNames']:
                print("!", end="")
                if self.debug: print(f"DEBUG: Role:\t{iamrole_name}\thas a INLINE-Policy: {policy_name}")
                policy_arn = f"arn:aws:iam::{iamrole_name}:policy/{policy_name}"
                if policy_arn in iam_role_associated_inline_policy_lookup:
                    policy_details = iam_role_associated_inline_policy_lookup[policy_arn]
                else:
                    print(f"!!!!!! Policy IN-MEMORY Lookup = None.  Invoking AWS-API get_role_policy() for {policy_arn} !!!!!!")
                    policy = self.client.get_role_policy(RoleName=iamrole_name, PolicyName=policy_name)
                    policy_details = policy['PolicyDocument']
                    iam_role_associated_inline_policy_lookup[policy_arn] = policy_details
                inline_policies.append( policy_details)

        except Exception as e:
            traceback.print_exc()
            print(f"Error getting inline policies: {str(e)}")
            print(f"Error getting inline-associated policies for\t{iamrole_name}")
            time.sleep(2)

    ### -----------------------------------------------------------------------------------------------------------

    """ The only parameter is the -NAME- of the method of the class "InvokeAWSApi" (See file: ./aws_invoker_api.py).
        Assumption: That☝🏾 method takes 2 parameters: (1) json_output_filepath (2) cache_no_older_than
    """
    def save_aws_api_data(self, aws_api_name :str):
        if not hasattr(self.awsapi_invoker, aws_api_name):
            raise MyException(f"Error: {aws_api_name} is not a valid Method of InvokeAWSApi custom-class.")
        if aws_api_name not in self.inmemory_cache:
            raise MyException(f"Error: {aws_api_name} was -NOT- previously loaded into IN-memory-cache using InvokeAWSApi custom-class.")
        # else:
        #     dynamic_method_ref = getattr(self.awsapi_invoker, aws_api_name)
        self.awsapi_invoker.update_diskfile_cache(
            json_output_filepath=self.json_output_filepath,
            inmemory_cache=self.inmemory_cache[aws_api_name],
        )

### EoScript
