#!/bin/bash

apt-get clean
apt-get update
apt-get -y upgrade
apt-get install -y libffi-dev
apt-get install -y locales curl tini nano build-essential

python -m pip install --upgrade pip

# Configure locales
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen en_US.UTF-8
dpkg-reconfigure locales
/usr/sbin/update-locale LANG=en_US.UTF-8

# Initialize the synuser account and group
groupadd -g 999 synuser
useradd -r --home-dir=/home/synuser -u 999 -g synuser --shell /bin/bash synuser
mkdir -p /home/synuser
chown synuser:synuser /home/synuser

PIP_NO_CACHE_DIR=1
PIP_ROOT_USER_ACTION=ignore
python -m pip install --verbose --break-system-packages /build/synapse

# Cleanup build time deps and remove problematic files
apt-get remove -y --purge curl build-essential
apt-get remove -y --allow-remove-essential --purge e2fsprogs
apt-get autoremove -y --purge
apt-get clean
apt-get purge

rm -rf /build
rm -rf /usr/local/lib/python3.14/site-packages/synapse/tests/files/certdir/
rm -rf /usr/local/lib/python3.14/site-packages/synapse/tests/files/aha/certs/
rm -rf /usr/local/lib/python3.14/site-packages/tornado/test/test.key
rm -rf /var/lib/apt/lists/*
