from pathlib import Path
from common.cdk.standard_lambda import LambdaLayerOption

LAMBDA_LAYER_ID = "psycopg2"
LAMBDA_LAYER_FLDR = Path(__file__).parent
# LAMBDA_LAYER_FLDR = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/psycopg'

LAMBDA_LAYER_SIZING_OPTION = LambdaLayerOption.LARGER_ZIP_FILE_FASTER_COLDSTART

### ==========================================================================================================

### private constants.
# _LAMBDA_LAYER_BUILDER_SCRIPT = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/bin/etl-lambdalayer-builder-venv.sh'
### x86_764: pip3 install --platform manylinux2014_x86_64  --target . --python-version 3.12 --only-binary=:all: psycopg2-binary
### arm64:   pip3 install --platform manylinux2014_aarch64 --target . --python-version 3.12 --only-binary=:all: psycopg2-binary
        ### REF: https://medium.com/@bloggeraj392/creating-a-psycopg2-layer-for-aws-lambda-a-step-by-step-guide-a2498c97c11e

# _ZIP_FILE_SIMPLENAME = "psycopg-layer-{}.zip"
### Assuming it will be created into the folder specified via the `layer_fldr_path` param below.
### For accuracy, check the `Dockerfile` within `lambda_layer/psycopg` subfolder.

### EoF