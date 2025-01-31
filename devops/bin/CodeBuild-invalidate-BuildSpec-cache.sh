if [ $# != 3 ]; then
    echo "Usage: $0 <Tier> <AWSPROFILE> <AWSREGION>"
    exit 1
fi

Tier="$1"
AWSPROFILE="$2"
AWSREGION="$3"

ComponentName="backend"
CDKAppName="FACT"

DEBUG="true"
DEBUG="false"

RelevantCBProjectList=(
    "${CDKAppName}-${ComponentName}-${Tier}_Appln_CDKSynthDeploy"
    "${CDKAppName}-${ComponentName}-${Tier}_LambdaLayer-arm64"
    "${CDKAppName}-${ComponentName}-${Tier}_LambdaLayer-amd64"
)

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

### Define the temporary files (to save the output of JQ commands below)
###------------ SCRATCH-VARIABLES & FOLDERS ----------

# TMPROOTDIR="/tmp/${MyCompanyName}"
TMPROOTDIR="/tmp/devops"
if [ -z ${SCRIPTFOLDER+x}          ]; then SCRIPTFOLDER=$(dirname -- "$0");                   fi
if [ -z ${SCRIPTNAME+x}            ]; then SCRIPTNAME=$(basename -- "$0");                    fi
if [ -z ${SCRIPTFOLDER_FULLPATH+x} ]; then SCRIPTFOLDER_FULLPATH="$(pwd)/${SCRIPTFOLDER}";    fi
# echo "${SCRIPTFOLDER_FULLPATH}"
if [ -z ${TMPDIR+x}                ]; then TMPDIR="${TMPROOTDIR}/DevOps/${PROJECTID}/${SCRIPTNAME}"; fi

mkdir -p "${TMPROOTDIR}"
mkdir -p "${TMPDIR}"

touch ${TMPDIR}/junk ### To ensure rm commands (under noglob; see many lines below) always work.

TMPFILE11=${TMPDIR}/tmp1.txt
TMPFILE22=${TMPDIR}/tmp22.txt
TMPDIFFOUTP=${TMPDIR}/tmp333.txt

rm -rf "${TMPFILE11}" "${TMPFILE22}" "${TMPDIFFOUTP}"

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

aws codebuild list-projects --profile ${AWSPROFILE} --region ${AWSREGION} > ${TMPFILE11}
CBProjectNameList=$( jq '.projects[]' --raw-output ${TMPFILE11} )

for CBProjectName in ${CBProjectNameList}; do
    if [ "${DEBUG}" == "true" ]; then echo "CBProjectName: ${CBProjectName}"; fi
    for RelevantCBProjectNameRegex in ${RelevantCBProjectList[@]}; do
        if [[ "$CBProjectName" == "${RelevantCBProjectNameRegex}"* ]]; then
            echo " CBProjectName '${CBProjectName}' starts with ${CDKAppName}"
            echo \
            aws codebuild invalidate-project-cache --project-name "${CBProjectName}" --profile ${AWSPROFILE} --region ${AWSREGION}
            aws codebuild invalidate-project-cache --project-name "${CBProjectName}" --profile ${AWSPROFILE} --region ${AWSREGION}
        else
            if [ "${DEBUG}" == "true" ]; then echo "CBProjectName '${CBProjectName}' does --NOT-- start with ${CDKAppName}"; fi
            echo -n '.'
        fi
    done
done

### EoF
