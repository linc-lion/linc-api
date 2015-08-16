#!/bin/bash
echo "Starting provision..."
echo " "
# Timezone definition
#echo "Setting timezone: America/Sao_Paulo"
#sudo timedatectl set-timezone America/Sao_Paulo

# adding mongodb repo
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
sudo apt-get update
sudo apt-get -y install build-essential  python-pip python3-pip python-dev python3-dev python-virtualenv git supervisor
sudo apt-get -y dist-upgrade
sudo apt-get install -y mongodb-org
sudo service mongod start
sudo update-rc.d mongod defaults

echo "Starting provision for python app..."
virtualenv --python=python3 --prompt=" LINC-API " /home/vagrant/app/venv
source /home/vagrant/app/venv/bin/activate
pip install -r /home/vagrant/app/requirements.txt --upgrade

echo "Configuring supervisord to daemonize"
cat << EOF | sudo tee -a /etc/supervisor/conf.d/linc-api.conf
[program:linc-api]
command=/home/vagrant/app/venv/bin/python /home/vagrant/app/app/linc-api.py
redirect_stderr=true
stdout_logfile=/tmp/linc-api.log
numprocs=1
user=vagrant
directory=/home/vagrant/app/app

EOF

sudo supervisorctl update
sudo apt-get -y autoremove
sudo apt-get -y autoclean
echo "Provision phase completed!"
