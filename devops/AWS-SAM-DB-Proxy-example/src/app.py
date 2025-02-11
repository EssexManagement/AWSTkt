import json
import os
import boto3
import psycopg
from botocore.exceptions import ClientError

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities import parameters

# Initialize Powertools
app = APIGatewayRestResolver()
tracer = Tracer()
logger = Logger()
metrics = Metrics(namespace="DatabaseUserMmgmt")

### ........................................................................

def get_secret(secret_arn: str) -> dict:
    """Retrieve and return secret from AWS Secrets Manager"""
    try:
        secret_value = parameters.get_secret(secret_arn)
        if isinstance(secret_value, str):
            return json.loads(secret_value)
        return secret_value
    except Exception as e:
        logger.error(f"Failed to retrieve secret: {str(e)}")
        raise

def get_proxy_endpoint() -> str:
    """Get the RDS Proxy endpoint from its ARN"""
    try:
        rds_client = boto3.client('rds')
        proxy_arn = os.environ.get('DBP')
        logger.info(f"Proxy ARN: {proxy_arn}")
        proxy_name  = os.environ.get('DBPName')
        logger.info(f"Proxy proper-name: {proxy_name}")
        if not proxy_name:
            raise ValueError("RDS Proxy's NAME not found in environment variables")

        response = rds_client.describe_db_proxies(
            DBProxyName = proxy_name
        )
        logger.info(f"RDS Proxy response: {response}")

        if not response['DBProxies']:
            raise ValueError(f"No proxy found with name: {proxy_name}")

        logger.info(f"Security Groups configured: {response['DBProxies'][0]['VpcSecurityGroupIds']}")
        logger.info(f"VPC Subnets configured: {response['DBProxies'][0]['VpcSubnetIds']}")
        return response['DBProxies'][0]['Endpoint']

    except Exception as e:
        logger.error(f"Failed to get proxy endpoint: {str(e)}")
        raise

### ........................................................................

### ........................................................................

@tracer.capture_method
def execute_sql_commands(conn, commands: list) -> None:
    """Execute SQL commands and handle transactions properly"""
    try:
        with conn.cursor() as cur:
            for command in commands:
                logger.info(f"Executing SQL command: {command[:50]}...")  # Log only first 50 chars for security
                cur.execute(command)
            conn.commit()
            metrics.add_metric(name="SuccessfulSQLCommands", unit="Count", value=len(commands))
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        metrics.add_metric(name="FailedSQLCommands", unit="Count", value=1)
        raise

### ........................................................................

@logger.inject_lambda_context(
    log_event = True,
    correlation_id_path = correlation_paths.API_GATEWAY_REST
)

### ........................................................................


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    admin_secret_arn = os.environ.get('DBA')
    user_secret_arn = os.environ.get('DBU')

    if not admin_secret_arn or not user_secret_arn:
        logger.error("Missing required environment variables")
        raise ValueError("Required environment variables DBA and/or DBU are not set")

    try:
        ### Get secrets and proxy endpoint
        logger.info("Retrieving secrets and proxy endpoint")
        admin_creds = get_secret(admin_secret_arn)
        user_creds = get_secret(user_secret_arn)
        proxy_endpoint = get_proxy_endpoint()

        ### Extract the new user's password
        new_user_password = user_creds.get('password')
        if not new_user_password:
            raise ValueError("Password not found in user credentials secret")

        ### define the SQL commands
        check_and_modify_user_sql = f"""
DO $$
BEGIN
    IF EXISTS ( SELECT FROM pg_catalog.pg_user WHERE usename = 'emfact_user' ) THEN
        ALTER USER emfact_user WITH PASSWORD '{new_user_password}';
    ELSE
        CREATE USER emfact_user WITH PASSWORD '{new_user_password}';
    END IF;
END
$$;
"""
        sql_commands = [
            check_and_modify_user_sql,
            "GRANT CONNECT ON DATABASE essex_emfact TO emfact_user",
            "GRANT CREATE ON SCHEMA public TO emfact_user",
            "GRANT ALL PRIVILEGES ON DATABASE essex_emfact TO emfact_user",
            "GRANT USAGE, CREATE ON SCHEMA public TO emfact_user",
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO emfact_user",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO emfact_user",
            "GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO emfact_user",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO emfact_user"
        ]

        logger.info("Connecting to database via RDS Proxy")
        logger.info(f"Connection parameters: host={proxy_endpoint}, "
            f"dbname={admin_creds['dbname']}, "
            f"port={admin_creds.get('port', 5432)}")
        region = os.environ.get('AWS_REGION', 'us-east-1')
        rds_client = boto3.client('rds')
        auth_token = rds_client.generate_db_auth_token(
            DBHostname=proxy_endpoint,
            Port = admin_creds.get('port', 5432),
            DBUsername = admin_creds['username'],
            Region = region,
        )

        logger.info("Connecting to database via RDS Proxy with IAM authentication")
        ### Connect via RDS Proxy
        ### SAMPLE: https://docs.aws.amazon.com/lambda/latest/dg/services-rds.html#rds-connection
        conn = psycopg.connect(
            host=proxy_endpoint,
            dbname=admin_creds['dbname'],
            user=admin_creds['username'],
            password=auth_token, ### <---- use the output of get_db_auth_token()
            port=admin_creds.get('port', 5432),
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=10,
            keepalives_interval=10,
            keepalives_count=5,
            sslmode='require' ### enforce SSL/TLSv1.2
        )

        logger.info("Executing SQL commands")
        execute_sql_commands(conn, sql_commands)

        return {
            'statusCode': 200,
            'body': json.dumps('User creation and permission grants completed successfully')
        }

    except psycopg.OperationalError as e:
        logger.error(f"Connection error details: {str(e)}")
        # Add more specific error handling
        if "timeout expired" in str(e):
            logger.error("Connection timeout - checking network connectivity")
            # You could add additional diagnostic code here
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

    except Exception as e:
        logger.exception("Error in lambda execution")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
            logger.info("Database connection closed")
