### HOW-TO:
###     AWS_PROFILE={DEVINT | UAT | PROD}
###     Applications/FACTrial-CRRI/delete-ECRRepo-Images-Not-In-Use.py     ${AWS_PROFILE}"
###
### This is a utilityto retrieve information about Lambda functions and ECR repositories, as well as to check if a Lambda function is using an ECR image.
### Finally, it lists ALL the ECR-images -NOT- in use by any Lambda.
### Warning: The image may be in use by ECS, or other AWS-Services.
###
### This Python code is designed to interact with AWS services, specifically AWS Lambda and Amazon Elastic Container Registry (ECR), using the Boto3 library. Here's a summary of the code: [1]
###
### The `get_DEFAULT_ECR_REPOSITORY_NAME()` function generates the default name for an ECR repository based on a provided prefix and AWS account ID.
###
### The `get_all_lambdas()` function retrieves a list of all Lambda functions and their details from the AWS account, using pagination to ensure all functions are obtained.
###
### The `get_all_images_in()` function retrieves a list of all images in a specified ECR repository. It includes a sample response object for reference.
###
### The `check_if_func_uses_ECR_image()` function checks if a given Lambda function uses an ECR image. If it does, it prints the full details of the function configuration. The function returns the full URL to the ECR image if the Lambda function uses one, or None otherwise.
###           It includes a sample response object for a Lambda function using an ECR image and another sample response for a non-ECR Lambda function. [2]



import sys
import boto3
import datetime
import tzlocal
import json

### ----------------------------------------------------------------------

global AWS_ACCOUNT_ID
global AWS_REGION
AWS_ACCOUNT_ID = "NotYetSet!!!"
AWS_REGION     = "us-east-1"

CDK_REPO_UUID_PREFIX = "hnb659fds"

def get_DEFAULT_ECR_REPOSITORY_NAME(
    cdk_repo_uuid_prefix :str,
    aws_account_id :str = None,
) -> str:
    acct = aws_account_id or AWS_ACCOUNT_ID
    return f"cdk-{cdk_repo_uuid_prefix}-container-assets-{acct}-us-east-1"

### ----------------------------------------------------------------------

ECR_REPO_DETAILS_CACHE = {}

### ----------------------------------------------------------------------
def get_all_lambdas(lambda_client, DEBUG :bool) -> list:
    """
    Get all Lambda functions and their details (as JSON objects).
    Paginate and ensure entire list of Lambdas are obtained.
    """

    # Get 1st 50 Lambda functions ONLY.
    # response = lambda_client.list_functions()
    # functions = response['Functions']

    # Get all Lambda functions using pagination
    functions = []
    marker = None
    while True:
        if marker:
            response = lambda_client.list_functions(Marker=marker)
        else:
            response = lambda_client.list_functions()
        if DEBUG:
            print('-'*80);print(f"list-all-functions=")
            print(json.dumps(response, indent=4))
            # json_response = json.loads(response['Payload'].read().decode('utf-8'))
            # print('-'*80);print(json.dumps(json_response, indent=4));print('-'*80)

        functions.extend(response['Functions'])
        print("↓", end="", flush=True)

        if 'NextMarker' in response:
            marker = response['NextMarker']
        else:
            break

    return functions

