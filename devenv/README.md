# linc-api

## Development environment

The LINC-API development environment (devenv) is based on Vagrant environments.
This document considers that you already have a clone of the LINC-API git repository.
The current version have the PostgreSQL database for migration purposes.

### Dependencies

1. Requires [VirtualBox](https://www.virtualbox.org/)
2. Requires [Vagrant](https://www.vagrantup.com/downloads.html)

#### Install vbguest plugin to keep VirtualBox modules updated

After you install Vagrant, execute in the terminal:
```
$ vagrant plugin install vagrant-vbguest
```

### Provision for the devenv

To start development execute:
```
$ cd <git-repository-clone>/devenv
$ vagrant up --provision
```
Vagrant will prepare the box and start the provision for the app, as defined in the VagrantFile and the provision shell script.
With provision completed you can do request in [http://localhost:5000](http://localhost:5000)

### Stop working

Once you decide to stop working execute:
```
$ cd <git-repository-clone>/devenv
$ vagrant suspend
```

### Start to work again

Resume the devenv with:
```
$ cd <git-repository-clone>/devenv
$ vagrant resume
```

### Logging/Monitoring the devenv

You can use the OS of the devenv executing:
```
$ cd <git-repository-clone>/devenv
$ vagrant ssh
```

Also you can look log files with (example):
```
$ cd <git-repository-clone>/devenv
$ vagrant ssh -c "tail -f /tmp/linc-api*.log"
```

## MongoDB Admin Tool for development purposes

Once you have the vagrant env running go to browser and access
[http://localhost:8081](http://localhost:8081). To access use username `admin`
and password `pass`.

## PgAdmin3 - PostgreSQL Admin Tool

Execute:
```
$ cd <git-repository-clone>/devenv
$ vagrant ssh -c '/usr/bin/pgadmin3'
```
It requires a X Window Server (in Mac XQuartz, Linux commonly installs one).
You will have to create a connection and provide name, and the password 'postgres' for the user 'postgres'.
