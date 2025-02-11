#!/bin/bash -f

###---------------------------------------------------------------

SCRIPT_FOLDER=$(dirname -- "$0")
SCRIPT_NAME=$(basename  -- "$0")
CWD="$(pwd)"

###---------------------------------------------------------------

.  ${SCRIPT_FOLDER}/common-settings.sh

COMMON_DESCRIPTION="factrial.com on BIAD"

###---------------------------------------------------------------

echo "CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME=${CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME}"
read -s -p "Enter the value of the API-Key for ${CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME} >>" CLINICALTRIALSAPI_KEY
echo ''; echo ''

aws secretsmanager create-secret --name "${CLINICALTRIALSAPI_KEY_UNPUBLISHEDNAME}"   \
            --secret-string ${CLINICALTRIALSAPI_KEY}                            \
            --description "${COMMON_DESCRIPTION}"                               \
            --tags ${PROD_TAGS[@]}  ${AWSPROFILEREGION}

###---------------------------------------------------------------

### Temporarily disabled, until CodePipeline switches to GitHub-WEBHOOKS (from current Polling-Mechanism)
# echo "GITHUB_TOKEN_UNPUBLISHEDNAME=${GITHUB_TOKEN_UNPUBLISHEDNAME}"
# read -s -p "Enter the value of the GitHub-Token for ${GITHUB_TOKEN_UNPUBLISHEDNAME} >>" GITHUB_TOKEN
# echo ''; echo ''

# aws secretsmanager create-secret --name "${GITHUB_TOKEN_UNPUBLISHEDNAME}"    \
#             --secret-string ${GITHUB_TOKEN}                             \
#             --description "${COMMON_DESCRIPTION}"                       \
#             --tags ${PROD_TAGS[@]}  ${AWSPROFILEREGION}

### EoScript
