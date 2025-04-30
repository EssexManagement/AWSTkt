#!/opt/homebrew/bin/bash -f

### The CDK deployment of Lambdas as separate stacks from APIGW-Stack .. causes the RestAPI-to-Lamnda integrations to be broken at deployment.
### Manual fix is to edit EACH Path in RESTAPI and re-link to the Lambda, this time ensuring Lambda-name is converted automatically to Lambda-ARN by AWS-Console.
### This script aims to do that automatically.

if [ $# -lt 1 ]; then
    echo "Usage: $0 <Tier>"
    exit 1
fi
Tier="$1"
printf "\t\tYou've specified Tier ='${Tier}'\n"
sleep 2

###---------------------------------------------------------------

SCRIPT_FOLDER=$(dirname -- "$0")
SCRIPT_NAME=$(basename  -- "$0")
CWD="$(pwd)"

###---------------------------------------------------------------

.  ${SCRIPT_FOLDER}/common-settings.sh


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Section: derived variables & TEMP-FILES

COGNITO_USERPOOL_NAME="userpoolFACTbackend${Tier}"
COGNITO_APPINTEGRATION_NAME="userpoolFACTbackend${Tier}apiappclient"

COGNITO_TESTUSER_NAME="test_user"
COGNITO_TESTUSER_PASSWORD=$( openssl rand -base64 16 )
COGNITO_TESTUSER_PASSWORD=${COGNITO_TESTUSER_PASSWORD}$( openssl rand -hex 8 )
COGNITO_TESTUSER_EMAIL="vivek.ramani@nih.gov"
COGNITO_TESTUSER_ATTRIBUTES="Name=email,Value=${COGNITO_TESTUSER_EMAIL} Name=email_verified,Value=True"

UNPUBLISHED_ID="${CDK_APP_NAME}/${Tier}/testing/frontend/${COGNITO_TESTUSER_NAME}"
SecretCLITemplate="${TMPDIR}/tmp-secret.json"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

if [ ! -e ${TMPFILE11} ]; then
    echo \
    aws cognito-idp list-user-pools --output json --max-results 50 ${AWSPROFILEREGION[@]}
    aws cognito-idp list-user-pools --output json --max-results 50 ${AWSPROFILEREGION[@]} > ${TMPFILE11}
    if [ $? -ne 0 ]; then
        printf "\n!! ERROR !! Invalid AWS-Credentials or missing Cognito-UserPool\n"
        exit 88
    fi
fi
ls -la "${TMPFILE11}"

### -----------------------------------

### aws cognito-idp list-user-pools --output json --max-results 50 ${AWSPROFILEREGION[@]} | jq ".UserPools[] | select( .Name  | startswith(\"${COGNITO_USERPOOL_NAME}\") )"
jq ".UserPools[] | select( .Name  | startswith(\"${COGNITO_USERPOOL_NAME}\") )" ${TMPFILE11} > ${TMPFILE22}

COGNITO_USERPOOL_NAME=$( jq ".Name" ${TMPFILE22} --raw-output )
echo "COGNITO_USERPOOL_NAME='${COGNITO_USERPOOL_NAME}'"
TMP_POOL_ID=$( jq ".Id" ${TMPFILE22} --raw-output )
if [ "${TMP_POOL_ID}" != "${COGNITO_USERPOOL_ID}" ]; then
    if [ "developer-git_branch" != "${COGNITO_USERPOOL_ID}" ] && []; then
        echo "Looked up POOL_ID for pool-NAME='${COGNITO_USERPOOL_NAME}' and got a value '${TMP_POOL_ID}' that does --NOT-- match common-settings-value='${COGNITO_USERPOOL_ID}'"
        exit 109
    else
        COGNITO_USERPOOL_ID=${TMP_POOL_ID}
    fi
fi
echo "COGNITO_USERPOOL_ID='${COGNITO_USERPOOL_ID}'"

COGNITO_APPINTEGRATION_ID=$( aws cognito-idp list-user-pool-clients --user-pool-id "${COGNITO_USERPOOL_ID}" ${AWSPROFILEREGION[@]} --output json | jq ".UserPoolClients[] | select( .ClientName | startswith(\"${COGNITO_APPINTEGRATION_NAME}\") ) | .ClientId " --raw-output )
if [ $? -ne 0 ]; then
    exit 104
fi
echo "COGNITO_APPINTEGRATION_ID='${COGNITO_APPINTEGRATION_ID}'"

echo \
aws cognito-idp describe-user-pool-client --user-pool-id $COGNITO_USERPOOL_ID --client-id ${COGNITO_APPINTEGRATION_ID} ${AWSPROFILEREGION[@]} --output json
CLIENT_UNPUBLISHED=$( aws cognito-idp describe-user-pool-client --user-pool-id $COGNITO_USERPOOL_ID --client-id ${COGNITO_APPINTEGRATION_ID} ${AWSPROFILEREGION[@]} --output json | jq '.UserPoolClient.ClientSecret' --raw-output )
if [ $? -ne 0 ] || [ "${CLIENT_UNPUBLISHED}" == "" ]; then
    echo "!!Internal-ERROR!! unable to determine CLIENT_UNPUBLISHED.  '${CLIENT_UNPUBLISHED}'"
fi

### -----------------------------------
### https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cognito-idp/admin-create-user.html
read -p "Continue creating Cognito-User? >>" ANS
aws cognito-idp admin-create-user                       \
    --user-pool-id ${COGNITO_USERPOOL_ID}               \
    --username ${COGNITO_TESTUSER_NAME}                 \
    --user-attributes ${COGNITO_TESTUSER_ATTRIBUTES}    \
    --temporary-password "${COGNITO_TESTUSER_PASSWORD}" \
    --desired-delivery-mediums EMAIL                    \
    --message-action SUPPRESS                           \
     ${AWSPROFILEREGION[@]}
if [ $? -ne 0 ]; then
    exit 106
fi

### https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cognito-idp/admin-set-user-password.html
### aws cognito-idp admin-set-user-password --user-pool-id us-east-1_fvKf0U6q7 --username vivek.ramani --password D@vidDem0123 ${AWSPROFILEREGION[@]}

read -p "Are you SURE .. that you want to add above Cognito-User to Cognito-Group '${COGNITO_GROUPID}'? [yN] >> " ANS
if [ "${ANS}" == "y" ]; then
    aws cognito-idp admin-add-user-to-group --user-pool-id ${COGNITO_USERPOOL_ID}    \
        --username ${COGNITO_TESTUSER_NAME} --group-name ${COGNITO_GROUPID} ${AWSPROFILEREGION[@]}
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

cat > ${SecretCLITemplate} <<EOTXT
{
    "Name": "${UNPUBLISHED_ID}",
    "Description": "${Tier} Tier's QE-team's Automated-Testing user: ${COGNITO_TESTUSER_NAME}",
    "SecretString": "{ \"EMFACT_PASSWORD_CCDI\": \"${COGNITO_TESTUSER_PASSWORD}\", \"APP_INTEGRATION_CLIENT_ID\": \"${COGNITO_APPINTEGRATION_ID}\", \"APP_CLIENT_UNPUBLISHED\": \"${CLIENT_UNPUBLISHED}\" }",
    "Tags": [
       { "Key": "PRODUCT", "Value": "$( echo ${HUMAN_FRIENDLY_APP_NAME} | tr '[:upper:]' '[:lower:]' )" },
       { "Key": "VERSION", "Value": "${HUMAN_FRIENDLY_APP_VERSION}" },
       { "Key": "application", "Value": "${CDK_APP_NAME}" },
       { "Key": "component",   "Value": "${CDK_BACKEND_COMPONENT_NAME}" },
       { "Key": "git_branch",      "Value": "${Tier}" },
       { "Key": "env",         "Value": "${Tier}" },
       { "Key": "ENVIRONMENT", "Value": "${AWS_ENV}" },
       { "Key": "Contact",     "Value": "${COGNITO_TESTUSER_EMAIL}" }
    ]
}
EOTXT

### Looks like the following two are NO longer supported via CLI's --generate-cli-skeleton ????

### -----------------------------------------------------------
### Subsitute values within the JSON file.
# INPUTFILE="${UNPUBLISHEDSTEMPLATEFILE}"    ### <-------- pay attention to this line.  Do this for the 1st "sed" command!!!
# OUTPUTFILE=${TMPFILE11}
# sed -e "s/{DBEngine}/${DBEngine}/" < ${INPUTFILE} > ${OUTPUTFILE}

# INPUTFILE=${TMPFILE11}
# OUTPUTFILE=${TMPFILE22}
# sed -e "s/{PortNum}/${PortNum}/" < ${INPUTFILE} > ${OUTPUTFILE}

# INPUTFILE=${TMPFILE22}
# OUTPUTFILE=${TMPFILE11}
# sed -e "s/{RDSFQDN}/${RDSFQDN}/" < ${INPUTFILE} > ${OUTPUTFILE}

ls -la ${SecretCLITemplate}

set +e

echo \
aws secretsmanager describe-secret --secret-id ${UNPUBLISHED_ID}  ${AWSPROFILEREGION[@]}
aws secretsmanager describe-secret --secret-id ${UNPUBLISHED_ID}  ${AWSPROFILEREGION[@]} >& /dev/null
if [ $? -eq 0 ]; then
    printf "\n\tSecret already exists!\n\n"
    echo \
    aws secretsmanager delete-secret --secret-id ${UNPUBLISHED_ID} --force-delete-without-recovery ${AWSPROFILEREGION[@]}
    printf "\nOk to--DELETE-- existing AWS-Secret? "
    read -p ">>" ANS
    aws secretsmanager delete-secret --secret-id ${UNPUBLISHED_ID} --force-delete-without-recovery ${AWSPROFILEREGION[@]}
    # aws secretsmanager update-secret --secret-id ${UNPUBLISHED_ID} --cli-input-json file://${SecretCLITemplate}
fi

set -e

### Assert: Secret does Not exist.
echo \
aws secretsmanager create-secret --cli-input-json file://${SecretCLITemplate} ${AWSPROFILEREGION[@]}
read -p "Continue creating AWS-Secret? >>" ANS
aws secretsmanager create-secret --cli-input-json file://${SecretCLITemplate} ${AWSPROFILEREGION[@]}

### Do Not leave passwords lying around
echo '';
\rm -rf ${SecretCLITemplate}

### EoF
