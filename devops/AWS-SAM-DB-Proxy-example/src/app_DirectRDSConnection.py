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
        # Using Powertools parameters utility
        secret_value = parameters.get_secret(secret_arn)

        # Handle the case where the secret is returned as a JSON string
        if isinstance(secret_value, str):
            return json.loads(secret_value)
        return secret_value

    except Exception as e:
        logger.error(f"Failed to retrieve secret: {str(e)}")
        raise

### ........................................................................

@tracer.capture_method
def execute_sql_commands(conn, commands: list) -> None:
    """Execute SQL commands and handle transactions properly"""
    try:
        # psycopg3 uses with blocks for both connection and cursor
        with conn.cursor() as cur:
            for command in commands:
                logger.debug(f"Executing SQL command: {command[:50]}...")  # Log only first 50 chars for security
                cur.execute(command)
            conn.commit()
            metrics.add_metric(name="SuccessfulSQLCommands", unit="Count", value=len(commands))
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        metrics.add_metric(name="FailedSQLCommands", unit="Count", value=1)
        raise

### ........................................................................

# Enrich logging with contextual information from Lambda
@logger.inject_lambda_context(
    log_event = True,
    correlation_id_path = correlation_paths.API_GATEWAY_REST
)
# Adding tracer
# See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/tracer/
# ensures metrics are flushed upon request completion/failure and capturing ColdStart metric
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    # Get secret ARNs from environment variables
    admin_secret_arn = os.environ.get('DBA')
    user_secret_arn = os.environ.get('DBU')

    if not admin_secret_arn or not user_secret_arn:
        logger.error("Missing required environment variables")
        raise ValueError("Required environment variables DBA and/or DBU are not set")

    try:
        # Get secrets
        logger.info("Retrieving secrets")
        admin_creds = get_secret(admin_secret_arn)
        user_creds = get_secret(user_secret_arn)

        # Extract the new user's password
        new_user_password = user_creds.get('password')
        if not new_user_password:
            raise ValueError("Password not found in user credentials secret")

        # define the SQL commands
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

        logger.info("Connecting to database")
        # psycopg3 connection string format
        conn = psycopg.connect(
            host=admin_creds['host'],
            dbname=admin_creds['dbname'],
            user=admin_creds['username'],
            password=admin_creds['password'],
            port=admin_creds['port']
        )

        logger.info("Executing SQL commands")
        execute_sql_commands(conn, sql_commands)

        return {
            'statusCode': 200,
            'body': json.dumps('User creation and permission grants completed successfully')
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
