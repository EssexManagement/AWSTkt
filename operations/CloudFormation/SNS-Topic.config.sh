#!/bin/false

ArchLayer="Operations"

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

# SNSTopicName="${application}-${TIER}"
# SNSTopicName="${application}-Ops"
SNSTopicName="Operations"

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------
PARAMETERS=(
    ParameterKey="TopicName",ParameterValue="${SNSTopicName}"
    ParameterKey="EmailAddress",ParameterValue="${EMAILADDRESS}"
)

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

StackName="${application}-SNS-Ops"
CFT_FILENAME="SNS-Topic-CFT.yaml"

### EoScript
