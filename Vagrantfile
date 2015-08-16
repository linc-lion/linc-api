# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.synced_folder "./", "/home/vagrant/app", create: true

  # Use it with Linux and Mac OSX
  config.vm.box = "ubuntu/trusty64"
  # Use it with Windows
  #config.vm.box = "ubuntu/precise32"

  # For Heroku Deploy
  config.vm.network :forwarded_port, guest:  5000, host: 5000 # API Port

  config.vm.network :private_network, ip: "192.168.100.10"

  config.vm.provider :virtualbox do |vb|
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/app", "1"]
    vb.customize ["modifyvm", :id, "--memory", "512"]
  end

  # Provision without puppet or cheff, using shell scripts
  config.vm.provision :shell, path: "./provision/provision.sh"

  # ssh
  config.ssh.forward_x11 = true
end
