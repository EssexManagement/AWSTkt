import threading
from typing import Optional
import json

from aws_cdk import (
    Stack,
    CfnMapping,
    aws_kinesis,
    aws_logs_destinations,
)
from constructs import Construct

import constants

### ========================================================================================================

lock = threading.Lock()
SINGLETON_STORE = dict()

class createCftMapping(object):
    def __new__(cls, *args, **kwargs ):
        lock.acquire()
        try:
            if not 'myUniqueCftMapping' in SINGLETON_STORE:
                SINGLETON_STORE['myUniqueCftMapping'] = super(createCftMapping, cls).__new__(cls)
            return SINGLETON_STORE['myUniqueCftMapping']
        finally:
            lock.release()

    def __init__(self, scope: Construct, tier :str, aws_env :str ):
        if not hasattr(self, 'init_already_invoked'):
            datadogstreams_by_aws_acct = {
                "CTF": { ### AWS-Account-wide configuration.  --NOT-- tier-specific configuration.
                    "acct-nonprod": None,
                    "acct-prod":    None,
                    # "acct-nonprod": "stream/DatadogLambdaLogStream",     ### arn:aws:kinesis:us-east-1:123456789012:stream/DatadogLambdaLogStream
                    # "acct-prod":    "stream/DatadogLambdaLogStream",     ### arn:aws:kinesis:us-east-1:123456789012:stream/DatadogLambdaLogStream
                },
                "FACT": { ### AWS-Account-wide configuration.  --NOT-- tier-specific configuration.
                    "devint": "stream/DatadogLambdaLogStream",          ### arn:aws:kinesis:us-east-1:123456789012:stream/DatadogLambdaLogStream
                    "uat":    "stream/DatadogLogsStream",               ### arn:aws:kinesis:us-east-1:123456789012:stream/DatadogLambdaLogStream
                    "prod":   "stream/DatadogLogsStream",
                },
            }
            try:
                lock.acquire()
                lkp = datadogstreams_by_aws_acct[constants.CDK_APP_NAME]
                mapping={
                    "dev":  {
                        "FACT": lkp["devint"] if "devint" in lkp else None,
                        "CTF": lkp["acct-nonprod"] if "acct-nonprod" in lkp else None,
                    },
                    "test":  {
                        "CTF": lkp["acct-nonprod"] if "acct-nonprod" in lkp else None,
                    },
                    "int":  {
                        "FACT": lkp["devint"] if "devint" in lkp else None,
                    },
                    "stage":  {
                        "CTF": lkp["acct-prod"] if "acct-prod" in lkp else None,
                    },
                    "uat":  {
                        "FACT": lkp["uat"] if "uat" in lkp else None,
                    },
                    # "perf": {},
                    "prod": {
                        "CTF": lkp["acct-prod"] if "acct-prod" in lkp else None,
                        "FACT": lkp["prod"] if "prod" in lkp else None,
                    },
                }
                ### Remove empty elements in above JSON.
                tiers2bDeleted = []
                for tier in mapping:
                    j = mapping[tier]
                    newKVs = { k:v for k,v in j.items() if v is not None }
                    mapping[tier] = newKVs
                    # j = mapping[tier] ### after removing empty elements, repeat.
                    if newKVs == {}:
                        tiers2bDeleted.append( tier )
                for tier in tiers2bDeleted:
                    del mapping[tier]
                if mapping == {}:
                    mapping = None
                print(f"mapping = "); print(json.dumps(mapping, indent=2, default=str))

                self.DataDogDestinations = CfnMapping( scope=scope, id="DataDogDestinations",          ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnMapping.html
                    lazy=False, ### TODO Is this a good idea?  As per following output from `cdk synth`:
                            ### [Info at /{CDK_APP_NAME}-backend-pipeline-main/{CDK_APP_NAME}-backend-main/StatelessETL/dailETL/DataDogDestinations]
                            ###             Consider making this CfnMapping a lazy mapping by providing `lazy: true`:
                            ###             either no findInMap was called or every findInMap could be immediately resolved without using Fn::FindInMap
                    mapping = mapping,
                ) if mapping is not None else None

                self.init_already_invoked = "__init__ has been invoked before already!"  ### Make sure this is set LAST, and NO EXCEPTIONS after this line!!!

            finally:
                lock.release()

### ========================================================================================================

