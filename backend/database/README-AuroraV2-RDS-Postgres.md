# Aurora-V2 Postgres database INITIALIZATION


<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

## Create the new Application-user

1. Go to Secrets-manager Console.
1. locate the secret named `{CDK_APP_NAME}-backend-{TIER}-Stateful/emfact_user`
1. Access the raw-secret-values.
    1. Confirm the `username` == `emfact_user`
    1. Confirm the `dbname` == `essex_emfact`
    1. Confirm the `engine` == `potgres`
1. Note down the password !!!!!!!!!   You will need it below.
1. Edit the pssword in the SQL below &  .. .. run it.
1. 👉🏾👉🏾 Look CAREFULLY in the QUery-Editor's console to confirm that .. .. SQL ran SUCCESSFULLY !!

```sql
CREATE USER emfact_user WITH PASSWORD '????????????????????????';
```

Finally, give the user all the privileges to the database!

```sql
-- Grant basic connect permission
GRANT CONNECT ON DATABASE essex_emfact TO emfact_user;

-- First, grant create privilege on the schema
GRANT CREATE ON SCHEMA public TO emfact_user;

-- Grant all necessary privileges
GRANT ALL PRIVILEGES ON DATABASE essex_emfact TO emfact_user;

-- Grant schema usage and create
GRANT USAGE, CREATE ON SCHEMA public TO emfact_user;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO emfact_user;

-- For future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO emfact_user;

-- If you need sequence permissions (for auto-incrementing IDs)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO emfact_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO emfact_user;
```

## Change password for Application-user

FYI: In case, the user ALREADY exists .. ..

```sql
ALTER USER emfact_user WITH PASSWORD '????????????????????????';
```

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

## APPENDIX - CDK How-To to automate the above SQL

```python
# Create a script to set up the user and permissions
init_script = f"""
DO $$
BEGIN
    CREATE USER {emfact_user} WITH PASSWORD :'{password}';
    GRANT .. ..
    .. .. ON SEQUENCES TO {emfact_user};
END $$;
"""

self.db = rds.DatabaseCluster( self, id="AuroraV2-PGSQL",
    # ... your existing configuration ...
    instance_props=rds.InstanceProps(
        # ... your existing instance props ...
        initialization_script=rds.InitializationScript.from_string(init_script)
    ),
```

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

## APPENDIX - List all users in the database

```sql
SELECT
    current_user as current_login,
    session_user as session_login,
    current_database() as database_name;
```

/EoF
