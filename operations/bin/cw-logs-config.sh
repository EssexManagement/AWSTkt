#!/bin/bash -f

### Since setting CW-Log-Group retention blows up the Cloudformation-file-sizes, we're manually setting it via this script file.

CDK_APP_NAME="CTF"


if [ $# -ge 1 ]; then
    if [ "$1" == "--debug" ]; then
        DEBUGG="y"
        shift
    fi
fi
if [ $# -lt 1 ]; then
    printf "\nUsage: $0 [--debug] <ENV>\n"
    printf "\t\t\t\t\t\tdev|int|stage|uat|prod\n"
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


if [ "${ENV}" == "dev" ]; then
    RETENTION_DAYS=5
else
    if [ "${ENV}" == "int" ]; then
        RETENTION_DAYS=5
    else
        if [ "${ENV}" == "uat" ]; then
            RETENTION_DAYS=30
        else
            if [ "${ENV}" == "prod" ]; then
                RETENTION_DAYS=90
            else
                printf "\n!! ERROR !! Invalid cli-arg '${ENV}' passed in.  Should be dev|int|uat|prod only\n"
                exit 9
            fi
        fi
    fi
fi
echo "RETENTION_DAYS='$RETENTION_DAYS'"
sleep 3

###---------------------------------------------------------------

TMPROOTDIR="/tmp"
TMPDIR="${TMPROOTDIR}/DevOps/Github/${SCRIPT_NAME}"
TMPFILE11="${TMPDIR}/tmp1.txt"
TMPFILE22="${TMPDIR}/tmp2.txt"
TMPFILE_FINAL="${TMPDIR}/tmp99.txt"

mkdir -p ${TMPROOTDIR}
mkdir -p ${TMPDIR}
# rm -rf "${TMPFILE11}" "${TMPFILE22}" "${TMPFILE_FINAL}"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

if [  !  -e ${TMPFILE11} ]; then
    aws lambda list-functions --output json > ${TMPFILE11}
fi
if [ "${DEBUGG}" == "y" ]; then ls -la ${TMPFILE11}; fi

FUNCTION_NAMES=$( jq '.Functions[].FunctionName' ${TMPFILE11} --raw-output )
FUNCTION_ARNS=$(  jq '.Functions[].FunctionArn'  ${TMPFILE11} --raw-output )

for FN in ${FUNCTION_NAMES[@]}; do
    # printf "${FN} .. "
    if [[ "${FN}" =~ "${CDK_APP_NAME}-backend-${ENV}-" ]]; then
        if [ "${DEBUGG}" == "y" ]; then printf "\n${FN} is a ${CDK_APP_NAME} Lambda !!!\n"; fi
        aws lambda get-function --function-name "${FN}" --output json > ${TMPFILE22}
        if [ "${DEBUGG}" == "y" ]; then ls -la ${TMPFILE22}; fi
        LOGGRP_NAME=$( jq '.Configuration.LoggingConfig.LogGroup' ${TMPFILE22} --raw-output )
        echo ${LOGGRP_NAME}
        aws logs put-retention-policy --log-group-name ${LOGGRP_NAME} --retention-in-days ${RETENTION_DAYS}
    fi
done

### EoScript
