from typing import Tuple
import json
import pytz
import re

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

""" Lookup ARN for WAF-ACL to be associated with CloudFRONT.
    Assumes following structure in `cdk.json`

    "security": {
        "WAF-ACL": {
            "global": {
                "dev": "arn:aws:wafv2:xx-abcd-1:123456789012:global/webacl/.. ..",
"""
def lkp_waf_acl_for_cloudFront(
    cdk_context,
    effective_tier :str,
) -> str:
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

### ---------------------------------------------------------------------------------

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
def lkp_waf_acl_for_apigw(
    cdk_context,
    effective_tier :str,
) -> str:
    return _lkp_waf_acl_for_aws_resource(
        cdk_context = cdk_context,
        effective_tier = effective_tier,
        lkp_key = "regional",
    )

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
def lkp_waf_acl_for_cognito(
    cdk_context,
    effective_tier :str,
) -> str:
    return _lkp_waf_acl_for_aws_resource(
        cdk_context = cdk_context,
        effective_tier = effective_tier,
        lkp_key = "Cognito-WAF-ACLs",
    )

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

### ---------------------------------------------------------------------------------

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
    print("cdk.json's Git-SourceCode configuration JSON is:")
    print( json.dumps(git_src_code_config, indent=4) )

    gitTokenRef = git_src_code_config["git_token_ref"]
    print( f"gitTokenRef = '{gitTokenRef}' within "+ __file__ )
    # gitTokenRefARN :str = git_src_code_config["git_token_ref_arn"]
    # print( f"gitTokenRefARN = '{gitTokenRefARN}' within "+ __file__ )
    # gitTokenRefARN = gitTokenRefARN.format( stk.region, stk.account )
    # print( f"gitTokenRefARN = '{gitTokenRefARN}' within "+ __file__ )

    git_commit_hashes = git_src_code_config["git_commit_hashes"]
    print( json.dumps( git_commit_hashes, indent=4 ) )
    if tier in constants.STD_TIERS:
        git_commit_hash :str = git_commit_hashes[tier]
    else:
        if tier in git_commit_hashes:
            ### In case Developer-tier wants an override
            git_commit_hash = git_commit_hashes[tier]
        else:
            git_commit_hash = tier ### assuming developer always wants to use LATEST git-commit (latest git-hash)

    print( f"git_commit_hash='{git_commit_hash}'" )

    ### As Git-Tags are supposed to be on main git-branch, Just for the PIPELINE-stack, replace the Release-Git-Tag# with `main`
    if git_commit_hash is None or re.compile(r'^[ver0-9.]+').match( git_commit_hash ):
        pipeline_source_gitbranch = constants.GIT_BRANCH_FOR_UPPER_TIERS
    else:
        pipeline_source_gitbranch = git_commit_hash
    print( f"pipeline_source_gitbranch = '{pipeline_source_gitbranch}' within "+ __file__ )

    ### ---------------------------------------------
    # git_token_secret = aws_secretsmanager.Secret.from_secret_complete_arn( cdk_scope, "gitToken", gitTokenRefARN )

    return git_src_code_config , gitTokenRef , git_commit_hash , pipeline_source_gitbranch

### ---------------------------------------------------------------------------------

def lkp_cdk_json_for_codestar_arn(
    cdk_scope :Construct,
    tier :str,
    aws_env :str,
    git_src_code_config :any,
) -> Tuple[str,str, str, str, str]:
    """ Looks up `cdk.json` file and .. .. returns codestar_connection_arn :str
        Parameter #1 - cdk_scope :Construct => Pass in any Construct within a Stack
        Parameter #2 - tier :str            => dev|int|uat|prod
        Parameter #3 - aws_env :str
    """

    stk = Stack.of(cdk_scope)

    effective_tier = tier if tier in constants.STD_TIERS else "dev"
    if "codestar-connection" in git_src_code_config and effective_tier in git_src_code_config["codestar-connection"]:
        codestar_connection_name = git_src_code_config["codestar-connection"][effective_tier]["name"]
        codestar_connection_arn = git_src_code_config["codestar-connection"][effective_tier]["arn"]
    else:
        ### WARNING !!! maxLength: 32
        codestar_connection_name = f"{constants.CDK_APP_NAME}-GitHub-V2-{effective_tier}"
        # create a arn:aws:codestar-connections
        codestar_connection = aws_codestarconnections.CfnConnection( scope=cdk_scope, id="codestar-connection",
            connection_name = codestar_connection_name,
            provider_type = "GitHub",
        )
        codestar_connection_arn = f"arn:{stk.partition}:codestar-connections:{stk.region}:{stk.account}:connection/{codestar_connection.ref}"

    print( f"codestar_connection_name = '{codestar_connection_name}' within "+ __file__ )
    print( f"codestar_connection_arn = '{codestar_connection_arn}' within "+ __file__ )

    return codestar_connection_arn

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

""" Given the tier, this function looks inside cdk.json
    1. first looks for the "root_domain"            -- within cdk.json
    2. NEXT looks for the "frontend_domain"         -- within cdk.json
    2. NEXT looks for the entry for "tier" in it    -- within cdk.json
    Returns a tuple of Strings:
        root_domain/FQDN       :str
        frontend_website_FQDN  :str
"""
def lkp_website_details(
    cdk_scope :Construct,
    tier :str,
) -> Tuple[str,str]:

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

### EoF
