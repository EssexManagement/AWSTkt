### HOW-TO:
###     AWS_PROFILE={DEVINT | UAT | PROD}
###     scripts/invoke-a-Deployed-Lambda.py     ${AWS_PROFILE}   {dev|int|uat|prod}   LambdaFuncName-asPythonStrExpression
### Example usage:
###     python3 scripts/invoke-a-Deployed-Lambda.py     DEVINT   int   FACT-backend-dev-Stateful-Rds-Init-lambda
###     python3 scripts/invoke-a-Deployed-Lambda.py     DEVINT   int   FACT-backend-int-StatelessETL-ncit-lambda
###     python3 scripts/invoke-a-Deployed-Lambda.py     DEVINT   int   FACT-backend-int-StatelessETL-daily-etl-lambda

### This invokes an AWS-Lambda-function (via Boto3).
### You can specify which 𝜆 via 3 CLI-args:
###   1. AWS profile name,
###   2. application environment (dev, int, uat, or prod)
###   3. and the name of the Lambda function to invoke.
###
### The script constructs the full name of the Lambda function by replacing the "{ENV}" placeholder in the function name with the provided application environment.
###
### It retrieves the tags associated with the Lambda function using the list_tags() method of the boto3-Lambda-client.
###
### For debugging-purposes, the script prints the values of specific tags (that will be used to invoke the correct lambda function).
### Finally, it invokes the Lambda function using the invoke() method of the boto3-Lambda-client.

import sys
import boto3
import json
from botocore.config import Config

### ----------------------------------------------------------------------

global AWS_ACCOUNT_ID
global AWS_REGION
AWS_ACCOUNT_ID = "NotYetSet!!!"
AWS_REGION     = "us-east-1"

### ----------------------------------------------------------------------
def main():

    # Check if the AWS profile name is provided as a command-line argument
    if len(sys.argv) < 4:
        print(f"Usage:   python3 {sys.argv[0]}   <aws_profile_name>     (dev|int|uat|prod)   LambdaFuncName-asPythonStrExpression   [--Debug]")
        print(f"Example: python3 {sys.argv[0]}     DEVINT   int     'FACT-backend-"+"{ENV}-Stateful-Rds-Init-lambda'")
        print(f"Example: python3 {sys.argv[0]}     DEVINT   int     'FACT-backend-"+"{ENV}-StatelessETL-ncit-lambda'")
        print(f"Example: python3 {sys.argv[0]}     DEVINT   int     'FACT-backend-"+"{ENV}-StatelessETL-daily-etl-lambda'")
        sys.exit(1)

    DEBUG = False
    if len(sys.argv) == 5:
        DEBUG = (sys.argv[4].lower() == '--debug')
        if DEBUG:
            print("\nDebug mode enabled !!!\n")

    # Get the AWS profile name from the command-line argument
    aws_profile_name = sys.argv[1]
    application_env  = sys.argv[2]
    function_name    = sys.argv[3]

    if DEBUG: print(f"aws_profile_name='{aws_profile_name}'")
    if DEBUG: print(f"application_env='{application_env}'")
    if DEBUG: print(f"function_name (as-provided)='{function_name}'")

    function_name = function_name.replace("{ENV}", application_env)
    print(f"function_name (final)='{function_name}'")

    ### ----------------------
    # Create a custom configuration with increased read timeout
    config = Config(read_timeout=900)  # Timeout in seconds.  Max-RUNTIME for Lambda is 15-minutes.

    # Set up the AWS session with the provided profile
    session = boto3.Session(profile_name=aws_profile_name)
    # get AWS_ACCOUNT_ID from the session
    global AWS_ACCOUNT_ID
    sts_client = session.client('sts')
    AWS_ACCOUNT_ID = sts_client.get_caller_identity().get('Account')
    print(f"AWS_ACCOUNT_ID='{AWS_ACCOUNT_ID}'")
    print(f"AWS_REGION='{AWS_REGION}'")

    # Create the Lambda and ECR clients
    lambda_client = session.client(service_name='lambda', region_name=AWS_REGION, config=config)

    ### ----------------------
    # Get the tags for the Lambda function
    lambda_arn = f"arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT_ID}:function:{function_name}"
    if DEBUG: print(f"lambda_arn='{lambda_arn}'")
    response = lambda_client.list_tags(Resource=lambda_arn)
    if DEBUG:
        print('-'*80);print(json.dumps(response, indent=4));print('-'*80)

    # Extract the tags from the response
    tags = response['Tags']
    if DEBUG: print(json.dumps(tags, indent=4));print('-'*80);

    # Print the values of the desired tags
    stkname = 'UNDEFINED'
    stkRsrcId = 'UNDEFINED'
    for tag_key in tags:
        if DEBUG: print(json.dumps(tag_key, indent=4))
        if tag_key == 'aws:cloudformation:stack-name':
            stkname = tags[tag_key]
            if DEBUG: print(f"cloudformation_stack-name: {stkname}")
        elif tag_key == 'aws:cloudformation:logical-id':
            stkRsrcId = tags[tag_key]
            if DEBUG: print(f"cloudformation_stack:logical-resource-id: {stkRsrcId}")
    print(f"sam remote invoke --stack-name {stkname} {stkRsrcId} --event"+"  '{}'  "+f"--profile {aws_profile_name} --region {AWS_REGION}")

    # Invoke the Lambda function
    print(f"Invoking Lambda function: {function_name} .. ..")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=b'{"Dummykey": "DummyValue"}'  # Payload for the Lambda function
    )
    if DEBUG:
        print('-'*80);print(response)
    json_response = json.loads(response['Payload'].read().decode('utf-8'))
    print('-'*80);print(json.dumps(json_response, indent=4));print('-'*80);
    print(f"✅ Lambda function {function_name} invoked successfully.")

### ----------------------------------------------------------------------
if __name__ == "__main__":
    main()

### EoScript
