# Deploy MAJOR-version of FACTrial onto CRRI-cloud

# What is a Major Release

1.  Changes to the Pipeline (**[even if]{.underline}** we THINK the
    application will Not be affected, **[if No]{.underline}**
    Application-code-changes)

    1.  CodePipeline changes

    2.  changes to devops-StepFunctions

2.  Changes that **[require deletion]{.underline}** of Stacks:

    1.  Example: Some 𝜆s are retired, and should No longer be in
        Production

    2.  Example: New Stacks with inter-stack inter-dependencies.

    3.  Example: Upgrade of Data-Repository AWS-Services like RDS-Aurora
        V1-to-V2, RDS-Postgres-Version, DynamoDB-schemas, etc..

3.  Software **Upgrades**.

    1.  Example: CDK-Version Upgrade (which will be treated as impact to
        Pipeline as well as Stacks)

4.  Drastically difference / changes in Application functionality.

5.  Even for (what should be a) MINOR-Release, if there are **Any
    Stack-Failures at deployment** into int and uat that require
    deletion of Stacks, we will switch from minor-release-process to
    major-release process.

# Pre-Requisite: GFE-based activities:- 

1.  Developer merges dev -to-\> main Git-Branch.

2.  Developer does  git push -to-\> main git branch.

3.  git switch main\
     (that is, switch over to main git-branch), and then ..

4.  git fetch \--all

5.  git pull 

