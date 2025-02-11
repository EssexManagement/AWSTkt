24c24
< from app_pipeline.AllStacks import Gen_AllApplicationStacks
---
> from cdk_app.AllStacks import Gen_AllApplicationStacks
97c97
<     scope   = app,
---
>     app   = app,
110,113c110
< ### ==============================================================================================
< ### ..............................................................................................
< ### ==============================================================================================
< 
---
> ### -------------------------------
126,135c123
< # ### Suppress: [Error at /FACT-backend-pipeline-sarma/FACT-backend-sarma_Appln_CDKSynthDeploy-arm64-CodeBuild-arm64/Role/DefaultPolicy/Resource] AwsSolutions-IAM5[Resource::arn:<AWS::Partition>:ec2:us-east-1:127516845550:network-interface/*]: The IAM entity contains wildcard permissions and does not have a cdk-nag rule suppression with evidence for those permission.
< # NagSuppressions.add_resource_suppressions(
< #     construct = app.stateless_stack.api_construct,
< #     suppressions = [{
< #         'id': 'AwsSolutions-IAM5',
< #         'reason': 'CodeBuild requires network interface permissions to run in VPC. This is AWS managed policy permission.',
< #         'appliesTo': ['Resource::arn:<AWS::Partition>:ec2:us-east-1:127516845550:network-interface/*']
< #     }],
< #     apply_to_children = True,
< # )
---
> ### -------------------------------
137,140d124
< 
< 
< ### ..............................................................................................
< 
149,150c133,134
< from backend.infra.cdk_tests.test_cdk_backend_stk import test_backend_cdk_synth
< test_backend_cdk_synth(app)
---
> # from backend.infra.cdk_tests.test_cdk_backend_stk import test_backend_cdk_synth
> # test_backend_cdk_synth(app)
