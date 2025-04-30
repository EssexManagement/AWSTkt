import json
from typing import Union, Optional
from aws_cdk import (
    CfnOutput,
    Tag, CfnTag,
    Fn,
    Names,
    Duration,
    RemovalPolicy,
    Stack,
    CfnParameter,
    aws_ec2,
    aws_kms,
    aws_iam,
)
from constructs import Construct

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import get_tags_as_array, get_tags_as_json

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

ADMIN_IAM_ROLE_NAMES = [
    "aws-reserved/sso.amazonaws.com/AWSReservedSSO_NCIAWSDevOpsUserAccess_bbed7858ce9dcb72",
    "aws-reserved/sso.amazonaws.com/AWSReservedSSO_NCIAWSPowerUserAccess_b8929064e5912818",
    "aws-reserved/sso.amazonaws.com/AWSReservedSSO_NCIAWSSecurityAdminAccess_3301760e9600b7a8",
    "aws-reserved/sso.amazonaws.com/AWSReservedSSO_NCIAWSAdministratorAccess_9e5ed493ce7dc498",
    "power-user-terraform-apply-nonprod",
    "nci_full_admin",
    "security_admin",
]

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class KMSKeysConstruct(Construct):
    """
        Creates a KMS Key for the given tier, and grants the specified IAM roles access to it.
        The KMS Key is created in the specified AWS account and region.
        The KMS Key is also created in the specified AWS account and region.
        The KMS Key is also created in the specified AWS account and region.
        The KMS Key is also created in the specified AWS account and region.
    """
    def __init__(self, scope: Construct, construct_id: str,
        aws_env :str,
        rotation_period :Duration = Duration.days(365), ### RuntimeError: 'rotationPeriod' value must between 90 and 2650 days. Received: 30
        admin_role_names :list[str] = ADMIN_IAM_ROLE_NAMES,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id)
        stk = Stack.of(self)

        # # define stack-cloudformation-param named "cdkAppName"
        # cdk_app_name_cfnp = CfnParameter(self, "cdkAppName",
        #     type="String",
        #     description="The name of the CDK app",
        #     default=constants.CDK_APP_NAME,
        # )

        role_arn_list :list[str] = []
        admin_principals :list[aws_iam.IPrincipal] = []
        for rolename in admin_role_names:
            arn = f"arn:{stk.partition}:iam::{stk.account}:role/{rolename}"
            role_arn_list.append( arn )
            admin_principals.append( aws_iam.ArnPrincipal( arn = arn ) )

        ### ----------------------------
        ### 1st, KMS-Key used across --ALL-- Tiers
        description = f"Common KMS CMK for use by ALL tiers in this aws-acct"
        alias = "common-cmk"

        common_kms_key = aws_kms.Key( scope=self,
            id = alias,
            alias = alias,
            description = description,
            admins = admin_principals,
            enable_key_rotation = True,
            rotation_period = rotation_period,
            removal_policy = RemovalPolicy.DESTROY,
            # key_spec = "SYMMETRIC_DEFAULT",
            # key_usage = "ENCRYPT_DECRYPT",
        )

        # output the KMS Key ARN
        CfnOutput(self, "KmsKeyArn",
            value = common_kms_key.key_arn,
            description = "KMS Key ARN"
        )

        ### ----------------------------
        ### 2nd, create multiple KMS-Keys .. specific to each Tier

        tier_based_info = constants_cdk.SUBNET_NAMES_LOOKUP[ aws_env ]
        # if tier_based_info is of type "list[str]", do nothing else, but if it is of type "dict[str,list[str]]", the tier_based_info = tier_based_info[tier], else .. raise exception
        if not isinstance(tier_based_info, list):
            if isinstance(tier_based_info, dict):
                for tier_in_this_acct in tier_based_info.keys():
                    print( f"tier_in_this_acct = '{tier_in_this_acct}'")

                    alias = f"common-cmk-{tier_in_this_acct}"
                    description = f"Common KMS CMK for {tier_in_this_acct} TIER only"

                    tier_specific_kms_key = aws_kms.Key( scope=self,
                        id = alias,
                        alias = alias,
                        description = description,
                        admins = admin_principals,
                        enable_key_rotation = True,
                        rotation_period = rotation_period,
                        removal_policy = RemovalPolicy.DESTROY,
                        # key_spec = "SYMMETRIC_DEFAULT",
                        # key_usage = "ENCRYPT_DECRYPT",
                    )

                    # output the KMS Key ARN
                    CfnOutput(self, "CfnOutput-"+alias,
                        value = tier_specific_kms_key.key_arn,
                        description = description,
                    )

        # root_arn = f"arn:{stk.partition}:iam::{stk.account}:root"
        # role_arn_list.append( root_arn )
        # admin_principals.append( aws_iam.ArnPrincipal( arn = root_arn ) )

        ### grant the specified IAM roles access to the KMS Key
        # kms_key.add_to_resource_policy( aws_iam.PolicyStatement(
        #         principals = {
        #         "AWS": role_arn_list,
        #     },
        #     action = [
        #         "kms:ListAliases",
        #         "kms:Lists",
        #     ],
        #     resources = [
        #         f"*"
        #     ]
        # ))


        # kms_key.add_to_resource_policy( aws_iam.PolicyStatement(
        #     principals = {
        #         "AWS": role_arn_list,
        #     },
        #     action = [
        #         "kms:Create*",
        #         "kms:Describe*",
        #         "kms:Enable*",
        #         "kms:List*",
        #         "kms:Put*",
        #         "kms:Update*",
        #         "kms:Revoke*",
        #         "kms:Disable*",
        #         "kms:Get*",
        #         "kms:Delete*",
        #         "kms:TagResource",
        #         "kms:UntagResource",
        #         "kms:ScheduleKeyDeletion",
        #         "kms:CancelKeyDeletion"
        #     ],
        #     action = [
        #         "kms:Encrypt",
        #         "kms:Decrypt",
        #         "kms:ListKeyPolicies",
        #         "kms:GetKeyPolicy",
        #         "kms:PutKeyPolicy",
        #         "kms:CreateAlias",
        #         "kms:DeleteAlias",
        #         "kms:UpdateAlias",
        #         "kms:ScheduleKeyDeletion",
        #         # "kms:ReEncrypt*",
        #         # "kms:GenerateDataKey*",
        #         "kms:DescribeKey",
        #         "kms:UpdateKeyDescription",
        #         "kms:ListResourceTags",
        #         "kms:TagResource",
        #         "kms:UntagResource",
        #     ],
        #     resources = [
        #         f"arn:{stk.partition}:kms:{stk.region}:{stk.account}:key/*"
        #     ]
        # ))


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class ExistingKMSKeyAccessMgrConstruct(Construct):
    """
        For each KMS key listed in cdk.json, ensure the appropriate service WILL HAVE access to use it.
        Since there are TOO many resources (like CWLogsGroups, etc..), Policy-Size limitations PREVENT us from giving each AWS-Resource access to KMS-Key
    """

    def __init__(self,
        scope: Construct,
        construct_id: str,
        aws_env :str,
        **kwargs
    ):
        super().__init__(scope, construct_id)
        stk = Stack.of(self)

        ### Get the security context
        cdk_json_security_config :any = scope.node.try_get_context("security")
        if not cdk_json_security_config:
            raise ValueError("Missing 'security' json-configuration in cdk.json")
        print("cdk.json's Git-SourceCode configuration JSON is:")
        print( json.dumps(cdk_json_security_config, indent=4) )

        kms_config :dict[str,Union[str,dict[str,str]]] = cdk_json_security_config.get("kms", {})

        default_keys_for_all_tiers = None
        for service in kms_config.keys():
            if service == "default":
                default_keys_for_all_tiers = kms_config["default"]
                continue
            keys_per_tier = kms_config[service]
            if isinstance(keys_per_tier, dict):
                for tier, kms_key_arn in keys_per_tier.items():
                    print( f"kms_key (pre)ARN for '{service} -> {tier}' = '{kms_key_arn}' within "+ __file__ )
                    if kms_key_arn:
                        kms_key_arn = kms_key_arn.format(stk.region, stk.account)
                    print( f"kms_key (final))ARN for '{service} -> {tier}' = '{kms_key_arn}' within "+ __file__ )
                    self.grant_access_to_kms_key( scope=scope, tier=tier, aws_env=aws_env,
                        service = service,
                        kms_key_arn = kms_key_arn,
                    )
                    default_key_arn = None
                    if default_keys_for_all_tiers and tier in default_keys_for_all_tiers:
                        default_key_arn = default_keys_for_all_tiers[tier]
                        default_key_arn = default_key_arn.format(stk.region, stk.account)
                    print( f"default_key_arn (final)ARN for tier:'{tier}' for AWS-Svc '{service}' = '{default_key_arn}' within "+ __file__ )
                    if default_key_arn == kms_key_arn:
                        continue ### identical. So, skip the next line of code
                    self.grant_access_to_kms_key( scope=scope, tier=tier, aws_env=aws_env,
                        service = service,
                        kms_key_arn = default_key_arn, ### default_key_arn
                    )
            else: ### if -NOT- a dict
                raise ValueError(f"Invalid 'kms' configuration in cdk.json for service '{service}'")


    def grant_access_to_kms_key(self,
        scope: Construct,
        tier: str,
        aws_env: str,
        service :str,
        kms_key_arn: str,
    ) -> None:
        """ Grants access to the specified KMS key to the specified service.
            The service is determined by the service name in the cdk.json file.
            The service name is the key in the cdk.json file.
            The service name is the key in the cdk.json file.
            The service name is the key in the cdk.json file.
        """
        if not kms_key_arn or not service:
            print( f"⚠️⚠️ Missing parameter-values kms_key_arn='{kms_key_arn}' or service='{service}' to method" )
        else:
            print( f"Granting access to {service} in {tier} with kms_key_arn: {kms_key_arn}" )
            # kms_key_arn = lkp_cdk_json_for_kms_key( cdk_scope=scope, tier=tier, aws_env=None, aws_rsrc_type="cwlogs" )
            encryption_key = aws_kms.Key.from_key_arn(scope, f"KMSLkp-{service}-{tier}-{kms_key_arn}", kms_key_arn )
            if not encryption_key:
                print(f"Skipping INVALID ⚠️⚠️ KMS-Key for {service} in {tier}: {kms_key_arn}")
                return

            ### Grant permissions to the log group's service principal
            encryption_key.add_to_resource_policy( aws_iam.PolicyStatement(
                principals = [aws_iam.ServicePrincipal( f'{service}.amazonaws.com' )],
                actions = [
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey",
                    "kms:CreateGrant",
                    "kms:ListGrants",
                    "kms:RevokeGrant"
                ],
                resources = ["*"]
            ) )
