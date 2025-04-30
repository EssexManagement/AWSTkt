from typing import Optional, Tuple, Union
import json
import pytz
import re
import boto3

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_codestarconnections,
    aws_iam,
    aws_secretsmanager,
    SecretValue,
)
from constructs import Construct

import constants

### ---------------------------------------------------------------------------------

from enum import Enum, auto, unique

@unique
class AwsServiceNamesForKmsKeys(Enum):
    """ Enumerated values for AWS Service Names -- to be used as LOOKUP json-key within cdk.json.
        See: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    """
    cloudfront = (auto(),)
    codebuild = (auto(),)
    codepipeline = (auto(),)
    cognito = (auto(),)
    dynamodb = (auto(),)
    ecr = (auto(),)
    elasticbeanstalk = (auto(),)
    elasticfilesystem = (auto(),)
    elasticloadbalancing = (auto(),)
    es = (auto(),)
    events = (auto(),)
    firehose = (auto(),)
    glue = (auto(),)
    iam = (auto(),)
    kms = (auto(),)
    # lambda = (auto(),)   ??? some wierd compiler error.  Perhaps `lambda` is a keyword/variable somewhere????
    logs = (auto(),)
    maven = (auto(),)
    pinpoint = (auto(),)
    quicksight = (auto(),)
    rds = (auto(),)
    redshift = (auto(),)
    s3 = (auto(),)
    secretsmanager = (auto(),)
    servicecatalog = (auto(),)
    sns = (auto(),)
    sqs = (auto(),)
    ssm = (auto(),)
    stepfunctions = (auto(),)
    sts = (auto(),)
    waf = (auto(),)
    wafv2 = (auto(),)


### ---------------------------------------------------------------------------------

def lkp_waf_acl_for_cloudFront(
    cdk_context,
    effective_tier :str,
) -> str:
    """ Lookup ARN for WAF-ACL to be associated with CloudFRONT.
        Assumes following structure in `cdk.json`

        "security": {
            "WAF-ACL": {
                "global": {
                    "dev": "arn:aws:wafv2:xx-abcd-1:123456789012:global/webacl/.. ..",
    """
    return _lkp_waf_acl_for_aws_resource(
        cdk_context = cdk_context,
        effective_tier = effective_tier,
        lkp_key = "global",
    )
    # security_config = cdk_context.node.try_get_context("security")
    # # print(f"security_config = {security_config}")
    # if security_config and "WAF-ACL" in security_config:
    #     web_acl_json = security_config["WAF-ACL"]
    # else:
    #     web_acl_json = None
    # print( f"DEBUG: web_acl_json = '{web_acl_json}'")

    # if web_acl_json and "global" in web_acl_json:
    #     web_acl_json = web_acl_json["global"]
    # else:
    #     web_acl_json = None

    # if web_acl_json and effective_tier in web_acl_json:
    #     web_acl_arn = web_acl_json[effective_tier]
    #     if web_acl_arn == "None" or web_acl_arn == "":
    #         web_acl_arn = None
    # else:
    #     web_acl_arn = None
    # return web_acl_arn

### -----------------------

def lkp_waf_acl_for_apigw(
    cdk_context,
    effective_tier :str,
) -> str:
    """ Lookup ARN for WAF-ACL to be associated with APIGW.
        Assumes following structure in `cdk.json`

        "security": {
            "WAF-ACL": {
                "regional": {
                    "dev": "arn:aws:wafv2:xx-abcd-1:123456789012:regional/webacl/.. ..",
                },
                "APIGW-WAF-ACLs": {
                    "dev": "None",
                    "int": "regional",
                    "uat": "regional",
                    "prod": "regional"
    """
    return _lkp_waf_acl_for_aws_resource(
        cdk_context = cdk_context,
        effective_tier = effective_tier,
        lkp_key = "regional",
    )

### -----------------------

