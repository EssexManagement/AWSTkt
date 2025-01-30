import pytz
from datetime import datetime
from typing import Optional

from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_logs,
    aws_lambda,
    aws_rds,
    aws_codebuild,
)

import constants

### ===============================================================================================

CDK_APP_PYTHON_VERSION = "3.12"
LAMBDA_PYTHON_RUNTIME = aws_lambda.Runtime.PYTHON_3_12
LAMBDA_PYTHON_RUNTIME_VER_STR = aws_lambda.Runtime.PYTHON_3_12.name.replace("python","")

### ===============================================================================================

CDK_IAMRoleName_prefix = "hnb659fds"

### ===============================================================================================

BUILD_KICKOFF_TIMESTAMP = datetime.now()
TIMEZONE = pytz.timezone('America/New_York')
# Localize the datetime object
localized_now = TIMEZONE.localize(BUILD_KICKOFF_TIMESTAMP)
# Format the localized datetime as a string
BUILD_KICKOFF_TIMESTAMP_STR = localized_now.strftime('%Y-%m-%d %H:%M:%S %Z')

### ===============================================================================================

DEFAULT_CPU_ARCH         = aws_lambda.Architecture.ARM_64
DEFAULT_CPU_ARCH_NAMESTR = aws_lambda.Architecture.ARM_64.name
CPU_ARCH_LIST :list[aws_lambda.Architecture] = [
    aws_lambda.Architecture.ARM_64,
    aws_lambda.Architecture.X86_64,
]

ENGINE_VERSION_LOOKUP :dict = {
    # '11': rds.AuroraPostgresEngineVersion.VER_11_13,
    # '12': rds.AuroraPostgresEngineVersion.VER_12_18,
    '13': aws_rds.AuroraPostgresEngineVersion.VER_13_16,
    '14': aws_rds.AuroraPostgresEngineVersion.VER_14_13,
    '15': aws_rds.AuroraPostgresEngineVersion.VER_15_8,
    '16': aws_rds.AuroraPostgresEngineVersion.VER_16_4,
}

### ---------------------------------------------------------------------------------

CODEBUILD_BUILD_IMAGE = aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3
CODEBUILD_BUILD_IMAGE_X86 = aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
CODEBUILD_BUILD_IMAGE_UBUNTU = aws_codebuild.LinuxBuildImage.STANDARD_7_0
CODEBUILD_EC2_SIZE    = aws_codebuild.ComputeType.LARGE

USE_CODEBUILD_CACHE = True
CODEBUILD_FILECACHE_FLDRPATH = "tmp/CodeBuild_FileCacheFldr"  ### Keep this in sync with

### ===============================================================================================

### Define how long will --all- BDDs be allowed to run, before CodeBuild-project TIMES-OUT.  This is a generic/common setting.
BDD_CODEBUILD_TIMEOUT = Duration.minutes(120)

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

"""Return the CW-Logs Retention based on the Tier/Environment """
def get_LOG_RETENTION(
    construct :Optional[Construct],
    tier :str,
    aws_env :str = None
) -> aws_logs.RetentionDays:
    if tier in constants.STD_TIERS:
        dys = construct.node.try_get_context("retention")["log-retention"][tier]
    else:
        dys = construct.node.try_get_context("retention")["log-retention"]["dev"]

    print(f"LOG_RETENTION/prefor {tier} is {dys} days")
    dys = aws_logs.RetentionDays[dys]
    print(f"LOG_RETENTION/post for {tier} is {dys} days")
    return dys
    # return aws_logs.RetentionDays.ONE_YEAR


### ===============================================================================================

def get_stateful_removal_policy(
    construct :Optional[Construct],
    tier :str,
    aws_env :str = None
) -> aws_logs.RetentionDays:
    if tier == constants.PROD_TIER or tier == constants.UAT_TIER:
        return RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE
    else:
        return RemovalPolicy.DESTROY

### ===============================================================================================

### EoF
