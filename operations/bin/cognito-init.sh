#!/bin/bash -f


if [ $# -ge 1 ]; then
    if [ "$1" == "--resend" ]; then
        RESEND="y"
        shift  ### <---------
    fi
    if [ "$1" == "--PRE-register-users" ]; then
        PreRegister="y"
        shift  ### <---------
    fi
fi
if [ $# -ne 2 ]; then
    echo "Usage: $0 {TIER} {AWSPROFILE}"
    echo "Usage: $0 --PRE-register-users {TIER} {AWSPROFILE}"
    echo "WARNING !! Advanced-Usage: $0 --resend {TIER} {AWSPROFILE}"
    echo ''; echo ''; # read -p "CONTINUE? [^C to cancel]>>" ANS
    exit 1
fi
export Tier="$1"
export TIER="${Tier}"
export AWSPROFILE="$2"
printf "\t\tYou've specified Tier ='${Tier}'\n"
printf "\t\tYou've specified AWSPROFILE ='${AWSPROFILE}'\n\n"

###---------------------------------------------------------------

SCRIPT_FOLDER=$(dirname -- "$0")
SCRIPT_NAME=$(basename  -- "$0")
CWD="$(pwd)"

###---------------------------------------------------------------
### Now based on Tier, define variables like `COGNITO_USERPOOL_ID` etc..


.  ${SCRIPT_FOLDER}/common-settings.sh


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Section: derived variables & TEMP-FILES

echo \
aws cognito-idp describe-user-pool --user-pool-id ${COGNITO_USERPOOL_ID} ${AWSPROFILEREGION[@]} --output json
aws cognito-idp describe-user-pool --user-pool-id ${COGNITO_USERPOOL_ID} ${AWSPROFILEREGION[@]} --output json > /dev/null
if [ $? -ne 0 ]; then
    printf "\n!! ERROR !! Invalid AWS-Credentials or Invalid USERPOOL-ID='${COGNITO_USERPOOL_ID}'\n"
    exit 88
fi

EXISTING_COGNITO_GROUPNAME=$( aws cognito-idp list-groups --user-pool-id ${COGNITO_USERPOOL_ID} ${AWSPROFILEREGION[@]} --output json | jq '.Groups[0].GroupName' --raw-output )

if [ "${EXISTING_COGNITO_GROUPNAME}" == "null" ]; then
    printf "\t\t👉🏾👉🏾 EXISTING_COGNITO_GROUPNAME='${EXISTING_COGNITO_GROUPNAME}'\n"
    echo '';echo ''; read -p "CONTINUE with creating a NEW Group in Cognito? [^C to cancel]>>" ANS
    aws cognito-idp create-group --user-pool-id ${COGNITO_USERPOOL_ID}   \
            --group-name ${COGNITO_GROUPID}                         \
            --description "The only valid Group containing ALL users - internal as well as external/internet-users"     \
            ${AWSPROFILEREGION[@]}
    aws cognito-idp create-group --user-pool-id ${COGNITO_USERPOOL_ID}   \
            --group-name ${COGNITO_ADMIN_GROUPID}                         \
            --description "The only valid Group containing ADMIN-users - Super-power privileges alert!!"     \
            ${AWSPROFILEREGION[@]}
else
    printf "\t\t✅ EXISTING_COGNITO_GROUPNAME='${EXISTING_COGNITO_GROUPNAME}'\n"
fi

###---------------------------------------------------------------

### https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/admin-create-user.html

cat >> "${TMPFILE11}" <<EOTXT
[
    { "username": "richard", "email": "richard.takamoto@nih.gov" },
    { "username": "david", "email": "loosed@mail.nih.gov" },
    { "username": "sandy", "email": "sandy.chon@nih.gov" },
    { "username": "melissa", "email": "melissa.marver@nih.gov" },
    { "username": "idongesit.inyang", "email": "idongesit.inyang@nih.gov" },
    { "username": "jennifer.harvey", "email": "jennifer.harvey@nih.gov" },
    { "username": "jeremy", "email": "jeremy.pumphrey@nih.gov" },
    { "username": "matthew.mariano", "email": "matthew.mariano@nih.gov" },
    { "username": "mark", "email": "mark.hanna@nih.gov" },
    { "username": "sarma", "email": "sarma.seetamraju@nih.gov" }
]
EOTXT
    # { "username": "jada.andrade", "email": "jada.andrade@nih.gov" },
    # { "username": "hubert.hickman", "email": "hubert.hickman@nih.gov" },
    # { "username": "frankie", "email": "frankie.parks@nih.gov" },
    # { "username": "hong", "email": "cheunghd@nih.gov" },
    # { "username": "tony", "email": "tony.fu@nih.gov" },

if [ -z ${PreRegister+x} ]; then
    echo "FYI: Not pre-registering -ANY- user in Cognito"
else

        USERNAMES=$( jq --raw-output '.[] | .username' "${TMPFILE11}" )
        for USERNAME in ${USERNAMES}; do
            printf "\t\tUSERNAME='${USERNAME}'"
            EMAIL=$( jq --raw-output --arg USERNAME "${USERNAME}" '.[] | select(.username == $USERNAME) | .email' "${TMPFILE11}" )
            printf "\tEMAIL='${EMAIL}'\t\t"

            if [ "${RESEND}" == "y" ]; then
                ADDL_CLI_ARG="--message-action RESEND"
                while read -t 1 -r; do read -r -t 1; done
                read -p "Resend for '${USERNAME}' ? [N]>" ANS
                if [ "${ANS}" != "y" ] && [ "${ANS}" != "Y" ]; then
                    printf "🚮 skipping ..\n"
                    continue
                fi
            else
                ADDL_CLI_ARG=""
            fi

            sleep 2
            set -x
            aws cognito-idp admin-create-user --user-pool-id ${COGNITO_USERPOOL_ID}      \
                    --desired-delivery-mediums EMAIL                \
                    --username ${USERNAME}                          \
                    ${ADDL_CLI_ARG}                                 \
                    --user-attributes Name=email,Value=${EMAIL}     \
                    ${AWSPROFILEREGION[@]}
            set +x

            ### Do NOT use for NEW-USER ----->  --message-action RESEND

            set -x
            aws cognito-idp admin-add-user-to-group --user-pool-id ${COGNITO_USERPOOL_ID}    \
                    --username ${USERNAME} --group-name ${COGNITO_GROUPID}  \
                    ${AWSPROFILEREGION[@]}
            set +x

        done

fi ### if PreRegister

### EoF