def lkp_waf_acl_for_cognito(
    cdk_context,
    effective_tier :str,
) -> str:
    """ Lookup ARN for WAF-ACL to be associated with COGNITO USER-POOL.
        Assumes following structure in `cdk.json`

        "security": {
            "WAF-ACL": {
                "regional": {
                    "dev": "arn:aws:wafv2:xx-abcd-1:123456789012:regional/webacl/.. ..",
                },
                "Cognito-WAF-ACLs": {
                    "dev": "None",
                    "int": "regional",
                    "uat": "regional",
                    "prod": "regional"
    """
    return _lkp_waf_acl_for_aws_resource(
        cdk_context = cdk_context,
        effective_tier = effective_tier,
        lkp_key = "Cognito-WAF-ACLs",
    )

### -----------------------

def _lkp_waf_acl_for_aws_resource(
    cdk_context,
    effective_tier :str,
    lkp_key :str,
) -> str:
    security_config = cdk_context.node.try_get_context("security")
    # print(f"security_config = {security_config}")
    if security_config and "WAF-ACL" in security_config:
        web_acl_json = security_config["WAF-ACL"]
    else:
        web_acl_json = None
    print( f"DEBUG: web_acl_json = '{web_acl_json}'")

    # if web_acl_json and "regional" in web_acl_json:
    #     web_acl_regional_json = web_acl_json["regional"]
    # else:
    #     web_acl_regional_json = None
    if web_acl_json and lkp_key in web_acl_json:
        web_acl_json          = web_acl_json[ lkp_key ]
    else:
        web_acl_json = None

    if web_acl_json and effective_tier in web_acl_json:
        web_acl_arn = web_acl_json[effective_tier]
        if web_acl_arn == "None" or web_acl_arn == "":
            web_acl_arn = None
    else:
        web_acl_arn = None
    return web_acl_arn

### ---------------------------------------------------------------------------------
### .................................................................................
### ---------------------------------------------------------------------------------

def lkp_cdk_json_for_VPCEndPts(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
) -> list[str]:
    """ Looks up `cdk.json` file and .. .. returns the VPCEndPoint-ARN :str
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str

        return array-of-str (or None)
    """

    stk = Stack.of(cdk_scope)

### ---------------------------------------------------------------------------------

already_printed_debug_output_1 = False

@staticmethod
def get_cdk_json_vpc_details(
    scope :Construct,
    aws_env :str,
    tier :str,
) -> tuple[  dict[str,dict[str, Union[str,list[dict[str,str]]]]],     dict[str, Union[str,list[dict[str,str]]]] ]:
    """
        Reads cdk.json context, and Returns the following as a tuple:
            1. acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]]
            2. vpc_details_for_tier  :dict[str, Union[str,list[dict[str,str]]]]
    """
    vpc_ctx :any = scope.node.try_get_context("vpc")
    acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
    vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
    global already_printed_debug_output_1;
    if not already_printed_debug_output_1:
        print( "vpc_ctx..............................")
        print( json.dumps(vpc_ctx, indent=4, default=str) )

    if vpc_ctx and aws_env in vpc_ctx:
        acct_wide_vpc_details = vpc_ctx[ aws_env ]
    else:
        raise ValueError(f"cdk.json file is MISSING the JSON-details for aws_env=`{aws_env} (under `vpc`) /// FYI: tier='{tier}'.")
    if not already_printed_debug_output_1:
        print( f"acct_wide_vpc_details aws_env={aws_env}..............................")
        print( json.dumps(acct_wide_vpc_details, indent=4, default=str) )
        already_printed_debug_output_1 = True

    if acct_wide_vpc_details and tier in acct_wide_vpc_details:
        vpc_details_for_tier = acct_wide_vpc_details[tier]
    elif tier is None or tier in [ constants.ACCT_NONPROD, constants.ACCT_PROD ]:
        vpc_details_for_tier = None
    else:
        raise ValueError(f"cdk.json file is MISSING the JSON-details for tier=`{tier}` (under `vpc.{aws_env}`) /// FYI: tier='{tier}'.")

    print( f"vpc_details_for_tier for tier={tier}..............................")
    print( json.dumps(vpc_details_for_tier, indent=4, default=str) )

    return [ acct_wide_vpc_details, vpc_details_for_tier ]

