from pathlib import Path
from aws_cdk import aws_lambda

import constants
import common.cdk.constants_cdk as constants_cdk
from common.cdk.standard_lambda import LambdaLayerOption
from common.cdk.StandardLambdaLayer import LambdaLayerProps

pyver = constants_cdk.LAMBDA_PYTHON_RUNTIME_VER_STR
cpustr = aws_lambda.Architecture.X86_64.name

props = LambdaLayerProps(
    lambda_layer_id = "weasy",
    lambda_layer_fldr = Path(__file__).parent,
    # lambda_layer_fldr = constants.PROJ_ROOT_FLDR_PATH / 'api/lambda_layer/psycopg',
    lambda_layer_sizing_option = LambdaLayerOption.LARGER_ZIP_FILE_FASTER_COLDSTART,

    cpu_arch = [ aws_lambda.Architecture.X86_64 ],   ### Python does NOT check.  So, make sure this is a list/ARRAY!
    builder_cmd = f"make CPU_ARCH={cpustr} RUNTIME={pyver}",
    lambda_layer_zipfilename = f"layer-weasyprint-{pyver}-{cpustr}.zip",
    # lambda_layer_zipfilename = f"layer-weasyprint-3.12-x86_64.zip",
)

### EoF
