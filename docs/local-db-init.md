# Create and Initialize Local Database
Last Revision Date: 9/13/2022
EMFACT_PYTHON_VERSION = 3.11 
 
**Experienced users can skip to the following sections**
* Installing and starting postgres
* Section I : Creating the postgres Database
* Section II Running rds_init and etl from commandline
 
## Introduction
This document is for creating and initializing a local database for emFACT.
This repo includes three distinct projects:
* The API -- all the endpoints. This is not relevant for this document.
* RDS Init -- initializing the database
* ETL -- populating the database with CTS data.


## Prerequisites
* You should have the EMFACT_PYTHON_VERSION of python installed.
* You will need to create python virtual environments for each of the 3 projects.
However, as of this writing, you may decide to create one python virtual environment in the root folder of this repo.
* You will need postgres installed. Insalling postgres is explained below.
* export CTS_API_KEY=<YOUR CTS API KEY>
* If using PyCharm, you will need to set an environment variable for CTS_API_KEY in the IDE


### Important Files
* rds_init/runtime/sql_install_handler.py - the lambda for rds_init
* rds_init/runtime/requirements.txt - the requirements file for rds_init
* etl/runtime/refresh_ncit.py - the lambda for populating ncit tables
* etl/runtime/api_etl.py - the lambda for populating the rest of the tables
* etl/runtime/requirements.txt - the requirements file for etl


## Installing and starting postgres:
1. You can install postgres using brew: <br>
'''
brew install postgresql@14
brew service start postgresql@14
''''

## Section I : Creating the postgres Database

Find psql command on your system using which and if found long list it to make sure it is right.
<br>As in the below output.
```
:which psql
/opt/homebrew/bin/psql

:ls -l /opt/homebrew/bin/psql
lrwxr-xr-x  1 marianom2  admin  40 Jan 26 18:03 /opt/homebrew/bin/psql -> ../Cellar/postgresql@14/14.10_1/bin/psql
```
Otherwise do a find on /Applications for psql. This is the result on my system

/Applications/Postgres.app/Contents/Versions/14/bin/psql

**You must use psql for these steps**

1. Enter the command **psql postgres**


2. You should not be prompted for a password. The default install is passwordless.


3. enter the following in psql
May need to use psql -d postgres
```sh
create database fact;
create user fact with password 'fact';
grant all privileges on database fact to fact;
\connect fact;
```
```sh
create schema fact;
alter user fact set search_path to fact;
grant all privileges on schema fact to fact;
```

4. quit psql:
\quit

## Section II Running rds_init and etl from commandline
**This is the quickest way to get started.**

* Follow Appendix D: Create a Single Virtual Env
* You should now be in a virtual environment with all requirements installed
* Run the following commands:
    1.  export CTS_API_KEY=.. .. YOUR-CTS-API-KEY .. ..
    1.  cd rds_init/runtime
    1.  pip3 install -r requirements.txt
    1.  export PYTHONPATH=./
    1.  python sql_install_handler.py
    1.  That should complete in a couple minutes
    1.  pip3 uninstall --yes -r requirements.txt
    1.  cd ../../etl/runtime
    1.  pip3 install -r requirements.txt
    1.  python refresh_ncit.py   --  YOU NEED TO ANSWER THE PROMPTS. YOU SHOULD BE ABLE TO HIT ENTER FOR ALL
    1.  python api_etl.py
    1.  pip3 uninstall --yes -r requirements.txt



## Section III: Running rds_init from PyCharm
If you don't want to use PyCharm you will need to follow the alternative to this section.
1. Follow Appendix A and create a PyCharm project in rds_init
2. Follow Appendix B and create a run configuration:
* Specify rds_init/runtime/local_run_sql_install_handler.py in Script Path
* Specify your parameters. They will look something like the following, depending on what you did in Scetion I
`--host localhost --port 5432 --user emfact --password emfact --dbname emfact`
3. Run your configuration
## Section II(Alternative): Running rds_init from command line
1. Follow Appendix C and create a virtual env for rds_init.
2. while still in the console, run the following(using user, password and dbname you used previously):
```
$ python3.11 --host localhost --port 5432 --user emfact --password emfact --dbname emfact local_run_sql_install_handler.py
```

