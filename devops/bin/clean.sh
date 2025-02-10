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

### Topmost folder of project.
\rm -rf "./node_modules/"
\rm -rf "./cdk.out/"

### For each subfolder listed above ..
for dd in ${SrcPaths[@]}; do
    find ${dd} -name '__pycache__' -exec rm -rf {} \;
done

### EoF
