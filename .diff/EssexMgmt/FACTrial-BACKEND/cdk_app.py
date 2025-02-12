24c24
< from app_pipeline.AllStacks import Gen_AllApplicationStacks
---
> from cdk_app.AllStacks import Gen_AllApplicationStacks
97c97
<     scope   = app,
---
>     app   = app,
125a126
> ### -------------------------------
138,140d138
< 
< ### ..............................................................................................
< 
149,150c147,148
< from backend.infra.cdk_tests.test_cdk_backend_stk import test_backend_cdk_synth
< test_backend_cdk_synth(app)
---
> # from backend.infra.cdk_tests.test_cdk_backend_stk import test_backend_cdk_synth
> # test_backend_cdk_synth(app)
