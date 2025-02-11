#!/opt/homebrew/bin/bash -f

### The CDK deployment of Lambdas as separate stacks from APIGW-Stack .. causes the RestAPI-to-Lamnda integrations to be broken at deployment.
### Manual fix is to edit EACH Path in RESTAPI and re-link to the Lambda, this time ensuring Lambda-name is converted automatically to Lambda-ARN by AWS-Console.
### This script aims to do that automatically.

if [ $# -lt 1 ]; then
    echo "Usage: $0 <ENV>"
    exit 1
fi
ENV="$1"
printf "\t\tYou've specified environment ='${ENV}'\n"

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

RESTAPI_NAME="FACT-backend-${ENV}-StatelessAPIGW-emfact-api"

###---------------------------------------------------------------

TMPFILE_AllAPIs="${TMPDIR}/tmp-all-APIs.txt"
TMPFILE22="${TMPDIR}/tmp22.txt"
TMPFILE_AllResources="${TMPDIR}/tmp-all-rscrs.txt"
TMPFILE_BASHARRAY="${TMPDIR}/tmp-bash-arr-var.txt"

# rm -rf "${TMPFILE_AllAPIs}" "${TMPFILE22}" "${TMPFILE_BASHARRAY}"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

if [ ! -e $TMPFILE_AllAPIs ]; then
    echo \
    aws apigateway get-rest-apis --output json
    aws apigateway get-rest-apis --output json > ${TMPFILE_AllAPIs}
    if [ $? -ne 0 ]; then
        printf "\n!! ERROR !! Invalid AWS-Credentials\n"
        exit 88
    fi
fi
ls -la "${TMPFILE_AllAPIs}"

### -----------------------------------
jq ".items[] | select( .name == \"${RESTAPI_NAME}\" ) " ${TMPFILE_AllAPIs} > ${TMPFILE22}
ls -la "${TMPFILE22}"

APIGW_ID=$( jq ".id" --raw-output ${TMPFILE22} )
APIGW_ROOTRES_ID=$( jq ".rootResourceId" --raw-output ${TMPFILE22} )
echo "APIGW_ID='${APIGW_ID}'"
echo "APIGW_ROOTRES_ID='${APIGW_ROOTRES_ID}'"

### -----------------------------------
if [ ! -e ${TMPFILE_AllResources} ]; then
    # aws apigateway get-rest-api --rest-api-id ${APIGW_ID} --output json > ${TMPFILE_AllResources}
    set -x
    aws apigateway get-resources --rest-api-id ${APIGW_ID} --output json > ${TMPFILE_AllResources}
    set +x
fi
ls -la "${TMPFILE_AllResources}"

### -----------------------------------
# jq '.items[] | { "id": .id, "pathPart": .pathPart, "path": .path }' ${TMPFILE_AllResources} > ${TMPFILE_BASHARRAY}
set -x
jq '.items[] | .id+" "+.pathPart+" "+.path ' --raw-output ${TMPFILE_AllResources} > ${TMPFILE_BASHARRAY}
# jq '.items[] | .id+" "+.pathPart+" "+.path+" "+.resourceMethods.keys_unsorted[0] ' --raw-output ${TMPFILE_AllResources} > ${TMPFILE_BASHARRAY}
set +x
ls -la "${TMPFILE_BASHARRAY}"

### -----------------------------------
readarray -t LINES < <( cat ${TMPFILE_BASHARRAY} )

for line in "${LINES[@]}"; do
    # echo "$line"
    WORDS=()
    for word in ${line}; do
        # printf "${word} .."
        WORDS+=( ${word} )

    done
    # printf " !!!\n"
    APIGW_RES_ID=${WORDS[0]}
    set -x
    jq ".items[] | select( .id == \"${APIGW_RES_ID}\" ) | .resourceMethods | keys_unsorted[0] " --raw-output < ${TMPFILE_AllResources}
    set +x
    HTTP_METHOD=$( jq ".items[] | select( .id == \"${APIGW_RES_ID}\" ) | .resourceMethods | keys_unsorted[0] " --raw-output < ${TMPFILE_AllResources} )
    echo "HTTP_METHOD='${HTTP_METHOD}'"
    echo \
    aws apigateway get-integration --rest-api-id ${APIGW_ID} --resource-id ${APIGW_RES_ID} --http-method ${HTTP_METHOD} --output json
    aws apigateway get-integration --rest-api-id ${APIGW_ID} --resource-id ${APIGW_RES_ID} --http-method ${HTTP_METHOD} --output json > ${TMPFILE22}

    printf "%0.s-" {1..80}; echo ""
    ls -la ${TMPFILE22}
    cat ${TMPFILE22}
    printf "%0.s-" {1..80}; echo ""
    LAMBDA_NAME=$( jq '.uri' ${TMPFILE22} | cut -d : -f 12 | cut -d / -f 1 )
    echo "LAMBDA_NAME='$LAMBDA_NAME'"

    ### REF: https://awscli.amazonaws.com/v2/documentation/api/latest/reference/apigateway/put-integration.html
    ### Examples: https://docs.aws.amazon.com/cli/v1/userguide/cli_api-gateway_code_examples.html
    echo \
    aws apigateway put-integration --rest-api-id ${APIGW_ID} --resource-id ${APIGW_RES_ID} --http-method ${HTTP_METHOD} \
            --type AWS --integration-http-method POST --content-handling CONVERT_TO_TEXT --passthrough-behavior WHEN_NO_MATCH \
            --uri "arn:aws:apigateway:${AWSREGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${AWSREGION}:${AWSACCOUNTID}:function:${LAMBDA_NAME}/invocations" \
            --output json

    sleep 3

    # {
    #     "type": "AWS_PROXY",
    #     "httpMethod": "POST",
    #     "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:127516845550:function:FACT-backend-dev-Lambdas--06getpriortherapyE9B595E-uvaKERc9HRt2/invocations",
    #     "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:668282225937:function:FACT-backend-uat-Lambdas--2430gettrialcriteriacoun-52XHvjDIo4F2/invocations",

    #     "requestTemplates": {
    #         "application/json": "{ \"statusCode\": \"200\" }"
    #     },
    #     "passthroughBehavior": "WHEN_NO_MATCH",
    #     "contentHandling": "CONVERT_TO_TEXT",
    #     "timeoutInMillis": 29000,
    #     "cacheNamespace": "1aubzg",
    #     "cacheKeyParameters": []
    # }


done

# if [ "${EXISTING_COGNITO_GROUPNAME}" == "null" ]; then
#     printf "\t\t👉🏾👉🏾 EXISTING_COGNITO_GROUPNAME='${EXISTING_COGNITO_GROUPNAME}'\n"
#     echo '';echo ''; read -p "CONTINUE with creating a NEW Group in Cognito? [^C to cancel]>>" ANS
#             ${AWSPROFILEREGION}
# else
#     printf "\t\t✅ EXISTING_COGNITO_GROUPNAME='${EXISTING_COGNITO_GROUPNAME}'\n"
# fi

# USERNAMES=$( jq --raw-output '.[] | .username' "${TMPFILE???????????????????}" )
# for USERNAME in ${USERNAMES}; do
#     printf "\t\tUSERNAME='${USERNAME}'"
#         while read -t 1 -r; do read -r -t 1; done
#         read -p "Resend for '${USERNAME}' ? [N]>" ANS
#         if [ "${ANS}" != "y" ] && [ "${ANS}" != "Y" ]; then
#             printf "🚮 skipping ..\n"
#             continue
#         fi
#     set -x
#     set +x
# done

### EoF
