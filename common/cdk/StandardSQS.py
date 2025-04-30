from numbers import Number
from typing import Any, Dict
from constructs import Construct
from aws_cdk import (
    Stack,
    Fn,
    CfnOutput,
    RemovalPolicy,
    Duration,
    aws_logs,
    aws_secretsmanager,
    aws_kms,
    aws_sns,
    aws_sqs,
)

import cdk_utils.CdkDotJson_util as CdkDotJson_util

class StandardSQS(Construct):
    def __init__(self,
        scope: Construct,
        construct_id: str,
        tier :str,
        uniq_queue_name: str | None = None,
        visibility_timeout: Duration | None = None,
        delivery_delay: Duration | None = None,
        max_message_size_bytes: Number | None = None,
        receive_message_wait_time: Duration | None = None,
        removal_policy: RemovalPolicy | None = None,
        retention_period: Duration | None = None,
        dead_letter_queue: aws_sqs.DeadLetterQueue | Dict[str, Any] | None = None,
        content_based_deduplication: bool | None = None,
        deduplication_scope: aws_sqs.DeduplicationScope | None = None,
        fifo: bool | None = None,
        fifo_throughput_limit: aws_sqs.FifoThroughputLimit | None = None,
        redrive_allow_policy: aws_sqs.RedriveAllowPolicy | Dict[str, Any] | None = None,
        data_key_reuse: Duration | None = None,

        encryption: aws_sqs.QueueEncryption | None = None,
        encryption_master_key: aws_kms.IKey | None = None,
        # enforce_ssl: bool | None = None,
    ):
        super().__init__(scope, construct_id)

        stk = Stack.of(self)

        full_name = f"{stk.stack_name}-{construct_id}"
        std_sqs_key_ARN = CdkDotJson_util.lkp_cdk_json_for_kms_key( cdk_scope = scope,
            tier = tier,
            aws_env = None,
            aws_rsrc_type = CdkDotJson_util.AwsServiceNamesForKmsKeys.sqs
        )
        std_sqs_key = aws_kms.Key.from_key_arn( scope=self, id=f"KMSLkp-{construct_id}", key_arn=std_sqs_key_ARN )
        # encryption_master_key=aws_kms.Key.from_key_arn( self, f"KMSLkp-{construct_id}", f"arn:aws:kms:{stk.region}:{stk.account}:alias/aws/sns"),

        self.queue = aws_sqs.Queue(
            scope=self,
            id = construct_id,
            queue_name = uniq_queue_name if uniq_queue_name else full_name,

            enforce_ssl=True,
            encryption = encryption if encryption else aws_sqs.QueueEncryption.KMS,
            encryption_master_key = encryption_master_key if encryption_master_key else std_sqs_key,

            visibility_timeout=visibility_timeout,
            delivery_delay=delivery_delay,
            max_message_size_bytes=max_message_size_bytes,
            receive_message_wait_time=receive_message_wait_time,
            removal_policy=removal_policy,
            retention_period=retention_period,
            dead_letter_queue=dead_letter_queue,
            content_based_deduplication=content_based_deduplication,
            deduplication_scope=deduplication_scope,
            fifo=fifo,
            fifo_throughput_limit=fifo_throughput_limit,
            redrive_allow_policy=redrive_allow_policy,
            data_key_reuse=data_key_reuse,
        )

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