## Section IV: Running etl/refresh_ncit.py Using PyCharm
This section uses PyCharm. If you don't want to use PyCharm, follow the alternative to this section.
1. Follow Appendix A to create a PyCharm project for etl
2. Follow Appendix B to create a launch configuration.
* For Script Path use: `etl/runtime/refresh_ncit.py`
* For Parameters use(again your user, password and dbname will depend on what you selected previously): `--dbname ab2 --host localhost --user ab2 --password ab2 --port 5432 --local_run`
3. Run your configuration
## Section III(Alternative): Running etl/refresh_ncit.py Using Commandline
1. Follow Appendix C to create a virtual env folder, venv for subproject etl.
2. While still in the commandline and in the dir etl/runtime, run the following(again noting that your dbname, user and password may differ):
```
python3.11 --dbname ab2 --host localhost --user ab2 --password ab2 --port 5432 --local_run refresh_ncit.py
```
## Section V: Running etl/api_etl.py Using PyCharm
This section uses PyCharm. If you don't want to use PyCharm, follow the alternative to this section.
1. Follow Appendix A to create a PyCharm project for etl (if not already done)
2. Follow Appendix B to create a launch configuration.
* For Script Path use: `etl/runtime/api_etl.py`
* For Parameters use(again your user, password and dbname will depend on what you selected previously): `--dbname ab2 --host localhost --user ab2 --password ab2 --port 5432 --local_run`
* For Environment Variables set the following
* x-api-key=YOUR CTS API KEY
* CT_API_URL_V2=https://clinicaltrialsapi.cancer.gov/api/v2/trials
* CT_API_VERSION=2
3. Run your configuration

## Section VI(Alternative): Running etl/api_etl.py Using Commandline
1. If not already done, follow Appendix C to create a virtual env folder, venv for subproject etl.
2. While still in the commandline and in the dir etl/runtime, run the following(again noting that your dbname, user and password may differ):
```
export x-api-key=YOUR CTS API KEY
export CT_API_URL_V2=https://clinicaltrialsapi.cancer.gov/api/v2/trials
export CT_API_VERSION=2
python3.11 --dbname ab2 --host localhost --user ab2 --password ab2 --port 5432 --local_run api_etl.py
```
## Appendix A: Creating a PyCharm Project for etl or rds_init

The process for creating a PyCharm project for etl or rds_init is similar. I'll start with etl.
<br>
Open a command line and from the root directory of the repo and execute the following:
```
$ cd etl/runtime
$ python3.11 -m venv venv
$ source venv/bin/activate
$ pip install -r requrirements.txt
```
That creates a virtual environment in a subdirectory named venv. It also initializes the virtual environment with the requirements. The next step will use this virtual environment in PyCharm.

Open PyCharm
Select File **-->** New Project
<br>
The dialog should have an option like **previously configured interpreter**.
<br>
* Use this and navigate to the bin dir of the virtual env you created, etl/runtime/venv/bin
<br>
* Select python3.11 executable
* In the Project tree, right click on runtime folder
* Select Mark Directory As **-->** Sources Root
* Go into the following menu option dialog: PyCharm --> Preferences --> Project --> Python Interpreter
* Click the + sign and add boto3 as a dependency
<br>
<br>
Repeat the above steps for rds_init but substitute rds_init wherever mention of etl folder appears.
*


## Appendix B: Create a PyCharm Run Configuration

* In PyCharm select the following: Run --> Edit Configurations...
* Use the dialog to create a python configuration
* For Script Path, select the script
* Configure the environment variables and parameters as instructed

## Appendix C: Create a Virtual Env for Subproject xyz

Subproject XYZ refers to etl or rds_init. These steps create a virtual env folder named venv which contains the python3.11 runtime and all of the requirements to run scripts in the subproject.
<br>
Open a command line and from the root directory of the repo and execute the following:
```
$ cd xyz/runtime
$ python3.11 -m venv venv
$ source venv/bin/activate
$ pip install -r requrirements.txt
pip install boto3
```

## Appendix D: Create a Single Virtual Env

Open a command line and from the **root directory of the repo** and execute the following:
```
$ python3.11 -m venv venv
$ source venv/bin/activate
$ pip install -r rds_init/runtime/requirements.txt
$ pip install -r etl/runtime/requirements.txt
```
* Type in python -V    -- this should be EMFACT_PYTHON_VERSION
* Type in which python -- this should point to python in your virtual env