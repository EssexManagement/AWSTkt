"""
This file has the following for public use across the project.
*   2 enums "DATA_CLASSIFICATION_TYPES" and "S3_LIFECYCLE_RULES"
*   A class "DataClassification" and it's STATIC methods "retention_for()" "removal_policy()" and "versioning()"; The 4th method "default_retention()" should only be used EARLY in the development, and should be replaced with "retention_for()".
*   A function "create_nccr_bucket()" -- which should be used in place of -ALL- instances of "aws_s3.Bucket(..)";
*   A function "gen_bucket_props()" -- which should be used when Buckets are AUTO-created by level-2 and level-3 CDK-constructs (example: aws_cloudfront.BucketDeployment, etc..)
"""

from typing import Optional
from enum import Enum, auto, unique
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_logs,
)

from constants import DEV_TIER, UPPER_TIERS, STD_TIERS

### ======================================================================================================


class DataClassificationException(Exception):
    pass


@unique
class DATA_CLASSIFICATION_TYPES(Enum):
    INTERNAL_DATA = (auto(),)  ### Internal raw data and database information -7 years min
    USER_REQUESTS = (auto(),)  ### User data requests-5 years min
    CLOUD_AUDITTRAILS = (auto(),)  ### AWS Logs that must be retained, typically for Security-reasons.
    CLOUD_TEMPORARY = (auto(),)  ### AWS Logs like CloudFront Bucket logs
    SCRATCH = (auto(),)  ### AWS Logs like CloudFront Bucket logs


@unique
class S3_LIFECYCLE_RULES(Enum):
    COMMON = (auto(),)  ### common-settings for all of following s3-lifecycle rules.
    STD_EXPIRY = (auto(),)  ### NON-Prod AWS Logs
    INTELLIGENT_TIERING = (auto(),)  ### Production AWS Logs
    LOW_COST = (auto(),)  ### All User-Data in GLACIER_INSTANT_RETRIEVAL
    COLD_STORAGE = (auto(),)  ### All User-Data in DEEP_ARCHIVE
    SCRATCH = (auto(),)
    ### This exists ONLY for the requirement that -> All Query-Results (S3-objects) must expire after 1 day (Retention-period of 1-day).


MOVE_TO_GLACIER_INSTANT_RETRIEVAL_AFTER: int = 7  # days
MOVE_TO_DEEP_ARCHIVE_AFTER: int = 365 * 14  # 14 yrs, in days

NUM_OF_NONCURRENT_VERSIONS_TO_RETAIN = (
    5  ### count;  Do NOT retain any OLDER versions of objects, beyond these many versions.
)
RETAIN_NONCURRENT_VERSIONS_FOR = 5  ### days; Do NOT retain any OLDER versions of objects, beyond these many versions.

### ======================================================================================================


