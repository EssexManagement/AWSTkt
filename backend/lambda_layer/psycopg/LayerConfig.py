from pathlib import Path
from common.cdk.standard_lambda import LambdaLayerOption
from common.cdk.StandardLambdaLayer import LambdaLayerProps

props = LambdaLayerProps(
    lambda_layer_id = "psycopg",
    lambda_layer_fldr = Path(__file__).parent,
    # lambda_layer_fldr = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/psycopg',
    lambda_layer_sizing_option = LambdaLayerOption.LARGER_ZIP_FILE_FASTER_COLDSTART,
)

### EoF