### ----------------------------------------------------------------------
def get_all_images_in( ecr_client, ecr_repository_name :str, DEBUG :bool ) -> list:
    all_images = ecr_client.describe_images(repositoryName=ecr_repository_name)
    sample_response = {
        "repositories": [
            {
                "repositoryArn": "arn:aws:ecr:us-east-1:123456789012:repository/cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1",
                "registryId": "123456789012",
                "repositoryName": "cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1",
                "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1",
                "createdAt": datetime.datetime(2024, 2, 1, 15, 0, 8, 782000, tzinfo=tzlocal.get_localzone()),
                "imageTagMutability": "IMMUTABLE",
                "imageScanningConfiguration": { "scanOnPush": False },
                "encryptionConfiguration": { "encryptionType": "AES256" }
            },
            # ...
            # ...
            # ...
            # ...
        ],  ### repositories
        "ResponseMetadata": {
            "RequestId": "c59f559a-02cd-4a30-84c5-4d9e763f1a12",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "c59f559a-02cd-4a30-84c5-4d9e763f1a12",
                "date": "Wed, 17 Jul 2024 21:39:02 GMT",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "522",
                "connection": "keep-alive"
            },
            "RetryAttempts": 0
        } ### ResponseMetaData
    }
    if DEBUG:
        print('-'*80);print(f"all_images=")
        ## WARNING: TypeError: Object of type datetime is not JSON serializable
        print(json.dumps(all_images, indent=4, default=str))
        # print(json.dumps(all_images, indent=4))
        # json_response = json.loads(response['Payload'].read().decode('utf-8'))
        # print('-'*80);print(json.dumps(json_response, indent=4));print('-'*80)
    return all_images

