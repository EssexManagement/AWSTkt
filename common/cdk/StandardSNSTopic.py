from typing import Optional
from constructs import Construct
from aws_cdk import (
    Stack,
    Fn,
    CfnOutput,
    Duration,
    aws_logs,
    aws_secretsmanager,
    aws_kms,
    aws_sns,
    aws_sqs,
)

import common.cdk.constants_cdk as constants_cdk
import cdk_utils.CdkDotJson_util as CdkDotJson_util

class StandardSNSTopic(Construct):
    def __init__(self,
        scope: Construct,
        construct_id: str,
        tier :str,
        aws_env :Optional[str] = None,
        full_topic_name :Optional[str] = None,
        display_name :Optional[str] = None,
        # **kwargs
    ):
        super().__init__(scope, construct_id)

        stk = Stack.of(self)

        if not full_topic_name:
            full_topic_name = f"{stk.stack_name}-{construct_id}"
        std_sns_key_ARN = CdkDotJson_util.lkp_cdk_json_for_kms_key( cdk_scope = scope,
            tier = tier,
            aws_env = None,
            aws_rsrc_type = CdkDotJson_util.AwsServiceNamesForKmsKeys.sns
        )
        std_sns_key = aws_kms.Key.from_key_arn( scope=self, id=f"KMSLkp-{construct_id}", key_arn=std_sns_key_ARN )
        # master_key=aws_kms.Key.from_key_arn( self, f"KMSLkp-{construct_id}", f"arn:aws:kms:{stk.region}:{stk.account}:alias/aws/sns"),

        self.topic = aws_sns.Topic(
            scope=self,
            id = construct_id,
            topic_name = full_topic_name,
            display_name = display_name if display_name else full_topic_name,
            enforce_ssl = True,
            master_key = std_sns_key,
        )
        self.topic.apply_removal_policy( constants_cdk.get_stateful_removal_policy( tier=tier, construct=self, aws_env=None ))

        # self.topic.add_to_resource_policy(
        #     aws_iam.PolicyStatement(
        #         sid="AllowPublishFromAccount",
        #         effect=iam.Effect.ALLOW,
        #         principals=[iam.AccountPrincipal(aws_account_id=props.account_id)],
        #         actions=["sns:Publish"],
        #         resources=[self.topic.topic_arn]
        #     )
        # )

### EoF
