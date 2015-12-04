#!/bin/bash

DBNAME=
HOST=
USER=
PASS=

echo mongorestore -d $DBNAME -h $HOST -u $USER -p $PASS dump/linc-api-lions/ --drop
mongorestore -d $DBNAME -h $HOST -u $USER -p $PASS dump/linc-api-lions/ --drop
