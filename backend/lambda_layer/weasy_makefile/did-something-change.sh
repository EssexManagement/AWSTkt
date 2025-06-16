#!/bin/bash -f

### The whole point of this script is to CATCH developer-mistakes.
### When any of the below files are changed, but the `HashInput.txt` is -NOT- updated and -NOT- committed into git .. (a developer mistake) ..
### Make-command should FAIL, if that happens.

### The contents of "HashInput.txt" is used within Pipeline (specifically, `backend/lambda_layer/lambda_layers_builder_stacks.py`) ..
###     .. to determine if anything changed in this 𝜆-Layer, and if a new version of the 𝜆-Layer needs to be deployed.

set -e

HashingInputFile="HashInput.txt"

ListOfFiles=(
    "Dockerfile"
    "LayerConfig.py"
    "Makefile"
    "weasyprint/Makefile"
    "weasyprint/layer_builder.sh"
    "weasyprint/README.md"
    "fonts/layer_builder.sh"
)

### --------------------------------------------------------

cat ${ListOfFiles[@]} > ${HashingInputFile}
# cat "Dockerfile" "LayerConfig.py" "Makefile" "weasyprint/layer_builder.sh" "fonts/Makefile" "fonts/layer_builder.sh" > ${HashingInputFile}

numOfLinesChanged=$( git diff ${HashingInputFile} | wc -l )
echo "numOfLinesChanged='${numOfLinesChanged}'"

### --------------------------------------------------------

if [ ${numOfLinesChanged} -eq 0 ]; then
    echo "HashInput is trustworthy.  All good.✅"
    exit 0
else
    echo "❌ NOT Acceptable! Something changed ⚠️ .. within one or more of ${ListOfFiles[@]}"
    exit 1
fi

### EoScript
