import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

import constants

from app_pipeline.BackendStacks import stk_refs

def test_backend_cdk_synth(
    app :cdk.App,
    tier :str,
    aws_env :str,
    git_branch :str,
):

    stk = stk_refs.stateful_stk
    stk = stk_refs.buckets_stk

    # Prepare the stack for assertions.
    template = Template.from_stack(stk)

    # "Session-Results" bucket can Not have objects retained for > 1 day.
    template.has_resource(
        "AWS::S3::Bucket",
        {
            "Properties": {
                "BucketName": Match.string_like_regexp( f"{constants.ENTERPRISE_NAME}-{constants.CDK_APP_NAME}-backend-{tier}-session-results".lower() ),
                # "BucketName": Match.string_like_regexp( f"{constants.ENTERPRISE_NAME}-{constants.CDK_APP_NAME}-backend-[a-zA-Z0-9-]+-session-results".lower() ),
                "LifecycleConfiguration": {
                    "Rules": Match.array_with([
                        Match.object_like({"ExpirationInDays": Match.exact(365)}),
                    ])
                },
                # "LifecycleConfiguration": {
                #     "Rules": Match.array_with(
                #         [
                #             Match.object_like({"Prefix": "/internal"}),
                #             Match.object_like({"Prefix": "/archive"}),
                #             Match.object_like({"Prefix": "/tmp"}),
                #         ]
                #     )
                # },
            },
            "Metadata": {
                "aws:cdk:path": Match.string_like_regexp( f"{constants.CDK_APP_NAME}-backend-[a-zA-Z0-9-]+-Buckets/buckets/Resource" )
                # "aws:cdk:path": "nccr-2567-stateful/data store/nccr_internal/Resource"
            },
        },
    )

    # "etl-data-sets" bucket can Not have objects retained for > 1 day.
    template.has_resource( "AWS::S3::Bucket", {
        "Properties": {
            "BucketName": Match.string_like_regexp( f"{constants.ENTERPRISE_NAME}-{constants.CDK_APP_NAME}-backend-{tier}-etl-data-sets".lower() ),
            "LifecycleConfiguration": {
                "Rules": Match.array_with([
                    Match.object_like({"Transitions": [{"StorageClass": "GLACIER_IR", "TransitionInDays": 2}]})
                 ])
        }},
        "Metadata": { "aws:cdk:path": Match.string_like_regexp( f"{constants.CDK_APP_NAME}-backend-[a-zA-Z0-9-]+-Buckets/etl_data_sets/Resource" ) },
    })