6.  GITHUB_REPOSITORY=\$(git ls-remote \--get-url \| sed -e
    \'s/..\*github.com\\/\\(.\\)/\\1/\');

7.  **Synth** the BACKEND Pipelines (both CI-CD and devops):

    1.  npx cdk synth \--require-approval never \--quiet \--app
        \"python3 all_pipelines.py\" FACT-backend-pipeline-\${TIER}
        FACT-devops-pipeline-\${TIER} -c tier=\${TIER} -c
        git_repo=\${GITHUB_REPOSITORY} \--profile \${AWSPROFILE}
        \--region \${AWSREGION}

    2.  npx cdk synth \--require-approval never \--quiet \--all -c
        tier=\${TIER} -c git_repo=\${GITHUB_REPOSITORY} \--profile
        \${AWSPROFILE} \--region \${AWSREGION}

8.  **Synth** the FRONTEND pipelines (both CI-CD and devops):

    1.  npx cdk synth \--require-approval never \--quiet \--app
        \"python3 all_pipelines.py\" \--all -c tier=\${TIER} -c
        git_repo=\${GITHUB_REPOSITORY} \--profile \${AWSPROFILE}
        \--region \${AWSREGION}

    2.  npx cdk synth \--require-approval never \--quiet \--all -c
        tier=\${TIER} -c git_repo=\${GITHUB_REPOSITORY} \--profile
        \${AWSPROFILE} \--region \${AWSREGION}

 There should be NO errors NOR warnings in any of the above commands.

# Cloud-Engineering Team's Tasks:

1.  Go to Backend Git-Repo's GitHub **website** at:
    [https://github.com/BIAD/FACTrial-backend-cdk](https://github.com/BIAD/emFACT-backend-cdk)

2.  Switch to main git-branch.\
    Note: Always avoid ; Instead use switch always.

    1.  Update cdk.json in main git-branch, with latest version#.

3.  Click on "*Releases*" link (Look for it on ***right-hand side*** of
    webpage)

4.  Create a New *Release* with a NEW *git-tag* (say, 1.9.9 )

5.  **[Repeat]{.underline}** for Frontend's GitHub-repo  at:
    [https://github.com/BIAD/FACTrial-frontend-cdk](https://github.com/BIAD/emFACT-frontend-cdk)

6.  **Deploy** / Update the BACKEND Pipeline deployment / update:

    1.  npx cdk deploy \--require-approval never \--quiet \--app
        \"python3 all_pipelines.py\" FACT-backend-pipeline-\${TIER}
        FACT-devops-pipeline-\${TIER} -c tier=\${TIER} -c
        git_repo=\${GITHUB_REPOSITORY} \--profile \${AWSPROFILE}
        \--region \${AWSREGION}

7.  **Deploy** / Update the FRONTEND Pipeline Deployment / update:

    1.  npx cdk synth \--require-approval never \--quiet \--app
        \"python3 all_pipelines.py\" \--all -c tier=\${TIER} -c
        git_repo=\${GITHUB_REPOSITORY} \--profile \${AWSPROFILE}
        \--region \${AWSREGION}

8.  Follow instructions in
    [Appendix](https://bioappdev.atlassian.net/wiki/spaces/BADC/pages/3754983439)
    -- to fix the CDK's global-roles (which are common to all
    CDK-projects)

9.  Manually: via AWS-Console

    1.  Re-creating RDS-Database? **-IF-** yes, remove Delete-protection
        for existing RDS-instance.

    2.  Re-creating Dynamo-DB Tables? **-IF-** yes, then remove
        Delete-protection for existing DDB-Table.

    3.  Re-creating Cognito user-pool? **-IF-** yes, then remove any
        Delete-protections, if any.

    4.  Similarly for other AWS-Resources.

10. Manually: Within CodePipeline-console:

    1.  click on FACT-devops-pipeline-\${TIER}.

    2.  click on the **Orange-button** labeled "*Release Change*".

    3.  **Wait for it to complete** successfully.\
        FYI -- on completion it will UPDATE / DEPLOY the "*devops*"
        StepFunctions/pipeline.

11. Manually click "*Start Execution*" **orange**-button on the
    ***1ClickEnd2End*** Stepfunction, for that specific TIER (
    int\|uat\|prod ).\
    NOTE: Provide the following json as input to this stepfunction.\
       {   \"delete-all-stacks-NO-pipelines\":   \"yup\"  }           \
    In case the StepFunction **FAILS** .. .. STOP ALL deployment.

12. WAIT \-- Above step/stepfunction takes \~ 1hr + 45min +/- to
    complete.

13. Next, check whether that TIER's ( int\|uat\|prod ) pipeline &
    application are *DEPLOYED successfully*.

14. In case of any **Stack-Errors**, please refer to other sections of
    this document titled "***[Error! Reference source not
    found.]{.underline}***" in all-inclusive word-document for
    FACTrial.\
    This strategy above .. works sometimes .. .. **[but
    is]{.underline}** specific to issues with "*StateLESS*" stacks (𝜆,
    apigw, CF).

15. In case of **"failure" of BDDs** in INT\|UAT\|PROD FRONTEND's
    pipeline,  ..\
    2 steps to try to resolve:-

    1.  STEP 1:\
        Independent of whether the BDDs succeed or fail, ..\
        .. **Manually Sanity-check** the application via GFE's browser.\
        Use the contents in the Appendix section titled "*Appendix --
        Checklist for Sanity Tests*".

    2.  STEP 2:\
        Re-Run the StepFunction named
        "FACT-devops-{ENV}-sfn-1ClickEnd2End".

        -   If BDDs are .. STILL  NOT  .. successful, move to step 3
            below.

    3.  STEP 3:\
        please seek help from **Vivek or Matt** (and finally Sarma), ..\
        RE: **whether the failure is benign**, and whether we can STILL
        proceed to UAT & PROD.

16. If **all OK with** above steps .. ..\
    Run the script:
    <https://github.com/BIAD/cloud_eng/blob/master/Applications/FACTrial-CRRI/delete-ECRRepo-Images-Not-In-Use.py>
    as:

    1.  **[Objective]{.underline}**: To Cleanup FACTrial-specific
        ECR-Repo so old ECR-images do Not trigger Security-Findings.

    2.  CLI commands:\
        git clone <https://github.com/BIAD/cloud_eng>\
        cd cloud_eng\
        AWSPROFILE= .. .. ..\
        python3 ./operations/bin/delete-ECRRepo-Images-Not-In-Use.py 
        \$AWSPROFILE

    3.  Copy and run the aws-cli-commands **[OUTPUTTED by the above
        script]{.underline}** .. .. As-Is !!!\
        Those commands start with aws ecr batch-delete-image .. ..

 

End of Page.
