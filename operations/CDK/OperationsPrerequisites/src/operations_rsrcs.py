import json
import sys
from aws_cdk import (
    Stack,
    aws_kms,
    aws_iam,
    aws_sns,
    aws_sns_subscriptions,
)
from constructs import Construct

import constants
from common.cdk.StandardSNSTopic import StandardSNSTopic

class OperationsResources(Construct):

    def __init__(self,
        scope: Construct,
        construct_id: str,
        aws_env :str,
        **kwargs
    ) -> None:
        super().__init__(
            scope = scope,
            id = construct_id,
            **kwargs
        )
        SNSTopicName = "Operations"
        construct_id = "SNSTopic-Operations"
        constr = StandardSNSTopic( self,
            construct_id = construct_id,
            tier = aws_env, ### <------
            full_topic_name = SNSTopicName,  ### Explicitly name the SNS-Topic
            display_name = f"{aws_env} - {constants.CDK_APP_NAME} - common/shared SNS-Topic for ALL TIERS",
            # display_name = "Unique-per-AWS-Acct - A common/shared Topic for ALL TIERS of this application",
        )
        self.operations_topic = constr.topic

        # SNSTopicName=f"{constants.CDK_APP_NAME}-Ops"
        # SNSTopicName=f"{constants.CDK_APP_NAME}-{tier}"

        supportTeamEmails :list[str] = None;
        # If "constants.DefaultITSupportEmailAddress" is already a list, set supportTeamEmails to it as is.
        if type(constants.DefaultITSupportEmailAddress).__name__ == "list":
            supportTeamEmails = constants.DefaultITSupportEmailAddress
        else:
            supportTeamEmails = [ constants.DefaultITSupportEmailAddress ]

        # supportTeamEmailsJson = self.node.try_get_context("support-email")
        # print( json.dumps(supportTeamEmailsJson, indent=4) )
        # supportTeamEmails :list[str] = None

        # if supportTeamEmailsJson is None:
        #     supportTeamEmails = []
        # else:
        #     if tier in supportTeamEmailsJson:
        #         supportTeamEmails = supportTeamEmailsJson[tier]
        #     elif tier not in constants.STD_TIERS:
        #         supportTeamEmails = supportTeamEmailsJson["dev"]
        #     else:
        #         supportTeamEmails = supportTeamEmailsJson["prod"]

        ### Sanity-checks
        print( json.dumps(supportTeamEmails, indent=4) )
        if not supportTeamEmails or len(supportTeamEmails) <= 0:
            print( f"ERROR:❌❌❌ INVALID value for support-emails!! within "+ __file__ )
            sys.exit(1)
        if type(supportTeamEmails).__name__ != "list" or supportTeamEmails[0].strip(' \t?!-_*#%.') == "":
            print( f"ERROR:❌❌❌ 'supportTeamEmails' should be a proper-list!! within "+ __file__ )
            # print( f"ERROR:❌❌❌ 'supportTeamEmails' should be a proper-list within cdk.json. Found '{type(supportTeamEmailsJson).__name__}'" )
            sys.exit(1)

        ### Add SNS-Subscription(s) to the topic created above
        for an_email in supportTeamEmails:
            self.operations_topic.add_subscription(
                aws_sns_subscriptions.EmailSubscription(
                    email_address = an_email,
                    json = True,
                ))
