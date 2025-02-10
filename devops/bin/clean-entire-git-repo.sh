#!/bin/bash -f

### ===============================================================================

SrcPaths=(
    backend
    api
    cognito
    tests
    user_data

    app_pipeline
    cdk_utils
    common
    devops
    operations
)

DevOpsSrcPaths=(
    devops/1-click-end2end
    devops/post-deployment
    devops/cleanup-stacks
)

### ===============================================================================


for dd in ${DevOpsSrcPaths[@]}; do
    \rm -rf "${dd}/node_modules/"
    \rm -rf "${dd}/cdk.out/"
done

for dd in ${SrcPaths[@]}; do
    find ${dd} -name '__pycache__' -exec rm -rf {} \;
done

### EoF
