### python-script that takes 3 CLI arguments (AWSPROFILE, AWSREGION and CWLogGrpRetentionPeriodInDays).
### Looks at all CW-LogGroups that have Retention set to "Never Expire".
### If the name of the LogGroup contains "-CustomS3AutoDeleteObject-", then it sets the retention to the 3rd CLI argument.

### Re: APIGW's Execution Logs.
### https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html
### 2 types of API logging in CloudWatch: (1) execution logging and (2) access logging.
### In execution logging, API Gateway --FULLY-- manages the CloudWatch Logs.
### This includes creating log groups and log streams, and reporting to the log streams any caller's requests and responses.
### When you deploy an API, API Gateway creates a log group named: `API-Gateway-Execution-Logs_{rest-api-id}/{stage_name}`.


import sys
import boto3
import re

from backend.lambda_layer.bin.generic_aws_cli_script import ( GenericAWSCLIScript )
import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import add_tags, get_cpu_arch_as_str

### ==============================================================================================

CDK_APP_NAME = "CTF"
THIS_SCRIPT_DATA = "stacks"
DEBUG = False

### ==============================================================================================

class LogGrpRetentionSetter(GenericAWSCLIScript):

    def __init__(self,
        appl_name :str,
        aws_profile :str,
        aws_region :str,
        tier :str,
        retention_period_in_days :int,
        purpose :str,
        debug :bool = False,
    ) -> None:
        """ Use boto3 to lookup all Lambda-Layers that belong to this constants.CDK_APP_NAME.
            Then get the description-field of each Lambda-Layer (which should be the HASH for the zip-file inside it)
            Save all these SHA-256 HEX hashes into a file
        """
        super().__init__(
            appl_name=appl_name,
            purpose=purpose,
            aws_profile=aws_profile,
            tier=tier,
            debug=debug,
        )

        # us_east_1_session = boto3.Session(profile_name=aws_profile, region_name="us-east-1")
        # ec2_client = session.client('logs')
        # Validate the value of "aws_region"
        if not re.match(r'^[a-z]{2}-[a-z]+-\d$', aws_region):
            print(f"\n\n❌❌ Invalid AWS region specified as CLI-arg #2: '{aws_region}'")
            sys.exit(1)

        logs_client = self.awsapi_invoker.session.client(service_name='logs', region_name=aws_region)

        # Get the list of log groups
        log_groups = self.awsapi_invoker.invoke_aws_GenericAWSApi_for_complete_response(
            aws_client_type = 'logs',
            api_method_name = "describe_log_groups",
            response_key = 'logGroups',
            json_output_filepath = self.json_output_filepath,
            additional_params={},
            # additional_params={ "StackStatusFilter": ALL_ACTIVE_STACK_STATUSES },
            cache_no_older_than = 1, ### Override the value for 'self.cache_no_older_than' .. as stacks frequently change every-day!
        )
        if self.debug > 1: print(log_groups)

        for log_group in log_groups:
            log_group_name = log_group['logGroupName']
            retention_in_days = log_group.get('retentionInDays', None)
            # print( log_group_name, end=" .. ")

            # Check if the log group has "Never Expire" retention and matches the specified regex
            if retention_in_days is None:
                if (re.search( r'-CustomS3AutoDel?e?t?e?O?b?j?e?c?t?s?C?-[a-zA-Z0-9]+$', log_group_name) or
                    re.search( r'API-Gateway-Execution-Logs_[a-zA-Z0-9]+/[a-zA-Z]+$', log_group_name) or
                    re.search( r'-BucketNotif?i?c?a?t?i?o?n?sH?a?n?d?l?-[a-zA-Z0-9]+$', log_group_name) or
                    re.search( r'-Stateful-AuroraV2-PG-16-RDSAdminCredsRotation$', log_group_name) or
                    re.search(fr'^/aws/lambda/{CDK_APP_NAME}-devops-[0-9a-zA-Z]+-CleanupOrphanResources$', log_group_name) or
                    re.search(fr'^/aws/lambda/{CDK_APP_NAME}-backend-matt-Statefu-LogRe?t?e?n?t?i?o?n?', log_group_name)
                ):
                    print(f"\nSetting retention for log group: {log_group_name} to {retention_period_in_days} days")
                    logs_client.put_retention_policy(
                        logGroupName=log_group_name,
                        retentionInDays=int(retention_period_in_days)
                    )
            else:
                # print(f"\n⚠️⚠️ NOT fixing NeverExpire retention for {log_group_name}")
                if self.debug: print(f"⚠️ {log_group_name}", end=" .. ")

if __name__ == "__main__":

    # log_group_name = f"/aws/lambda/{CDK_APP_NAME}-meta-pipeline-matt-CustomS3AutoDeleteObjectsC-EwjD7kD29eGj"
    # if re.search(r'-CustomS3AutoDel?e?t?e?O?b?j?e?c?t?s?C?-', log_group_name):
    #     print("True")
    # else:
    #     print("False")

    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <AWSPROFILE> <AWSREGION> <CWLogGrpRetentionPeriodInDays>")
        sys.exit(1)

    aws_profile = sys.argv[1]
    aws_region = sys.argv[2]
    retention_period_in_days = sys.argv[3]

    scr = LogGrpRetentionSetter(
        appl_name = constants.CDK_APP_NAME,
        aws_profile = aws_profile,
        aws_region = aws_region,
        tier = "tier-N/A",
        retention_period_in_days = retention_period_in_days,
        purpose = THIS_SCRIPT_DATA,
        debug = DEBUG,
    )

### EoF
