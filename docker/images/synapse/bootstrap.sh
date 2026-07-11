#!/bin/bash

apt-get clean
apt-get update
apt-get -y upgrade
apt-get install -y libffi-dev
apt-get install -y locales tini nano gosu build-essential

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

# Pre-create the storage volume owned by synuser. This is captured into the
# image before the VOLUME line so fresh named/anonymous volumes inherit it.
# Bind mounts are corrected at runtime by the entrypoint (see dropprivs.sh).
mkdir -p /vertex/storage
chown synuser:synuser /vertex/storage

if [ -d /build/dist ]; then
    python -m pip install /build/dist/*.whl
fi

# Cleanup build time deps and remove problematic files
apt-get remove -y --purge build-essential
apt-get remove -y --allow-remove-essential --purge e2fsprogs
apt-get autoremove -y --purge
apt-get clean
apt-get purge

rm -rf /build
rm -r /var/lib/apt/lists/*
rm /usr/local/lib/python3.14/site-packages/tornado/test/test.key
