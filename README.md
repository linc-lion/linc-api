# linc-api
LINC is a simple API allowing Lion Guardians to identify lions in Africa.
This API coordinate interactions between front-ends and the computational vision service.



# Troubleshooting

## Development

* Sometimes the code will continue return values that is no more in the structures, so try:

```
$ cd <git-repo-directory>/devenv
$ vagrant ssh
$ find /home/vagrant/linc-api/app/ -name __pycache__ -exec rm -fr {} \;
$ find /home/vagrant/linc-api/app/ -name *.pyc -exec rm -fr {} \;  
