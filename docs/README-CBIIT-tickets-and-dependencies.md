# Overview of interactions with CBIIT.

1. New ESR a.k.a. ServiceNow Ticket to be created by OWNER of the system (example: subhashini.jagu@nih.gov)
1. Calls will be setup by CBIIT - with extensive-agenda covering:
   1. to review the solution,
   2. require any common/popular or unique AWS-requirements,
   3. revuew security-requirements,
   4. etc..
1. After approval of review, CBIIT team will be given go-ahead to create "stuff".
   1. AWS Accounts
   2. IAM-Roles - standard/common
      1. Admin-Role - explicitly identify team-members
      2. DevOps-Role - explicitly identify team-members
      3. ReadOnly-Role - explicitly identify team-members
      4. PowerUser-Role (developers) - explicitly identify team-members
   3. IAM-Roles - UNIQUE to solution - if any.
      1. Define each such unique role + explicitly identify team-members
   4. VPCs
   5. Subnets
   6. VPC-EndPoints (if necessary)
   7. Egress arrangements (connect to internet from VPC) .. and/or NATGW.
   8. Domains, FQDNs & SSL-Certs
   9.  SES-setup
   10. SMTP-Outbound
   11. Cognito-Outbound

2. Be aware of CBIIT tagging requirements.
    * REF: https://clinicalbiomed.slack.com/archives/C0886J6PEDP/p1743021532056109?thread_ts=1742584049.213409&cid=C0886J6PEDP

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# `NON-Prod` aws-account

Create ticket or informally connect with CBIIT-Team re:

1. `NON-prod` account -- Private CIDR - that is sufficiently large (example: `/18`)
2. `NON-prod` Egress CIDR - that is small (example: `/28`)

<BR/><BR/>
<HR/><HR/>

# `dev` Tier

Create ticket or informally connect with CBIIT-Team re:

1. `dev` VPC
1. `dev` Cloud-Private Subnets - in 2 AZs for resiliency -- based on `Private CIDR` above.
1. `dev` Egress Subnet - at least one AZ -- based on `EGRESS CIDR` above.
1. `dev` VPC's VPC-EndPoints for:
    1. secretsmanager
    2. ssm
    3. ssm-contacts
    4. ssm-incidents
    5. ec2
    6. logs
    7. ec2messages
    8. ssmmessages
    9. ssm-quicksetup
    10. ecr.api
    11. ecr.dkr
    12. s3 (Gateway)
    13. dynamodb (Gateway)
7. `DEV` VPC - request a EC2 instance inside the `Cloud-Private Subnet`
   1.  ONLY IF the VPCEndPt for `ssm` exists & `session-manager` access allowed, then .. the DevOps-Role should be able to do this.
8. `dev` VPC - using EC2
   1. confirm `Session-Manager` access and
   1. confirm egress


<BR/><BR/>
<HR/><HR/>

# `test | qa` Tier

Same as for `dev`

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# `Production` aws-account

Create ticket or informally connect with CBIIT-Team re:

1. `production` account -- Private CIDR - that is sufficiently large (example: `/18`)
2. `production` Egress CIDR - that is small (example: `/28`)

<BR/><BR/>
<HR/><HR/>

# `stage` Tier

Create ticket or informally connect with CBIIT-Team re:

1. `stage` VPC
1. `stage` Cloud-Private Subnets - in 2 AZs for resiliency -- based on `Private CIDR` above.
1. `stage` Egress Subnet - at least one AZ -- based on `EGRESS CIDR` above.
1. `stage` VPC's VPC-EndPoints for:
    1. secretsmanager
    2. ssm
    3. ssm-contacts
    4. ssm-incidents
    5. ec2
    6. logs
    7. ec2messages
    8. ssmmessages
    9. ssm-quicksetup
    10. ecr.api
    11. ecr.dkr
    12. s3 (Gateway)
    13. dynamodb (Gateway)
7. `stage` VPC - request a EC2 instance inside the `Cloud-Private Subnet`
   1.  ONLY IF the VPCEndPt for `ssm` exists & `session-manager` access allowed, then .. the DevOps-Role should be able to do this.
8. `stage` VPC - using EC2:
   1. confirm `Session-Manager` access and
   1. confirm egress

<BR/><BR/>
<HR/><HR/>

# `production` Tier

Same as for `stage`

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

/ EoF
