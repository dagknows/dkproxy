#/bin/bash

## Installer for Linux
apt-get update
apt-get install -y make

make prepare

pip install dagknows --force-reinstall
