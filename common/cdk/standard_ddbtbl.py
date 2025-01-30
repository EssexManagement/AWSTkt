"""
*   NOT-in-SCOPE: Archiving (Data-Retention) the TTL-expired data from DynamoDB-Table into S3 -- via AWS Official Recommendation.

*   A function "create_nccr_ddb_tbl()" -- which should be used in place of -ALL- instances of "aws_dynamodb.Table(..)";

*   RETENTION & ARCHIVAL:
*   REF: Overall-Diagram: https://docs.aws.amazon.com/images/prescriptive-guidance/latest/patterns/images/pattern-img/e2a9c412-312e-4900-9774-19a281c578e4/images/32d21957-9072-48b5-87b4-df141f235238.png
*   REF: AWS Official Documentation https://docs.aws.amazon.com/solutions/latest/constructs/aws-kinesisstreams-kinesisfirehose-s3.html
*       REF: Construct-ONLY Diagram at https://docs.aws.amazon.com/images/solutions/latest/constructs/images/aws-kinesisstreams-kinesisfirehose-s3.png
*   Not applicable as Python -NOT- Supported --> AWS Official Documentation: https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/deliver-dynamodb-records-to-amazon-s3-using-kinesis-data-streams-and-amazon-data-firehose-with-aws-cdk.html
*           Not applicable as Python -NOT- Supported --> https://github.com/aws-samples/aws-dynamodb-kinesisfirehose-s3-ingestion/
*           So, re-implementing in Python (in a simpler manner). <------ <------- <------
"""

from typing import Optional
from constructs import Construct
from aws_cdk import (
    Duration,
    aws_dynamodb,
    RemovalPolicy,
)

from constants import STD_TIERS

### ======================================================================================================

from common.cdk.retention_base import (
    DATA_CLASSIFICATION_TYPES,
    DataClassification,
)

### ======================================================================================================
### ******************************************************************************************************
### ======================================================================================================

""" Create a DynamoDB-Table per NCCR standards - as appropriate for the `data_classification_type`.
    Any parameter Not passed will be appropriately set per the `data_classification_type`.
"""


def standard_dynamodb_table(
    scope: Construct,
    id: str,
    tier: str,
    data_classification_type: DATA_CLASSIFICATION_TYPES,
    partition_key: aws_dynamodb.Attribute,
    sort_key: aws_dynamodb.Attribute,
    ddbtbl_name: Optional[str] = None,
    local_secondary_indexes :aws_dynamodb.LocalSecondaryIndexProps = None,
    global_secondary_indexes :aws_dynamodb.GlobalSecondaryIndexPropsV2 = None,
    removal_policy: RemovalPolicy = None,
    deletion_protection: bool = False,
    encryption: aws_dynamodb.TableEncryptionV2 = None,
    table_class: aws_dynamodb.TableClass = aws_dynamodb.TableClass.STANDARD,
    ddbstream_type :Optional[aws_dynamodb.StreamViewType] = None,
    billingV2: Optional[aws_dynamodb.Billing] = None,
    # billing_mode_V1: aws_dynamodb.BillingMode = aws_dynamodb.BillingMode.PAY_PER_REQUEST,
    time_to_live_attribute: str = "expireAt",
    **kwargs,
) -> aws_dynamodb.Table:

    removal_policy2: RemovalPolicy = (
        removal_policy
        if removal_policy
        else DataClassification.removal_policy(tier=tier, data_type=data_classification_type)
    )

    ### TODO - restore this commented line below (so that all branches can have stacks automatically destroyed)
    deletion_protection2: bool = (
        deletion_protection
        if deletion_protection
        else (removal_policy2 == RemovalPolicy.RETAIN or removal_policy2 == RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE)
    )
    ### `removal-policy` can fix/override `deletion-protection` to True.
    print(f"removal_policy='{removal_policy2}' and deletion_protection2='{deletion_protection2}'")

    return aws_dynamodb.TableV2(
        scope=scope,
        id = id,
        table_name = ddbtbl_name,
        partition_key = partition_key,
        sort_key = sort_key,
        global_secondary_indexes = global_secondary_indexes,
        time_to_live_attribute = time_to_live_attribute,
        removal_policy = removal_policy2,
        deletion_protection = deletion_protection2,
        encryption = encryption,
        billing = billingV2,
        table_class = table_class,
        point_in_time_recovery = True,
        dynamo_stream = ddbstream_type,
        **kwargs,
    )


### ======================================================================================================

""" Per AWS best-practice.
    Most of the items in DDB-Table shuld have TTL set.
    All expired items will be streamed OUT (to a Kinesis), which is then stored into S3.
"""


def setup_ddbtbl_archival(
    tier: str,
    data_classification_type: DATA_CLASSIFICATION_TYPES,
    keep_older_versions: bool = False,  ### Whether to QUICKLY-delete the OLDER versions of ANY S3-object -- or not.
    enabled: bool = True,
):

    id = f"{tier}'s EXPIRE-data in 90-days - default for all Data"

    expiration = Duration.days(
        DataClassification.retention_for(
            tier=tier,
            data_type=DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY,
            # data_type = DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS if tier == "prod" else DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY
        )
    )


### ======================================================================================================


### EoF