### ----------------------------------------------------------------------
def check_if_func_uses_ECR_image(
        lambda_client,
        ecr_client,
        function_name,
        DEBUG :bool) -> str:
    """
    Check if the Lambda function uses an ECR image.
    If YES .. print full details.
    Returns the FULL URL to image, or None.
    """
    # Get the function configuration
    function_config = lambda_client.get_function(FunctionName=function_name)
    if DEBUG:
        print('-'*80);print(f"(boto3-get) function's details=")
        print(json.dumps(function_config, indent=4))
        # json_response = json.loads(function_config['Payload'].read().decode('utf-8'))
        # print('-'*80);print(json.dumps(json_response, indent=4));print('-'*80)

    sample_DockerFunc_response = {
                        "Configuration": {
                            "FunctionName": "FACT-backend-dev-Stateless-apireportLambda{UUID}-{UUID}",
                            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:FACT-backend-dev-Stateless-apireportLambda{UUID}-{UUID}}",
                            "Role": "arn:aws:iam::123456789012:role/FACT-????????????????????-{UUID}",
                            "CodeSize": 0,
                            "Description": "",
                            "Timeout": 900,
                            "MemorySize": 2048,
                            "LastModified": "2024-07-16T15:56:56.478+0000",
                            "CodeSha256": "d2c93aa47838ace30f89989d30c09132c020cdc916c2b7ac630a1d243274284c",
                            "Version": "$LATEST",
                            "VpcConfig": {
                                "SubnetIds": [
                                    "subnet-???????",
                                    "subnet-???????"
                                ],
                                "SecurityGroupIds": [
                                    "sg-???????"
                                ],
                                "VpcId": "vpc-?????????",
                                "Ipv6AllowedForDualStack": False
                            },
                            "Environment": {
                                "Variables": {
                                    "CT_API_URL": "https://clinicaltrialsapi.cancer.gov/v1/clinical-trials",
                                    "CT_API_URL_V2": "https://clinicaltrialsapi.cancer.gov/api/v2/trials",
                                    "CT_API_VERSION": "2"
                                }
                            },
                            "TracingConfig": {
                                "Mode": "Active"
                            },
                            "RevisionId": "9eb72404-b9a0-4bbf-aed8-c209bd7527bf",
                            "State": "Active",
                            "LastUpdateStatus": "Successful",
                            "PackageType": "Image",
                            "Architectures": [
                                "x86_64"
                            ],
                            "EphemeralStorage": {
                                "Size": 512
                            },
                            "SnapStart": {
                                "ApplyOn": "None",
                                "OptimizationStatus": "Off"
                            },
                            "LoggingConfig": {
                                "LogFormat": "Text",
                                "LogGroup": "/aws/lambda/FACT-backend-dev-Stateless-apireportLambda{UUID}-{UUID}"
                            }
                        },
                        "Code": {
                            "RepositoryType": "ECR",
                            "ImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1:0c3245d1cda63a29812fb45d61d33838c0c6233fd543c382c5dafaac74b0cb58",
                            "ResolvedImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1@sha256:d2c93aa47838ace30f89989d30c09132c020cdc916c2b7ac630a1d243274284c"
                        },
                        "Tags": {
                            "aws:cloudformation:stack-name": "FACT-backend-dev-StatelessAPIGW",
                            "aws:cloudformation:stack-id": "arn:aws:cloudformation:us-east-1:123456789012:stack/FACT-backend-............................",
                            "aws:cloudformation:logical-id": "apireportLambda{UUID}"
                        }
                    }

    sample_DockerFunc_response_invalid = {
                        "ResponseMetadata": {
                            "RequestId": "b1ffad73-0f47-4fb6-bfc9-9b1cefbe1f5f",
                            "HTTPStatusCode": 200,
                            "HTTPHeaders": {
                                "date": "Wed, 17 Jul 2024 19:29:42 GMT",
                                "content-type": "application/json",
                                "content-length": "1300",
                                "connection": "keep-alive",
                                "x-amzn-requestid": "b1ffad73-0f47-4fb6-bfc9-9b1cefbe1f5f"
                            },
                            "RetryAttempts": 0
                        },
                        "FunctionName": "frankietest",
                        "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:frankietest",
                        "Role": "arn:aws:iam::123456789012:role/service-role/?????????????????",
                        "CodeSize": 0,
                        "Description": "",
                        "Timeout": 3,
                        "MemorySize": 128,
                        "LastModified": "2023-09-19T20:03:08.000+0000",
                        "CodeSha256": "9f6e1789cfcee8cfc1f2443b35a6e5eb33fcd12ccf30405b8c471109b6a0c991",
                        "Version": "$LATEST",
                        "TracingConfig": { "Mode": "PassThrough" },
                        "RevisionId": "272593f8-74eb-4143-aadf-e58964196a8d",
                        "State": "Inactive",
                        "StateReason": "The function is currently idle.",
                        "StateReasonCode": "Idle",
                        "LastUpdateStatus": "Successful",
                        "PackageType": "Image",
                        "ImageConfigResponse": {
                            "ImageConfig": {
                                "Command": [
                                    "samtools version"
                                ]
                            }
                        },
                        "Architectures": [ "x86_64" ],
                        "EphemeralStorage": { "Size": 512 },
                        "SnapStart": { "ApplyOn": "None", "OptimizationStatus": "Off" },
                        "LoggingConfig": {
                            "LogFormat": "Text",
                            "LogGroup": "/aws/lambda/frankietest"
                        }
                    }


    # image_config = "NotYetSet!!!"

    # Check if the function uses a container image
    try:
        ### Do NOT understand this ImageConfigResponse .!!!
        # if 'ImageConfigResponse' in function_config:
        #     image_config = function_config['ImageConfigResponse']
        #     if 'ImageUri' in image_config:
        #         image_uri = image_config['ImageUri']
        #     else:
        #         print(f"Function '{function_name}' does --NOT-- hvae ImageUri !!")
        #         print(f"function_config='{function_config}'")
        #         print(f"image_config='{image_config}'")
        #         continue

        if 'Code' in function_config:
            func_code_details = function_config['Code']
            if DEBUG:
                RepositoryType=func_code_details['RepositoryType']
                print(f"RepositoryType='{json.dumps(RepositoryType, indent=4)}'")
            if 'ImageUri' in func_code_details:
                image_uri = func_code_details['ImageUri']
            else:
                if DEBUG:
                    print(f"Function '{function_name}' does --NOT-- have ImageUri !!")
                    print("function_config=")
                    print(json.dumps(function_config, indent=4))
                    print(f"func_code_details=")
                    print(json.dumps(func_code_details, indent=4))
                return

            # Parse the ECR repository URI from the image URI
            ecr_repository_uri = image_uri.split('/')[1]
            if DEBUG: print(f"ecr_repository_uri='{ecr_repository_uri}'")
            ecr_repository_name = ecr_repository_uri.split(':')[0]
            if DEBUG: print(f"ecr_repository_name='{ecr_repository_name}'")
            ecr_repository_image_id = ecr_repository_uri.split(':')[1]
            if DEBUG: print(f"ecr_repository_image_id='{ecr_repository_image_id}'")

            # Check if the ECR repository exists
            try:
                if ecr_repository_name != get_DEFAULT_ECR_REPOSITORY_NAME(CDK_REPO_UUID_PREFIX):
                    all_images = get_all_images_in(ecr_client=ecr_client, ecr_repository_name=ecr_repository_name, DEBUG=DEBUG)
                else:
                    all_images = ECR_REPO_DETAILS_CACHE[get_DEFAULT_ECR_REPOSITORY_NAME(CDK_REPO_UUID_PREFIX)]
                for img in all_images['imageDetails']:
                    if DEBUG: print(f"img='{img}'")
                    sample_value = {
                        "imageDetails": [
                            {
                                "registryId": "123456789012",
                                "repositoryName": "cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1",
                                "imageDigest": "sha256:53019dbc2657d8e6dc4741c901b49d29db8c8e7c4b827c3fd652fc96554e3b2d",
                                "imageTags": [
                                    "fb7d886887e5ea473cf2fed3e8d141babec4efc42d5089f15ebcf11884405839"
                                ],
                                "imageSizeInBytes": 471725494,
                                "imagePushedAt": "2024-07-09T20:35:10-04:00",
                                "imageManifestMediaType": "application/vnd.docker.distribution.manifest.v2+json",
                                "artifactMediaType": "application/vnd.docker.container.image.v1+json",
                                "lastRecordedPullTime": "2024-07-09T20:35:15.496000-04:00"
                            },
                            # ..
                            # ..
                            # ..
                            # ..
                        ]
                    }
                    if ecr_repository_image_id in img['imageTags']:
                        print(f"\n🛑🛑🛑 Function '{function_name}' uses container image:\n\t{ecr_repository_image_id}\nfrom ECR repository\n\t{ecr_repository_name}\nFull URL =\n\t{image_uri}")
                        print(img); print("\n")
                        if DEBUG: print(f"ImageTags='{img['imageTags']}'")
                        return image_uri
            except ecr_client.exceptions.RepositoryNotFoundException as e2:
                if DEBUG: print(f"Function '{function_name}' uses a container image, but the ECR repository '{ecr_repository_uri}' does not exist or you don't have access to it.")
                if DEBUG:
                    ANS = input("To abort.. Press Enter to continue...")
                    if not ANS:
                        raise e2
                    else:
                        print("\nContinuing .. ..\n")
                else:
                    return None
        else:
            if DEBUG: print(f"Function '{function_name}' does --NOT-- use a container image.✅")
    except Exception as e:
        print(f"Error WHILE processing the function='{function_name}'")
        print(f"function_config='{function_config}'")
        # print(f"image_config='{image_config}'")
        print(e)
        raise e

    return None

