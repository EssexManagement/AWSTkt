#!/bin/bash

### Use this script to download CWLogs -- for "Infrequent-Access" Log-Class (that saves money)
### For "Infrequent Access" logs-class, there is ONLY ONE way to get the logs!!!

### Warning: The START and END timestamps must be NEWER than the creation-time of the LogStream!!!!
### Warning: The START and END timestamps must be in UTC (not local time)

if [ $# -lt 3 ]; then
    echo "Usage: $0  AWSPROFILE  TIER   CWLogsGroupName"
    echo "Example: $0  DEVINT  int   '/aws/codebuild/FACT-backend-pipeline-uat-FACT-backend-uat_Appln_CDKSynthDeploy'"
    exit 1
fi

###---------------------------------------------------------------

AWSPROFILE="$1"
TIER="$2";
LOG_GROUP_NAME="$3"
# LOG_GROUP_NAME="/aws/codebuild/FACT-backend-pipeline-uat-FACT-backend-uat_Appln_CDKSynthDeploy"

### ===============================================================================

AWSREGION="us-east-1"

# S3BKT="nih-nci-fact-backend-uat-session-results"

### ===============================================================================

### start-time should be current-timezone (so that, when working late beyond 7pm ET, we avoid the problem that UTC is already in "tomorrow").
### end-time should be in UTC (per best practices)
START_TIMESTAMP="$( date +'%Y-%m-%d' ) 00:00:00"
END_TIMESTAMP=$( date -u +'%Y-%m-%d %H:%M:%S' )
echo "START_TIMESTAMP='${START_TIMESTAMP}' and END_TIMESTAMP='${END_TIMESTAMP}'"

# NOW=$( date  +'%Y-%m-%dT%H:%M:%SZ' )
# echo "NOW='${NOW}'"

#__ START_TIMESTAMP=$( date -u -d "${START_TIMESTAMP}" +%s000 ) ### Linux only
START_TIMESTAMP=$( date -j -u -f "%Y-%m-%d %H:%M:%S" "${START_TIMESTAMP}" "+%s000" ) ### MacOS only
echo "START_TIMESTAMP='${START_TIMESTAMP}'"

#__ END_TIMESTAMP=$( date -u -d "${END_TIMESTAMP}" +%s000 ) ### Linux only
END_TIMESTAMP=$( date -j -u -f "%Y-%m-%d %H:%M:%S" "${END_TIMESTAMP}" "+%s000" ) ### MacOS only
echo "END_TIMESTAMP='${END_TIMESTAMP}'"

# echo "S3BKT='${S3BKT}'"

LOCALFILEPATH="/tmp/logstream.txt"

### ===============================================================================

SCRIPT_FOLDER=$(dirname -- "$0")
SCRIPT_NAME=$(basename  -- "$0")
CWD="$(pwd)"

###---------------------------------------------------------------

.  ${SCRIPT_FOLDER}/common-settings.sh

### ===============================================================================

### Get the log streamS nameS
# STREAM_NAME=$(aws logs describe-log-streams \
#     --log-group-name "$LOG_GROUP_NAME" \
#     --max-items 1 \
#     --query 'logStreams[0].logStreamName' \
#     --output text \
#     --profile ${AWSPROFILE} --region ${AWSREGION}
# )

### Following cmd --ONLY-- works for REGULAR/STANDARD Log-Class !!
# aws logs create-export-task \
#     --log-group-name "${LOG_GROUP_NAME}" \
#     --from "${START_TIMESTAMP}" \
#     --to   "${END_TIMESTAMP}" \
#     --destination "${S3BKT}" \
#     --destination-prefix "CWLogs-exports_${NOW}"

set -e

set -x
### Start a query in CW-Logs
CWLogsQueryId=$(
    aws logs start-query \
        --log-group-name "${LOG_GROUP_NAME}" \
        --start-time "${START_TIMESTAMP}" \
        --end-time "${END_TIMESTAMP}" \
        --query-string "fields @timestamp, @message | sort @timestamp asc" |
    jq .queryId --raw-output
)
set +x
echo "CWLogsQueryId='${CWLogsQueryId}'"

### Get results using the query ID from above command
set -x
aws logs get-query-results --query-id "${CWLogsQueryId}" > "${TMPFILE11}"
set +x

### Pure JSON - but compact.
# jq '.results.[] | { "Dt": .[0].value, "Msg": .[1].value }' "${TMPFILE11}"

### raw text
# jq '.results.[] |  { "line": "\(.[0].value): \(.[1].value)" } | .line ' --raw-output  "${TMPFILE11}"
echo \
jq '.results | .[] | [ .[0].value, .[1].value ] | @tsv ' --raw-output  "${TMPFILE11}"
jq '.results | .[] | [ .[0].value, .[1].value ] | @tsv ' --raw-output  "${TMPFILE11}" > "${LOCALFILEPATH}"
ls -la "${LOCALFILEPATH}"

### TBC -- In CloudWatch-Logs, -NO- need to manually clean up or destroy queryIds.
### TBC -- Query results are automatically cleaned up by AWS after 7 days.

### ===============================================================================

### EoScript
