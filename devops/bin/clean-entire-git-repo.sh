#!/bin/bash -f

### ===============================================================================

SrcPaths=(
    api/
    backend/
    cognito/
    tests/
    user_data/

    app_pipeline/
    cdk_utils/
    common/
    devops/
    operations/
)

### ===============================================================================

### Run following at the Topmost folder of project.

echo "rm -rf ./node_modules/"
\rm -rf "./node_modules/"

echo "rm -rf ./cdk.out/"
\rm -rf "./cdk.out/"

### For each subfolder listed above ..
echo "wiping out __pycache__ sub-folders everywhere ..."
for dd in ${SrcPaths[@]}; do
    find ${dd} -name '__pycache__' -exec rm -rf {} \;
done

### EoF