### ..........................................................................................

@staticmethod
def get_list_of_azs(
        tier :str,
        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]],
) -> list[str]:
    """
        Returns the list of AZs as specified under the "subnets" in `cdk.json` file.
        Use this IMMEDIATELY AFTER invoking
    """
    if not vpc_details_for_tier:
        raise ValueError(f"vpc_details_for_tier is None")
    list_of_azs :list[str] = []
    if not "subnets" in vpc_details_for_tier:
        raise ValueError(f"vpc_details_for_tier '{tier}' is missing 'subnets' json-element")
    else:
        atleast_one_az_found = False
        for subnet_details in vpc_details_for_tier["subnets"]:
            if "az" in subnet_details:
                list_of_azs.append(subnet_details["az"])
                atleast_one_az_found = True
        if not atleast_one_az_found:
            raise ValueError(f"vpc_details_for_tier '{tier}' is missing 'az' json-element under 'subnets' array-of-elements")

    print( f"list_of_azs = '{list_of_azs}'" )
    return list_of_azs

### ==========================================================================================
### ..........................................................................................
### ==========================================================================================

one_time_debug_output_completed_2 :bool = False

def lkp_cdk_json_for_kms_key(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    aws_rsrc_type :AwsServiceNamesForKmsKeys,
) -> str:
    """ Looks up `cdk.json` file and .. .. returns the KMS-Key-ARN :str
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str
        Parameter #4 - one of the following values: "cwlogs" "s3" "dynamodb"

        return ARN (or None)
    """

    stk = Stack.of(cdk_scope)
    effective_tier = tier if (tier in constants.STD_TIERS or tier in constants.ACCT_TIERS) else "dev"

    cdk_json_security_config :any = cdk_scope.node.try_get_context("security")
    global one_time_debug_output_completed_2
    if not one_time_debug_output_completed_2:
        print("cdk.json's Git-SourceCode configuration JSON is:")
        print( json.dumps(cdk_json_security_config, indent=4) )
        one_time_debug_output_completed_2 = True

    kms_key_arn = None
    default_kms_key_arn = None
    if cdk_json_security_config and "kms" in cdk_json_security_config:
        kms_key_config = cdk_json_security_config["kms"]
        # print( json.dumps(kms_key_config, indent=4) )
        ### 1st look up any DEFAULT KMS-key (for use by --ALL-- AWS-Services.)
        if "default" in kms_key_config and effective_tier in kms_key_config["default"]:
            default_kms_key_arn = kms_key_config["default"][effective_tier]
        ### Next look up any KMS-key for use by --SPECIFIC-- AWS-Service
        if aws_rsrc_type.name in kms_key_config and effective_tier in kms_key_config[aws_rsrc_type.name]:
            kms_key_arn = kms_key_config[aws_rsrc_type.name][effective_tier]
        ### If no relevant AWS-specific KMS-Key found, use default KMS-Key
        if not kms_key_arn:
            kms_key_arn = default_kms_key_arn

    print( f"kms_key (pre)ARN for '{aws_rsrc_type.name}' = '{kms_key_arn}' within "+ __file__ )
    if kms_key_arn:
        kms_key_arn = kms_key_arn.format(stk.region, stk.account)
    print( f"kms_key ARN for '{aws_rsrc_type.name}' = '{kms_key_arn}' within "+ __file__ )

    return kms_key_arn

### ---------------------------------------------------------------------------------
### .................................................................................
### ---------------------------------------------------------------------------------

one_time_debug_output_completed_1 :bool = False

