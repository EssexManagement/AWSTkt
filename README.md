# FACT backend with cdk!


![](image/vpc-db.drawio.png)
![cdk digram](diagram.png)
* Diagram generated using https://github.com/pistazie/cdk-dia
## CDK Tree:
- App
  - pipeline (Stack)
    - Code pipeline
      - source:
        - github
          - repo
          - branch (X)
          - trigger: pull
      - synth:
        - code build
          - env: branch, repo
          - build spec
            - install
              - `npm install` cdk cli
              - `pip install` aws-cdk..
            - build
              - `export BUILDPLATFORM="linux/amd64"; export DOCKER_DEFAULT_PLATFORM="${BUILDPLATFORM}"; export TARGETPLATFORM="${DOCKER_DEFAULT_PLATFORM}"`
              - `cdk synth -c branch= -c git_repo=`
      - update pipeline
      - add **Backend** stage (*deployment.py*)
        - env: X
        - stateful Stack
          - VpcRds Constructor(L3) (*/vpc_rds*)
            - vpc
              - 2 AZ
              - public/private/isolated subnet (1 in each AZ)
              - IGW, VPCGW
            - db
              - rds-subnet-group
              - echodb
                - security group
                - master user secret with single user rotation lambda
                - sec_db user secret with multi user rotation lambda
            - custom resource
              - initialize db (create sec_db_user)


        - stateless Stack
          - etl (*/etl*)
            - aws_solutions_constructs.aws_eventbridge_lambda
            - DailyETL
              - VpcRds.vpc private-subnet
              - dailyETLlambda
              - dailyETL-rule
            - NCItETL
              - ...
          - api (*/api*)



## cross account deployment (for int, uat, main branch)
- pipeline in cicd account
  - name with *-branch*
- deploy to stage through pipeline
  - stage name as branch name
  - stage env and cidr:
    - mapping in cdk.json base on stage_name

- 1st initialize code pipeline for the branch in cicd account.
```sh
sso-cicd-devops
export BUILDPLATFORM="linux/amd64"; export DOCKER_DEFAULT_PLATFORM="${BUILDPLATFORM}"; export TARGETPLATFORM="${DOCKER_DEFAULT_PLATFORM}";
npx cdk deploy -c branch=$(git rev-parse --abbrev-ref HEAD) -c git_repo=$(git ls-remote --get-url | sed -e 's/..*github.com\/\(.*\)/\1/')

```
### Note from CDK Python blank project

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

