#!/bin/bash -f

### For each subfolder in here, iterate over each subfolder .. ..
### detect if there's a package.json, and if yes, `\rm -rf package-lock.json node_modules/ build/ dist/ cdk.out/ ; npm i ; npm run build`

shopt -s dotglob

pwd

for d in $( ls ) ; do
    if [ -d "$d" ] && [ "$d" != "." ] && [ "$d" != ".." ]; then
        echo ; printf '%.s_' {1..80}; echo;
        pushd $d

        if [ -f package.json ]; then
            echo \
            rm -rf package-lock.json node_modules/ build/ dist/ cdk.out/
            rm -rf package-lock.json node_modules/ build/ dist/ cdk.out/

            echo "running npm-i and npm-run-build inside subfolder './${d}/' .."
            npm i
            npm run build
        fi
        popd
    else
        echo "Skipping NON-Folder '${d}' .."
    fi
done
