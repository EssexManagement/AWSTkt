#!/bin/false

### !!! ATTENTION !!! keep this IM-SYNC with `constants.py`

### If any error in any commands, exit
set -e

HUMAN_FRIENDLY_APP_NAME="FACTrial"
CDK_APP_NAME="FACT"
CDK_FRONTEND_COMPONENT_NAME="frontend"
CDK_BACKEND_COMPONENT_NAME="backend"
### NOTE: HUMAN_FRIENDLY_APP_VERSION is automatically determined below, by looking for cdk.json

###---------------------------------------------------------------

CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME="${CDK_APP_NAME}/prod/clinicaltrialsapi.cancer.gov"

API_KEY_UNPUBLISHED_NAME="${CDK_APP_NAME}/${CDK_COMPONENT_NAME}/api"

# GITHUB_TOKEN_UNPUBLISHEDNAME="${CDK_APP_NAME}/${PROD_TIER}/github-token-biad"

###---------------------------------------------------------------

AWSREGION="us-east-1"

PROD_TIER="prod"
STD_TIERS=("dev" "test" "uat" "prod")

###---------------------------------------------------------------

if [[ "${STD_TIERS[*]}" =~ "${TIER}" ]]; then
    echo "You provided tier=${TIER} via BASH-shell environment-variables"
else
    if [ -z "${TIER+x}" ]; then
        TIER="dev"  ### developer branches are hosted in "dev" AWS-tier
        echo "!! Defaulting TIER='${TIER}' !!  Goign forward .. Pls. set the environment-variable 'TIER'"
        sleep 5
    else
        # echo "FATAL ERROR ❌❌: Invalid TIER='${TIER}' provided"
        read -p "❌: Un-expected TIER='${TIER}' provided!!  ENTER 'y' to continue ... [yN] > " ANS
        if [ "${ANS}" == "y" ] || [ "${ANS}" == "Y" ]; then
            echo "continuing .. "
        else
            exit 20
        fi
    fi
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### derived constants

CDK_JSON_FILEPATH="./cdk.json"
if [ ! -f "${CDK_JSON_FILEPATH}" ]; then
    CDK_JSON_FILEPATH="../cdk.json"
    if [ ! -f "${CDK_JSON_FILEPATH}" ]; then
        CDK_JSON_FILEPATH="../../cdk.json"
        if [ ! -f "${CDK_JSON_FILEPATH}" ]; then
            CDK_JSON_FILEPATH="../../cdk.json"
            if [ ! -f "${CDK_JSON_FILEPATH}" ]; then
                CDK_JSON_FILEPATH="../../cdk.json"
            else
                echo "!! FATAL ERROR❌❌ !! Not able to find cdk.json in ancestor-folders from $(pwd)"
                exit 9
            fi
        fi
    fi
fi
HUMAN_FRIENDLY_APP_VERSION="$( jq '.context.git_commit_hashes.prod' ${CDK_JSON_FILEPATH} --raw-output )"

if [ "${TIER}" == "dev" ];  then AWS_ENV="dev";   AWSPROFILE="DEVINT";  git_branch="dev";  fi
if [ "${TIER}" == "int" ];  then AWS_ENV="int";   AWSPROFILE="DEVINT";  git_branch="main"; fi
if [ "${TIER}" == "uat" ];  then AWS_ENV="uat";   AWSPROFILE="DEVINT";  git_branch="main"; fi
if [ "${TIER}" == "prod" ]; then AWS_ENV="prod";  AWSPROFILE="DEVINT";  git_branch="main"; fi
### If git_branch is not set, then exit this script
if [ -z "${AWS_ENV+x}" ]; then
    AWS_ENV="dev";   AWSPROFILE="DEVINT";   git_branch="${TIER}";
    # echo "FATAL ERROR❌❌: AWS_TIER & git_branch cannot be determined for TIER=${TIER}"
    # exit 11
fi

