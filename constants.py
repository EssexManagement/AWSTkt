import pathlib
import traceback

ENTERPRISE_NAME = "EssexMgmt"
HUMAN_FRIENDLY_APP_NAME = "AWS-Ticket"
# -- HUMAN_FRIENDLY_APP_VERSION  .. do NOT define here. Do it in cdk.json instead.
CDK_APP_NAME = "AWSTkt"
CDK_COMPONENT_NAME = "backend"

WEBSITE_DOMAIN_PREFIX = "www"              ### becomes "{WEBSITE_DOMAIN_PREFIX}.{ENV}.<FACTDOMAIN>.com"
### !!! Attention !!! Keep the above line IN-SYNC with FRONTEND-Repo's `constants.py`


PROD_TIER = "prod"
UAT_TIER = "uat"
INT_TIER = "int"
DEV_TIER = "dev"
STD_TIERS = [ PROD_TIER, UAT_TIER, INT_TIER, DEV_TIER, ]

UPPER_TIERS = STD_TIERS.copy()
UPPER_TIERS.remove( DEV_TIER )

GIT_BRANCH_FOR_UPPER_TIERS = "main"

ACCOUNT_ID = {
    DEV_TIER:  "127516845550",
    INT_TIER:  "127516845550",
    UAT_TIER:  "668282225937",
    PROD_TIER: "564062160093",
}

TIER_TO_AWSENV_MAPPING = {
    "dev": "DEVINT",
    "int": "DEVINT",
    "uat": "UAT",
    "prod": "PROD",

    "test": "NONPROD",
    "stage": "PROD",
    "prod": "PROD",
}

### ----------------------------------------------------------------
CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME = f"{CDK_APP_NAME}/prod/clinicaltrialsapi.cancer.gov"

# API_KEY_UNPUBLISHED_NAME = f"{CDK_APP_NAME}/{CDK_COMPONENT_NAME}/api"
API_KEY_UNPUBLISHED_NAME = "emfact@essexmanagement" ###  -- ORIGINAL !!!

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
""" Standardized naming for Git-Branches """
def get_git_branch( tier :str ) -> str:
    if tier in UPPER_TIERS:
        return GIT_BRANCH_FOR_UPPER_TIERS
    else:
        return tier

### ----------------------------------------------------------------
""" Standardized naming for AWS-Environments a.k.a. AWS-PROFILES """
def get_aws_env( tier :str ) -> str:
    if tier in TIER_TO_AWSENV_MAPPING:
        return TIER_TO_AWSENV_MAPPING[tier]
    else:
        return "DEVINT"
    # if tier in [ DEV_TIER, INT_TIER ]:
    #     return "DEVINT"
    # elif tier in [ UAT_TIER ]:
    #     return "UAT"
    # elif tier in [ PROD_TIER ]:
    #     return "PROD"
    # # elif tier in [ PROD_TIER, UAT_TIER ]:
    # #     return "PROD"
    # else:
    #     return "DEVINT"
    #     # traceback.print_exc()
    #     # raise ValueError(f"Invalid tier: {tier}")

### ----------------------------------------------------------------
### Attention: This represents an AWS-SES "Verified-emailaddress" --- for use by Cognito User-Pool's FROM-addr and REPLY-TO-addr.
def get_COGNITO_FROM_EMAIL( tier :str ) -> str:
    if tier == PROD_TIER:
        return "FACTSupport@mail.nih.gov"
        # return "matchbox-test@nih.gov"
    else:
        return "FACTSupport@mail.nih.gov"
        # return"emfact@essexmanagement.com"  ### old.

### ----------------------------------------------------------------
def get_COGNITO_REPLY_TO_EMAIL( tier :str ) -> str:
    if tier == PROD_TIER:
        return "FACTSupport@mail.nih.gov"
        # return "matchbox@nih.gov"
    else:
        return "FACTSupport@mail.nih.gov"
        # return"emfact@essexmanagement.com"  ### old.

### EoF
