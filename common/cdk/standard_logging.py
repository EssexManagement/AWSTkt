from enum import Enum, unique
from typing import Optional

from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Names,
    aws_logs,
    aws_kms,
    aws_iam,
)

import constants
from common.cdk.constants_cdk import get_LOG_RETENTION, get_stateful_removal_policy
import common.cdk.aws_names as aws_names
import cdk_utils.CdkDotJson_util as CdkDotJson_util

### ====================================================================================================================

""" The standardized log-groups should have "std-prefixes" based on the AWS-Service """
@unique
class LogGroupType(Enum):
    Misc = "", ### No prefix to NAME of Log-Group

    Lambda = "/aws/lambda",
    APIGW  = "/aws/apigateway",
    CodeBuild = "/aws/codebuild",
    StepFunction = "/aws/states",
    # CloudFront = "CloudFront",
    # S3 = "S3",
    # DynamoDB = "DynamoDB",
    # Kinesis = "Kinesis",


### ===============================================================================================

""" Standardizing the LogGroup class (std vs. infreq-access) by tier.
    Save money.
"""
def get_loggrp_class(
    construct :Optional[Construct],
    tier :str,
    aws_env :Optional[str] = None
) -> aws_logs.LogGroupClass:
    # logs.LogGroupClass.INFREQUENT_ACCESS Will --DENY-- features like Live Tail, metric extraction / Lambda insights, alarming,
    # !! WARNING !! it will also --DENY-- Subscription filters / Export to S3 (that Standard log-class provides)
    if tier == constants.PROD_TIER or tier == constants.UAT_TIER:
        return aws_logs.LogGroupClass.STANDARD ### for CRRI-Cloud; TODO for CloudOne
        # return aws_logs.LogGroupClass.INFREQUENT_ACCESS <--- This will PREVENT DataDog subscriptions to the LogStreams !!!!!!!!!!
    else:
        return aws_logs.LogGroupClass.STANDARD ### for `dev` and `int`

### ====================================================================================================================

""" Generic utility to create Log-Groups for --ANYTHING-- (APIGW, Lambdas, CodeBuild, ..)
    Right now all have same retention-periods.

    param # 1: scope :Construct
    param # 2: tier :str - dev|int|test|uat|stage|prod
    param # 3: loggrp_type :LogGroupType - See the enum for details.
    param # 4: what-is-being-logged :str -  EXAMPLE: "APIGW-1-AccessLogs", "${LambdaName}-Lambda", "CodeBuildProj-{}" ..
    param # 5: loggrp_name :str (OPTIONAL) -  name of the log-group to be created;  Best-practice = Never name the log-groups.
"""
def get_log_grp(
    scope :Construct,
    tier  :str,
    loggrp_type :LogGroupType,
    what_is_being_logged :str,
    loggrp_name :Optional[str] = None,
) -> aws_logs.LogGroup:

    stk = Stack.of(scope)
    auto_loggrp_name = loggrp_type.value[0] +'/'+ what_is_being_logged
    encryption_key_arn = CdkDotJson_util.lkp_cdk_json_for_kms_key( cdk_scope = scope,
        tier = tier,
        aws_env = None,
        aws_rsrc_type = CdkDotJson_util.AwsServiceNamesForKmsKeys.logs
    )
    encryption_key = aws_kms.Key.from_key_arn(scope, 'kmslkp-'+what_is_being_logged, encryption_key_arn) if encryption_key_arn else None
    # encryption_key = aws_kms.Key.from_key_arn( scope, 'kmslkp-'+what_is_being_logged, f"arn:aws:kms:{stk.region}:{stk.account}:alias/?????????")

    loggrp = aws_logs.LogGroup(
        scope = scope,
        id = "logs-"+ what_is_being_logged,
        log_group_name  = loggrp_name,
        # log_group_name  = loggrp_name or auto_loggrp_name,
        retention       = get_LOG_RETENTION(          construct=scope, tier=tier ),
        removal_policy  = get_stateful_removal_policy(construct=scope, tier=tier ),
        log_group_class = get_loggrp_class(           construct=scope, tier=tier ),
        # logs.LogGroupClass.INFREQUENT_ACCESS Will --DENY-- features like Live Tail, metric extraction / Lambda insights, alarming,
        # !! WARNING !! it will also --DENY-- Subscription filters / Export to S3 (that Standard log-class provides)
        encryption_key = encryption_key,
    )
    # if encryption_key:
        ### encryption_key.grant_encrypt_decrypt(loggrp) <--- fails to CDK-Synth
        ### Instead, the solution is to grant permissions to the log group's service principal
        ### This is taken care of, ONE-TIME, at account-level, via `FoundationalResourcesStack` in `operations/CDK/OperationsPrerequisites/src/all_stacks.py`

    Tags.of(loggrp).add(key="ResourceName", value =stk.stack_name+"-CWLogs-"+(loggrp_name if loggrp_name else Names.unique_id(scope)))
    return loggrp

### EoF
