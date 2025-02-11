### Write a lambda function - as per templates from;
###     https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-custom-message.html ..
### which is triggered when a new user self-registers themselves.
### FYI: See also: https://repost.aws/questions/QUuDRIpotdRCOrnTQowtpgQw/customization-of-the-forgot-password-email

import boto3
from botocore.exceptions import ClientError

### To keep this lambda VERY-SIMPLE, avoiding importing anything!  No `constants.py` either!
COGNITO_USER_GROUP="CCDI"

### -------------------------------------------------------------------------

""" Lambda function handler - triggered via Cognito's Custom-Event mechanism.
    The trigger is specifically for: when a new user is CREATED (self-registers).
"""
def lambda_handler(event, context):
    CTX = "within Cognito-Custom-Event lambda-Handler() within file: "+ __file__
    print( "DEBUG: --> "+ CTX )
    print(event)

    # if ( event["triggerSource"] != "CustomMessage_SignUp" ):
    if ( event["triggerSource"] != "PostConfirmation_ConfirmSignUp" ):
        print( "!! INTERNAL-ERROR !! TriggerSource is --NOT-- PostConfirmation_ConfirmSignUp // "+ CTX )
        ### In case of --ANY-- error, the "show must still go on!!!"
        return event

    print( "DEBUG: Confirming TriggerSource = CustomMessage_SignUp // "+ CTX )

    # following code invokes the boto3 api to set the Cognito-Group of this new user to "CCDI" Cognito-Group, and create that Cognito-Group if it does Not exist.

    cognito_client = boto3.client('cognito-idp')

    user_pool_id = event['userPoolId']
    print(f"DEBUG: user_pool_id = '{user_pool_id}' // "+ CTX)

    # Get the username of the -NEW- user from the event object
    username = event['userName']
    print(f"DEBUG: username = '{username}' // "+ CTX)
    user_email = event['request']['userAttributes']['email']
    print(f"DEBUG: user_email = '{user_email}' // "+ CTX)

    create_CCDI_CognitoGroup( user_pool_id=user_pool_id, cognito_group_name=COGNITO_USER_GROUP )

    try:

        print(f"Adding .. new-User '{username}' to Cognito-Group '{COGNITO_USER_GROUP}' // "+ CTX)
        sdk_response = cognito_client.admin_add_user_to_group(
            GroupName=COGNITO_USER_GROUP,
            UserPoolId=user_pool_id,
            Username=username
        )
        print(sdk_response)

        # print(f"Adding .. a new-User '{username}' as a NEW Admin-User // "+ CTX)
        # sdk_response = cognito_client.admin_create_user(
        #     UserPoolId=event['userPoolId'],
        #     Username=event['userName'],
        #     UserAttributes=[ {
        #             "Name": "email",
        #             "Value": user_email
        #     } ]
        # )
        print(sdk_response)
    except ClientError as e:
        print(e)
        ### In case of --ANY-- error, the "show must still go on!!!"

    ### NOTE: We're NOT customizing the email-message here in this Lambda. See the CDK for customization.
    return event

### -------------------------------------------------------------------------
""" Create a Cognit-User-Group, if it does NOT exist, else return quietly. """
def create_CCDI_CognitoGroup( user_pool_id :str,  cognito_group_name :str ):
    CTX = "within Cognito-Custom-Event create_CCDI_CognitoGroup() within file: "+ __file__
    print( "DEBUG: --> "+ CTX )
    print(f"DEBUG: user_pool_id = '{user_pool_id}'")
    print(f"DEBUG: cognito_group_name = '{cognito_group_name}'")

    cognito_client = boto3.client('cognito-idp')
    try:
        # Check if the cognito-group already exists
        response = cognito_client.get_group(
            GroupName  = cognito_group_name,
            UserPoolId = user_pool_id
        )
        print(f"Cognito-Group '{cognito_group_name}' already exists // "+ CTX)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Create the group if it doesn't exist
            response = cognito_client.create_group(
                GroupName  = cognito_group_name,
                UserPoolId = user_pool_id
            )
            print(f"Cognito-Group '{cognito_group_name}' created // "+ CTX)
        else:
            raise e
            ### In case of --ANY-- error, the "show must still go on!!!" .. .. so, lambda-handler above will take care of this exception!

### -------------------------------------------------------------------------
### ---------------- Following is 100% Documentation ONLY -------------------
### -------------------------------------------------------------------------

    ### SAMPLE JSON expected as `event` argument to handler.
    ### NOTE: function then returns the --SAME-- event object -BACK-TO- Amazon-Cognito, with any -CHANGES- in the `response` sub-element below.
    __sample_event_per_aws_documentation = {
        "version": 1,
        "triggerSource": "CustomMessage_SignUp | CustomMessage_ResendCode | CustomMessage_ForgotPassword | CustomMessage_VerifyUserAttribute",
        "region": "<region>",
        "userPoolId": "<userPoolId>",
        "userName": "<userName>",
        "callerContext": {
            "awsSdk": "<calling aws sdk with version>",
            "clientId": "<apps client id>",
                "...": "..."
        },
        "request": {
            "userAttributes": {
                "phone_number_verified": False,
                "email_verified": True,
                "...": "..."
            },
            "codeParameter": "####"
        },
        "response": {
            "smsMessage": "<custom message to be sent in the message with code parameter>",
            "emailMessage": "<custom message to be sent in the message with code parameter>",
            "emailSubject": "<custom email subject>"
        }
    }

    __sample_event_exactly_as_logged = {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_XcQH8l1FU",
        "userName": "sarma.seetamraju",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-unknown-unknown",
            "clientId": "qnv09v4e4gmuiolnq0r92kimo"
        },
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "request": {
            "userAttributes": {
                "sub": "24084418-90a1-70dd-d43a-95624725bc30",
                "email_verified": "true",
                "cognito:user_status": "CONFIRMED",
                "email": "sarma.seetamraju@nih.gov"
            }
        },
        "response": {}
    }

# EoF
