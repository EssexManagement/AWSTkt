"""
    BACKGROUND:
        CloudFront reads a Secrets-Manager Secret, to get the value of a HTTP-Header-Token, that needs to be passed on to its 2nd-origin (APIGW).
        The Regional-WAF in front of the APIGW, will ALLOW ONLY traffic that has that header.  This Token-matching is expected to be equivalent to a plain string-match.
        Per security best-practices, any Token (in this case, the HTTP-Header-Token) must be rotated periodically.
        Per AWS practices, such rotation of CUSTOM tokens is done using a Lambda.

    This Lambda will be passed 3 environment variables:
        1. ARN to Secrets-Manager Secret
        2. CloudFront Distribution ID
        3. Regional-WAF-ACL ARN
        4. Regional-WAF-ACL's Rule's name (Example: `x-origin-verify`)
        5. (Optional / Unused currently) APIGW's Stage-ID
    This Lambda will:-
        A. rotate the secret's simple text-value (ensure all characters are valid for a HTTP-Header-Token) and get the new value of the secret.
        B. Invoke boto3-CloudFront APIs to update the value of HTTP-header-token that CloudFront passes to APIGW/Regional-WAF.
            i.  Use a Global-constant/flag (in this file) to determine whether code will WAIT for the CloudFront-Distribution to be re-deployed.
        C. Invoke boto3-WAF APIs to update the WAF-ACL's Rule to check for the updated value.

    List out all the permissions that this Lambda will need, like:
        secretsmanager:PutSecretValue
        cloudfront:GetDistributionConfig
        cloudfront:UpdateDistribution
        wafv2:GetWebACL
        wafv2:UpdateWebACL

    OPEN QUESTIONS:
        ii. Correct me, but there's -NO- benefit to ~~WAITING~~ for the CloudFront-distribution to FINISH redeploying, as the website is expected to be down for that period.
        iii. So, what would be the suitable time-out for this lambda?
"""

from typing import Optional
import boto3
import json
import os
import traceback

import constants

# def generate_header_token(length=48):
#     """Generate a random token suitable for HTTP headers"""
#     # Using only alphanumeric characters to ensure HTTP header compatibility
#     chars = string.ascii_letters + string.digits
#     return ''.join(random.choice(chars) for _ in range(length))

def generate_header_token(length=48):
    secrets_client = boto3.client('secretsmanager')
    response = secrets_client.get_random_password(
        PasswordLength=length,
        ExcludeCharacters='!@#$%^&*()+={}[]|\\:;"\'<>?,/',
        ExcludePunctuation=False,
        IncludeSpace=False,
        RequireEachIncludedType=True
    )
    return response['RandomPassword']

# def update_secret(secret_arn, new_token):
#     """Update the secret in Secrets Manager"""
#     secrets = boto3.client('secretsmanager')
#     print(f"ABOUT TO Update secret: '{secret_arn}'")

#     try:
#         secrets.put_secret_value(
#             SecretId=secret_arn,
#             SecretString=new_token
#         )
#         print(f"Successfully Updated secret!")
#     except Exception as e:
#         print(traceback.print_exc())
#         print(f"\n\nError updating secret: {str(e)}")
#         if hasattr(e, 'response'):
#             print(f"Error's response: {json.dumps(e.response, indent=4, default=str)}")
#         print(f"\n\nError(Full): " )
#         print( json.dumps(e, indent=4, default=str) )
#         raise

