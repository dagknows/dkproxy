#/bin/bash

LINUX_TYPE=`grep -E -w 'NAME' /etc/os-release | sed -e "s/NAME=//g" | sed -e "s/\"//g"`

echo LINUX_TYPE=$LINUX_TYPE

if [ x"$LINUX_TYPE" = "x" ]; then
    echo "Could not determine linux type.   Only Amazon Linux, Ubuntu or RHEL supported"
fi

if [ x"$LINUX_TYPE" = "xAmazon Linux" ]; then
  sh install_amazonlinux.sh
fi

if [ x"$LINUX_TYPE" = "xRed Hat Enterprise Linux" ]; then
  sh install_rhel.sh
fi

if [ x"$LINUX_TYPE" = "xUbuntu" ]; then
  sh install_ubuntu.sh
fi
