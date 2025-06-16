### Attention: This is the authoritative list of all layers to be DEPLOYED !!!

from common.cdk.StandardLambdaLayer import LambdaLayerProps

from backend.lambda_layer.psycopg.LayerConfig import props as lambda_layer_psycopg
from backend.lambda_layer.psycopg_pandas.LayerConfig import props as lambda_layer_psycopg_pandas
from backend.lambda_layer.psycopg3.LayerConfig import props as lambda_layer_psycopg3
from backend.lambda_layer.psycopg3_pandas.LayerConfig import props as lambda_layer_psycopg3_pandas
from backend.lambda_layer.numpy_etc.LayerConfig import props as lambda_layer_numpy_etc

from backend.lambda_layer.weasy_makefile.LayerConfig import props as lambda_layer_weasy_makefile
from backend.lambda_layer.weasy_pypi.LayerConfig import props as lambda_layer_weasy_pypi

LAYER_MODULES :list[LambdaLayerProps]= [
    lambda_layer_psycopg,
    lambda_layer_psycopg_pandas,
    lambda_layer_psycopg3,
    lambda_layer_psycopg3_pandas,
    lambda_layer_numpy_etc,

    lambda_layer_weasy_makefile,
    lambda_layer_weasy_pypi,
]

### EoF