def _dist_filter(dist, tier :Optional[str]) -> bool:
    """ Used ONLY within get_all_cloudfront_distribution_ids() """

    ### For debugging purposes, 1st check the distribution's comment/description field.
    print( f"checking if cloudfront-DISTRIBUTION's 'comment/description' FIELD has value == '{tier}' .. ..")
    retval = False
    if tier and dist and 'Comment' in dist:
        dc :str = dist['Comment']
        print( f"dist['Comment'] = '{dc}'" )
        retval = (dc.startswith(f"{constants.CDK_APP_NAME}-{tier} = "));
        print( f"Good. Using just the comment/description property of CloudFRONT, we found the correct Distribution!")
    else:
        print( f"dist['Comment'] is MISSING⚠️⚠️ for CloudFRONT's distribution!!!" )

    # if retval:
    #     return retval
    ### Even if the above check succeeded, the real-test is in the Tags associated with the CloudFront-distribution.

    print(f"checking if cloudfront-DISTRIBUTION has a Tag called 'application' with value == '{constants.CDK_APP_NAME}' .. ..")
    if dist and 'Tags' in dist:
        application_value = None
        tier_value = None

        # Iterate through the tags to find 'application' and 'tier' tags
        for tag in dist['Tags']:
            if tag.get('Key') == 'application':
                application_value = tag.get('Value')
            elif tag.get('Key') == 'tier':
                tier_value = tag.get('Value')

        # Check if we found both tags with the expected values
        if application_value and tier_value:
            # print(f"DEBUG: Found tag 'application' with value '{application_value}'")
            # print(f"DEBUG: Found tag 'tier' with value '{tier_value}'")
            retval = (application_value == constants.CDK_APP_NAME and tier_value == tier)
            if retval:
                return retval  # <------ Found the right distribution, return immediately
        else:
            print( f"dist['Tags']['application'] is MISSING⚠️⚠️ for CloudFRONT's distribution!!!" )
    return retval  ### 99.9% likely that .. this is whatever `comment/description` field-check above came up with !!!

def get_all_cloudfront_distribution_ids( tier :Optional[str] ) -> list[str]:
    """ Given a tier, get all the distributions for that tier.
        if tier is None, get everysingle distribution_id
    """
    # distribution_id = os.environ['CLOUDFRONT_DISTRIBUTION_ID']
    ### Use boto3 to get list of all distributions & filter/pick all the distributions that have "Comment" field set to the value of variable `tier`
    cloudfront_client = boto3.client('cloudfront')
    ### 1st get all distributions.
    ### Next, get the Tags for each one of them
    ### Finally, utilizing Tags, filter for relevant distributions.
    distributions = cloudfront_client.list_distributions()
    for dist in distributions['DistributionList']['Items']:
        print( f"Getting tags for CloudFront-Distribution ARN='{dist['ARN']}'")
        ### https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront/client/list_tags_for_resource.html
        tags_response = cloudfront_client.list_tags_for_resource( Resource=dist['ARN'] )
        dist['Tags'] = tags_response.get('Tags', {}).get('Items', [])

    if not tier:
        print(f"WARNING: No tier passed as parm to get_all_cloudfront_distribution_ids(), so getting all distributions. WIthin: ", __file__)

    # relevant_distributions = (dist for dist in distributions['DistributionList']['Items'] if _dist_filter(dist,tier) )
    # relevant_distribution_ids :list[str] = [distribution['Id'] for distribution in relevant_distributions]
    relevant_distribution_ids = [dist['Id'] for dist in distributions['DistributionList']['Items'] if _dist_filter(dist,tier)]

    print(f"Found {len(relevant_distribution_ids)} relevant distributions")
    print( json.dumps(relevant_distribution_ids, indent=4, default=str) )
    return relevant_distribution_ids


def validate_distribution_config(config):
    required_fields = ['CallerReference', 'Origins', 'DefaultCacheBehavior', 'Comment', 'Enabled']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    if 'Items' not in config['Origins']:
        raise ValueError("Origins must contain 'Items' array")
    if not config['Origins']['Items']:
        raise ValueError("Origins 'Items' array cannot be empty")
    print("Successfully completed validate_distribution_config()")



