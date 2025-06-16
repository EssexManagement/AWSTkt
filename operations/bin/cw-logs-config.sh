#!/bin/bash -f

### Since setting CW-Log-Group retention blows up the Cloudformation-file-sizes, we're manually setting it via this script file.


###---------------------------------------------------------------

if [ $# -le 1 ]; then
    printf "\nUsage: $0 [--debug]  <AWS-CLI-Profile>  <Tier>\n"
    printf "\t\t\t\t\t\tdev|int|stage|uat|prod\n"
    echo "Example: $0 CTF-nonprod-devops dev"
    exit 1
fi

if [ "$1" == "--debug" ]; then
    DEBUGG="y"
    shift
fi

##__ AWSPROFILE="CTF-nonprod-devops";
CDK_APP_NAME="CTF"
AWSPROFILE="$1"
AWSREGION="us-east-1";
TIER="$2";
# printf "\t\tYou've specified environment ='${TIER}'\n"

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


if [ "${TIER}" == "dev" ]; then
    RETENTION_DAYS=5
else
    if [ "${TIER}" == "int" ]; then
        RETENTION_DAYS=5
    else
        if [ "${TIER}" == "uat" ]; then
            RETENTION_DAYS=365
        else
            if [ "${TIER}" == "prod" ]; then
                RETENTION_DAYS=365
            else
                printf "\n!! ERROR !! Invalid cli-arg '${TIER}' passed in.  Should be dev|int|uat|prod only\n"
                exit 9
            fi
        fi
    fi
fi
echo "RETENTION_DAYS='$RETENTION_DAYS'"
sleep 3

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

read -p "Should we check EVERY-SINGLE 𝜆 and its LogGrp?  [yN] >>" ANS
if [[ "${ANS}" == "y" || "${ANS}" == "Y" ]]; then

        if [  !  -e ${TMPFILE11} ]; then
            aws lambda list-functions ${AWSPROFILEREGION[@]} --output json > ${TMPFILE11}
        fi
        if [ "${DEBUGG}" == "y" ]; then ls -la ${TMPFILE11}; fi

        FUNCTION_NAMES=$( jq '.Functions[].FunctionName' ${TMPFILE11} --raw-output )
        # FUNCTION_ARNS=$(  jq '.Functions[].FunctionArn'  ${TMPFILE11} --raw-output )

        for FN in ${FUNCTION_NAMES[@]}; do
            # printf "${FN} .. "
            if [[ "${FN}" =~ "${CDK_APP_NAME}-backend-${TIER}-" ]]; then
                if [ "${DEBUGG}" == "y" ]; then printf "\n${FN} is a ${CDK_APP_NAME} Lambda !!!\n"; fi
                aws lambda get-function --function-name "${FN}" ${AWSPROFILEREGION[@]} --output json > ${TMPFILE22}
                if [ "${DEBUGG}" == "y" ]; then ls -la ${TMPFILE22}; fi
                LOGGRP_NAME=$( jq '.Configuration.LoggingConfig.LogGroup' ${TMPFILE22} --raw-output )
                echo ${LOGGRP_NAME}
                aws logs put-retention-policy --log-group-name ${LOGGRP_NAME} --retention-in-days ${RETENTION_DAYS} ${AWSPROFILEREGION[@]}
            fi
        done

fi

echo; read -p "Proceed to checking all LogGrps, to identify + FIX any with invalid retention-period ?? [enter to continue] >>"

# get the list of log-groups, iterate over each one of them, and increase all log-group retention to 12 months.
aws logs describe-log-groups ${AWSPROFILEREGION[@]} --output json > ${TMPFILE11}
if [ "${DEBUGG}" == "y" ]; then ls -la ${TMPFILE11}; fi
LOGGRP_NAMES=$( jq '.logGroups[].logGroupName' ${TMPFILE11} --raw-output )
for LG in ${LOGGRP_NAMES[@]}; do
    if [ "${DEBUGG}" == "y" ]; then printf " .. ${LG}"; else echo -n '.'; fi
    # if the Log Group's retention is < 12 months, then increase it to 12 months.
    aws logs describe-log-groups --log-group-name-prefix ${LG} ${AWSPROFILEREGION[@]} --output json > ${TMPFILE22}
    LoGrpRetDays=$( jq '.logGroups[].retentionInDays' ${TMPFILE22} --raw-output )
    if [ "${DEBUGG}" == "y" ]; then printf ": ${LoGrpRetDays} days.. "; fi
    if [[ "${LoGrpRetDays}" == "null" || ${LoGrpRetDays} -lt ${RETENTION_DAYS} ]]; then
        if [ "${DEBUGG}" == "y" ]; then printf "\n\nIncreasing retention from ${LoGrpRetDays} to ${RETENTION_DAYS}]\n"; fi
        echo \
        aws logs put-retention-policy --log-group-name ${LG} --retention-in-days 365 ${AWSPROFILEREGION[@]}
        aws logs put-retention-policy --log-group-name ${LG} --retention-in-days 365 ${AWSPROFILEREGION[@]}
        echo;
    fi
done

### EoScript
