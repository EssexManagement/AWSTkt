#!/bin/bash -f

if [ $# -le 5 ]; then
    echo "Usage: $0 <AWS-CLI-Profile>  <Tier>  <resource-name> <tag-command>"
    echo "Example: $0 CTF-nonprod-devops dev   secretsmanager   tag-resource  --secret-id    ${SecretId}"
    echo "Example: $0 CTF-nonprod-devops dev   ec2   create-tags  --resources    ${ARN}"
    echo "Example: $0 CTF-nonprod-devops dev   tag-resource --resource-arn ${ARN}"
    exit 1
fi

##__ AWSPROFILE="CTF-nonprod-devops";
AWSPROFILE="$1"
AWSREGION="us-east-1";
TIER="$2";
shift
shift

Tags=(
    "Key"="application","Value"="CTF"
    "Key"="ApplicationName","Value"="cancertrialsfinder"
    "Key"="aws_env","Value"="CTF-nonprod"
    "Key"="component","Value"="backend"
    "Key"="ENVIRONMENT","Value"="dev"
    "Key"="EnvironmentTier","Value"="DEV"
    "Key"="git_branch","Value"="N/A"
    "Key"="PRODUCT","Value"="cancertrialsfinder"
    "Key"="Project","Value"="cancertrialsfinder"
    "Key"="repo","Value"="CBIIT/CancerTrialsFinder.git"
    "Key"="ResourceFunction","Value"="backend"
    "Key"="ResourceName","Value"="CTF-backend-acct-nonprod"
    "Key"="SOURCE","Value"="CBIIT/CancerTrialsFinder.git"
    "Key"="tier","Value"="acct-nonprod"
    "Key"="VERSION","Value"="main"
)

TagTags=()
for kvpair in ${Tags[@]}; do
    tagsPair=${kvpair}
    tagsPair=$( echo ${tagsPair} | sed -e 's|"*Key"*=|TagKey=|' )
    tagsPair=$( echo ${tagsPair} | sed -e 's|"*Value"*=|TagValue=|' )
    # tagsPair=$( echo ${tagsPair} | tr "," " " )
    TagTags+=( "${tagsPair}" )
done

# echo "${TagTags[@]}"

echo; echo;
echo \
aws $* --tags ${Tags[@]} --profile ${AWSPROFILE} --region ${AWSREGION}
echo;
echo "AWS-Service is = '$1'"; echo;
read -p "Proceed? >>" ANS

if [ "$1" == "kms" ];  then
    aws $* --tags ${TagTags[@]} --profile ${AWSPROFILE} --region ${AWSREGION}
else
    aws $* --tags ${Tags[@]} --profile ${AWSPROFILE} --region ${AWSREGION}
fi

### EoScript
