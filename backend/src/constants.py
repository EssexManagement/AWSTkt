import pathlib
import traceback

ENTERPRISE_NAME = "NIH-NCI"
HUMAN_FRIENDLY_APP_NAME = "CancerTrialsFinder"
# -- HUMAN_FRIENDLY_APP_VERSION  .. do NOT define here. Do it in cdk.json instead.
CDK_APP_NAME = "CTF"

CDK_BACKEND_COMPONENT_NAME  = "backend"
CDK_FRONTEND_COMPONENT_NAME = "frontend"
CDK_DEVOPS_COMPONENT_NAME   = "devops"
CDK_OPERATIONS_COMPONENT_NAME   = "operations"
CDK_BDD_COMPONENT_NAME      = "BDD"
# CDK_COMPONENT_NAME = CDK_BACKEND_COMPONENT_NAME ### For legacy reasons.


WEBSITE_DOMAIN_PREFIX = "www"              ### becomes "{WEBSITE_DOMAIN_PREFIX}.{ENV}.<FACTDOMAIN>.com"
### !!! Attention !!! Keep the above line IN-SYNC with FRONTEND-Repo's `constants.py`

ACCT_PROD = "acct-prod"
ACCT_NONPROD = "acct-nonprod"

PROD_TIER = "prod"
STAGE_TIER = "stage"
UAT_TIER = "uat"
INT_TIER = "int"
TEST_TIER = "test"
QA_TIER = TEST_TIER
DEV_TIER = "dev"
STD_TIERS = [ PROD_TIER, STAGE_TIER, UAT_TIER, QA_TIER, TEST_TIER, INT_TIER, DEV_TIER, ]
ACCT_TIERS = [ ACCT_PROD, ACCT_NONPROD ]

UPPER_TIERS = STD_TIERS.copy()
UPPER_TIERS.remove( DEV_TIER )

GIT_BRANCH_FOR_UPPER_TIERS = "main"

### ----------------------------------------------------------------
CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME = f"{HUMAN_FRIENDLY_APP_NAME}/prod/clinicaltrialsapi.cancer.gov"

API_KEY_UNPUBLISHED_NAME = "emfact@essexmanagement" ###  -- ORIGINAL !!!

RDS_APPLN_USER_NAME = "emfact_user"

### ----------------------------------------------------------------
### CDK related.  Breaking up a large stack of Lambdas into smaller stacks.
NUM_OF_CHUNKS = 4

### -------------------------------------------------------------------------

COGNITO_USER_GROUP = 'CCDI'

### ----------------------------------------------------------------------------------------------------------------------------
### %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
### ----------------------------------------------------------------------------------------------------------------------------

### ====================
### derived "constants"
### ====================

PROJ_ROOT_FLDR_PATH = pathlib.Path(__file__).parent.resolve().absolute()

### ----------------------------------------------------------------
# """ Standardized naming for Git-Branches """
# def get_git_branch( tier :str ) -> str:
#     if tier in UPPER_TIERS:
#         return GIT_BRANCH_FOR_UPPER_TIERS
#     else:
#         return tier

### ----------------------------------------------------------------



DefaultITSupportEmailAddress = "nci-cancer-trials-finder-awsadmins@mail.nih.gov"  ### Can be a single/simple-string (one-email) or a LIST of email-addresses



### Attention: This represents an AWS-SES "Verified-emailaddress" --- for use by Cognito User-Pool's FROM-addr and REPLY-TO-addr.
def get_COGNITO_FROM_EMAIL( tier :str, aws_env :str ) -> str:

    if aws_env == ACCT_NONPROD or aws_env == ACCT_PROD: ### !!! NCI's CloudOne
            if tier == PROD_TIER:
                return "FACTSupport@mail.nih.gov"
            else:
                return "FACTSupport@mail.nih.gov"

    elif aws_env == "DEVINT" or aws_env == "PROD": ### !!! CRRI-Cloud
            if tier == PROD_TIER:
                return "FACTSupport@mail.nih.gov" # return "matchbox-test@nih.gov"
            else:
                return "FACTSupport@mail.nih.gov"

    # elif aws_env == "EssexCloud-DEV" or aws_env == "EssexCloud-PROD":
    #         if tier == PROD_TIER:
    #             return"emfact@essexmanagement.com"  ### old.
    #         else:
    #             return"USeetamraju@emmes.com"  ### Sarma
    else:
        raise ValueError(f"Invalid aws_env: '{aws_env}'")

### --------------------------
def get_COGNITO_REPLY_TO_EMAIL( tier :str, aws_env :str ) -> str:

    if aws_env == ACCT_NONPROD or aws_env == ACCT_PROD: ### !!! NCI's CloudOne
            if tier == PROD_TIER:
                return "FACTSupport@mail.nih.gov"
            else:
                return "FACTSupport@mail.nih.gov"

    elif aws_env == "DEVINT" or aws_env == "PROD": ### !!! CRRI-Cloud
            if tier == PROD_TIER:
                return "FACTSupport@mail.nih.gov" # return "matchbox@nih.gov"
            else:
                return "FACTSupport@mail.nih.gov"

    # elif aws_env == "EssexCloud-DEV" or aws_env == "EssexCloud-PROD":
    #         if tier == PROD_TIER:
    #             return"emfact@essexmanagement.com"  ### old.
    #         else:
    #             return"USeetamraju@emmes.com"  ### Sarma's email
    else:
        raise ValueError(f"Invalid aws_env: '{aws_env}'")

### EoF