class DataClassification:

    @staticmethod
    def default_retention(tier: str):
        return aws_logs.RetentionDays.ONE_DAY if tier != "prod" else aws_logs.RetentionDays.THREE_MONTHS

    @staticmethod
    def glacierinstant_transition_after(tier: str, data_type: DATA_CLASSIFICATION_TYPES) -> int:
        """# of days (to move to GLACIER-INSTANT-RETRIEVAL), based on the data-type specified as parameter."""
        if not data_type in DATA_CLASSIFICATION_TYPES:
            raise DataClassificationException(
                f"invalid data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        if data_type == DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:
            return 2
        elif data_type == DATA_CLASSIFICATION_TYPES.USER_REQUESTS:
            return 2
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS:
            return 2
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:
            return 2
        elif data_type == DATA_CLASSIFICATION_TYPES.SCRATCH:
            return 2
        else:
            raise DataClassificationException(
                f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        # match data_type:
        #     case DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:     return 1
        #     case DATA_CLASSIFICATION_TYPES.USER_REQUESTS:     return 1
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS: return 1
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:   return 1
        #     case DATA_CLASSIFICATION_TYPES.SCRATCH:    return 1
        #     case _:
        #         raise DataClassificationException( f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}")

    @staticmethod
    def deeparchive_transition_after(tier: str, data_type: DATA_CLASSIFICATION_TYPES) -> int:
        """# of days (to move to GLACIER-DEEP-ARCHIVE), based on the data-type specified as parameter."""
        if not data_type in DATA_CLASSIFICATION_TYPES:
            raise DataClassificationException(
                f"invalid data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        if data_type == DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:
            return 365 * 7
        elif data_type == DATA_CLASSIFICATION_TYPES.USER_REQUESTS:
            return -1  ###  that is, NEVER.
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS:
            return 91
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:
            return 91
        elif data_type == DATA_CLASSIFICATION_TYPES.SCRATCH:
            return 91
        else:
            raise DataClassificationException(
                f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        # match data_type:
        # case DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:     return 365*7
        # case DATA_CLASSIFICATION_TYPES.USER_REQUESTS:     return -1 ### that is, never.
        # case DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS: return 91
        # case DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:   return 91
        # case DATA_CLASSIFICATION_TYPES.SCRATCH:    return 91
        # case _:
        #     raise DataClassificationException( f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}")

    @staticmethod
    def retention_for(tier: str, data_type: DATA_CLASSIFICATION_TYPES) -> int:
        """# of days (to retain data/content), based on the data-type specified as parameter."""
        if not data_type in DATA_CLASSIFICATION_TYPES:
            raise DataClassificationException(
                f"invalid data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        if data_type == DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:
            return -1  ### -1 means Never
        elif data_type == DATA_CLASSIFICATION_TYPES.USER_REQUESTS:
            return -1  ### -1 means Never
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS:
            return 1 * 365
        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:
            return 1 * 365
        elif data_type == DATA_CLASSIFICATION_TYPES.SCRATCH:
            return 1  ### Just 1 day!!!
        else:
            raise DataClassificationException(
                f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        # match data_type:
        #     case DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:     return 7 * 365
        #     case DATA_CLASSIFICATION_TYPES.USER_REQUESTS:     return 5 * 365
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS: return 1 * 365
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:   return 1 * 365
        #     case DATA_CLASSIFICATION_TYPES.SCRATCH:    return 1 ### Just 1 day!
        #     case _:
        #         raise DataClassificationException( f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}")

    @staticmethod
    def removal_policy(tier: str, data_type: DATA_CLASSIFICATION_TYPES) -> RemovalPolicy:
        """determining CloudFormation removal_policy, based on the tier + data_type specified as parameter."""
        if not data_type in DATA_CLASSIFICATION_TYPES:
            raise DataClassificationException(
                f"invalid data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        if data_type == DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:
            return RemovalPolicy.RETAIN if tier in UPPER_TIERS else RemovalPolicy.DESTROY
            # return RemovalPolicy.RETAIN if tier in PROD_TIER_NAMES else RemovalPolicy.DESTROY

        elif data_type == DATA_CLASSIFICATION_TYPES.USER_REQUESTS:
            return RemovalPolicy.RETAIN if tier in UPPER_TIERS else RemovalPolicy.DESTROY
            # return RemovalPolicy.RETAIN if tier in PROD_TIER_NAMES else RemovalPolicy.DESTROY

        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS:
            return RemovalPolicy.RETAIN if tier in UPPER_TIERS else RemovalPolicy.DESTROY

        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:
            return RemovalPolicy.DESTROY  ### <--- irrespective of tier!!!
        elif data_type == DATA_CLASSIFICATION_TYPES.SCRATCH:
            return RemovalPolicy.DESTROY  ### <--- irrespective of tier!!!
        else:
            raise DataClassificationException(
                f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        # match data_type:
        #     case DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:     return RemovalPolicy.RETAIN if tier in UPPER_TIER_NAMES else RemovalPolicy.DESTROY
        #     case DATA_CLASSIFICATION_TYPES.USER_REQUESTS:     return RemovalPolicy.RETAIN if tier in UPPER_TIER_NAMES else RemovalPolicy.DESTROY
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS: return RemovalPolicy.RETAIN if tier in PROD_TIER_NAMES  else RemovalPolicy.DESTROY
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:   return RemovalPolicy.DESTROY ### <--- irrespective of tier!!!
        #     case DATA_CLASSIFICATION_TYPES.SCRATCH:    return RemovalPolicy.DESTROY ### <--- irrespective of tier!!!
        #     case _:
        #         raise DataClassificationException( f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}")

    @staticmethod
    def versioning(tier: str, data_type: DATA_CLASSIFICATION_TYPES) -> bool:
        """determining if S3-bucket should have VERSIONING turned-ON, based on the tier + data-type specified as parameter."""
        if not data_type in DATA_CLASSIFICATION_TYPES:
            raise DataClassificationException(
                f"invalid data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )

        if data_type == DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:
            return True if tier in UPPER_TIERS else False

        elif data_type == DATA_CLASSIFICATION_TYPES.USER_REQUESTS:
            return True if tier in UPPER_TIERS else False

        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS:
            return False  ### <--- irrespective of tier!!!

        elif data_type == DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:
            return False  ### <--- irrespective of tier!!!
        elif data_type == DATA_CLASSIFICATION_TYPES.SCRATCH:
            return False  ### <--- irrespective of tier!!!

        else:
            raise DataClassificationException(
                f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}"
            )
        # match data_type:
        #     case DATA_CLASSIFICATION_TYPES.INTERNAL_DATA:     return True if tier in PROD_TIER_NAMES else False
        #     case DATA_CLASSIFICATION_TYPES.USER_REQUESTS:     return True if tier in PROD_TIER_NAMES else False
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_AUDITTRAILS: return False ### <--- irrespective of tier!!!
        #     case DATA_CLASSIFICATION_TYPES.CLOUD_TEMPORARY:   return False ### <--- irrespective of tier!!!
        #     case DATA_CLASSIFICATION_TYPES.SCRATCH:   return False ### <--- irrespective of tier!!!
        #     case _:
        #         raise DataClassificationException( f"!!! INTERNAL-ERROR !!! code is NOT ready to handle data-classification-type '{data_type}'. Valid values are: {list(DATA_CLASSIFICATION_TYPES)}")


### EoF
