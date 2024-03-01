#/bin/bash

LINUX_TYPE=grep -E -w 'NAME' /etc/os-release | sed -e "s/NAME=//g" | sed -e "s/\"//g"

if [ x"$LINUX_TYPE" = "x" ]; then
    echo "Could not determine linux type.   Only Amazon Linux, Ubuntu or RHEL supported"
fi

if [ x"$LINUX_TYPE" = "Amazon Linux" ]; then
  sh install_amazonlinux.sh
fi

if [ x"$LINUX_TYPE" = "Redhat" ]; then
  sh install_rhel.sh
fi

if [ x"$LINUX_TYPE" = "Ubuntu" ]; then
  sh install_ubuntu.sh
fi