def lkp_cdk_json(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
) -> Tuple[str,str, str, str]:
    """ About Source-code.
        Looks up `cdk.json` file and returns in the following ORDER:
        1. git_src_code_config :str
        2. gitTokenRef :str
        3. git_commit_hash :str
        4. pipeline_source_gitbranch :str
    """

    git_src_code_config :any = cdk_scope.node.try_get_context("git-source")
    global one_time_debug_output_completed_1
    if not one_time_debug_output_completed_1:
        print("cdk.json's Git-SourceCode configuration JSON is:")
        print( json.dumps(git_src_code_config, indent=4) )

    gitTokenRef = git_src_code_config["git_token_ref"]
    print( f"gitTokenRef = '{gitTokenRef}' within lkp_cdk_json() within "+ __file__ )
    # gitTokenRefARN :str = git_src_code_config["git_token_ref_arn"]
    # print( f"gitTokenRefARN = '{gitTokenRefARN}' within "+ __file__ )
    # gitTokenRefARN = gitTokenRefARN.format( stk.region, stk.account )
    # print( f"gitTokenRefARN = '{gitTokenRefARN}' within "+ __file__ )

    git_commit_hashes = git_src_code_config["git_commit_hashes"]
    if not one_time_debug_output_completed_1:
        print( json.dumps( git_commit_hashes, indent=4 ) )
        one_time_debug_output_completed_1 = True
    if tier in constants.STD_TIERS or tier in constants.ACCT_TIERS:
        git_commit_hash :str = git_commit_hashes[tier]
    else:
        if tier in git_commit_hashes:
            ### In case Developer-tier wants an override
            git_commit_hash = git_commit_hashes[tier]
        else:
            git_commit_hash = tier ### assuming developer always wants to use LATEST git-commit (latest git-hash)

    print( f"git_commit_hash='{git_commit_hash}' within lkp_cdk_json()" )

    ### As Git-Tags are supposed to be on main git-branch, Just for the PIPELINE-stack, replace the Release-Git-Tag# with `main`
    if git_commit_hash is None or re.compile(r'^[ver0-9.]+').match( git_commit_hash ):
        pipeline_source_gitbranch = constants.GIT_BRANCH_FOR_UPPER_TIERS
    else:
        pipeline_source_gitbranch = git_commit_hash
    print( f"pipeline_source_gitbranch = '{pipeline_source_gitbranch}' within lkp_cdk_json() within "+ __file__ )

    ### ---------------------------------------------
    # git_token_secret = aws_secretsmanager.Secret.from_secret_complete_arn( cdk_scope, "gitToken", gitTokenRefARN )

    return git_src_code_config , gitTokenRef , git_commit_hash , pipeline_source_gitbranch

### ---------------------------------------------------------------------------------

def lkp_cdk_json_for_codestar_arn(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    git_src_code_config :any,
) -> str:
    """ Looks up `cdk.json` file and .. .. returns codestar_connection_arn :str
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str
    """

    stk = Stack.of(cdk_scope)

    # effective_tier = tier if (tier in constants.STD_TIERS or tier in constants.ACCT_TIERS) else "dev"
    if ("codestar-connection" in git_src_code_config and
        aws_env in git_src_code_config["codestar-connection"] and
        # effective_tier in git_src_code_config["codestar-connection"] and
        "arn" in git_src_code_config["codestar-connection"][aws_env]
        # "arn" in git_src_code_config["codestar-connection"][effective_tier]
    ):
        codestar_connection_name = git_src_code_config["codestar-connection"][aws_env]["name"]
        codestar_connection_arn  = git_src_code_config["codestar-connection"][aws_env]["arn"]
        # codestar_connection_name = git_src_code_config["codestar-connection"][effective_tier]["name"]
        # codestar_connection_arn  = git_src_code_config["codestar-connection"][effective_tier]["arn"]
        # codestar_connection_arn = f"arn:{stk.partition}:codestar-connections:{stk.region}:{stk.account}:connection/{?????}"

        print( f"codestar_connection_name = '{codestar_connection_name}' within "+ __file__ )
        print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )

        return codestar_connection_arn # , codestar_connection_name

    else:
        raise Exception( f"ERROR! Missing 'codestar-connection' in 'cdk.json' for '{aws_env}' environment" )

