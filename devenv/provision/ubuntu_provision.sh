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

msg "Starting provision..."

msg "Configuring OS"
# Provision config section
USER=vagrant
HOME_DIR=/home/vagrant
PROGRAM_NAME=linc-api
PROGRAMA_LABEL_NAME=LINC-API

msg "Disabling IPv6"
sudo echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
sudo echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
sudo echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
sudo echo 1 > /proc/sys/net/ipv6/conf/default/disable_ipv6

# Timezone definition
msg "Setting timezone: EST"
sudo timedatectl set-timezone EST > /dev/null
sudo dpkg-reconfigure locales

# mongodb
msg "Adding MongoDB package repository"

msg "Installing MongoDB 3 and other packages required"
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo "deb http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.0.list
sudo apt-get update > /dev/null

msg "Installing and configuring MongoDB"
sudo apt-get install -y mongodb-server > /dev/null
sudo service mongodb stop > /dev/null
sudo rm -fr /var/lib/mongodb/*

sudo service mongodb start > /dev/null
sudo update-rc.d mongodb defaults > /dev/null
sudo update-rc.d mongodb enable > /dev/null

msg "Loading MongoDB database"
mongorestore -d linc-api-lions /home/vagrant/linc-api/db/mongodb/dump/linc-api-lions --drop

# Adding Packages
# common

msg "Adding repo for Python 3.5"
sudo add-apt-repository -y ppa:fkrull/deadsnakes
sudo apt-get update > /dev/null

msg "Installing common packages and dependencies"
sudo apt-get install -y python3.5 python3.5-dev python3-pip build-essential python-dev python-virtualenv supervisor git > /dev/null

# Installing NodeJS
msg "Installing NodeJS"
sudo apt-get -y purge node > /dev/null
sudo apt-get -y install nodejs npm > /dev/null
sudo ln -s /usr/bin/nodejs /usr/bin/node > /dev/null

# Python image tools Pillow dependencies
msg "Installing Python Image Tools"
sudo apt-get -y install libjpeg-dev libzip2 > /dev/null
## Adjusting for Pillow JPEG creation
sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib > /dev/null
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib > /dev/null
sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib > /dev/null

# App Configuration
sudo rm -fr /home/vagrant/app/venv /home/vagrant/linc-api/venv /home/vagrant/linc-webapp/venv /home/vagrant/linc-webapp/venv 2> /dev/null

msg "Starting provision for LINC-API app..."
sudo apt-get -y install libcurl4-openssl-dev libffi-dev > /dev/null

virtualenv --python=python3.5 --prompt="LINC-API " /home/vagrant/linc-api/venv
source /home/vagrant/linc-api/venv/bin/activate
msg "Install Python Dependencies"
pip install pip --upgrade
pip install setuptools --upgrade
pip install -r /home/vagrant/linc-api/requirements.txt --upgrade
pip install -I Pillow

msg "Starting provision for python linc-webapp app..."
# dependencies for pycurl
virtualenv --python=python3.5 --prompt=" LINC-WebApp " /home/vagrant/linc-webapp/venv
msg "Install Python Dependencies"
source /home/vagrant/linc-webapp/venv/bin/activate
pip install pip --upgrade
pip install setuptools --upgrade
pip install -r /home/vagrant/linc-webapp/requirements.txt --upgrade
pip install -I Pillow

msg "Configuring supervisord to run linc services"
cat << EOF | sudo tee -a /etc/supervisor/conf.d/linc.conf
[program:linc-api]
command=/home/vagrant/linc-api/venv/bin/python /home/vagrant/app/linc-api.py --port=5050
redirect_stderr=true
stdout_logfile=/tmp/linc-api.log
numprocs=1
user=vagrant
directory=/home/vagrant/app

[program:linc-webapp]
command=/home/vagrant/linc-webapp/venv/bin/python /home/vagrant/linc-webapp/app/linc-webapp.py --port=5080
redirect_stderr=true
stdout_logfile=/tmp/linc-webapp.log
numprocs=1
user=vagrant
directory=/home/vagrant/app

EOF


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
