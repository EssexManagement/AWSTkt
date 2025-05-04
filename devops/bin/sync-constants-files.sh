#!/bin/bash -f

### This script is used to keep a list of files in sync, with the authoritative source, which is the `constants.py` in the root of the project.
### If the file is not identical to the authoritative file, the user will be prompted to overwrite the file.
### If the user does not provide any input other than "YyNn", it be considered as a distracted or dont-care-type-of-user, and so, the script will exit.
### If the user provides "Yy", the file will be overwritten.

set -euo pipefail

ORIG="${PWD}/constants.py"
pwd

ListOfFiles=(
    "./backend/etl/runtime/constants.py"
    # "./backend/etl/runtime/common/constants.py" <------- Leave this alone. It is mostly list of mime-types
    "./api/runtime/constants.py"
    # "./api/runtime/common/constants.py"         <------- Leave this alone. It is mostly list of mime-types
    "./api/runtime_report/src/constants.py"
)

### -----------------------------------------------------------------

checkFile() {
    echo -n "${1} .."
    if [ ! -f "${1}" ]; then
        echo "❌❌❌ File '${1}' does not exist (working-dir=${PWD})"
        exit 68
    fi
    if [ ! -f "${ORIG}" ]; then
        echo "❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌ Original-File '${ORIG}' does not exist ❌❌❌❌❌❌❌❌❌)"
        exit 68
    fi
    set +e
    diff "${ORIG}" "${1}" > /dev/null
    EXIT_CODE="$?"
    set -e
    if [ ${EXIT_CODE} -eq 0 ]; then
        echo "✅"
    else
        echo ''
        echo "File '${1}' is ❌ NOT identical to ${ORIG} (working-dir=${PWD})"
        echo ''; echo "diff '${ORIG}' '${1}'"; echo ''
        # Ask user whether to overwrite the file and if user provides any input other than "YyNn", exit this script.  If "Yy", overwrite the file
        read -p "Overwrite file? (Y/n) >> " -n 1 -r REPLY
        if [[    !    "${REPLY}" =~ ^[YyNn]$ ]]; then
            return
            # [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 ### handle exits from shell or function but don't exit interactive shell
        else
            if [[ "${REPLY}" =~ ^[Yy]$ ]]; then
                cp -ip "${ORIG}" "${1}"
            fi
        fi
    fi
}

### -----------------------------------------------------------------

for file in "${ListOfFiles[@]}"; do
    checkFile "$file"
done

### EoScript
