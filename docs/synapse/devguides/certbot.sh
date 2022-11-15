#!/bin/bash

# Certbot preboot example
# Author: william.gibb@vertex.link

# This script is an example of using Let's Encrypt certbot tool to generate
# a valid HTTPS certificate for a Synapse service. This example uses web
#
# This creates and stores a Python venv in the
# /vertex/storage/preboot/letsencrypt/venv directory, so the certbot
# tool it installed once in a separate python environment, and cached in
# a mapped volume.
#
# Once the venv is setup, certbot is is used to create and potentially renew
# an HTTPS certificate. This certificate and private key are then copied to
# the locations in /vertex/storage where Synapse services assume they will
# find the HTTPS keys.
#
# cerbot does use a random backoff timer when performing a renewal. There may
# be a random delay when starting a service when the certificate needs to be
# renewed.
#
# Required Environment variables:
#
# CERTBOT_HOSTNAME - the hostname that certbot will generate certificate for.
# CERTBOT_EMAIL - the email address used with certbot.
#
# Optional Environment variables:
#
# CERTBOT_ARGS - additional args passed to the "cerbot certonly" and
#   "certbot renew" commands.
#

# set -x # echo commands
set -e # exit on nonzero

BASEDIR=/vertex/preboot
DSTKEY=/vertex/storage/sslkey.pem
DSTCRT=/vertex/storage/sslcert.pem

if [ -z ${CERTBOT_HOSTNAME} ]; then
    echo "CERTBOT_HOSTNAME env var is unset"
    exit 1
fi

if [ -z ${CERTBOT_EMAIL} ]; then
    echo "CERTBOT_EMAIL env var is unset"
    exit 1
fi

LEDIR=$BASEDIR/letsencrypt

CONFDIR=$LEDIR/conf
LOGSDIR=$LEDIR/logs
WORKDIR=$LEDIR/work
VENV=$LEDIR/venv

mkdir -p $LOGSDIR
mkdir -p $CONFDIR
mkdir -p $WORKDIR

CERBOT_DIR_ARGS=" --work-dir ${WORKDIR} --logs-dir=${LOGSDIR} --config-dir=${CONFDIR} "

KEYFILE="${CONFDIR}/live/${CERTBOT_HOSTNAME}/privkey.pem"
CERTFILE="${CONFDIR}/live/${CERTBOT_HOSTNAME}/fullchain.pem"

# Create a python venv, activate it, and install certbot and supporting tools.
if [ ! -d $VENV ]; then
    echo "Creating venv and installing certbot"
    python3 -m venv --without-pip --copies $VENV

    . $VENV/bin/activate

    python3 -Im ensurepip --default-pip
    python3 -m pip install --no-cache-dir -U pip wheel
    python3 -m pip install --no-cache-dir "certbot==1.32.0"

else

    echo "Activating venv"
    . $VENV/bin/activate

fi

if [ ! -f ${KEYFILE} ]; then

    certbot -n ${CERBOT_DIR_ARGS} certonly --agree-tos --email ${CERTBOT_EMAIL} --standalone -d ${CERTBOT_HOSTNAME} ${CERTBOT_ARGS:-}

    if [ $? -ne 0 ]; then
        echo "Error running certbot"
        exit 1
    fi

fi

certbot -n ${CERBOT_DIR_ARGS} renew --standalone ${CERTBOT_ARGS:-}

if [ $? -ne 0 ]; then
    echo "Error checking certificate renewal"
    exit 1
fi

echo "Copying certificates"

cp ${KEYFILE} ${DSTKEY}
cp ${CERTFILE} ${DSTCRT}

echo "Done setting up HTTPS certificates"