def update_cloudfront_function(distribution_id, new_token):
    """Update CloudFront configuration with new header token"""
    cloudfront_client = boto3.client('cloudfront')
    new_http_header_name = 'x-origin-verify'

    try:
        # Get current distribution config
        print(f"ABOUT TO Update Header-Token for CloudFront distribution {distribution_id}...")
        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        ### REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront/client/get_distribution_config.html
        etag = response['ETag']
        print(f"ETag='{etag}'")
        ### Deep-Clone the response, as we need to pass it to another AWS-API-call.
        config_json = json.dumps(response['DistributionConfig'], indent=4, default=str)
        config = json.loads(config_json)

        # Update the origin custom header
        for origin in config['Origins']['Items']:
            if 'CustomHeaders' in origin and 'Items' in origin['CustomHeaders']:
                for header in origin['CustomHeaders']['Items']:
                    if header['HeaderName'] == new_http_header_name:
                        header['HeaderValue'] = new_token

        validate_distribution_config(config) ### Towards better insight into WHY update() occasionally fails.

        # Update the distribution: REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront/client/update_distribution.html
        cloudfront_client.update_distribution(
            Id=distribution_id,
            IfMatch=etag,
            DistributionConfig=config
        )
        print("Updated Distribution successfully.")

        # Wait for distribution to be deployed
        # print("Now, Waiting for CloudFront distribution to be deployed...")
        # waiter = cloudfront_client.get_waiter('distribution_deployed')
        # waiter.wait(Id=distribution_id)

    except Exception as e:
        print(traceback.print_exc())
        print(f"\n\nError updating CloudFront: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Error's response: {json.dumps(e.response, indent=4, default=str)}")
        print(f"\n\nError(Full): " )
        print( json.dumps(e, indent=4, default=str) )
        raise




def update_waf_rule(waf_acl_arn, waf_rule_name, new_token):
    """Update WAF rule with new header token"""
    wafv2 = boto3.client('wafv2')
    print(f"ABOUT TO Update Header-Token for WAF rule '{waf_rule_name}' // '{waf_acl_arn}'...")

    try:
        # Get current WAF ACL
        new_http_header_name = 'x-origin-verify'
        WafAclName=waf_acl_arn.split('/')[-2]
        WafAclId=waf_acl_arn.split('/')[-1]
        print(f"DEBUG: about to invoke wafv2.get_web_acl( Name='{WafAclName}', Id='{WafAclId}' ) .. ")
        response = wafv2.get_web_acl(
            Name=WafAclName,
            Scope='REGIONAL',
            Id=WafAclId,
        )
        if 'WebACL' not in response:
            print(f"Error:❌❌❌ No 'WebACL' key found in response from wafv2.get_web_acl( name='{WafAclName}', id='{WafAclId}' )")
            return

        # Find and update the specific rule
        rules = response['WebACL']['Rules']

        rule_num = 0
        found_rule = False
        for rule in rules:
            rule_num += 1
            print( f"Rule # {rule_num} = ", end="" )
            print( "'"+ rule['Name'] +"'" )
            if rule['Name'] == waf_rule_name:
                print( f"found WAF-Rule named '{waf_rule_name}' .." )
                # if 'Statement' in rule and 'NotStatement' in rule['Statement']:
                #     print( "Found NotStatement within above WAF-Rule.  So, assuming there's JUST ONE WAF-Rule w/ a NotStatement!!!!")
                #     stmt = rule['Statement']['NotStatement']
                #     print( "Completed parsing our variable `stmt` ..")
                if True:
                        stmt = rule['Statement']
                    # if 'Statement' in stmt:
                    #     stmt = stmt['Statement']
                    #     print( "located the `Statement` UNDER `NotStatement`" )
                        if 'ByteMatchStatement' in stmt:
                            print( f" ByteMatchStatement WITHIN the WAF-Rule .." )
                            stmt['ByteMatchStatement']['SearchString'] = new_token
                            found_rule = True

                # for statement in rule['Statement'].get('NotStatement', {}).get('Statement', []):
                #     if 'ByteMatchStatement' in statement:
                #         statement['ByteMatchStatement']['SearchString'] = new_token

        if not found_rule:
            print("WAF rule not found - creating new rule for 1st time ever (for this AWS-Account)...")
            new_rule = {
                'Name': waf_rule_name,
                'Priority': 2, ### Adjust priority as needed based on other rules
                'Action': {
                    'Block': {}
                },
                'Statement': {
                    'NotStatement': {
                        'Statement': {
                            'ByteMatchStatement': {
                                'FieldToMatch': {
                                    'SingleHeader': { 'Name': new_http_header_name }
                                },
                                'PositionalConstraint': 'EXACTLY',
                                'SearchString': new_token,
                                'TextTransformations': [{
                                        'Priority': 0, ### Set priority to 0 as it's the only transformation (in this Rule)
                                        'Type': 'NONE'
                                }]
                            }
                        }
                    }
                },
                ### FYI only: `OverrideAction` is ONLY used for `ManagedRuleGroups`
                'VisibilityConfig': {
                    'SampledRequestsEnabled': True,
                    'CloudWatchMetricsEnabled': True,
                    'MetricName': 'XOriginVerifyHeaderRule'
                }
            }

            # Append the new rule to the rules list
            rules.append(new_rule)
            print(f"Added --NEW-- rule '{waf_rule_name}' to WAF-ACL at {waf_acl_arn}")

        print( f"Successfully updated JSON -- to base passed into update_waf_rule()" )
        # Description :str = response['WebACL']['Description'] if 'Description' in response['WebACL'] else None
        # Description = None if Description.strip() == "" else Description
        Description = "CBIIT-Managed WAF-ACL enhanced by NCCR-project-team"
        DefaultVisibilityConfig={
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': 'AllBlockedAllowedCounted-' + response['WebACL']['Name'], ### Sum of all Rules in the ACL
        }

        # Update WAF ACL
        ### Sample Implementation: https://github.com/aws-samples/amazon-cloudfront-waf-secretsmanager/blob/master/lambda/lambda_function.py
        ### boto3 REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/wafv2/client/update_web_acl.html
        ### API REF: https://docs.aws.amazon.com/waf/latest/APIReference/API_UpdateWebACL.html
        wafv2.update_web_acl(
            Name=response['WebACL']['Name'],
            Id=response['WebACL']['Id'],
            # Id=waf_acl_arn.split('/')[-2],
            Scope='REGIONAL',
            Description=Description if Description else None,
            DefaultAction=response['WebACL']['DefaultAction'],
            Rules=rules,
            LockToken=response['LockToken'],
            VisibilityConfig=response['WebACL']['VisibilityConfig'] if 'VisibilityConfig' in response['WebACL'] else DefaultVisibilityConfig,

        )
        print("WAF rule updated successfully.")

    except Exception as e:
        print(traceback.print_exc())
        print(f"\n\nError updating WAF: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Error's response: {json.dumps(e.response, indent=4, default=str)}")
        print(f"\n\nError(Full): " )
        print( json.dumps(e, indent=4, default=str) )
        raise