### ----------------------------------------------------------------------
def main():

    # Check if the AWS profile name is provided as a command-line argument
    if len(sys.argv) < 2:
        print(f"Usage:  python3 {sys.argv[0]}    <aws_profile_name>     [--Debug]")
        print(f"Example: python3 {sys.argv[0]}     DEVINT   --debug")
        sys.exit(1)

    DEBUG = False
    if len(sys.argv) == 3:
        DEBUG = (sys.argv[2].lower() == '--debug')
        if DEBUG:
            print("\nDebug mode enabled !!!\n")

    # Get the AWS profile name from the command-line argument
    aws_profile_name = sys.argv[1]
    if DEBUG: print(f"aws_profile_name='{aws_profile_name}'")

    ### ----------------------
    # Set up the AWS session with the provided profile
    session = boto3.Session(profile_name=aws_profile_name)
    # get AWS_ACCOUNT_ID from the session
    global AWS_ACCOUNT_ID
    sts_client = session.client('sts')
    AWS_ACCOUNT_ID = sts_client.get_caller_identity().get('Account')
    print(f"AWS_ACCOUNT_ID='{AWS_ACCOUNT_ID}'")
    print(f"AWS_REGION='{AWS_REGION}'")

    # Create the Lambda and ECR clients
    lambda_client = session.client(service_name='lambda', region_name=AWS_REGION)

    ecr_client = session.client(service_name='ecr', region_name=AWS_REGION)

    ### ----------------------

    default_ecr_repository_name = get_DEFAULT_ECR_REPOSITORY_NAME(aws_account_id=AWS_ACCOUNT_ID, cdk_repo_uuid_prefix=CDK_REPO_UUID_PREFIX)
    input(f"Is this ECR-Repo \033[31m{default_ecr_repository_name}\033[0m correct/accurate? 1-of-2  >>")
    input(f"Is this ECR-Repo \033[31m{default_ecr_repository_name}\033[0m correct/accurate? 2-of-2  >>")
    ### Ask user for input ans store in variable RESP

    ### ----------------------

    all_images = get_all_images_in( ecr_client=ecr_client, ecr_repository_name=default_ecr_repository_name, DEBUG=DEBUG )
    ECR_REPO_DETAILS_CACHE[default_ecr_repository_name] = all_images

    functions = get_all_lambdas(lambda_client=lambda_client, DEBUG=DEBUG)
    functions_using_dockerimages = []
    ecr_image_uri_list = []
    ecr_image_id_list = []
    ### Loop through each Lambda function
    for function in functions:
        function_name = function['FunctionName']
        if DEBUG:
            print(f"{function_name} .. ", end="", flush=True)
        else:
            print(".", end="", flush=True)
        img_uri = check_if_func_uses_ECR_image(lambda_client=lambda_client, ecr_client=ecr_client, function_name=function_name, DEBUG=DEBUG)
        if img_uri:
            functions_using_dockerimages.append(function_name)
            ecr_image_uri_list.append(img_uri)
            image_id = img_uri.split(':')[1]
            ecr_image_id_list.append(image_id)

    # function_name = "FACT-backend-dev-Stateless-apireportLambda9DEC88B6-Y9sVvuZuvJL9"
    # check_if_func_uses_ECR_image(lambda_client=lambda_client, ecr_client=ecr_client, function_name=function_name, DEBUG=DEBUG)

    ### ----------------------
    print("\n\n\n\n")
    print(f"ecr_image_uri_list={ecr_image_uri_list}\n\n")
    for img in ECR_REPO_DETAILS_CACHE[default_ecr_repository_name]:
        if DEBUG: print(f"img='{img}'")
        for img in all_images['imageDetails']:
            if DEBUG: print(f"img='{img}'")
            sample_value = {
                "imageDetails": [
                    {
                        "registryId": "123456789012",
                        "repositoryName": "cdk-cdkUUIDcdk-container-assets-123456789012-us-east-1",
                        "imageDigest": "sha256:53019dbc2657d8e6dc4741c901b49d29db8c8e7c4b827c3fd652fc96554e3b2d",
                        "imageTags": [
                            "fb7d886887e5ea473cf2fed3e8d141babec4efc42d5089f15ebcf11884405839"
                        ],
                        "imageSizeInBytes": 471725494,
                        "imagePushedAt": "2024-07-09T20:35:10-04:00",
                        "imageManifestMediaType": "application/vnd.docker.distribution.manifest.v2+json",
                        "artifactMediaType": "application/vnd.docker.container.image.v1+json",
                        "lastRecordedPullTime": "2024-07-09T20:35:15.496000-04:00"
                    },
                    # ...
                    # ...
                    # ...
                ]
            }
            if DEBUG: print(f"ImageTags='{img['imageTags']}'")
            for img_id in img['imageTags']:
                if DEBUG: print(f"img_id='{img_id}'")
                if img_id in ecr_image_id_list:
                    print(f"\n# ✅ IN USE!!! Container image: '{img_id}' within ECR repository = '{default_ecr_repository_name}'\n")
                else:
                    print(f"aws ecr batch-delete-image --repository-name {default_ecr_repository_name} --image-ids imageTag={img_id}" + " --profile ${AWSPROFILE} --region ${AWSREGION}")

### ----------------------------------------------------------------------
if __name__ == "__main__":
    main()

### EoScript
