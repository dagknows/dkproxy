#!/bin/bash

## Installer for Ubuntu
sudo yum update
sudo yum install -y make git docker unzip python3-pip ca-certificates gnupg
# sudo yum install -y make docker.io docker docker-compose  docker-compose-v2

echo "Adding user to docker user group..."
sudo usermod -aG docker ${USER}
sudo chkconfig docker on

make prepare

pip install dagknows --force-reinstall
