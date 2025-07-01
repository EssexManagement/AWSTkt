from __future__ import annotations
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
    aws_ec2,
    aws_rds,
    aws_codebuild,
)

import constants

### ===============================================================================================

CDK_APP_PYTHON_VERSION = None
LAMBDA_PYTHON_RUNTIME = aws_lambda.Runtime.PYTHON_3_12
LAMBDA_PYTHON_RUNTIME_VER_STR = aws_lambda.Runtime.PYTHON_3_12.name.replace("python","")

CDK_NODEJS_VERSION = None
FRONTEND_NODEJS_VERSION = "20"

### ===============================================================================================

CDK_IAMRoleName_prefix = "hnb659fds"

### ===============================================================================================

BUILD_KICKOFF_TIMESTAMP = datetime.now()
TIMEZONE = pytz.timezone('America/New_York')
# Localize the datetime object
localized_now = TIMEZONE.localize(BUILD_KICKOFF_TIMESTAMP)
# Format the localized datetime as a string
BUILD_KICKOFF_TIMESTAMP_STR = localized_now.strftime('%Y-%m-%d %H:%M:%S %Z')
BUILD_KICKOFF_TIMESTAMP_LOCAL_STR = localized_now.strftime('%Y-%m-%dT%H:%M:%S')

### ===============================================================================================

TIER_TO_AWSENV_MAPPING = {

    ### CloudOne
    constants.ACCT_PROD:  constants.ACCT_PROD,
    constants.ACCT_NONPROD: constants.ACCT_NONPROD,

    constants.PROD_TIER:  constants.ACCT_PROD,
    constants.STAGE_TIER: constants.ACCT_PROD,
    constants.TEST_TIER:  constants.ACCT_NONPROD,
    constants.QA_TIER:    constants.ACCT_NONPROD,
    constants.DEV_TIER:   constants.ACCT_NONPROD,
    ### DEVELOPER-Tiers ONLY .. are handled within `get_aws_env()` function BELOW.

    ### CRRI-Cloud
    # constants.DEV_TIER: "DEVINT",
    # constants.INT_TIER: "DEVINT",
    # constants.UAT_TIER: "UAT",
    # constants.PROD_TIER: "PROD",

    ### Essex-Cloud - DEVELOPER-Tiers ONLY
    # "sarma": "EssexCloud-DEV",
    ### Essex-Cloud
    # constants.ACCT_NONPROD: "EssexCloud-DEV",
    # constants.DEV_TIER: "EssexCloud-DEV",
}

SUBNET_NAMES_LOOKUP = {
    ### Assumption: Each Tier has its -own- VPC!!    That individual VPC's name is SAME as "${TIER}"
    ### Assumption: Each "aws_env" will have >1 vpc at any time.
    ### Format: key = aws_env
    ### Format: value = { TIER: [ list of -NAMES- of subnets ],   .. ..  }

    "acct-nonprod": {
        "dev": [ constants.DEV_TIER  ],
        # "qa":  [ constants.QA_TIER ]
    },
    "acct-prod": {
        "stage": [ constants.STAGE_TIER ],
        "prod":  [ constants.PROD_TIER  ]
    },
    # "DEVINT":         [ constants.DEV_TIER,  constants.TEST_TIER ],
    # "EssexCloud-DEV": [ constants.DEV_TIER,  constants.TEST_TIER ],
}

class VpcInfo():
    vpc_name: Optional[str];
    vpc_id: Optional[str];
    vpc_con: Optional[aws_ec2.IVpc];
    subnet_selection: Optional[aws_ec2.SubnetSelection];
    subnet_ids: Optional[list[str]];
    security_groups: Optional[list[aws_ec2.ISecurityGroup]];
    security_group_ids: Optional[list[str]];
    def __init__(self,
        vpc_name :Optional[str] = None,
        vpc_id :Optional[str] = None,
        vpc_con :Optional[aws_ec2.IVpc] = None,
        subnet_selection :Optional[aws_ec2.SubnetSelection] = None,
        subnet_ids :Optional[list[str]] = None,
        security_groups :Optional[list[aws_ec2.ISecurityGroup]] = None,
        security_group_ids :Optional[list[str]] = None,
    ):
        self.vpc_name = vpc_name
        self.vpc_id = vpc_id
        self.vpc_con = vpc_con
        self.subnet_selection = subnet_selection
        self.subnet_ids = subnet_ids
        self.security_groups = security_groups
        self.security_group_ids = security_group_ids

    def clone(self) -> VpcInfo:
        retval = VpcInfo(
            vpc_name=self.vpc_name,
            vpc_id=self.vpc_id,
            vpc_con=self.vpc_con,
            subnet_selection=self.subnet_selection,
            subnet_ids=self.subnet_ids,
            security_groups=self.security_groups,
            security_group_ids=self.security_group_ids,
        )
        return retval

### ---------------------------------------------------------------------------------

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

# USE_ADVANCED_CODEBUILD_CACHE = True
def use_advanced_codebuild_cache( tier :str ) -> bool:
    if tier in constants.UPPER_TIERS:
        return False ### do --NOT-- touch this line.
    else:
        return True ### <------------- Developers!!! Only edit this line !!!!!!!!!!!!!!

CODEBUILD_FILECACHE_FLDRPATH = "tmp/CodeBuild_FileCacheFldr"  ### Keep this in sync with

### ===============================================================================================

### Define how long will --all- BDDs be allowed to run, before CodeBuild-project TIMES-OUT.  This is a generic/common setting.
BDD_CODEBUILD_TIMEOUT = Duration.minutes(120)

### ===============================================================================================
### ...............................................................................................
### ===============================================================================================
### ...............................................................................................
### ===============================================================================================

""" Standardized naming for AWS-Environments a.k.a. AWS-PROFILES """
def get_aws_env( tier :str ) -> str:
    if tier in TIER_TO_AWSENV_MAPPING:
        return TIER_TO_AWSENV_MAPPING[tier]
    else:
        return constants.ACCT_NONPROD  ### Typically, all developer-tiers
    # if tier in [ DEV_TIER, INT_TIER ]:
    #     return "DEVINT"
    # elif tier in [ UAT_TIER ]:
    #     return "UAT"
    # elif tier in [ PROD_TIER ]:
    #     return "PROD"
    # # elif tier in [ PROD_TIER, UAT_TIER ]:
    # #     return "PROD"
    # else:
    #     return "DEVINT"
    #     # traceback.print_exc()
    #     # raise ValueError(f"Invalid tier: {tier}")

### ----------------------------------------------------------------

"""Return the CW-Logs Retention based on the Tier/Environment """
def get_LOG_RETENTION(
    construct :Construct,
    tier :str,
    aws_env :Optional[str] = None
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
    tier :str,
    construct :Optional[Construct] = None,
    aws_env :Optional[str] = None,
) -> RemovalPolicy:
    if tier == constants.PROD_TIER or tier == constants.UAT_TIER:
        return RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE
    else:
        return RemovalPolicy.DESTROY

### ===============================================================================================

### EoF
