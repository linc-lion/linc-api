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

msg "Updating System..."
sudo apt-get update
  
# Provision config section
USER=vagrant

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

# mongodb
msg "Adding MongoDB package repository"
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.6 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.6.list
sudo apt-get update

msg "Installing and configuring MongoDB"
sudo apt-get install -y mongodb-org
sudo service mongod restart

msg "Loading MongoDB database"
DUMPDIR=/home/vagrant/linc-api/db/mongodb/dump/heroku_jrlc1bt9
if [ -d "$DUMPDIR" ]; then
    msg "Dump directory found... trying to restore"
    mongorestore -h 127.0.0.1:27017 -d linc-api-lions $DUMPDIR --drop
else
msg "No dump found so no MongoDB restore"
fi
#mongodump -h ds115360.mlab.com:15360 -d heroku_jrlc1bt9 -u heroku_jrlc1bt9 -p 4ro8ll4mc61u34ti0hnrnqe0t6 --out ./dump/

# Adding Packages - common
msg "Adding repo for Python 3.6"
sudo add-apt-repository -y ppa:fkrull/deadsnakes
sudo apt-get update

msg "Installing common packages and dependencies"
sudo apt-get install -y python3.6 python3.6-dev python-dev python-virtualenv supervisor git python3.6-venv python3-setuptools redis-server redis-tools

# Installing NodeJS
msg "Installing NodeJS"
curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
sudo apt-get install nodejs
sudo apt-get install build-essential
sudo apt-get update

# Update Python libs
sudo apt-get -y install libcurl4-openssl-dev libffi-dev libssl-dev
sudo apt-get -y nodejs npm

# Python image tools Pillow dependencies
msg "Installing Python Image Tools"
sudo apt-get -y install libjpeg-dev libzip4 libzip-dev zlib1g zlib1g-dev
sudo apt-get -y install libcurl4-openssl-dev libffi-dev

# Adjusting for Pillow JPEG creation
sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib

# App Configuration
sudo rm -fr /home/vagrant/app/venv /home/vagrant/linc-api/venv /home/vagrant/linc-webapp/venv /home/vagrant/linc-webapp/venv

msg "Starting provision for All Apps..."
/usr/bin/python3.6 -m venv /home/vagrant/app/venv
source /home/vagrant/app/venv/bin/activate

msg "Install Python Dependencies"
pip install pip --upgrade
pip install setuptools --upgrade
pip install -r /home/vagrant/linc-api/requirements.txt --upgrade
pip install -I Pillow

msg "Configuring supervisord to run Linc Api"

# msg "Configuring supervisord to run linc-api services"

sudo echo '[program:linc-api]' > /etc/supervisor/conf.d/linc-api.conf
sudo echo 'command=/home/vagrant/app/venv/bin/python  /home/vagrant/linc-api/app/linc-api.py --port=5050' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'environment=S3_URL=https://linc-media.linclion.org/,APPURL=http://localhost:5050,IsDevelopment=True' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'redirect_stderr=true' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'stdout_logfile=/tmp/linc-api.log' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'numprocs=1' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'user=vagrant' >> /etc/supervisor/conf.d/linc-api.conf
sudo echo 'directory=/home/vagrant/linc-api/app' >> /etc/supervisor/conf.d/linc-api.conf

msg "Configuring supervisord to run linc-web services"

sudo echo '[program:linc-webapp]' > /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'command=/home/vagrant/app/venv/bin/python  /home/vagrant/linc-webapp/app/linc-webapp.py --port=5080' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'environment=APPURL=http://linc-webapp.venidera.local,API_URL=http://localhost:5050,IsDevelopment=True' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'redirect_stderr=true' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'stdout_logfile=/tmp/linc-webapp.log' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'numprocs=1' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'user=vagrant' >> /etc/supervisor/conf.d/linc-webapp.conf
sudo echo 'directory=/home/vagrant/linc-webapp/app' >> /etc/supervisor/conf.d/linc-webapp.conf

# Updating

msg "Updating supervisord services"
sudo supervisorctl update

# Install nginx
msg "Install the nginx service"
sudo apt-get -y install nginx

msg "Configuring the nginx services"
sudo ufw allow 'Nginx Full'

msg "Copying nginx config file"
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.original
sudo cp /home/vagrant/linc-api/devenv/nginx/nginx.conf /etc/nginx/nginx.conf

msg "Restarting the nginx service"
sudo /etc/init.d/nginx restart

msg "Nginx service status"
/etc/init.d/nginx status
sudo systemctl enable nginx.service

echo "source /home/vagrant/app/venv/bin/activate" >> "/home/vagrant/.bashrc"
echo 'export LC_ALL=en_US.UTF-8' >> "/home/vagrant/.bashrc"
echo 'export LANGUAGE=en_US.UTF-8' >> "/home/vagrant/.bashrc"
echo 'export LANG=en_US.UTF-8' >> "/home/vagrant/.bashrc"

msg "Cleaning Everything"
msg "   dist-upgrade"
sudo apt-get -y dist-upgrade

# msg "Setting timezone: EST"
# sudo timedatectl set-timezone EST
# sudo dpkg-reconfigure -f noninteractive tzdata

# msg "   autoremove"
# sudo apt-get -y autoremove
# msg "   autoclean"
# sudo apt-get -y autoclean

# # Shrink image size
# sudo dd if=/dev/zero of=/EMPTY bs=1M
# sudo rm -f /EMPTY

msg "Provision completed!"
