#!/bin/bash

## Installer for RHEL
sudo yum update -y
sudo yum install -y make git docker unzip python3-pip ca-certificates gnupg
sudo yum install -y docker-ce --allowerasing

sudo dnf install --nobest docker-ce
sudo dnf install https://download.docker.com/linux/centos/7/x86_64/stable/Packages/containerd.io-1.2.6-3.3.el7.x86_64.rpm
sudo dnf install docker-ce

sudo usermod -aG docker ${USER}
sudo systemctl enable --now docker
systemctl is-active docker

echo "Installing Docker Compose Plugin"
curl -L "https://github.com/docker/compose/releases/download/1.23.2/docker-compose-$(uname -s)-$(uname -m)" -o docker-compose
sudo mv docker-compose /usr/local/bin && sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

make prepare

pip install dagknows --force-reinstall