### ---------------------------------------------------------------------------------
### .................................................................................
### ---------------------------------------------------------------------------------

def lkp_cdk_json_for_github_webhooks(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    # git_src_code_config :any,
    # gitTokenRef :str,
) -> Tuple[any,aws_secretsmanager.ISecret]:
    """ Looks up `cdk.json` file and .. .. returns Modern GitHub connection ..
        .. without (REPEAT: without) use of CodeStarConnection. Without!!!
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str
    """

    stk = Stack.of(cdk_scope)

    # source = pipelines.CodePipelineSource.connection(
    #     repo_string = git_repo_url.replace('.git', ''),
    #     branch = pipeline_source_gitbranch,
    #     connection_arn = codestar_connection_arn,
    #     trigger_on_push=False,
    #     # trigger_on_push=False if tier in constants.UPPER_TIERS else True,
    #     ### By setting `trigger_on_push == False`, you effectively set the `PollForSourceChanges = False`.
    # )

    # gitauth_secret :aws_secretsmanager.ISecret = aws_secretsmanager.Secret.from_secret_name_v2( scope=self, id=id+"-secret-gitTokenRef", secret_name=gitTokenRef )
    # gitauthtoken = gitauth_secret.secret_value
    # gitauthtoken = gitauth_secret.secret_value_from_json("access_token") --> fpr cdk.json:  "git_token_json" : "github/access_token",
    # gitauthtoken = SecretValue.secrets_manager(secret_id = gitTokenRef)

    # source = pipelines.CodePipelineSource.git_hub(
    #     repo_string = git_repo_url,
    #     # branch = branch,
    #     branch = git_commit_hash,
    #     authentication = gitauthtoken,
    #     trigger = codepipeline_actions.GitHubTrigger.POLL if tier not in constants.UPPER_TIERS else codepipeline_actions.GitHubTrigger.NONE,
    #         ### for int | uat | prod environments, the CodePipeline has to be triggered MANUALLY (as they all are connected to MAIN-Git-Branch).
    # )

    # print( f"gitTokenRef = '{gitTokenRef}' within "+ __file__ )
    # print( f"gitauth_secret = '{gitauth_secret}' within "+ __file__ )

    # return source, gitauth_secret

### ---------------------------------------------------------------------------------

def lkp_gitrepo_details(
    cdk_scope :Construct,
) -> Tuple[str,str]:
    """ Based on `--context` CDK-CLI arguments -or- by looking-up `cdk.json` file.. ..
        .. returns a tuple in the following ORDER:
        1. git repo's URL    :str
        2. git_repo_name     :str
        3. git_repo_org_name :str
    """

    gitRepoURL :str = None
    if isinstance(cdk_scope, Stack) or isinstance(cdk_scope, Construct):
        gitRepoURL = cdk_scope.node.try_get_context("git_repo")
    else:
        raise ValueError("Invalid type for `cdk_scope`. Expected Stack or Construct. Got: "+ type(cdk_scope).__name__)

    print( f"gitRepoURL = '{gitRepoURL}' within "+ __file__ )

    git_repo_name, git_repo_org_name  = parse_gitrepo_details( gitRepoURL )

    return gitRepoURL, git_repo_name, git_repo_org_name

### ---------------------------------------------------------------------------------

