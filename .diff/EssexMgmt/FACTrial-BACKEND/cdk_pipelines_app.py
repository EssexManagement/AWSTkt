23,26c23
< from app_pipeline.pipeline  import AppDeployPipelineStack ### ./pipeline.py
< from devops.pipeline        import MultiCdkSubProjectsPipelineStack
< from operations.pipeline    import OperationsPipelineStack
< from devops.meta_pipeline   import MetaPipelineUpdatesOtherPipelinesStack
---
> from cdk_app.pipeline_stack import AwsTktPipelineStack
28c25
< ### -------------------------------------------------------------------------------------
---
> ### ..............................................................................................
47,55d43
< # if tier in constants.STD_TIERS:
< #     pipeline_account = app.node.try_get_context("aws_env")[tier]
< # else:  ### developer specific tier
< #     pipeline_account = app.node.try_get_context("aws_env")[ "dev" ]
< # # if tier in constants.UPPER_TIERS: ### ["int", "uat", "prod"]:
< # #     pipeline_account = app.node.try_get_context("aws_env")["cicd"]
< # # else:
< # #     pipeline_account = app.node.try_get_context("aws_env")["dev"]
< 
63c51,53
< ### -----------------------------------
---
> HDR = " inside "+ __file__
> 
> ### ..............................................................................................
67,68c57
< stk = AppDeployPipelineStack(
<     scope=app,
---
> AwsTktPipelineStack( scope=app,
71,73c60,61
<     aws_env=aws_env,
<     git_branch=git_branch,
<     env=env ### kwargs
---
>     aws_env=constants.DEV_TIER,
>     git_branch=constants.get_git_branch(tier),
76c64
< add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )
---
> ### ..............................................................................................
78,80c66
< ### -----------------------------------
< cdk_component_name=f"devops-pipeline"
< stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )
---
> add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )
82,125d67
< multstks = MultiCdkSubProjectsPipelineStack(
<     scope=app,
<     stack_id=stack_id,
<     tier=tier,
<     git_branch=git_branch,
<     aws_env=aws_env,
<     env=env ### kwargs
< )
< 
< add_tags( a_construct=multstks, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )
< 
< ### -----------------------------------
< # cdk_component_name=f"operations-pipeline"
< # stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )
< 
< # stk = OperationsPipelineStack(
< #     scope=app,
< #     stack_id=stack_id,
< #     tier=tier,
< #     git_branch=git_branch,
< #     aws_env=aws_env,
< #     env=env ### kwargs
< # )
< 
< # add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )
< 
< ### -----------------------------------
< if tier == constants.DEV_TIER or tier not in constants.STD_TIERS:
<     cdk_component_name=f"meta-pipeline"
<     stack_id = aws_names.gen_awsresource_name_prefix( tier=tier, cdk_component_name=cdk_component_name )
< 
<     stk = MetaPipelineUpdatesOtherPipelinesStack(
<         scope=app,
<         stack_id=stack_id,
<         tier=tier,
<         git_branch=git_branch,
<         aws_env=aws_env,
<         env=env ### kwargs
<     )
< 
<     add_tags( a_construct=stk, tier=tier, aws_env=aws_env, git_branch=pipeline_source_gitbranch )
< 
< ### -----------------------------------
< 
128c70
< 
---
> ### ..............................................................................................
