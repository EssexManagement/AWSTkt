"""CDK construct for API Gateway and lambda functions"""

import typing
from typing import Optional

from os import path
import pathlib
import string
import random
import base64
from functools import partial

from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_logs as logs,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_kms,
    aws_wafv2,
    aws_secretsmanager,
)

from constants import CDK_APP_NAME

THIS_DIR = path.dirname(__file__)


class FrontEndWAFConstruct(Construct):
    """
        CDK construct for creating WAF-ACL w/ WAF-Rules mimicking CBIIT's Firewall-managed rules.
        This new TIER-specific WAF-ACL will be associated with the TIER-specific CloudFront-Distribution.
        It just contains AWS-Managed RuleSets + One Custom-Rule to throttle per-user (to prevent malware-infected end-user-laptops from beating the solution)
    """

    @property
    def waf_acl_id(self) -> str:
        return self._waf_acl.attr_id

    @property
    def waf_acl_arn(self) -> str:
        return self._waf_acl.attr_arn

    @property
    def waf_acl(self) -> str:
        return self._waf_acl

    @staticmethod
    def origin_token_http_header_name() -> str:
        """ Static method that returns a hardcoded-constant to be shared across Constructs"""
        return 'x-origin-verify'

    @staticmethod
    def waf_rule_name() -> str:
        """ Static method that returns a hardcoded-constant to be shared across Constructs"""
        return "HttpHeaderToken-"+FrontEndWAFConstruct.origin_token_http_header_name()

    @property
    def x_origin_verify_hdr_token_value(self) -> str:
        return self._x_origin_verify_hdr_token_value

    # @property
    # def x_origin_verify_hdr_secret(self) -> aws_secretsmanager.ISecret:
    #     return self._x_origin_verify_hdr_secret
        """
           This Secret needs to be accessible in the frontend_2nd_origin construct.
           This Secret's value must be readable over there.
           Hence, this property returns `Secret` and NOT `ISecret`.
        """

    def __init__(
        self,
        scope: "Construct",
        construct_id: str,
        tier :str,
    ) -> None:
        super().__init__(scope=scope, id_=construct_id)
        stk = Stack.of(self)

        ### -------------------
        waf_rule_priority = 0

        waf_rules :list[aws_wafv2.CfnWebACL.RuleProperty] = [ ]

        ### HOW-TO: aws wafv2 list-available-managed-rule-groups --scope REGIONAL
        aws_managed_waf_rule_groups = [
            # "AWSManagedRulesCommonRuleSet",
            "AWSManagedRulesAdminProtectionRuleSet",
            # "AWSManagedRulesKnownBadInputsRuleSet",

            ##__ "AWSManagedRulesSQLiRuleSet",
            ##__ "AWSManagedRulesLinuxRuleSet",
            ##__ "AWSManagedRulesUnixRuleSet",
            ##__ "AWSManagedRulesWindowsRuleSet",
            ##__ "AWSManagedRulesPHPRuleSet",
            ##__ "AWSManagedRulesWordPressRuleSet",

            "AWSManagedRulesAmazonIpReputationList",
            "AWSManagedRulesAnonymousIpList",
            "AWSManagedRulesBotControlRuleSet",

            ##__ "AWSManagedRulesATPRuleSet",
            ##__ "AWSManagedRulesACFPRuleSet",
        ]

        ### -------------------

        ### -------- add AWS-Managed WAF-Rules mimicking CBIIT-managed Firewall-Manager-managed rules ------
        for mgd_waf_rule_name in aws_managed_waf_rule_groups:
            new_rule = aws_wafv2.CfnWebACL.RuleProperty(
                ### https://docs.prismacloud.io/en/enterprise-edition/policy-reference/aws-policies/aws-networking-policies/ensure-waf-prevents-message-lookup-in-log4j2
                name=mgd_waf_rule_name,
                # name="CKV_AWS_192: Ensure WAF prevents message lookup in Log4j2. See CVE-2021-44228 aka log4jshell",
                priority=waf_rule_priority,  # Adjust priority as needed based on other rules

                override_action=aws_wafv2.CfnWebACL.OverrideActionProperty(none={}),
                # action=aws_wafv2.CfnWebACL.RuleActionProperty(block={}),
                ### Ticket # 174551690600321
                ### If the rule-statement references a rule-group, you must -NOT- set this action setting, because the `actions` are already set on the rules inside the rule-group.
                ### "Action" is used only for rules whose statements do NOT reference a rule-group.
                ### Rule-statements that reference a rule-group include `RuleGroupReferenceStatement` and `ManagedRuleGroupStatement`.
                ###      You must set either this `Action` setting or the rule's `OverrideAction`, but not both [1]:

                statement=aws_wafv2.CfnWebACL.StatementProperty(
                    managed_rule_group_statement=aws_wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                        name=mgd_waf_rule_name,
                        vendor_name="AWS",
                        # vendor_name="AWS-FMS",  # For Firewall-Manager managed CUSTOM Rules defined at AWS-Org Root-account.
                    )
                ),
                visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled=True,
                    metric_name=mgd_waf_rule_name,
                    sampled_requests_enabled=True,
                ),
            )
            waf_rules.append(new_rule)
            waf_rule_priority += 1

        ### -------------------
        ### Create the NEW custom WAF rule -- throttling each individual malware-user (Ticket # 2686 - rate-limiting by individual-user)
        ### oobox-WAF-capability: A rate-based rule counts incoming requests and rate limits requests when they are coming at too fast a rate.

        rate_waf_rule_name = "ticket-2686-throttle-each-individual-user-ip"
        waf_rule_throttle_each_user = aws_wafv2.CfnWebACL.RuleProperty(
            name = rate_waf_rule_name,
            priority=waf_rule_priority,  # Adjust priority as needed based on other rules
            action=aws_wafv2.CfnWebACL.RuleActionProperty(block={}),
            # override_action is ONLY used for ManagedRuleGroups
            statement=aws_wafv2.CfnWebACL.StatementProperty(
                # not_statement=aws_wafv2.CfnWebACL.NotStatementProperty(
                    rate_based_statement=aws_wafv2.CfnWebACL.RateBasedStatementProperty(
                        ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-wafv2-webacl-ratebasedstatement.html
                        limit = 50,  ### Note: minimum possible limit is 10 per second
                        ### To aggregate on only the IP-address or only the forwarded-IP-address, do -NOT- use `custom_keys`.
                        ### Instead, set the `aggregate_key_type` to `IP` or `FORWARDED_IP`.
                        aggregate_key_type="IP", ### individual aggregation keys: IP address or HTTP method
                        # aggregate_key_type="CUSTOM_KEYS", ### individual aggregation keys: IP address or HTTP method
                        # custom_keys="" ### https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RateBasedStatementProperty.html#aggregatekeytype
                        # scope_down_statement=aws_wafv2.CfnWebACL.StatementProperty(
                        #     ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-wafv2-webacl-ratebasedstatement.html#cfn-wafv2-webacl-ratebasedstatement-scopedownstatement
                        # )
                    )
                # )
            ),
            visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-wafv2-webacl-visibilityconfig.html
                cloud_watch_metrics_enabled=True,
                metric_name=rate_waf_rule_name,
                sampled_requests_enabled=True,
            ),
        )
        waf_rules.append(waf_rule_throttle_each_user)
        waf_rule_priority += 1

        ### ------ Create a new WAF-ACL -- just for this TIER -- using above WAF-rules -----
        waf_acl_name = CDK_APP_NAME + "-Custom-WAFACL-"+tier
        self._waf_acl = aws_wafv2.CfnWebACL(
            scope_=self,
            id = tier,
            name = waf_acl_name,
            description = f"Custom WAF-ACL for {tier} in {self.account_type} created via CDK - with MANUAL-efforts to mimic CBIIT-owned Firewall-Managed WAF-ACL entries",
            ### description must obey regular-expression pattern (No quotes at all): ^[\w+=:#@/\-,\.][\w+=:#@/\-,\.\s]+[\w+=:#@/\-,\.]$
            default_action=aws_wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope="REGIONAL",
            visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True, metric_name="OriginVerifyHeaderWAF", sampled_requests_enabled=True
            ),
            rules=waf_rules,
        )



    ### ------------------------------------------------------

    def protect_api_w_waf(
        self,
        rest_api: apigateway.RestApi,
        apigw_stage_name: str,
    ) -> None:
        """
            Lookup cdk.json, for the ARN to the WAF-ACL.
            Associate the WAF-ACL to the APIGW.

            Note: Adding a custom-WAF-Rule to this WAF-ACL is done inside `backend/runtime/src/nccr/handler/rotate_secret_cloudfront_apigw_hdr_token.py`
                  Why? 'cuz, there's only one way to change a WAF-ACL.  That is  thru AWS-SDk.  No CDK-support.
        """
        stk = Stack.of(self)

        # security_config = self.node.try_get_context("apigw")
        # if security_config and "WAF-ACL" in security_config:
        #     waf_acl_arn = security_config["WAF-ACL"]
        # else:
        #     waf_acl_arn = None
        # print(f"DEBUG: waf_acl_arn = '{waf_acl_arn}'")
        # if waf_acl_arn:
        #     if self.is_prod_account and C_ENV_PROD in waf_acl_arn:
        #         waf_acl_arn = waf_acl_arn[C_ENV_PROD]
        #     elif not self.is_prod_account and C_ENV_NON_PROD in waf_acl_arn:
        #         waf_acl_arn = waf_acl_arn[C_ENV_NON_PROD]
        #     else:
        #         waf_acl_arn = None
        # else:
        #     waf_acl_arn = None

        ### -------------------
        if self.waf_acl_arn:
            # given the ARN to a WAF-ACL, apply it to the above APIGW
            apigw_stage_arn = f"arn:{stk.partition}:apigateway:{stk.region}::/restapis/{rest_api.rest_api_id}/stages/{apigw_stage_name}"
            wafaclass = aws_wafv2.CfnWebACLAssociation(
                scope=self,
                id="wafv2ForAPIGW",
                web_acl_arn = self.waf_acl_arn,
                resource_arn = apigw_stage_arn,
            )
            wafaclass.add_dependency( rest_api.node.default_child )
            wafaclass.add_dependency( rest_api.deployment_stage.node.default_child )
        else:
            raise Exception("No WAF-ACL ARN defined, within WAFConstruct construct")

### EoF
