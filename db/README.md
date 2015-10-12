# linc-api

## Database documentation

This document describes the database structure and activities related to implement and migrate database from PostgreSQL to MongoDB.

## Migration from PostgreSQL to MongoDB

The procedure describe below was executed to generate the initial MongoDB database using a dump of the PostgreSQL database.

### Exporting data from PostgreSQL to JSON files

Once the devenv is running, the data from PostgreSQL can be exported using the script `exporting_data_from_pg2json.sh`, like:

```
$ vagrant ssh
$ sudo supervisorctl stop linc-api
$ source ~/linc-api/venv/bin/activate
LINC-API $ cd ~/linc-api/db/pg_exported2json
LINC-API $ bash exporting_data_from_pg2json.sh
```

The procedure above requires that you provide the password 'postgres' per table.
The generated files have a header and a footer invalid for JSON parse cause it shows informations related to the query in PostgreSQL.

### Import the JSON files into a MongoDB database

This activity considers that you just executed the commands of last section.
You need to edit `routes.py` and uncomment the line `(r"/import", ImportHandler)` that activates the handler for the url: /import.
Then start the linc-api:
```
LINC-API $ cd ~/linc-api/app
LINC-API $ python linc-api.py
```
Open the Postman/Curl and request a POST in the url `http://localhost:5000/import` and the import process will be executed.

To visualize data in MongoDB access in browser `http://localhost:8081` and use `admin` and `pass` to open the database admin tool.
