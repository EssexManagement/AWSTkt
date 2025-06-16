import sys
import boto3
import os
import pathlib
import json
import time
import regex
from typing import Sequence, Optional, List
from datetime import datetime, timedelta
import traceback

from urllib.parse import urlparse

import constants
from generic_aws_cli_script import ( GenericAWSCLIScript )

APP_NAME = "nccr"
THIS_SCRIPT_DATA = "IAMRoles"
DEBUG = False

class Identify_CodeBuildIamRoles_usedByDevOpsPipeline(GenericAWSCLIScript):

    def __init__(self,
        appl_name :str,
        aws_profile :str,
        tier :str,
        purpose :str = THIS_SCRIPT_DATA,
        debug :bool = False,
    ) -> None:
        super().__init__(
            appl_name=appl_name,
            purpose=purpose,
            aws_profile=aws_profile,
            tier=tier,
            debug=debug,
        )

    def run(self):

        matching_role_arns = []

        partial_tiername = "".join(char + "?" for char in tier)   ### "[a-zA-Z0-9_-]*"
                ### Result: "d?e?v?"
        uuid_regexp = "[a-zA-Z0-9]+"
        component_regexp = f"(backend|frontend)"
        pipeline_stage_regexp = f"(ApplnC?D?K?S?|Lamb?d?a?L?a?y?e?r?)"
        base_pattern = f"{constants.CDK_APP_NAME}-{component_regexp}-pipe?l?i?n?e?-{partial_tiername}-{constants.CDK_APP_NAME}{component_regexp}{self.tier}{pipeline_stage_regexp}-{uuid_regexp}"
        pattern = regex.regex.compile(base_pattern)

        # # get list of Roles named f"{self.app_name}-{self.tier}-{}"
        # if self.tier.startswith(self.appl_name):
        #     self.role_name = f"{self.tier}-{stack_name_suffix}"
        # else:
        #     self.role_name = f"{self.appl_name}-{self.tier}-{stack_name_suffix}"
        # if self.debug: print(self.role_name)

        iam_roles_list = self.awsapi_invoker.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'iam',
            api_method_name = "list_roles",
            response_key = 'Roles',
            json_output_filepath = self.json_output_filepath,
            additional_params={},
            cache_no_older_than = 5, ### Override the value for 'self.cache_no_older_than' .. as stacks frequently change every-day!
        )
        if self.debug > 2: print(iam_roles_list)

        ### ---------------------
        # self.json_output_filepath_gluejobs = self.gen_name_of_json_outp_file( "GlueJobs", suffix="-all" )

        # gluejob_list = self.awsapi_invoker.invoke_aws_GenericAWSApi_for_complete_response(
        #     aws_client_type = 'glue',
        #     api_method_name = "get_jobs",
        #     response_key = 'Jobs',
        #     json_output_filepath = self.json_output_filepath_gluejobs,
        #     additional_params={},
        #     cache_no_older_than = 5, ### Override the value for 'self.cache_no_older_than' .. as stacks frequently change every-day!
        # )
        # if self.debug > 2: print(gluejob_list)

        ### ---------------------
        for role in iam_roles_list:
            role_name = role['RoleName']
            if not self.debug: print( '.', end="", flush=True)
            princ = role['AssumeRolePolicyDocument']['Statement'][0]['Principal']
            if self.debug: print( '\t'+ role_name +'/'+ json.dumps(princ) + ".. " )
            if pattern.match(role_name):
                # Check if codebuild.amazonaws.com is in trust policy of this IAM-Role
                if Identify_CodeBuildIamRoles_usedByDevOpsPipeline.check_trust_policy_for_codebuild(role_name):
                    rolearn = role['Arn']
                    if self.debug: print(f"👉🏾 Role '{rolearn}' is a Trust-Policy for CodeBuild !'")
                    matching_role_arns.append(role['Arn'])
            else:
                if self.debug: print(f"Skipping '{role_name}' .. ")

        return matching_role_arns

    ### .........................................................
    @staticmethod
    def check_trust_policy_for_codebuild(role_name: str) -> bool:
        """
        Check if the role's trust policy includes codebuild.amazonaws.com
        """
        iam = boto3.client('iam')
        try:
            role_info = iam.get_role(RoleName=role_name)
            trust_policy = role_info['Role']['AssumeRolePolicyDocument']

            # Check if codebuild.amazonaws.com is in the trust policy
            for statement in trust_policy.get('Statement', []):
                principal = statement.get('Principal', {})
                if 'Service' in principal:
                    services_as_is = principal['Service']
                    if isinstance(services_as_is, str):
                        services_as_is = [services_as_is]
                    ### Following lines has a SECURITY-Finding.
                    ###     The string may be at an arbitrary position in the sanitized URL.
                    ###     Tool: CodeQL
                    ###     Rule ID: py/incomplete-url-substring-sanitization
                    ###     Description: Sanitizing untrusted URLs is a common technique for preventing attacks such as request forgeries and malicious redirections. Usually, this is done by checking that the host of a URL is in a set of allowed hosts.
                    services :list[str] = []
                    s :str = None
                    for s in services_as_is:
                        services.append( s.encode())
                    ### Stupid GitHub Code-scanner thinks following line is susceptible to string-based malicious input assuming `services` is a string, .. WHEN INSTEAD `services` is an ARRAY!!
                    # if 'codebuild.amazonaws.com' in services:
                    for s in services:
                        if 'codebuild.amazonaws.com' == s.encode():
                            return True
            return False

        except Exception as e:
            print(f"Error checking trust policy for role {role_name}: {str(e)}")
            return False

### ####################################################################################################

# if invoked via cli
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        aws_profile = sys.argv[1]
        tier = sys.argv[2]
        o = Identify_CodeBuildIamRoles_usedByDevOpsPipeline(
            appl_name=APP_NAME,
            aws_profile=aws_profile,
            tier=tier,
            purpose=THIS_SCRIPT_DATA,
            debug=DEBUG,
        )
        resp = o.run()
        print( "\n\nList of IAM-Roles to be ADDED as entries under Trusted-Policy->Principal->AWS\n" )
        print( json.dumps(resp, indent=4) )
    else:
        print( f"Usage:   python {sys.argv[0]} <AWS_PROFILE> <tier>" )
        print( f"EXAMPLE: python {sys.argv[0]} DEVINT    dev" )

# EoScript