""" Not a Construct.  Just a simple UTILITY Class (representing the Mapping-Section of a CloudFormation-template)"""
class Mappings:
    """ Private variable """
    ref2scope :Construct
    stream_cache = {}
    dest_cache = {}

    def __init__(self, scope :Construct, **kwargs) -> None:
        super().__init__(**kwargs)

        self.ref2scope = scope

    ### ========================================================================================================
    """ Use this method (for aws_logs.ILogSubscriptionDestination) !!!
        This will lookup the DataDog's Kinesis Stream (Python Object), for the environment specified via `tier`.
    """
    def get_dd_subscription_dest( self, tier :str, aws_env :str ) -> Optional[aws_logs_destinations.KinesisDestination]:
        stk = Stack.of(self.ref2scope)
        arnstr = self.get_datadog_arn( tier=tier, aws_env=aws_env )
        if arnstr is None:
            return None
        if self.stream_cache.get( arnstr ) is None:
            kinstrm :aws_kinesis.IStream =  aws_kinesis.Stream.from_stream_arn( scope=self.ref2scope, id=stk.stack_name+"-DataDogDestination-"+tier,
                stream_arn=arnstr
            )
            self.stream_cache[ arnstr ] = kinstrm
        else:
            kinstrm = self.stream_cache[ arnstr ]

        if self.dest_cache.get( arnstr ) is None:
            d = aws_logs_destinations.KinesisDestination(                                        ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_logs_destinations/KinesisDestination.html
                stream = kinstrm,
                ### role=  .. .. do NOT specify this, a new Role will be automatically created.
            )
            self.dest_cache[ arnstr ] = d
            return d
        else:
            return self.dest_cache[ arnstr ]

    """ Use this method (for aws_kinesis.Stream) !!!
        This will lookup the DataDog's Kinesis Stream (Python Object), for the environment specified via `tier`.
    """
    def get_dd_stream( self, tier :str, aws_env :str ) -> Optional[aws_kinesis.IStream]:
        stk = Stack.of(self.ref2scope)
        arnstr = self.get_datadog_arn( tier=tier, aws_env=aws_env )
        if arnstr is None:
            return None
        if self.stream_cache.get( arnstr ) is None:
            kinstrm :aws_kinesis.IStream =  aws_kinesis.Stream.from_stream_arn( scope=self.ref2scope, id=stk.stack_name+"-DataDogDestination-"+tier,
                stream_arn=arnstr
            )
            self.stream_cache[ arnstr ] = kinstrm
            return kinstrm
        else:
            return self.stream_cache[ arnstr ]

    """ Use this method (for ARN-string) !!!
        This will generate ARN (to DataDog's Kinesis Stream) for the environment specified via `tier`.
    """
    def get_datadog_arn( self, tier :str, aws_env :str ) -> Optional[str]:
        stk = Stack.of(self.ref2scope)
        return self.get_datadog_arn_for_stack( tier=tier, aws_env=aws_env, stk=stk )


    ### ========================================================================================================
    """ Try to avoid this polymorphism !!!!!!!!!!!!!!!!
        Given a Stack (as last parameter), it will generate ARN for that same region and account-id (for the environment specified via `tier`)
    """
    def get_datadog_arn_for_stack( self, tier :str, aws_env :str, stk :Stack ) -> Optional[str]:
        try:
            DataDogDestinations = createCftMapping( scope=self.ref2scope, tier=tier, aws_env=aws_env ).DataDogDestinations
            effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER
            ddname = DataDogDestinations.find_in_map( effective_tier, constants.CDK_APP_NAME, "NotFound" ) if DataDogDestinations else None
            if ddname is None or ddname == "NotFound":
                return None
            s :str = f"arn:{stk.partition}:kinesis:{stk.region}:{stk.account}:{ddname}"
            print( "DEBUG: arn ='", s, "' -- in get_dd_destination_arn_for_stack() within ", __file__ )
            return s
        except Exception as e:
            # print( e )
            if f"Error: Mapping doesn't contain second-level key '{constants.CDK_APP_NAME}'" == str(e):
                return None
            else:
                raise e

    """ Try to avoid this polymorphism !!!!!!!!!! """
    def get_datadog_arn_elsewhere( self, tier :str, aws_env :str, region :str, account_id: str ) -> Optional[str]:
        try:
            DataDogDestinations = createCftMapping( scope=self.ref2scope, tier=tier, aws_env=aws_env ).DataDogDestinations
            effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER
            ddname = DataDogDestinations.find_in_map( effective_tier, constants.CDK_APP_NAME, "NotFound" ) if DataDogDestinations else None
            if ddname is None or ddname == "NotFound":
                return None
            s :str = f"arn:aws:kinesis:{region}:{account_id}:{ddname}"
            print( "DEBUG: arn ='", s, "' -- in get_dd_destination_arn_elsewhere() within ", __file__ )
            return s
        except Exception as e:
            # print( e )
            if f"Error: Mapping doesn't contain second-level key '{constants.CDK_APP_NAME}'" == str(e):
                return None
            else:
                raise e

### EoF
