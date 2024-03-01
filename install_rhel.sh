#!/bin/bash

## Installer for Ubuntu
sudo yum update
sudo yum install -y make git docker unzip python3-pip ca-certificates gnupg
# sudo yum install -y make docker.io docker docker-compose  docker-compose-v2

echo "Adding user to docker user group..."
sudo usermod -aG docker ${USER}
sudo chkconfig docker on

echo "Installing Docker Compose Plugin"
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose


make prepare

pip install dagknows --force-reinstall
