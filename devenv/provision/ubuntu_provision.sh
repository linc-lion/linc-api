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
#msg "Setting timezone: America/Sao_Paulo"
#sudo timedatectl set-timezone America/Sao_Paulo

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
#mongorestore -d beholder /home/vagrant/app/db/dump/beholder --drop

# Install PostgreSQL for migration purposes. It will be removed in future.
msg "Installing PostgreSQL"
sudo apt-get -y install postgresql-server-dev-all postgresql-client postgresql postgresql-contrib pgadmin3 > /dev/null
sudo service postgresql start
sudo update-rc.d postgresql defaults

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
sudo rm -fr /home/vagrant/app/venv 2> /dev/null
virtualenv --python=python3 --prompt="LINC-API " /home/vagrant/app/venv
source /home/vagrant/app/venv/bin/activate
msg "Install Python Dependencies"
pip install pip setuptools --upgrade
pip install -r /home/vagrant/app/requirements.txt --upgrade
pip install -I Pillow

msg "Configuring supervisord to run linc-api"
cat << EOF | sudo tee -a /etc/supervisor/conf.d/linc-api.conf
[program:linc-api]
command=/home/vagrant/app/venv/bin/python /home/vagrant/app/app/linc-api.py
redirect_stderr=true
stdout_logfile=/tmp/linc-api.log
numprocs=1
user=vagrant
directory=/home/vagrant/app/app

EOF

msg "Install MongoDB Admin for development purposes"
sudo apt-get -y install libkrb5-dev > /dev/null
sudo npm install -g mongo-express > /dev/null
sudo cp /usr/local/lib/node_modules/mongo-express/config.default.js /usr/local/lib/node_modules/mongo-express/config.js

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

# Updating
sudo supervisorctl update

msg "Cleaning Everything"
sudo apt-get -y autoremove > /dev/null
sudo apt-get -y autoclean > /dev/null
# Shrink image size
sudo dd if=/dev/zero of=/EMPTY bs=1M
sudo rm -f /EMPTY

msg "Provision completed!"