def lambda_handler(event, context):
    # Get environment variables
    tier = os.environ['TIER']
    # secret_arn = os.environ['SECRET_ARN']
    waf_acl_arn = os.environ['WAF_ACL_ARN']
    waf_rule_name = os.environ['WAF_RULE_NAME']

    try:
        # Generate new token
        new_token = generate_header_token()

        # Update secret first
        # update_secret(secret_arn, new_token)

        # Get all relevant distribution IDs (for the specific tier, if tier is Not None, else get all distribution-ids)
        relevant_distribution_ids = get_all_cloudfront_distribution_ids(tier)

        for distribution_id in relevant_distribution_ids:
            # Update CloudFront configuration
            update_cloudfront_function(distribution_id, new_token)

        # Update WAF rule
        update_waf_rule(waf_acl_arn, waf_rule_name, new_token)

        return {
            'statusCode': 200,
            'body': json.dumps('Token rotation completed successfully')
        }

    except Exception as e:
        print(traceback.print_exc())
        print(f"\n\nError during token rotation: {str(e)}")
        print(f"\n\nError(Full): " )
        print( json.dumps(e, indent=4, default=str) )
        if hasattr(e, 'response'):
            print(f"\n\nError-Response(Full): " )
            print( json.dumps(e.response, indent=4, default=str) )
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error during token rotation: {str(e)}')
        }

### EoF
