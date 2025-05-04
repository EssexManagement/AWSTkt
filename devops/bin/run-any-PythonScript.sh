#!/bin/bash -f

if [ $# -lt 3 ]; then
echo "Usage: $0 </Absolute/Path/To/PythonScript> <AWS_PROFILE> <Tier>?? <AWSRegion> .. .. "
echo "Example: $0 devops/bin/delete_old_n_empty_CWLogGrps.py.py \${AWSPROFILE} \${AWSREGION}"
echo "Example: $0 devops/bin/list_CodeBuildIamRoles_usedByDevOpsPipeline.py \${AWSPROFILE} \${TIER} \${AWSREGION}"
echo "Example: $0 backend/lambda_layers/python_layers/bin/get_lambda_layer_hashes.py \${AWSPROFILE} \${TIER} \${AWSREGION} ../HashesForLambdaLayers.json "
echo "Example: $0 backend/lambda_layers/python_layers/bin/wipeout_deployed_lambda_layers.py \${AWSPROFILE} \${TIER} \${AWSREGION}"
exit 1
fi

### Constants

pythonScriptPath="$1"
shift

PYTHON_VERSION="3.12"

###---------------------------------------------------------------

### Derived Variables

SCRIPT_FOLDER="$(dirname ${BASH_SOURCE[0]})"
SCRIPT_NAME="$(basename ${BASH_SOURCE[0]})"
CWD="$(pwd)"

# . "${SCRIPT_FOLDER}/settings.sh"

# if [ ! -z "${PROJECT_NAME+x}" ]; then
# KNOWN_PROJ_ITEMS=~/LocalDevelopment/etc/cfn-lint-ignore_${PROJECT_NAME}.txt
# echo "Will compare with KNOWN warnings stored in ${KNOWN_PROJ_ITEMS}"
# fi

RootDir_LambdaLayers="$( dirname "${SCRIPT_FOLDER}" )" ### Grand-Parent-folder of this script.
echo "RootDir_LambdaLayers = '${RootDir_LambdaLayers}'"

# pythonScriptFolder=$( dirname -- "${SCRIPT_FOLDER}" )
pythonScriptFolder=$( dirname -- "${pythonScriptPath}" )
pythonScriptSimpleName=$( basename -- "${pythonScriptPath}" )
echo "pythonScriptFolder = '${pythonScriptFolder}'"
echo "pythonScriptSimpleName = '${pythonScriptSimpleName}'"

if [ ! -f "${pythonScriptFolder}/Pipfile.lock" ]; then
echo "Pipfile & Pipfile.lock --NOT-- found at '${pythonScriptFolder}'"
### ASSUMPTION: Pipfile & Pipfile.lock are in the --PARENT-- folder
pythonScriptFolder=$( dirname -- "${pythonScriptFolder}" )
echo "pythonScriptFolder (UPDATED) = '${pythonScriptFolder}'"
pythonScriptSimpleName="$( basename -- "${pythonScriptPath}" )/${pythonScriptSimpleName}"
echo "pythonScriptSimpleName (UPDATED) = '${pythonScriptSimpleName}'"
if [ ! -f "${pythonScriptFolder}/Pipfile.lock" ]; then
echo "Pipfile & Pipfile.lock --NOT-- found at PARENT-Folder '${pythonScriptFolder}'"
exit 86
fi
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Sanity Checks

###---------------------------------------------------------------

### PREP section

cd ${pythonScriptFolder}
pwd

# export PYTHONPATH="${PWD}/${pythonScriptFolder}/bin"
# export PYTHONPATH="${pythonScriptFolder}:${pythonScriptFolder}/bin"
export PYTHONPATH=".:..:../..:./bin"
echo "PYTHONPATH = '${PYTHONPATH}'"

pip install pipenv
## `pipenv lock --dev --python ${constantsCdk.CDK_APP_PYTHON_VERSION} --clear`,
## `pipenv install boto3 regex --ignore-pipfile`,

###---------------------------------------------------------------

### Do section

pipenv install --deploy --ignore-pipfile --dev --python "${PYTHON_VERSION}"
echo \
pipenv run python3 "${pythonScriptSimpleName}" $*
pipenv run python3 "${pythonScriptSimpleName}" $*

### EoScript
