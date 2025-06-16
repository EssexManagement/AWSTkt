from pathlib import Path
from aws_cdk import aws_lambda

from common.cdk.standard_lambda import LambdaLayerOption
from common.cdk.StandardLambdaLayer import LambdaLayerProps

props = LambdaLayerProps(
    lambda_layer_id = "weasy_pypi",
    lambda_layer_fldr = Path(__file__).parent,
    lambda_layer_sizing_option = LambdaLayerOption.SMALLEST_ZIP_FILE_SLOW_COLDSTART,

    cpu_arch = [ aws_lambda.Architecture.X86_64 ],   ### Python does NOT check.  So, make sure this is a list/ARRAY!
)

### EoF
