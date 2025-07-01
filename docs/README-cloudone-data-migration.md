
# Data Migration

Two ETL scripts are run. These populate the db and make datasets that get put into bucket:
* nih-nci-ctf-backend-{TIER}-etl-data-sets

All lambdas in the API use the static datasets with two exceptions.
* user bookmarks are stored in dynamo (not really relevant for this)
* report_data lambda uses the db

If the datasets don't match the db then report_data lambda will have issues.
Just follow the ETL steps and that won't happen

## Code Issues
* merge issues created duplicated blocks of code of varying length in several py files. Fixed these and checked into *matt2* branch.
Since these are not being checked into dev branch, you will need to manually update the lambdas with the correct code.

### Update These:
* etl_start_mp lambda
* refresh_ncit lambda
* post_search_and_match lambda




## Data Issues

* there is only one lambda in the API that still uses the database. Because of this, we must make sure that ETL has created datasets. In this way the datasets ETL creates will match the db tables that ETL populates. 
* a couuple of datasets (zip files) are missing a file or two. This is do to merge difference. But is easily fixed

## ETL Process

* run rds_init  -- resets the db. step function usually runs this (but you can *ALWAYS* wipe out the db and start again)
* run refresh_ncit <strong>** If this fails see the note below</strong> -- processes thesaurus
* run etl_start_mp -- get trials, processes db and uploads datasets to S3
* if etl_start_mp fails, run refresh_ncit and then etl_start_mp again
* look at etl_start_mp logs. make sure datasets were uploaded. I had to fix a bad merge that prevented upload. It was line 839 in etl_start_mp. I commented it out: #df_crit_np=dict(func=get_df_crit_np, zipit=True, ),
* Fix datasets -- currently we need to do this
* If ETL lambdas (refresh and etl_start_mp) are run again, then *fix the datasets again*

** <strong>If EVS has a bad thesaurus zip file</strong>
* you will need to include a previous valid thesaurus id in the payload
* Go to this link to get a valid id: [EVS Archive](https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/)
* you will see folders named like 25.04d_Release, 25.03e_Release etc
* the id for these is: 25.04d and 25.03e
* assuming 25.04d is the latest and it fails, use 25.03e
* this is the payload
```json
{"body": "\ncit_version\": \"25.03e\""}
```

## Fix Datasets Process

* create clean local folder
* sync datasets bucket to local folder
* fix the zip files locally in your folder
* sync local to datasets bucket and for safe measure can also sync to sesion results bucket (probably not needed)


### Fixing the Datasets

Because  of merge issue, some datasets need to be fixed by adding missing files.
After ETL lambda etl_start_mp runs, it uploads the datasets to the etl dataset bucket.
You will follow the process in <strong>Fix Datasets Process</strong>
And make sure that the fixed zip files have the <strong>correct structure</strong> with files in the root.

* See Section: Ensure Correct Zip Structure

After you sync to your local folder, the files that you need to add to the 'broken' zip files will be in your directory.

* added these to ui_latest_dataset.zip
1. ncit_compiled_lookup.pickle.zip**
2. sid_to_bio_inc.pickle
3. sid_to_bio_exc.pickle

** YOU CAN GET ncit_compiled.pickle from ui_latest_dataset.zip. Simply zip it and add back to ui_latest_dataset.zip

* add these  to site_zip_distance.zip
1. site_lat_lon.pickle.zip
2. sites.pickle.zip

* put latest ui_latest_dataset.zip to BOTH
1. search results bucket
2. etl datasets bucket

### Ensure Correct Zip Structure
When adding to a zip we want the files to be in the root of the zip not under some folder.
<strong>I do the following</strong>

* copy the zip to a clean dir
* cd to the dir
* unzip some-zip.zip
* copy the missing files to ./
* remove the zip (we don't want it in the final fixed zip file)
* zip -r some-zip.zip ./
* copy it back to your 'sync' dir etc.....

* Fix env vars in lambdas to use correct secrets. This may already be the case. 


### Validating and Troubleshooting

* go into the UI
* open dev tools
* after logon most of the datasets are loaded
* if you don't get to the search screen see below
* in search screen select a disease and click search
* if you don't get to results screen see below
* in search screen enter a zip code
* check the dev tools and make sure the last call succeeded if not see below
* click on 'details' on a trial to expand it
* if the spinner keeps spinning see below

* if search screen doesn't appear, there's a problem with the datasets. find the endpoijnt being called. check the logs. 
You'll probably see a KeyError which will give a hint on what is mising
* if zip code doesn't work, probably you missed step for update_site_distance.zip
* if the details doesn't work, there is probably a db error. check the logs.

### Other Possible Issues

* The API uses datasets from the bucket above.
* If you get a KeyError in the logs, it may be do to a file missing from one of the datasets or similar
* you should make sure also that the DATASET_BUCKET var is correct
* DATASET_BUCKET=nih-nci-ctf-backend-{TIER}-etl-data-sets
* we ran into issue where env vars for some lambdas were incorrect. for example one was pointing to ClinicalTrials secret instead of CancerTrials
