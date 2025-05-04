#!/bin/bash -f


### Cleanup working-scratch-files from under "~/operations/" top-level subfolder.

echo "Usage: $0 [--include-Pipfile.lock]"
sleep 5

if [ "$1" == "--include-Pipfile.lock" ]; then
    shift
    DELETE_Pipfile_LOCK="y"
else
    unset DELETE_Pipfile_LOCK
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Constants

PYTHON_VERSION="3.12"

###---------------------------------------------------------------

### Derived Variables

SCRIPT_FOLDER="$(dirname ${BASH_SOURCE[0]})"
SCRIPT_NAME="$(basename ${BASH_SOURCE[0]})"
CWD="$(pwd)"

# .  "${SCRIPT_FOLDER}/settings.sh"

# if [ ! -z "${PROJECT_NAME+x}" ]; then
#     KNOWN_PROJ_ITEMS=~/LocalDevelopment/etc/cfn-lint-ignore_${PROJECT_NAME}.txt
#     echo "Will compare with KNOWN warnings stored in ${KNOWN_PROJ_ITEMS}"
# fi

RootDir_BackendCode="./backend"
RootDir_OperationsCode="./operations"
echo "RootDir_OperationsCode = '${RootDir_OperationsCode}'"


# Bash-flag to appropriately set `glob` (allow '*' to work)
set +o noglob

DirEntry_List=$(   ### <------------------------ Unique to this file !!!! <------------------------
    ls -d "${RootDir_OperationsCode}/CDK/"*
    ls -d "${RootDir_OperationsCode}/AWS-SAM/"*
    ls -d "${RootDir_BackendCode}/lambda_layer/"*
)

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Sanity Checks

###---------------------------------------------------------------

### Do section

# echo ''; printf '%.0s=' {1..160}; echo ''; printf '%.0s=' {1..160}; echo ''; echo '';

\rm -rf ~/.cache/ ~/.local/ ~/.venv/ ~/node_modules  ./node_modules  ./.venv   ./__pycache__

\rm -rf ./frontend/ui/dist/   ./frontend/ui/node_modules

\rm -rf ${RootDir_OperationsCode}/node_modules  ${RootDir_OperationsCode}/__pycache__

# Loop over each subfolder of RootDir_OperationsCode and if subfolder does Not have a "Pipfile" skip it
for subfolder in ${DirEntry_List[@]}; do
    if [ ! -d "${subfolder}" ]; then
        echo -n "skipping NON-dir '$( basename ${subfolder} )' ..  "
        continue
    fi

    ls -lad "${subfolder}"
    # echo "Pipfile path for subfolder = '${subfolder}/Pipfile'"
    # ls -la "${subfolder}/Pipfile"
    if [ ! -f "${subfolder}/package.json" ] && [ ! -f "${subfolder}/Pipfile" ] && [ ! -f "${subfolder}/template.yaml" ] && [ ! -f "${subfolder}/requirements.in" ] && [ ! -f "${subfolder}/requirements.txt" ]; then
        echo -n "skipping '$( basename ${subfolder} )' as it does --NOT-- have package.json NOR Pipfile.lock NOR AWS-SAM  ..  "
        continue
    fi

    echo ''; echo "👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾 ${subfolder} contains a devops-utility !"
    cd "${subfolder}"

    \rm -rf ./.venv/ ./.cache/  ./.local/  ./.aws-sam/  ./__pycache__/  ./cdk.out/  ./dist/ ./build/   ./node_modules/  ./src/node_modules/  ./cdk.out/
    \rm -rf *.egg-info *.dist-info .pytest_cache .mypy_cache .tox .coverage .coverage.* .hypothesis

    while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
    read -p "Re-create the 'package-LOCK.json' ? [y/N] >> " ANSWER
    if [[ $ANSWER =~ ^[Yy]$ ]]; then
        npm i --include-dev
    fi

    if [ ! -z "${DELETE_Pipfile_LOCK+x}" ]; then
        \rm -f Pipfile.lock
        \rm -f requirements.txt
        find "${subfolder}" -name '__pycache__' -depth -5 -exec rm -rf {} \;

        while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
        read -p "Re-create the 'Pipfile.lock' ? [y/N] >> " ANSWER
        if [[ $ANSWER =~ ^[Yy]$ ]]; then
            pip install pipenv > /dev/null
            echo \
            pipenv lock --dev --clear --python ${PYTHON_VERSION}
            pipenv lock --dev --clear --python ${PYTHON_VERSION}
        fi
    fi

    cd - > /dev/null

done

### EoScript
