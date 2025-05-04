---
FACTrial
---

-   [backend repo](https://github.com/BIAD/emFACT-backend-cdk)

-   [frontend repo](https://github.com/BIAD/emFACT-frontend-cdk)

-   [frontend
    package.json](https://github.com/BIAD/emFACT-frontend-cdk/blob/main/frontend/ui/package.json)

-   [backend API
    requirements](https://github.com/BIAD/emFACT-backend-cdk/blob/main/api/runtime/requirements.txt)

-   [backend ETL
    requirements](https://github.com/BIAD/emFACT-backend-cdk/blob/main/etl/runtime/requirements.txt)

-   [backend Rds Init
    requirements](https://github.com/BIAD/emFACT-backend-cdk/blob/main/rds_init/runtime/requirements.txt)

-   [Infrastructure, Methodology and Dataflow
    Lucidchart](https://lucid.app/lucidchart/b84c4364-8114-46ea-b232-6f8912afa776/edit?invitationId=inv_58ffbaa7-460c-4bbe-96a6-33a24525ab8b&page=HUXaWI3mgkW5)

-   [Local DB
    Setup](https://github.com/BIAD/emFACT-backend-cdk/blob/main/docs/local-db-init.md)

## Technical Stack High Level

### Frontend

-   Vue 2.0

-   See package.json

### Backend

-   Python 3.10

-   AWS RDS Aurora

-   Cognito User Pools

-   API GW

-   Lambda

-   Secrets Manager

-   Parameter Store

-   S3

-   psycopg2

-   pandas

-   See backend requirements above

### Infrastructure, Build and Deploy

-   CDK

-   CodePipeline

-   See Infrastructure LucidChart link above
