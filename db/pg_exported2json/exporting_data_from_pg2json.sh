#!/bin/bash

# This script export data from PostgreSQL to JSON
# The source for data is a backup file acquired in Heroku

# To create the database local you have to:
# 1 - create user uinncqqseaysgl;
# 2 - create database dbnameyouwant with owner = uinncqqseaysgl; >> you will provide the same name below in the db variable
# 3 - pg_restore -d dbnameyouwant postgre-backup-YYYY-MM-DD

# To execute this script just do:
# $ bash exporting_data_from_pg2json.sh
# You will need to provide 'postgres' as password for each table
# The password was defined in the provision of Vagrant
db=final_db
ldir=$(pwd)
export () {
    echo " Exporting data from table: "$1
    echo "select row_to_json($1) from $1;" | psql -U postgres -W $db > $ldir/$1.json
    return 0
}

# This array are build using the result from the tables list commando above
tables=( "active_admin_comments" "admin_users" "cv_requests" "cv_results" "image_sets" "images" "lions" "organizations" "schema_migrations" "users" )
for i in "${tables[@]}"
do
  export $i
done

## Listing tables in the schema to generate the commands below
# select * from pg_tables where tableowner = 'uinncqqseaysgl';

## Common ways to export to JSON
#1 select array_to_json(array_agg(<table_name>)) from <table_name>;
#2 select row_to_json(table_name) from table_name; >> USED
