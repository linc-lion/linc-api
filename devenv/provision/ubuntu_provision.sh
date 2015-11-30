#!/bin/bash

# Functions definitions
msg () {
    echo " "
    echo -e "\033[33;34m >>> "$1
    echo " "
    return 0
}

msg "Starting provision..."

msg "Configuring OS"
# Provision config section
USER=vagrant
HOME_DIR=/home/vagrant
PROGRAM_NAME=linc-api
PROGRAMA_LABEL_NAME=LINC-API

# Timezone definition
msg "Setting timezone: EST"
sudo timedatectl set-timezone EST > /dev/null

# Adding repos
msg "Adding packages repos"
# mongodb
msg "Adding MongoDB package repository"
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list

# Update Packages Database
msg "Update packages database"
sudo apt-get update > /dev/null

# Adding Packages
# common
msg "Installing common packages and dependencies"
sudo apt-get -y install build-essential  python-pip python3-pip python-dev python3-dev python-virtualenv git supervisor > /dev/null

# Installing NodeJS
msg "Installing NodeJS"
sudo apt-get -y purge node > /dev/null
sudo apt-get -y install nodejs npm > /dev/null
sudo ln -s /usr/bin/nodejs /usr/bin/node > /dev/null

# Mongodb
msg "Installing MongoDB"
sudo apt-get install -y mongodb-org > /dev/null
sudo service mongod start
sudo update-rc.d mongod defaults

msg "Loading MongoDB database"
mongorestore -d linc-api-lions /home/vagrant/linc-api/db/dump/linc-api-lions --drop

# Install PostgreSQL for migration purposes. It will be removed in future.
msg "Installing PostgreSQL"
sudo apt-get -y install postgresql-server-dev-all postgresql-client postgresql postgresql-contrib > /dev/null
sudo service postgresql start
sudo update-rc.d postgresql defaults
#P4Ssw0rd

msg "Loading PostgreSQL database"
# User: postgres password: postgres
sudo su - postgres -c sh -c 'echo "create user uinncqqseaysgl superuser login ;" | psql '
sudo su - postgres -c sh -c "cat $HOME_DIR/linc-api/db/2015-08-26-pg-dump.sql | psql "
sudo su - postgres -c sh -c "psql -U postgres -d postgres -c \"alter user postgres with password 'postgres';\""
sudo echo 'local all all md5' | cat - /etc/postgresql/9.3/main/pg_hba.conf > /tmp/temp && sudo mv /tmp/temp /etc/postgresql/9.3/main/pg_hba.conf
sudo service postgresql restart

# Python image tools Pillow dependencies
msg "Installing Python Image Tools"
sudo apt-get -y install libjpeg-dev libzip2 > /dev/null
## Adjusting for Pillow JPEG creation
sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib > /dev/null
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib > /dev/null
sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib > /dev/null

# App Configuration
msg "Starting provision for LINC-API app..."
sudo apt-get -y install libcurl4-openssl-dev libffi-dev > /dev/null
sudo rm -fr /home/vagrant/app/venv /home/vagrant/linc-api/venv 2> /dev/null
virtualenv --python=python2.7 --prompt="LINC-API " /home/vagrant/linc-api/venv
source /home/vagrant/linc-api/venv/bin/activate
msg "Install Python Dependencies"
pip install pip --upgrade
pip install setuptools --upgrade
pip install -r /home/vagrant/linc-api/requirements.txt --upgrade
pip install -I Pillow

msg "Configuring supervisord to run linc-api"
cat << EOF | sudo tee -a /etc/supervisor/conf.d/linc-api.conf
[program:linc-api]
command=/home/vagrant/linc-api/venv/bin/python /home/vagrant/app/linc-api.py
redirect_stderr=true
stdout_logfile=/tmp/linc-api.log
numprocs=1
user=vagrant
directory=/home/vagrant/app

EOF

msg "Install MongoDB Admin for development purposes"
sudo apt-get -y install libkrb5-dev > /dev/null
sudo npm install -g mongo-express > /dev/null
sudo cp /usr/local/lib/node_modules/mongo-express/config.default.js /usr/local/lib/node_modules/mongo-express/config.js
# Configuring mongo-express
sudo /bin/sed -i -e 's/readOnly: true/readOnly: false/g' /usr/local/lib/node_modules/mongo-express/config.js
sudo /bin/sed -i -e 's/documentsPerPage: 10,/documentsPerPage: 100,/g' /usr/local/lib/node_modules/mongo-express/config.js

cat << EOF2 | sudo tee -a /usr/local/bin/mongo-express

#!/bin/bash
cd /usr/local/lib/node_modules/mongo-express && /usr/bin/node app.js

EOF2
sudo chmod +x /usr/local/bin/mongo-express

cat << EOF3 | sudo tee -a /etc/supervisor/conf.d/mongo-express.conf

