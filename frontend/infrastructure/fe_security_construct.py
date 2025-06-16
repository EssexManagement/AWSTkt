"""CDK construct for protecting API Gateway and CloudFront-distribution"""

import typing
from typing import Optional, Literal

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
    aws_iam,
    aws_apigateway as apigateway,
    aws_cloudfront,
    aws_wafv2,
)

import constants
import common.cdk.constants_cdk as constants_cdk
import cdk_utils.CdkDotJson_util as CdkDotJson_util

### ---------------------------------------------------------------------------------------------
### .............................................................................................
### ---------------------------------------------------------------------------------------------

IPAllowedLists = [
    ### Use these strings to LOOKUP "cdk.json" for the ARN to the WAF-IP-Sets.
    ### Ideally, these strings are very-very similar to the names of the WAF-IP-Sets on WAF-Console.
    "AllowNIHWhitelistIPs",
    "NATGWs",
]

### ---------------------------------------------------------------------------------------------
### .............................................................................................
### ---------------------------------------------------------------------------------------------

class FrontendWAFConstruct(Construct):
    """
        CDK construct for creating WAF-ACL w/ WAF-Rules mimicking Enterprise Firewall-managed rules.
        This new TIER-specific WAF-ACL will be associated with the TIER-specific CloudFront-Distribution.
        It just contains AWS-Managed RuleSets + One Custom-Rule to throttle per-user (to prevent malware-infected end-user-laptops from beating the solution)
    """

    @staticmethod
    def waf_acl_name( tier :str ) -> str:
        waf_acl_name = constants.CDK_APP_NAME + "-Global-Custom-WAFACL-"+ tier
        return waf_acl_name

    @property
    def waf_acl_id(self) -> str:
        return self._waf_acl.attr_id

    @property
    def waf_acl_arn(self) -> str:
        return self._waf_acl.attr_arn

    @property
    def waf_acl(self) -> aws_wafv2.CfnWebACL:
        return self._waf_acl

    def __init__(
        self,
        cdk_scope: "Construct",
        construct_id: str,
        tier :str,
    ):
        super().__init__(scope=cdk_scope, id=construct_id)

        stk = Stack.of(self)
        effective_tier = tier if (tier in constants.STD_TIERS or tier in constants.ACCT_TIERS) else "dev"
        nonprod_or_prod = constants_cdk.TIER_TO_AWSENV_MAPPING[ effective_tier ]

        ### -------------------
        waf_rule_priority = 0

        waf_rules :list[aws_wafv2.CfnWebACL.RuleProperty] = [ ]

        ### HOW-TO: aws wafv2 list-available-managed-rule-groups --scope REGIONAL
        aws_managed_waf_rule_groups = [
            # "AWSManagedRulesCommonRuleSet", ### Limits payloads to just 8KB.  https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html#aws-managed-rule-groups-baseline-crs
            "AWSManagedRulesAdminProtectionRuleSet",
            "AWSManagedRulesKnownBadInputsRuleSet",  ### prevents `localhost` in host-header https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html#aws-managed-rule-groups-baseline-known-bad-inputs

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

        ### -------- add AWS-Managed WAF-Rules mimicking Enterprise Firewall-Manager-managed rules ------
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
                        # vendor_name="AWS-FMS",  # For Enterprise Firewall-Manager managed CUSTOM Rules defined at AWS-Org Root-account.
                    )
                ),
                visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled = True,
                    metric_name = f"{tier}-{mgd_waf_rule_name}",
                    sampled_requests_enabled = True,
                ),
            )
            waf_rules.append(new_rule)
            waf_rule_priority += 1

        ### -------------------
        ### Create the NEW custom WAF rule -- throttling each individual malware-user (Ticket # 2686 - rate-limiting by individual-user)
        ### oobox-WAF-capability: A rate-based rule counts incoming requests and rate limits requests when they are coming at too fast a rate.

        rate_waf_rule_name = "throttle-each-individual-user-ip"
        waf_rule_throttle_each_user = aws_wafv2.CfnWebACL.RuleProperty(
            name = rate_waf_rule_name,
            priority=waf_rule_priority,  # Adjust priority as needed based on other rules
            action = aws_wafv2.CfnWebACL.RuleActionProperty(block={}),
            # override_action is ONLY used for ManagedRuleGroups
            statement = aws_wafv2.CfnWebACL.StatementProperty(
                # not_statement=aws_wafv2.CfnWebACL.NotStatementProperty(
                    rate_based_statement=aws_wafv2.CfnWebACL.RateBasedStatementProperty(
                        ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-wafv2-webacl-ratebasedstatement.html
                        evaluation_window_sec = 60,   ### Metrics are captured for each minute; Valid settings are 60, 120, 300, and 600.
                        limit = 3000,  ### Note: minimum possible limit is 10/sec; This is 50/sec; (CloudFront only, due to SPA & BDDs being very active)
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
                cloud_watch_metrics_enabled = True,
                metric_name = f"{tier}-{rate_waf_rule_name}",
                sampled_requests_enabled = True,
            ),
        )
        waf_rules.append(waf_rule_throttle_each_user)
        waf_rule_priority += 1

        ### -------------------
        ### !! ATTENTION !! since these are the LAST Rules within this frontend's WAF-ACL, ..
        ###     .. they are "allow" (unlike Backend-WAF-ACL's equivalent-rule)
        ### Creates NEW custom WAF rule(s) -- only allowing traffic from the 2 Allowed-IP-lists
        for ipset_name in IPAllowedLists:
            ipset_arn = CdkDotJson_util.lkp_waf_IPSet_arn( cdk_scope, tier, ipset_name )
            new_rule = aws_wafv2.CfnWebACL.RuleProperty(
                name = ipset_name,
                priority = waf_rule_priority,  # Adjust priority as needed based on other rules
                action = aws_wafv2.CfnWebACL.RuleActionProperty(allow={}),
                statement = aws_wafv2.CfnWebACL.StatementProperty(
                    ip_set_reference_statement = aws_wafv2.CfnWebACL.IPSetReferenceStatementProperty(arn=ipset_arn)
                    # ip_set_reference_statement={ "arn": ipset_arn }
                ),
                visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled = True,
                    metric_name = f"{tier}-{ipset_name}",
                    sampled_requests_enabled = True,
                ),
            )
            waf_rules.append(new_rule)
            waf_rule_priority += 1

        ### ------ Create a new WAF-ACL -- just for this TIER -- using above WAF-rules -----
        self._waf_acl = aws_wafv2.CfnWebACL(
            scope_=self,
            id = tier,
            name = FrontendWAFConstruct.waf_acl_name(tier),
            description = f"Custom WAF-ACL for {tier} in {nonprod_or_prod} created via CDK - with MANUAL-efforts to mimic Enterprise Firewall-Managed WAF-ACL entries",
            ### description must obey regular-expression pattern (No quotes at all): ^[\w+=:#@/\-,\.][\w+=:#@/\-,\.\s]+[\w+=:#@/\-,\.]$
            default_action=aws_wafv2.CfnWebACL.DefaultActionProperty(block={}),
            scope = "CLOUDFRONT",
            visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled = True,
                metric_name = f"{tier}-OriginVerifyHeaderWAF",
                sampled_requests_enabled = True
            ),
            rules = waf_rules,
        )


    ### ---------------------------------------------------------------------------------------------
    ### .............................................................................................
    ### ---------------------------------------------------------------------------------------------

    def protect_cloudfront_w_waf( self,
        distribution: aws_cloudfront.Distribution,
    ) -> None:
        """
            Lookup cdk.json, for the ARN to the WAF-ACL.
            Associate the WAF-ACL to the CloudFront-distribution.

            Note: Adding a custom-WAF-Rule to this WAF-ACL is done inside `backend/src/rotate_secret_cloudfront_apigw_hdr_token/index.py`
                  Why? 'cuz, there's only one way to change a WAF-ACL.  That is  thru AWS-SDk.  No CDK-support.
        """
        stk = Stack.of(self)

        if self.waf_acl_arn:
            ### !!!!!!!! ATTENTION !!!!!!!!
            ### For CloudFront distributions, you do ---NOT--- use AWS::WAFv2::WebACLAssociation.
            ### Instead, you specify the WebACL directly in the CloudFront distribution properties.
            # wafaclass = aws_wafv2.CfnWebACLAssociation( scope = self,
            #     id="wafv2ForAPIGW",
            #     web_acl_arn = self.waf_acl_arn,
            #     resource_arn = distribution.distribution_arn,
            # )
            cfn_distribution: aws_cloudfront.CfnDistribution = distribution.node.default_child # type: ignore
            cfn_distribution.add_property_override( "DistributionConfig.WebACLId", self.waf_acl_arn )
        else:
            raise Exception("No WAF-ACL ARN defined, within FrontendWAFConstruct construct")

    ### ---------------------------------------------------------------------------------------------
    ### .............................................................................................
    ### ---------------------------------------------------------------------------------------------

    # @staticmethod
    # def get_global_waf_acl_arn(
    #     cdk_scope :Construct,
    #     tier :str,
    #     waf_acl_name :str = None,
    # ) -> str:
    #     stk = Stack.of(cdk_scope)
    #     if waf_acl_name is None: waf_acl_name = FrontendWAFConstruct.waf_acl_name( tier )
    #     global_waf_acl_arn = f"arn:{stk.partition}:wafv2:{stk.region}:{stk.account}:global/webacl/" + waf_acl_name;
    #     return global_waf_acl_arn

    # @staticmethod
    # def get_global_waf_acl_arn(
    #     cdk_scope :Construct,
    #     tier :str,
    #     waf_acl_name :str = None,
    # ) -> str:
    #     stk = Stack.of(cdk_scope)
    #     if waf_acl_name is None: waf_acl_name = FrontendWAFConstruct.waf_acl_name( tier )
    #     regional_waf_acl_arn = f"arn:{stk.partition}:wafv2:{stk.region}:{stk.account}:regional/webacl" + waf_acl_name;
    #     return regional_waf_acl_arn


### EoF
