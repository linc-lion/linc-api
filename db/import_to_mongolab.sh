#!/bin/bash

DBNAME=
HOST=
USER=
PASS=

mongorestore -d $DBNAME -h $HOST -u $USER -p $PASS dump/linc-api-lions/

