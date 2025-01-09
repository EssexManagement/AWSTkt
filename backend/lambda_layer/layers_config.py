### Attention: This is the authoritative list of all layers to be DEPLOYED !!!

import backend.lambda_layer.psycopg.lambda_layer_psycopg as lambda_layer_psycopg
import backend.lambda_layer.psycopg_pandas.lambda_layer_psycopg_pandas as lambda_layer_psycopg_pandas
import backend.lambda_layer.psycopg3.lambda_layer_psycopg3 as lambda_layer_psycopg3
import backend.lambda_layer.psycopg3_pandas.lambda_layer_psycopg3_pandas as lambda_layer_psycopg3_pandas

LAYER_MODULES = [
    lambda_layer_psycopg,
    lambda_layer_psycopg_pandas,
    lambda_layer_psycopg3,
    lambda_layer_psycopg3_pandas,
]

### EoF