[program:mongo-express]
command=sh -c /usr/local/bin/mongo-express
redirect_stderr=true
stdout_logfile=/tmp/mongo-express.log
numprocs=1
user=vagrant
directory=/usr/local/lib/node_modules/mongo-express

EOF3

msg "Install PostgreSQL Admin for development purposes"
sudo npm install -g express-admin > /dev/null
cd /usr/local/lib/node_modules/express-admin && sudo npm install pg@2.8.2 && cd -
sudo mkdir $HOME_DIR/pgadmcfg
echo '{"app": {"themes": true, "languages": true, "layouts": true}, "pg": {"password": "postgres", "user": "postgres", "database": "postgres"}, "server": {"port": 7081}}' > $HOME_DIR/pgadmcfg/config.json
echo '{}' > $HOME_DIR/pgadmcfg/custom.json
echo '{"organizations": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "organizations", "verbose": "organizations"}, "listview": {"order": {}, "page": 25}, "slug": "organizations", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "name", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "name"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}]}, "schema_migrations": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "", "name": "schema_migrations", "verbose": "schema_migrations"}, "listview": {"order": {}, "page": 25}, "slug": "schema_migrations", "columns": [{"control": {"text": true}, "name": "version", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "version"}]}, "admin_users": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "admin_users", "verbose": "admin_users"}, "listview": {"order": {}, "page": 25}, "slug": "admin_users", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "email", "defaultValue": "", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "email"}, {"control": {"text": true}, "name": "encrypted_password", "defaultValue": "", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "encrypted_password"}, {"control": {"text": true}, "name": "reset_password_token", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "reset_password_token"}, {"control": {"text": true}, "name": "reset_password_sent_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "reset_password_sent_at"}, {"control": {"text": true}, "name": "remember_created_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "remember_created_at"}, {"control": {"text": true}, "name": "sign_in_count", "defaultValue": "0", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "sign_in_count"}, {"control": {"text": true}, "name": "current_sign_in_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "current_sign_in_at"}, {"control": {"text": true}, "name": "last_sign_in_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "last_sign_in_at"}, {"control": {"text": true}, "name": "current_sign_in_ip", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "inet", "verbose": "current_sign_in_ip"}, {"control": {"text": true}, "name": "last_sign_in_ip", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "inet", "verbose": "last_sign_in_ip"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}]}, "users": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "users", "verbose": "users"}, "listview": {"order": {}, "page": 25}, "slug": "users", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "email", "defaultValue": "", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "email"}, {"control": {"text": true}, "name": "organization_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "organization_id"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "encrypted_password", "defaultValue": "", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "encrypted_password"}, {"control": {"text": true}, "name": "remember_created_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "remember_created_at"}, {"control": {"text": true}, "name": "sign_in_count", "defaultValue": "0", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "sign_in_count"}, {"control": {"text": true}, "name": "current_sign_in_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "current_sign_in_at"}, {"control": {"text": true}, "name": "last_sign_in_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "last_sign_in_at"}, {"control": {"text": true}, "name": "authentication_token", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "authentication_token"}, {"control": {"text": true}, "name": "current_sign_in_ip", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "current_sign_in_ip"}, {"control": {"text": true}, "name": "last_sign_in_ip", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "last_sign_in_ip"}]}, "image_sets": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "image_sets", "verbose": "image_sets"}, "listview": {"order": {}, "page": 25}, "slug": "image_sets", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "lion_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "lion_id"}, {"control": {"text": true}, "name": "main_image_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "main_image_id"}, {"control": {"text": true}, "name": "uploading_organization_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "uploading_organization_id"}, {"control": {"text": true}, "name": "uploading_user_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "uploading_user_id"}, {"control": {"text": true}, "name": "owner_organization_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "owner_organization_id"}, {"control": {"text": true}, "name": "is_verified", "defaultValue": "false", "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "char", "verbose": "is_verified"}, {"control": {"text": true}, "name": "latitude", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "decimal(10,6)", "verbose": "latitude"}, {"control": {"text": true}, "name": "decimal", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "decimal(10,6)", "verbose": "decimal"}, {"control": {"text": true}, "name": "longitude", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "decimal(10,6)", "verbose": "longitude"}, {"control": {"text": true}, "name": "photo_date", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "photo_date"}, {"control": {"text": true}, "name": "gender", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "gender"}, {"control": {"text": true}, "name": "is_primary", "defaultValue": "false", "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "char", "verbose": "is_primary"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "date_of_birth", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "date_of_birth"}, {"control": {"text": true}, "name": "tags", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "ARRAY", "verbose": "tags"}, {"control": {"text": true}, "name": "date_stamp", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "date", "verbose": "date_stamp"}, {"control": {"text": true}, "name": "notes", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "text", "verbose": "notes"}]}, "active_admin_comments": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "active_admin_comments", "verbose": "active_admin_comments"}, "listview": {"order": {}, "page": 25}, "slug": "active_admin_comments", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "namespace", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "namespace"}, {"control": {"text": true}, "name": "body", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "text", "verbose": "body"}, {"control": {"text": true}, "name": "resource_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "resource_id"}, {"control": {"text": true}, "name": "resource_type", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "resource_type"}, {"control": {"text": true}, "name": "author_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "author_id"}, {"control": {"text": true}, "name": "author_type", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "author_type"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}]}, "cv_requests": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "cv_requests", "verbose": "cv_requests"}, "listview": {"order": {}, "page": 25}, "slug": "cv_requests", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "uploading_organization_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "uploading_organization_id"}, {"control": {"text": true}, "name": "image_set_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "image_set_id"}, {"control": {"text": true}, "name": "status", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "status"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "server_uuid", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "server_uuid"}]}, "lions": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "lions", "verbose": "lions"}, "listview": {"order": {}, "page": 25}, "slug": "lions", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "name", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "name"}, {"control": {"text": true}, "name": "organization_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "organization_id"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "primary_image_set_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "primary_image_set_id"}]}, "cv_results": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "cv_results", "verbose": "cv_results"}, "listview": {"order": {}, "page": 25}, "slug": "cv_results", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "cv_request_id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "cv_request_id"}, {"control": {"text": true}, "name": "match_probability", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "double", "verbose": "match_probability"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "lion_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "lion_id"}]}, "images": {"mainview": {"show": true}, "editview": {"readonly": false}, "table": {"pk": "id", "name": "images", "verbose": "images"}, "listview": {"order": {}, "page": 25}, "slug": "images", "columns": [{"control": {"text": true}, "name": "id", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "id"}, {"control": {"text": true}, "name": "image_type", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "image_type"}, {"control": {"text": true}, "name": "image_set_id", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "integer", "verbose": "image_set_id"}, {"control": {"text": true}, "name": "is_public", "defaultValue": "false", "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "char", "verbose": "is_public"}, {"control": {"text": true}, "name": "url", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "url"}, {"control": {"text": true}, "name": "created_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "created_at"}, {"control": {"text": true}, "name": "updated_at", "defaultValue": null, "allowNull": false, "editview": {"show": true}, "listview": {"show": true}, "type": "timestamp", "verbose": "updated_at"}, {"control": {"text": true}, "name": "is_deleted", "defaultValue": "false", "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "char", "verbose": "is_deleted"}, {"control": {"text": true}, "name": "full_image_uid", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "full_image_uid"}, {"control": {"text": true}, "name": "thumbnail_image_uid", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "thumbnail_image_uid"}, {"control": {"text": true}, "name": "main_image_uid", "defaultValue": null, "allowNull": true, "editview": {"show": true}, "listview": {"show": true}, "type": "varchar(null)", "verbose": "main_image_uid"}]}}' > $HOME_DIR/pgadmcfg/settings.json
echo '{"admin": {"admin": true, "hash": "NDK06UNx/oEW/znUkiEZBFJ4gvcBOH7FiZS6bbB2GUe8vy+SY0hJjSZEGgwcZEj9ayxRVfGrlQ3dDGKpaE4eTPDFJz5xfPQZhhq8XXaOh/owQWEy1Y1LoelLoB6IygweB7vHFJAyXX9f7C9rLkWFy/3ID5ZjyETFY7dgK4qiA48=", "salt": "bbOyTwInW/c1/vCE5VI7f0FQGfIV7qbt/qoHUyqN0vJfoxmtZz4+vdej75GBKHR77htL05K+b4FgMc7hom7bBNWmmcekZIpuiMAgEsVagqdZLx3U/Z6UbC18nPliMSO9MpKSP6hdnG053BIZFaHKmqutO1ZKmUSU0A0jZdya8Vc=", "name": "admin"}}' > $HOME_DIR/pgadmcfg/users.json

cat << EOF4 | sudo tee -a /usr/local/bin/express-admin-pg

#!/bin/bash
node /usr/local/lib/node_modules/express-admin/app.js $HOME_DIR/pgadmcfg


EOF4
sudo chmod +x /usr/local/bin/express-admin-pg

cat << EOF5 | sudo tee -a /etc/supervisor/conf.d/express-admin-pg.conf

[program:express-admin-pg]
command=sh -c /usr/local/bin/express-admin-pg
redirect_stderr=true
stdout_logfile=/tmp/express-admin-pg.log
numprocs=1
user=root
directory=/usr/local/lib/node_modules/express-admin

EOF5


# Updating
sudo supervisorctl update

msg "Cleaning Everything"
sudo apt-get -y dist-upgrade > /dev/null
sudo apt-get -y autoremove > /dev/null
sudo apt-get -y autoclean > /dev/null
# Shrink image size
sudo dd if=/dev/zero of=/EMPTY bs=1M
sudo rm -f /EMPTY

msg "Provision completed!"