AWSPROFILEREGION=( --profile ${AWSPROFILE} --region ${AWSREGION} )          ### NOT working on macbook-m1 with BIAD-Oka
printf "\t\tAWSPROFILEREGION='${AWSPROFILEREGION[@]}'\n"

echo  aws sts get-caller-identity --query Account --output text ${AWSPROFILEREGION[@]}
AWSACCOUNTID=$( aws sts get-caller-identity --query Account --output text ${AWSPROFILEREGION[@]} )
echo "AWSACCOUNTID='${AWSACCOUNTID}'"

### Attention: This represents an AWS-SES "Verified-emailaddress" --- for use by Cognito User-Pool's FROM-addr and REPLY-TO-addr.
### old - COGNITO_FROM_EMAIL="emfact@essexmanagement.com"  ### old.
# COGNITO_FROM_EMAIL="factsupport@nih.gov"
# COGNITO_FROM_EMAIL="matchbox-test@nih.gov"
if [ "${TIER}" == "${PROD_TIER}" ]; then
    COGNITO_FROM_EMAIL="factsupport@nih.gov"
    # COGNITO_FROM_EMAIL="matchbox@nih.gov"
else
    COGNITO_FROM_EMAIL="factsupport@nih.gov"
    # COGNITO_FROM_EMAIL="matchbox-test@nih.gov"
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

PROD_TAGS=(
    Key="PRODUCT",Value="$( echo ${HUMAN_FRIENDLY_APP_NAME} | tr '[:upper:]' '[:lower:]' )"
    Key="VERSION",Value="${HUMAN_FRIENDLY_APP_VERSION}"
    Key="application",Value="${CDK_APP_NAME}"
    Key="component",Value="${CDK_BACKEND_COMPONENT_NAME}"
    Key="git_branch",Value="${git_branch}"
    Key="env",Value="${AWS_ENV}"
    Key="ENVIRONMENT",Value="$(echo ${AWS_ENV} | tr '[:upper:]' '[:lower:]')"
)


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

if [ "${TIER}" == "dev" ]; then
    COGNITO_USERPOOL_ID="us-east-1_Sx8vl4NET"
else
    if [ "${TIER}" == "int" ]; then
        COGNITO_USERPOOL_ID="us-east-1_vRZDKxXxu"
    else
        if [ "${TIER}" == "uat" ]; then
            COGNITO_USERPOOL_ID="us-east-1_D7SAYsvXb"
        else
            if [ "${TIER}" == "prod" ]; then
                COGNITO_USERPOOL_ID="us-east-1_EQfl74pOQ"
            else
                COGNITO_USERPOOL_ID="us-east-1_BpKKmPzy7"
                printf "\n!! ERROR !! UN-Expected Tier = '${TIER}' passed in.  Should be dev|int|uat|prod only\n"
                read -p "ENTER 'y' to continue -ANYWAYS- with COGNITO_USERPOOL_ID='${COGNITO_USERPOOL_ID}' ... > " ANS
                if [ "${ANS}" == "y" ] || [ "${ANS}" == "Y" ]; then
                    echo "continuing .. "
                else
                    exit 9
                fi
            fi
        fi
    fi
fi
printf "Cognito User-POOL ID for ${TIER} tier = '${COGNITO_USERPOOL_ID}'\n"
COGNITO_GROUPID="CCDI"


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

TMPROOTDIR="/tmp"
TMPDIR="${TMPROOTDIR}/DevOps/AWS/${TIER}/${SCRIPT_NAME}"
TMPFILE11="${TMPDIR}/tmp1.txt"
TMPFILE22="${TMPDIR}/tmp2.txt"
TMPFILE_FINAL="${TMPDIR}/tmp99.txt"

mkdir -p ${TMPROOTDIR}
mkdir -p ${TMPDIR}
rm -rf "${TMPFILE11}" "${TMPFILE22}" "${TMPFILE_FINAL}"

###---------------------------------------------------------------

### EoScript
