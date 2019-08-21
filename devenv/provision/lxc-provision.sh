#!/bin/bash

# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

# Functions definitions
msg () {
    echo " "
    echo -e "\033[33;34m >>> "$1
    echo " "
    return 0
}

HOME='/home/vagrant'
USER='vagrant'
GROUP='vagrant'

cd ${HOME}

msg "Starting provision..."
export DEBIAN_FRONTEND=noninteractive

msg "Configuring OS"

msg "Updating System..."
sudo apt-get update --fix-missing
sudo apt-get -y dist-upgrade
  
# Provision config section

msg "Disabling IPv6"
sudo echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
sudo echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
sudo echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
sudo echo 1 > /proc/sys/net/ipv6/conf/default/disable_ipv6

msg "Installing Systemd Services..."
sudo apt-get install -y systemd-services apt-transport-https

# Timezone definition
export LANGUAGE=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

echo -e 'LANG="en_US.UTF-8"\nLANGUAGE="en_US:en"\n' | sudo tee /etc/default/locale
echo -e 'LANG="en_US.UTF-8"\nLC_ALL="en_US.UTF-8"\n' | sudo tee -a /etc/environment

sudo apt-get install ntp

msg "Setting locale"
sudo locale-gen en_US.UTF-8
sudo dpkg-reconfigure -f noninteractive locales tzdata

# Adding Packages - common
msg "Installing Common Packages"
sudo apt-get -y install git unzip wget curl net-tools > /dev/null
sudo apt-get -y install build-essential > /dev/null
sudo apt-get -y install liblapack-dev libpq-dev pkg-config > /dev/null

msg "Installing Python Packages and Dependencies"
sudo apt-get -y install python3.6 python3.6-dev python3.6-venv python3-virtualenv python3-pip python3-setuptools > /dev/null
sudo apt-get -y install python-dev python-virtualenv python-setuptools-git > /dev/null

msg "Install Supervisor && GIT"
sudo apt-get -y install supervisor git > /dev/null

msg "Install Redis-Server"
sudo apt-get -y install redis-server > /dev/null

# Update Python libs
msg "Updating Python Libs"
sudo apt-get -y install libcurl4-openssl-dev libffi-dev libssl-dev > /dev/null
sudo apt-get -y install libjpeg-dev libzip4 libzip-dev zlib1g zlib1g-dev

# mongodb
msg "Adding MongoDB package repository"
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.0.list
sudo apt-get update > /dev/null

msg "Installing and configuring MongoDB"
sudo apt-get install -y mongodb-org > /dev/null
sudo service mongod restart

msg "Loading MongoDB database"
DUMPDIR=/home/vagrant/linc-api/db/mongodb/dump/heroku_jrlc1bt9
if [ -d "$DUMPDIR" ]; then
    msg "Dump directory found... trying to restore"
    mongorestore -h 127.0.0.1:27017 -d linc-api-lions $DUMPDIR --drop
else
msg "No dump found so no MongoDB restore"
fi

# Installing NodeJS
msg "Installing NodeJS"
sudo apt-get -y nodejs npm

# Python image tools Pillow dependencies
msg "Installing Python Image Tools"

# Adjusting for Pillow JPEG creation
sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib

# App Configuration
sudo rm -fr /home/vagrant/app/venv /home/vagrant/linc-api/venv /home/vagrant/linc-webapp/venv /home/vagrant/linc-webapp/venv

msg "Starting provision for All Apps..."
cd ${HOME}
/usr/bin/python3.6 -m venv ${HOME}/venv-3.6 --prompt=Linc
source ${HOME}/venv-3.6/bin/activate

msg "Change Directory Owner"
sudo chown -hR ${USER} ${HOME}/venv-3.6

msg "Install Python Dependencies"
pip install pip --upgrade
pip install setuptools --upgrade
pip install -r /home/vagrant/linc-api/requirements.txt --upgrade
pip install -I Pillow

PYTHON=${HOME}/venv-3.6/bin/python
SUPERV=/etc/supervisor/conf.d
msg "Configuring supervisord to run Linc Api"

# msg "Configuring supervisord to run linc-api services"

sudo echo "[program:linc-api]" > $SUPERV/linc-api.conf
sudo echo "command=$PYTHON $HOME/linc-api/app/linc-api.py --port=5050" >> $SUPER/linc-api.conf
sudo echo "environment=S3_URL=https://linc-media.linclion.org/,APPURL=http://localhost:5050,IsDevelopment=True" >> $SUPER/linc-api.conf
sudo echo "redirect_stderr=true" >> $SUPER/linc-api.conf
sudo echo "stdout_logfile=/tmp/linc-api.log" >> $SUPER/linc-api.conf
sudo echo "numprocs=1" >> $SUPER/linc-api.conf
sudo echo "user=$USER" >> $SUPER/linc-api.conf
sudo echo "directory=$HOME/linc-api/app" >> $SUPER/linc-api.conf

msg "Configuring supervisord to run linc-web services"

sudo echo "[program:linc-webapp]" > $SUPERV/linc-webapp.conf
sudo echo "command=$PYTHON  $HOME/linc-webapp/app/linc-webapp.py --port=5080" >> $SUPERV/linc-webapp.conf
sudo echo "environment=APPURL=http://linc-webapp.venidera.local,API_URL=http://localhost:5050,IsDevelopment=True" >> $SUPERV/linc-webapp.conf
sudo echo "redirect_stderr=true" >> $SUPERV/linc-webapp.conf
sudo echo "stdout_logfile=/tmp/linc-webapp.log" >> $SUPERV/linc-webapp.conf
sudo echo "numprocs=1" >> $SUPERV/linc-webapp.conf
sudo echo "user=vagrant" >> $SUPERV/linc-webapp.conf
sudo echo "directory=$HOME/linc-webapp/app" >> $SUPERV/linc-webapp.conf

# Updating

msg "Updating supervisord services"
sudo supervisorctl update > /dev/null

# Install nginx
msg "Install the nginx service"
sudo apt-get -y install nginx ufw > /dev/null

msg "Configuring the nginx services"
sudo ufw allow 'Nginx Full'

msg "Copying nginx config file"
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.original
sudo cp /home/vagrant/linc-api/devenv/nginx/nginx.conf /etc/nginx/nginx.conf

msg "Restarting the nginx service"
sudo systemctl restart nginx

msg "Nginx service status"
sudo systemctl status nginx

echo "source /home/vagrant/app/venv/bin/activate" >> "/home/vagrant/.bashrc"
echo 'export LC_ALL=en_US.UTF-8' >> "/home/vagrant/.bashrc"
echo 'export LANGUAGE=en_US.UTF-8' >> "/home/vagrant/.bashrc"
echo 'export LANG=en_US.UTF-8' >> "/home/vagrant/.bashrc"

msg "Cleaning Everything"
msg "   dist-upgrade"
sudo apt-get -y dist-upgrade

msg "Provision completed!"
