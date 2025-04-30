import json
from typing import Union, Optional
from aws_cdk import (
    CfnOutput,
    Tag, CfnTag,
    Fn,
    Names,
    App,
    Stack,
    RemovalPolicy,
    Duration,
    CfnParameter,
    aws_iam,
    aws_logs,
    aws_ssm,
    aws_ec2,
)

from constructs import Construct

import constants
import common.cdk.aws_names as aws_names
import common.cdk.constants_cdk as constants_cdk

from cdk_utils.CdkDotJson_util import get_cdk_json_vpc_details

class VpcWithSubnetsConstruct(Construct):
    """
        Current Implementation:  Creates a new VPC with --ONLY-- No-Egress Private-Subnets.
        But, if a VPC-ID is provided within `cdk.json`, then this does Construct nothing.
    """

    @property
    def vpc_id(self) -> aws_ec2.IVpc:
        return self._vpc_id

    @property
    def new_private_subnet_ids(self) -> list[str]:
        return self._new_private_subnet_ids

    @property
    def new_private_subnets(self) -> list[aws_ec2.CfnSubnet]:
        return self._new_private_subnets

    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    def __init__(self, scope: Construct, construct_id: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        cdk_app_name :CfnParameter,
        tags :list[dict[str,str]],
        tagsCfn :list[CfnTag],
    ) -> None:
        """
            If vpc_id provided in cdk.json, it will look it up as a aws_ec2.IVpc, or .. Creates just one single NEW VPC.

            Named as per `aws_names.py` naming standards (for each tier).
            Other than the usual triplet (tier, aws_env/aws_acct and git_branch) ..
                .. pass in param #4 (app-name) ..
               .. so that the CLoudFormation-generated is generic.
        """
        super().__init__(scope, construct_id)
        stk = Stack.of(scope)

        print( f"tier = '{tier}' within "+ __file__ )
        print( f"git_branch = '{git_branch}' within "+ __file__ )
        print( f"aws_env = '{aws_env}' within "+ __file__ )

        vpc_name=aws_names.get_vpc_name( tier=tier, aws_region=stk.region )
        print( f"vpc_name = '{vpc_name}' -- for aws_env ='{aws_env}' and tier = '{tier}' and git_branch = '{git_branch}'" )

        # ### Only applicable for personal-cloud Safety-check.
        # if tier != constants.ACCT_NONPROD and tier != constants.ACCT_PROD:   ###  and tier not in constants.STD_TIERS:
        #     # print( f"For tier='{tier}', --NOT-- creating a new VPC. Instead RE-USING dev-environment's VPC='{vpc_name}' // "+ __file__)
        #     # vpc = aws_ec2.Vpc.from_lookup( scope=scope, id="vpcLookup", vpc_name=vpc_name )
        #     raise ValueError(f"ERROR: ❌❌❌ for aws_env=`{aws_env}` & tier='{tier}': Rejecting VPC-creation for '{vpc_name}'")

        ### ----------------------------
        ### define all common variables to be used in rest of this Construct

        vpcL2Construct :aws_ec2.Vpc = None;
        vpc_cfn :aws_ec2.CfnVPC = None;

        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
        [ acct_wide_vpc_details, vpc_details_for_tier ] = get_cdk_json_vpc_details( self, aws_env, tier )

        if vpc_details_for_tier and "vpc-id" in vpc_details_for_tier and vpc_details_for_tier["vpc-id"].strip(' \t?!-_*#%.') != "":
            ### "vpc-id" is specified in cdk.json, representing an actual PRE-CREATED Vpc.
            vpc_id = vpc_details_for_tier["vpc-id"]
            self._vpc_id = vpc_id
            print( f"Re-using an existing VPC {vpc_id} for aws_env='{aws_env}' and tier='{tier}'" )
        else:
            vpc_id = None

        if vpc_details_for_tier and "vpc-cidr" in vpc_details_for_tier:
            vpc_cidr_block = vpc_details_for_tier["vpc-cidr"]
            print(f"vpc_cidr_block = '{vpc_cidr_block}'")
        else:
            if not vpc_id:
                raise ValueError(f"cdk.json file is MISSING value for `vpc-cidr` and missing `vpc_id` under aws_env='{aws_env}' under 'vpc' /// FYI: tier='{tier}'.")
            # else:

        ### ----------------------
        if vpc_id:
            ### (NOT Working) add a new CIDR block to ---EXISTING--- VPC
            ###         See more details in CDK-code below.
            ### Hence, if VPC already exists,  we can --NOT-- do much to ALTER the vpc here in CDK-code
            vpcL2Construct :aws_ec2.IVpc = aws_ec2.Vpc.from_lookup( scope=scope, id="vpc-lookup-"+vpc_id, vpc_id=vpc_id )
            vpc_cidr_block = vpcL2Construct.vpc_cidr_block

        else:

            ### Create the VPC using RAW-CloudFormation
            [ vpc_cfn, vpc_id ] = self.create_raw_CfnVPC( scope=scope, tier=tier, aws_env=aws_env, vpc_name=vpc_name, cdk_app_name=cdk_app_name, vpc_cidr_block=vpc_cidr_block, tags=tags, tagsCfn=tagsCfn )

            ### Create the VPC using Level-2 CDK-construct aws_ec2.Vpc.
            ### Big problem with this L2-Construct.  It forces a certain Subnet-structure that we do NOT want !!!
            # [ vpcL2Construct, vpc_id, new_private_subnets, new_private_subnet_ids, subnet_lkp, subnet_per_az_lkp ] = self.create_new_Level2VpcConstruct(
            #             tier, aws_env, git_branch, acct_wide_vpc_details, vpc_name, cdk_app_name, vpc_cidr_block, tags, tagsCfn )

            self._vpc_id = vpc_id

        print( f"vpc_id = '{vpc_id}'" )

        ### ----------------------

        # [ new_private_subnets, new_private_subnet_ids, subnet_lkp,  list_of_azs, subnet_per_az_lkp
        # ] = VpcWithSubnetsConstruct.create_raw_subnet( aws_env=aws_env, vpc_id=vpc_id, acct_wide_vpc_details=acct_wide_vpc_details, tags=tags, tagsCfn=tagsCfn )

        # [ new_private_subnets, new_private_subnet_ids, subnet_lkp, list_of_azs, subnet_per_az_lkp
        # ] = VpcWithSubnetsConstruct.create_L2Subnets( tier=tier, aws_env=aws_env, vpc_id=vpc_id, acct_wide_vpc_details=acct_wide_vpc_details, tags=tags, tagsCfn=tagsCfn )

        # self._new_private_subnets    = new_private_subnets
        # self._new_private_subnet_ids = new_private_subnet_ids


    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    @staticmethod
    def create_raw_CfnVPC(
        scope :Construct,
        tier :str,
        aws_env :str,
        vpc_name :str,
        cdk_app_name :CfnParameter,
        vpc_cidr_block :str,
        tags :list[dict[str,str]],
        tagsCfn :list[CfnTag],
    ) -> tuple[ aws_ec2.CfnVPC, str ]:
        """
            Params:
                1. tier :str
                2. aws_env :str
                3. vpc_name :str -- NOT used currently (but this value is utilized via tagsCfn parameter)
                4. cdk_app_name :str -- typically, constants.CDK_APP_NAME
                5. vpc_cidr_block :str
                6. tags :dictionary
                7. tagsCfn :raw-tags format (list of aws_ec2.CfnTags objects)
            Returns the following as a tuple:
                1. new aws_ec2.CfnVPC Raw-CloudFormation-Level-0 construct-instance <------- Note !!!!!
                2. vpc_id :str
        """

        ### If No "vpc-id" specified, then we create the VPC from scratch, with ONE default PUBLIC Subnet (as per the below Standard CDK-Construct)
        print( f"Creating a new VPC for tier='{tier}'" )

        flowlogs_name = f"{cdk_app_name.default}-{tier}-VPC"
        uuid = Names.unique_id(scope)

        vpc_cfn = aws_ec2.CfnVPC( scope=scope, id="VPC",
            cidr_block = vpc_cidr_block,
            enable_dns_hostnames = True,
            enable_dns_support = True,
            tags = tagsCfn,
        )
        vpc_cfn.apply_removal_policy( RemovalPolicy.DESTROY )
        # vpc_cfn.apply_removal_policy( constants_cdk.get_stateful_removal_policy( scope=scope, tier=tier, aws_env=aws_env ) )
        vpc_id = vpc_cfn.ref

        flow_logs_role = aws_iam.Role( scope=scope, id="VPCFlowLogsRole",
            assumed_by=aws_iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
            description="Role for VPC Flow Logs to publish to CloudWatch",
        )
        flow_logs_role.apply_removal_policy( RemovalPolicy.DESTROY )
        # flow_logs_role.apply_removal_policy( constants_cdk.get_stateful_removal_policy( scope=scope, tier=tier, aws_env=aws_env ) )
        flow_logs_loggrp = aws_logs.LogGroup( scope=scope, id="VPCFlowLogsCWLogsGroup",
            log_group_name = f"/aws/VPC/{flowlogs_name}/FlowLogs-"+uuid,
            log_group_class = aws_logs.LogGroupClass.STANDARD,
            retention = constants_cdk.get_LOG_RETENTION( construct=scope, tier=tier, aws_env=aws_env ),
            # removal_policy = constants_cdk.get_stateful_removal_policy( scope, tier, aws_env ),
        )
        flow_logs_loggrp.apply_removal_policy( RemovalPolicy.DESTROY )
        # flow_logs_loggrp.apply_removal_policy( constants_cdk.get_stateful_removal_policy( scope=scope, tier=tier, aws_env=aws_env ) )
        flow_logs_role.add_to_policy( aws_iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams"
                ],
                resources=[flow_logs_loggrp.log_group_arn]
        ))
        flow_logs_role.add_to_policy( aws_iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[flow_logs_role.role_arn]
        ))

        flowlog = aws_ec2.CfnFlowLog( scope=scope, id="VPCFlowLogs",
            resource_id = vpc_id,
            resource_type = "VPC",
            log_group_name = flow_logs_loggrp.log_group_name,
            log_destination_type = "cloud-watch-logs",
            traffic_type = "ALL",
            deliver_logs_permission_arn = flow_logs_role.role_arn,
            # max_aggregation_interval = 600,
            # log_format = "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}",
            tags=tagsCfn,
        )
        flowlog.apply_removal_policy( RemovalPolicy.DESTROY )
        # flowlog.apply_removal_policy( constants_cdk.get_stateful_removal_policy( scope=scope, tier=tier, aws_env=aws_env ) )
            ### "Type": "AWS::EC2::FlowLog",
            ### "Properties": {
            ###     "ResourceId": {"Ref": "vpconlyVPC93135FBE"},
            ###     "ResourceType": "VPC",
            ###     "LogGroupName": {"Ref": "vpconlyVPCFlowLogs889B9A96"},
            ###     "LogDestinationType": "cloud-watch-logs",
            ###     "LogFormat": "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}",
            ###     "TrafficType": "ALL"
            ###     "DeliverLogsPermissionArn": {"Fn::GetAtt": ["vpconlyVPCacctIAMRole9737AD5C", "Arn"]},
            ###     "MaxAggregationInterval": 600,

        ### ------------------------------------------------------
        ### Whether or not VPC -already- exists .. do the following
        ### ------------------------------------------------------
        ### 1. (NOT Working) add a new CIDR block to the VPC --> instead, create a new vpc using this CIDR.
        ### 2. create NEW Private Subnets with NO-EGRESS whatsoever.
        ### 3. Create Route-Tables to connect these subnets
        ### 4. Finally create all the VPCEndPoints.
        ### ------------------------------------------------------

        # aws_ec2.CfnVPCCidrBlock( scope=scope, id="AdditionalCIDR"+vpc_cidr_block,
        #     vpc_id = vpc_id,
        #     cidr_block = vpc_cidr_block,
        # )
        ### Error: CREATE_FAILED vpconlyAdditionalCIDR1000016BF33E643
        ### Resource handler returned message: "The CIDR '10.0.0.0/16' is restricted. Use a CIDR from the same private address range as the current VPC CIDR, or use a publicly-routable CIDR.
        ### FYI only. ROOT CAUSE: The original-VPC's original-CIDR block was already RFC 1918 private range ( 192.168.0.0/16).
        ###             Per Amazon-Q, can -NOT- add a 2nd VPC-CIDR that is -ALSO- RFC 1918 private range ( 10.0.0.0/16),
        ### ATTENTION: When I tried the above --MANUALLY-- via VPC-Console, I got the EXACT-SAME error-message!!!

        return [ vpc_cfn, vpc_id ]

    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    @staticmethod
    def create_raw_subnets_for_acct(
        scope :Construct,
        aws_env :str,
        vpc_id_lkp :dict[str,str],
        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]],
        tags :list[dict[str,str]],
        tagsCfn :list[CfnTag],
    ) -> tuple[ list[aws_ec2.CfnSubnet], list[str],   dict[str,aws_ec2.CfnSubnet],   list[str],   dict[str,list[aws_ec2.CfnSubnet]]  ]:
        """
            NOTE: This method uses `aws_ec2.CfnSubnet` lowest-level Construct (almost same as CloudFormation)
            NOTE: If "route-table" is provided in cdk.json, that will be used, else a new CfnRouteTable instance is created.

            params:
                2. aws_env :str
                3. vpc_id_lkp :dict[str,str]
                4. acct_wide_vpc_details :json-snippet from cdk.json
                5. tags :dict[str,str]
                6. tagsCfn :list[aws_ec2.CfnTag]
            Returns the following as a tuple:
                1. new_private_subnets :list[aws_ec2.CfnSubnet]
                2. new_private_subnet_ids :list[str]
                3. subnet_lkp :dict[str,aws_ec2.CfnSubnet] ---  subnet-name -to-> construct
                4. list_of_azs :list[str]
                5. subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] --- AZ-name -to-> construct
        """

        new_private_subnets :list[aws_ec2.CfnSubnet] = []
        new_private_subnet_ids :list[str] = []
        list_of_azs :list[str] = []
        subnet_lkp :dict[str,aws_ec2.CfnSubnet] = {}   ### subnet-name -to-> construct
        subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] = {}   ### AZ-name -to-> construct
        counter = 1

        tier_based_info :dict[str,list[str] ]= constants_cdk.SUBNET_NAMES_LOOKUP[ aws_env ]
        # if tier_based_info is of type "list[str]", do nothing else, but if it is of type "dict[str,list[str]]", the tier_based_info = tier_based_info[??], else .. raise exception
        if not isinstance(tier_based_info, list):
            if isinstance(tier_based_info, dict):
                print( f"About to create RAW-CloudFormation-subnets for tiers: '{tier_based_info.keys()}'" )
                # for tiers_in_this_acct in tier_based_info.keys():
                #     print( f"Creating RAW-CloudFormation-subnets for tier_in_this_acct='{tiers_in_this_acct}'" )
            else:
                raise Exception(f"`constants_cdk.SUBNET_NAMES_LOOKUP` is of UNKNOWN type {type(tier_based_info)}, but it should be of type list[str] or dict[str,list[str]]")

        ### create pure NO-egress PRIVATE-Subnets across AZs

        for tier_in_awsenv in tier_based_info.keys():
            print( f"tier_in_awsenv = '{tier_in_awsenv}' ................................................................................. " )

            ### 1st identify if a Route-Table is already specified in cdk.json
            ### If NONE, then create a RoutTable per Tier.
            vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
            if acct_wide_vpc_details and tier_in_awsenv in acct_wide_vpc_details:
                vpc_details_for_tier = acct_wide_vpc_details[tier_in_awsenv]
            else:
                raise Exception(f"`cdk.json's acct_wide_vpc_details is missing entry for tier: {tier_in_awsenv}")

            if "route-table" in vpc_details_for_tier:
                route_table_id = vpc_details_for_tier["route-table"]
            else:
                ### Need to create our own RouteTable.  So, that it can be shared across --ALL-- the PRIVATE-NO-EGRESS-subnets
                route_table = aws_ec2.CfnRouteTable( scope=scope, id = 'Shared-RouteTable for private-NO-egress-subnets',
                    vpc_id = vpc_id_lkp[tier_in_awsenv],
                    tags = tagsCfn,
                )
                route_table_id = route_table.attr_route_table_id
            print( f"route_table_id = '{route_table_id}'" )

            for subnet_name in tier_based_info[tier_in_awsenv]:

                [ retval_new_private_subnets, retval_new_private_subnet_ids,  retval_subnet_lkp,  retval_list_of_azs,    retval_subnet_per_az_lkp
                ] = VpcWithSubnetsConstruct.create_raw_subnet(
                    scope = scope,
                    aws_env = aws_env,
                    tier_in_awsenv = tier_in_awsenv,
                    vpc_id = vpc_id_lkp[tier_in_awsenv],
                    route_table_id = route_table_id,
                    subnet_name = subnet_name,
                    vpc_details_for_tier = vpc_details_for_tier,
                    tags = tags,
                    tagsCfn = tagsCfn,
                )
                # copy all content from retval_*** into local-variables (which are used as return-values of this method)
                new_private_subnets.extend( retval_new_private_subnets )
                new_private_subnet_ids.extend( retval_new_private_subnet_ids )
                list_of_azs.extend( retval_list_of_azs )
                subnet_lkp |= retval_subnet_lkp
                subnet_per_az_lkp |= retval_subnet_per_az_lkp


            # ### ATTENTION !!  --NO-- longer need to do this ---> Create Route-Tables to connect these subnets
            # for subnet_name in subnet_name_list:
            #     print( f"Adding RouteTable-Entries for subnet '{subnet_name}' ")
            #     for subnet_details in vpc_details_for_tier[subnet_name]:
            #         az = subnet_details["az"];
            #         # subnet_cidr_block = subnet_details["subnet-cidr"];
            #         subnet_id = subnet_name +'-'+ az

            #         subnet = subnet_lkp[ subnet_id ]
            #         subnet_id = subnet.subnet_id
            #         for other_subnet_name in subnet_lkp.keys():
            #             print( f"\tTBD: whether a new RouteTableEntry for {subnet_id} <--> {other_subnet_name}")
            #             other_subnet = subnet_lkp[ other_subnet_name ]
            #             other_subnet_id = other_subnet.subnet_id
            #             # if other_subnet_name == (subnet_id):
            #             if subnet_id == other_subnet_id:
            #                 print( f"\t\t ..Skipping creating a 'self' RouteTableEntry for {subnet_name}")
            #                 continue ### Skip adding a route to itself
            #             ### Create route using the network interface of the other subnet
            #             aws_ec2.CfnRoute( scope=scope, id = subnet_id +'-'+ other_subnet_name +'-rtb-route',
            #                 route_table_id = subnet.route_table.route_table_id,
            #                 destination_cidr_block = other_subnet.ipv4_cidr_block,
            #                 network_interface_id   = other_subnet.node.default_child.ref  # Use subnet's network interface as target
            #             )

        return [ new_private_subnets, new_private_subnet_ids,  subnet_lkp,  list_of_azs,    subnet_per_az_lkp ]


    @staticmethod
    def create_raw_subnet(
        scope :Construct,
        aws_env :str,
        tier_in_awsenv :str,
        vpc_id :str,
        route_table_id :str,
        subnet_name :str,
        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]],
        tags :list[dict[str,str]],
        tagsCfn :list[CfnTag],
    ) -> tuple[ list[aws_ec2.CfnSubnet], list[str],   dict[str,aws_ec2.CfnSubnet],   list[str],   dict[str,list[aws_ec2.CfnSubnet]]  ]:
        """
            NOTE: This method uses `aws_ec2.CfnSubnet` lowest-level Construct (almost same as CloudFormation)

            params:
                2. aws_env :str
                3. vpc_id :str
                4. acct_wide_vpc_details :json-snippet from cdk.json
                5. tags :dict[str,str]
                6. tagsCfn :list[aws_ec2.CfnTag]
            Returns the following as a tuple:
                1. new_private_subnets :list[aws_ec2.CfnSubnet]
                2. new_private_subnet_ids :list[str]
                3. subnet_lkp :dict[str,aws_ec2.CfnSubnet] ---  subnet-name -to-> construct
                4. list_of_azs :list[str]
                5. subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] --- AZ-name -to-> construct
        """
        print( f"creating a new PRIVATE-Noooo-EGRESS subnet '{subnet_name}' ..")

        new_private_subnets :list[aws_ec2.CfnSubnet] = []
        new_private_subnet_ids :list[str] = []
        subnet_lkp :dict[str,aws_ec2.CfnSubnet] = {}   ### subnet-name -to-> construct
        list_of_azs :list[str] = []
        subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] = {}   ### AZ-name -to-> construct

        subnet_details :dict[str,str];
        # for subnet_details in vpc_details_for_tier[subnet_name]:
        for subnet_details in vpc_details_for_tier["subnets"]:
            az = subnet_details["az"];
            subnet_cidr_block = subnet_details["subnet-cidr"];
            list_of_azs.append( az )

            if "subnet-id" in subnet_details:
                subnet_id = subnet_details["subnet-id"]
                if subnet_id.strip(' \t?!-_*#%.') == "":
                    subnet_id = subnet_name +'-'+ az
                    ### Fall thru and continue with subnet-creation.
                else:
                    print( f"Subnet-id {subnet_id} was specified. Assuming it already exists!  Will move on." )
                    continue ### onto NEXT `subnet_details`.

            subnet_tagsCfn :list[CfnTag] = []
            for tag in tags:
                subnet_tagsCfn.append(CfnTag( key = tag["Key"], value = tag["Value"] ))
            subnet_tagsCfn.append(CfnTag(key = "Name", value = subnet_id)) ### Name the subnet!
            new_subnet = aws_ec2.CfnSubnet( scope=scope,
                id = subnet_id,
                vpc_id = vpc_id,
                availability_zone = az,
                cidr_block = subnet_cidr_block,
                map_public_ip_on_launch = False,
                # private_dns_name_options_on_launch = Any,  affects EC2-instances only
                tags = subnet_tagsCfn,
            )
            ### associate this RouteTable with the subnet
            aws_ec2.CfnSubnetRouteTableAssociation( scope=scope, id = subnet_id +'-rtb-assoc',
                route_table_id = route_table_id,
                subnet_id = new_subnet.attr_subnet_id,
            )
            new_private_subnet_ids.append( new_subnet.attr_subnet_id )
            new_private_subnets.append( new_subnet )
            subnet_lkp[ subnet_id ] = new_subnet
            if az not in subnet_per_az_lkp:
                subnet_per_az_lkp[ az ] = [new_subnet]
            else:
                subnet_per_az_lkp[ az ].append( new_subnet )


            # parameter_name = Fn.join('/', ['/', cdk_app_name.value_as_string, aws_env, t i e r, 'private-subnet-'+str(count)] )
            # parameter_name = f'/{aws_env}/{tier_in_awsenv}/private-subnet-'+str(count)
            parameter_name = f'/{aws_env}/{tier_in_awsenv}/private-subnet/{subnet_name}/{az}'
            param1 = aws_ssm.StringParameter( scope=scope, id=parameter_name,
                string_value = new_subnet.attr_subnet_id,
                parameter_name = parameter_name,
                simple_name = False  # Because we're using '/' in the parameter name
            )
            param1.apply_removal_policy( RemovalPolicy.DESTROY )
            # count += 1

        return [ new_private_subnets, new_private_subnet_ids,  subnet_lkp,  list_of_azs,    subnet_per_az_lkp ]

    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    def create_new_Level2VpcConstruct(self,
        scope :Construct,
        tier :str,
        aws_env :str,
        git_branch :str,
        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]],
        vpc_name :str,
        cdk_app_name :CfnParameter,
        # subnet_selection :aws_ec2.SubnetSelection,
        tagsCfn :list[CfnTag]
    ) -> tuple[ aws_ec2.Vpc, list[aws_ec2.CfnSubnet], list[str], dict[str,aws_ec2.CfnSubnet], dict[str,list[aws_ec2.CfnSubnet]]  ]:
        """
            Returns the following as a tuple:
                1. new aws_ec2.Vpc construct-instance <------------ Note !!!!
                2. new_private_subnets :list[aws_ec2.CfnSubnet]
                3. new_private_subnet_ids :list[str]
                4. subnet_lkp :dict[str,aws_ec2.CfnSubnet] ### subnet-name -to-> construct
                5. subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]]  ### AZ-name -to-> construct
        """

        ### NIST 800-53 finding -- VPC Flow Logs are mandatory, else HIGH-finding
        flowlogs_name = Fn.join("-", [cdk_app_name.value_as_string, tier, "VPC"])
        flow_logs = {
            tier: aws_ec2.FlowLogOptions(
                destination=aws_ec2.FlowLogDestination.to_cloud_watch_logs(
                    log_group=aws_logs.LogGroup( scope = scope, id="VPCFlowLogs",
                        log_group_name = f"/aws/VPC/{flowlogs_name}/FlowLogs",
                        #### !! Warning !! if you set retention to RETAIN_ON_DELETE, remember to REMOVE the name of log-grp above!!!
                        removal_policy=RemovalPolicy.DESTROY, ### Landing Zone for Prod also should be provided and NOT created by App.
                        log_group_class = aws_logs.LogGroupClass.STANDARD,
                        retention=aws_logs.RetentionDays.SEVEN_YEARS,
                    )
                    ## ,iam_role = .. automatically generated by CDK
                ),
                log_format=[aws_ec2.LogFormat.ALL_DEFAULT_FIELDS],
                max_aggregation_interval=aws_ec2.FlowLogMaxAggregationInterval.TEN_MINUTES,
                traffic_type=aws_ec2.FlowLogTrafficType.ALL,
            )
        }

        ### The "standard" CDK-Construct for VPC requires a PUBLIC-Subnet !!!
        subnet_configuration = [
            ### Add a PUBLIC subnet to get started.
            aws_ec2.SubnetConfiguration(
                name="public",
                # name=aws_names.get_subnet_name( tier, "public"),
                cidr_mask = 19, ### When this is used to create 2 subnets (per max_azs=2 below) =implies= /27
                reserved = False,
                subnet_type = aws_ec2.SubnetType.PUBLIC,
            ### !!!!!!!!!!!!!!!!!!!!!!!!!!!! ATTENTION !!!!!!!!!!!!!!!!!!!!!!!!!!!!
            ### RuntimeError: If you configure PRIVATE subnets in `subnetConfiguration`, you must also configure PUBLIC subnets
            ###          to put the NAT gateways into
            ### !!!!!!!!!!!!!!!!!!!!!!!!!!!! ATTENTION !!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # ipv6_assign_address_on_creation = False, ### This line causes ERROR: RuntimeError: ipv6AssignAddressOnCreation can only be set if IPv6 is enabled. Set ipProtocol to DUAL_STACK
                map_public_ip_on_launch = False,
            ),
            # aws_ec2.SubnetConfiguration(
            #     name="DB",
            #     cidr_mask=24,
            #     reserved=False,
            #     subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
            # ),
        ]

        vpcL2Construct = aws_ec2.Vpc( scope=scope, id="VPC",
            vpc_name=vpc_name,
            ip_addresses=aws_ec2.IpAddresses.cidr( "192.168.0.0/24" ),
            # ip_addresses=aws_ec2.IpAddresses.cidr( vpc_cidr_block ), ### Since this will create a Public-Subnet automatically, we will -NOT- use this CIDR.
            # cidr=_block,  ### Deprecated. Use ip_addresses as shown below.
            flow_logs = flow_logs,
            max_azs = 2,
            nat_gateways = 0,  ### <-------- No NAT-Gateway !
            subnet_configuration = subnet_configuration, ### If None, then Construct will do its own unknown thing -- like creating a Public Subnet!
            restrict_default_security_group = True,
            create_internet_gateway = False,
            enable_dns_hostnames = True,
            enable_dns_support = True,
            ip_protocol = aws_ec2.IpProtocol.IPV4_ONLY,
            # gateway_endpoints = .. ### see this taken care of below.
        )

        vpc_id = vpcL2Construct.vpc_id
        vpcL2Construct.apply_removal_policy( RemovalPolicy.DESTROY )

            ### ------------------------------------------------------
            ### Whether or not VPC -already- exists .. do the following
            ### ------------------------------------------------------
            ### 1. (NOT Working) add a new CIDR block to the VPC --> instead, create a new vpc using this CIDR.
            ### 2. create NEW Private Subnets with NO-EGRESS whatsoever.
            ### 3. Create Route-Tables to connect these subnets
            ### 4. Finally create all the VPCEndPoints.
            ### ------------------------------------------------------

            # aws_ec2.CfnVPCCidrBlock( scope=scope, id="AdditionalCIDR"+vpc_cidr_block,
            #     vpc_id = vpc_id,
            #     cidr_block = vpc_cidr_block,
            # )
            ### Error: CREATE_FAILED vpconlyAdditionalCIDR1000016BF33E643
            ### Resource handler returned message: "The CIDR '10.0.0.0/16' is restricted. Use a CIDR from the same private address range as the current VPC CIDR, or use a publicly-routable CIDR.
            ### FYI only. ROOT CAUSE: The original-VPC's original-CIDR block was already RFC 1918 private range ( 192.168.0.0/16).
            ###             Per Amazon-Q, can -NOT- add a 2nd VPC-CIDR that is -ALSO- RFC 1918 private range ( 10.0.0.0/16),
            ### ATTENTION: When I tried the above --MANUALLY-- via VPC-Console, I got the EXACT-SAME error-message!!!

        return None

    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    def create_L2Subnets(self,
        scope :Construct,
        tier :str,
        aws_env :str,
        vpc_id :str,
        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]],
    ) -> tuple[ list[aws_ec2.CfnSubnet],   list[str],   dict[str,aws_ec2.CfnSubnet],   list[str],   dict[str,list[aws_ec2.CfnSubnet]]  ]:
        """
            ATTENTION ! Instead of aws_ec2.CfnSubnet, this uses aws_ec2.Subnet() construct, which is QUITE OPIONATED !!!
            ATTENTION ! aws_ec2.Subnet() is QUITE OPIONATED !!!
                        Each Subnet will get its own Route-Table!!

            params:
                1. tier :str
                2. aws_env :str
                3. vpc_id :str
                4. acct_wide_vpc_details representing JSON-snippet from cdk.json
            Returns the following as a tuple:
                1. new_private_subnets :list[aws_ec2.CfnSubnet]
                2. new_private_subnet_ids :list[str]
                3. subnet_lkp :dict[str,aws_ec2.CfnSubnet] --- subnet-name -to-> construct
                4. list_of_azs :list[str]
                5. subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] --- AZ-name -to-> construct
        """

        vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
        if vpc_details_for_tier and tier in acct_wide_vpc_details:
            vpc_details_for_tier = acct_wide_vpc_details[tier]
        else:
            vpc_details_for_tier = acct_wide_vpc_details

        new_private_subnets :list[aws_ec2.CfnSubnet] = []
        new_private_subnet_ids :list[str] = []
        subnet_lkp :dict[str,aws_ec2.CfnSubnet] = {}   ### subnet-name -to-> construct
        list_of_azs :list[str] = []
        subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] = {}   ### AZ-name -to-> construct

        subnet_name_list = constants_cdk.SUBNET_NAMES_LOOKUP[ aws_env ]
        # if subnet_name_list is of type "list[str]", do nothing else, but if it is of type "dict[str,list[str]]", the subnet_name_list = subnet_name_list[tier], else .. raise exception
        if not isinstance(subnet_name_list, list):
            if isinstance(subnet_name_list, dict) and tier in subnet_name_list:
                subnet_name_list = subnet_name_list[tier]
            else:
                raise Exception(f"`constants_cdk.SUBNET_NAMES_LOOKUP` is of UNKNOWN type {type(subnet_name_list)}, but it should be of type list[str] or dict[str,list[str]]")

        for subnet_name in subnet_name_list:
            print( f"creating a new PRIVATE-Noooo-EGRESS subnet '{subnet_name}' ..")
            subnet_details :dict[str,str];
            for subnet_details in vpc_details_for_tier[subnet_name]:
                az = subnet_details["az"];
                subnet_cidr_block = subnet_details["subnet-cidr"];
                subnet_id = subnet_name +'-'+ az
                list_of_azs.append( az )
                ### We do --NOT-- want to use `aws_ec2.Subnet` since it will create a UNIQUE RouteTable automatically.
                new_subnet = aws_ec2.Subnet( scope=scope,
                    id = subnet_id,
                    vpc_id = vpc_id,
                    availability_zone = az,
                    cidr_block = subnet_cidr_block,
                    # assign_ipv6_address_on_creation = False,  ### This line causes ERROR: RuntimeError: ipv6AssignAddressOnCreation can only be set if IPv6 is enabled. Set ipProtocol to DUAL_STACK
                    map_public_ip_on_launch = False,
                )
                new_private_subnet_ids.append( new_subnet.subnet_id )
                new_private_subnets.append( new_subnet )
                subnet_lkp[ subnet_id ] = new_subnet
                if az not in subnet_per_az_lkp:
                    subnet_per_az_lkp[ az ] = [new_subnet]
                else:
                    subnet_per_az_lkp[ az ].append( new_subnet )

        count = 1
        for psubid in new_private_subnet_ids:
            # parameter_name = Fn.join('/', ['/', cdk_app_name.value_as_string, aws_env, tier, 'private-subnet-'+str(count)] )
            parameter_name = f'/{aws_env}/{tier}/private-subnet-'+str(count)
            param1 = aws_ssm.StringParameter(scope=scope, id='private-subnet-'+ str(count),
                string_value = psubid,
                parameter_name = parameter_name,
                simple_name = False  # Because we're using '/' in the parameter name
            )
            param1.apply_removal_policy( RemovalPolicy.DESTROY )
            count += 1

        return [ new_private_subnets, new_private_subnet_ids, subnet_lkp,  list_of_azs,   subnet_per_az_lkp ]


### EoF
