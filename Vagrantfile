# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  # Debian 7 box
  config.vm.define "debian" do |deb|
    deb.vm.box = "debagent"
    deb.vm.box_url = "https://dl.dropboxusercontent.com/s/xymcvez85i29lym/vagrant-debian-wheezy64.box"
    deb.vm.synced_folder ".", "/src"
    deb.vm.provider :virtualbox do |vb|
      # Use VBoxManage to customize the VM. For example to change memory:
      vb.customize ["modifyvm", :id, "--memory", "512"]
    end

    # Manual set-up
    deb.vm.provision "shell", inline: "sudo apt-get update"
    deb.vm.provision "shell", inline: "sudo apt-get -y install ruby"
    deb.vm.provision "shell", inline: "sudo apt-get -y install ruby-dev"
    deb.vm.provision "shell", inline: "sudo apt-get -y install python"
    deb.vm.provision "shell", inline: "sudo gem install --no-ri --no-rdoc fpm"
  end

  # Centos 6 box
  config.vm.define "redhat" do |rh|
    rh.vm.box = "rhagent"
    rh.vm.box_url = "https://github.com/2creatives/vagrant-centos/releases/download/v6.5.1/centos65-x86_64-20131205.box"
    rh.vm.synced_folder ".", "/src"
    rh.vm.provider :virtualbox do |vb|
      # Use VBoxManage to customize the VM. For example to change memory:
      vb.customize ["modifyvm", :id, "--memory", "512"]
    end

    # Manual set-up
    rh.vm.provision "shell", inline: "sudo yum -y update"
    rh.vm.provision "shell", inline: "sudo yum -y install ruby"
    rh.vm.provision "shell", inline: "sudo yum -y install ruby-devel"
    rh.vm.provision "shell", inline: "sudo yum -y install rubygems"
    rh.vm.provision "shell", inline: "sudo gem install --no-ri --no-rdoc fpm"
    rh.vm.provision "shell", inline: "sudo yum -y localinstall http://yum.datadoghq.com/rpm/supervisor-3.0-0.5.a10.el6.noarch.rpm"
  end
end
