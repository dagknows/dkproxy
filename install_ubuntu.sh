#!/bin/bash

## Installer for Ubuntu
sudo apt-get update
sudo apt-get install -y make
sudo apt-get install -y make docker.io docker-compose unzip python3-pip docker-compose-v2 python3-venv
echo "Installing Docker Repos..."
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg ;
fi

echo "Adding user to docker user group..."
sudo usermod -aG docker ${USER}
sudo chmod a+r /etc/apt/keyrings/docker.gpg

make prepare

python3 -m venv ~/dkenv
~/dkenv/bin/pip install setuptools
~/dkenv/bin/pip install dagknows --force-reinstall