def parse_gitrepo_details(
    gitRepoURL :str,
) -> Tuple[str,str]:
    """ Based on `--context` CDK-CLI arguments -or- by looking-up `cdk.json` file.. ..
        .. returns a tuple in the following ORDER:
        1. git_repo_name     :str
        2. git_repo_org_name :str
    """

    gitRepoURL_NoProtocol = gitRepoURL.replace("https://github.com/", "")
    print( f"gitRepoURL_NoProtocol = '{gitRepoURL_NoProtocol}' within "+ __file__ )

    git_repo_org_name :str  = gitRepoURL_NoProtocol.split("/")[0]
    print( f"git_repo_org_name = '{git_repo_org_name}' within "+ __file__ )

    git_repo_name :str  = gitRepoURL_NoProtocol.split("/")[1].replace(".git","")
    print( f"git_repo_name = '{git_repo_name}' within "+ __file__ )

    return git_repo_name, git_repo_org_name

### ---------------------------------------------------------------------------------

def lkp_git_branch(
    cdk_scope :Construct,
    tier :str,
) -> str:
    """ Lookup actual git-branch to use for a specific-tier.
        Assumes following structure in `cdk.json`

        "context": {
            "git-source": {
                .. ..
                "git_commit_hashes" : {
                    "acct-nonprod" : "sarma",    <--------- note: This is for "accountWide" shared across all TIERs !!!
                    "acct-prod" : "main",        <--------- note: This is for "accountWide" shared across all TIERs !!!
                    "matt": "matt",
                    "nathan" : "nathan",

                    "dev" : "dev",
                    "int" : "main",
                    "test" : "main",

                    "uat" : "v2.0.5.1",
                    "stage" : "v3.0.0",
                    "prod" : "v3.0.0"
                }
    """

    git_src_code_config :any = cdk_scope.node.try_get_context("git-source")
    global one_time_debug_output_completed_1
    if not one_time_debug_output_completed_1:
        print("cdk.json's Git-SourceCode configuration JSON is:")
        print( json.dumps(git_src_code_config, indent=4) )

    git_commit_hashes = git_src_code_config["git_commit_hashes"]
    if not one_time_debug_output_completed_1:
        print( json.dumps( git_commit_hashes, indent=4 ) )
        one_time_debug_output_completed_1 = True
    if tier in constants.STD_TIERS or tier in constants.ACCT_TIERS:
        git_commit_hash :str = git_commit_hashes[tier]
    else:
        if tier in git_commit_hashes:
            ### In case Developer-tier wants an override
            git_commit_hash = git_commit_hashes[tier]
        else:
            git_commit_hash = tier ### assuming developer always wants to use LATEST git-commit (latest git-hash)

    print( f"git_commit_hash='{git_commit_hash}' within lkp_git_branch()" )
    return git_commit_hash

### ---------------------------------------------------------------------------------
### .................................................................................
### ---------------------------------------------------------------------------------

def lkp_website_details(
    cdk_scope :Construct,
    tier :str,
) -> Tuple[str,str]:
    """ Given the tier, this function looks inside cdk.json
        1. first looks for the "root_domain"            -- within cdk.json
        2. NEXT looks for the "frontend_domain"         -- within cdk.json
        2. NEXT looks for the entry for "tier" in it    -- within cdk.json
        Returns a tuple of Strings:
            root_domain/FQDN       :str
            frontend_website_FQDN  :str
    """

    root_domain :str  = cdk_scope.node.try_get_context("root_domain")
    print( f"root_domain = '{root_domain}' within "+ __file__ )

    frontend_domain_names :any =  cdk_scope.node.try_get_context("frontend_domain")[root_domain]
    print( f"frontend_domain_names = '{frontend_domain_names}' within "+ __file__ )

    frontend_website_FQDN  :str =  frontend_domain_names[tier]
    print (f"frontend_website_FQDN = '{frontend_website_FQDN}' within "+ __file__ )
    frontend_website_FQDN = frontend_website_FQDN.format( constants.WEBSITE_DOMAIN_PREFIX )
    print (f"frontend_website_FQDN (formatted) = '{frontend_website_FQDN}' within "+ __file__ )

    return root_domain, frontend_website_FQDN

### ---------------------------------------------------------------------------------

### EoF
