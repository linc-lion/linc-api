#!/bin/bash

# This script intents to export the data from PostgreSQL to JSON that can be
# adapt to import to MongoDB

## Listing tables in the schema to generate the commands below
# select * from pg_tables where tableowner = 'uinncqqseaysgl';

## Common ways to export to JSON
#1 select array_to_json(array_agg(<table_name>)) from <table_name>;
#2  select row_to_json(table_name) from table_name; >> USED

# To execute this script just do:
# $ bash exporting_data_from_pg2mongodb.sh
# You will need to provido 'postgres' as password for each table

ldir=$(pwd)
export () {
    echo " Exporting data from table: "$1
    echo "select row_to_json($1) from $1;" | psql -U postgres -W postgres > $ldir/$1.json
    return 0
}

# This array are build using the result from the tables list commando above
tables=( "active_admin_comments" "admin_users" "cv_requests" "cv_results" "image_sets" "images" "lions" "organizations" "schema_migrations" "users" )
for i in "${tables[@]}"
do
  export $i
done
