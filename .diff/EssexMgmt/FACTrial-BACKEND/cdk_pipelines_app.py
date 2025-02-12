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
77a66,67
> add_tags( a_construct=app, tier=tier, aws_env=aws_env, git_branch=git_branch )
> 
128c118
< 
---
> ### ..............................................................................................
