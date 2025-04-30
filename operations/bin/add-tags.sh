#!/bin/bash -f

if [ $# -le 1 ]; then
    echo "Usage: $0 <resource-name> <tag-command>"
    echo "Example: $0 ec2   create-tags  --resources    ARN"
    echo "Example: $0 sesv2 tag-resource --resource-arn ARN"
    exit 1
fi

AWSPROFILE="CTF-nonprod-devops";
AWSREGION="us-east-1";
TIER="dev";

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

echo; echo;
echo \
aws $* --tags ${Tags[@]} --profile ${AWSPROFILE} --region ${AWSREGION}
echo;
read -p "Proceed? >>" ANS

aws $* --tags ${Tags[@]} --profile ${AWSPROFILE} --region ${AWSREGION}

### EoScript
