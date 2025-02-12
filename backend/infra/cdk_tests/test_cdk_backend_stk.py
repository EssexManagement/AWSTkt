from aws_cdk import aws_sns as sns
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from app_pipeline.AllStacks import stk_refs

def test_backend_cdk_synth(app: cdk.App):

    stk = stk_refs.stateful_stk
    stk = stk_refs.buckets_stk

    # Prepare the stack for assertions.
    template = Template.from_stack(stk)

    # "Session-Results" bucket can Not have objects retained for > 1 day.
    template.has_resource(
        "AWS::S3::Bucket",
        {
            "Properties": {
                "BucketName": Match.string_like_regexp("nih-nci-fact-backend-[a-zA-Z0-9-]+-session-results"),
                "LifecycleConfiguration": {
                    "Rules": Match.array_with([
                        Match.object_like({"ExpirationInDays": Match.exact(1)}), ### We do NOT want the
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
                "aws:cdk:path": Match.string_like_regexp("FACT-backend-[a-zA-Z0-9-]+/FACT-backend-[a-zA-Z0-9-]+-Buckets/buckets/Resource")
                # "aws:cdk:path": "nccr-2567-stateful/data store/nccr_internal/Resource"
            },
        },
    )
