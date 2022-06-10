#!/usr/bin/env bash

##############################################################################
#
# Build and tag a the synapse base image.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/build_base.sh
#
# This will rebuild the base image if it already exists.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
#set -x # debugging

BASEIMAGE=${1:-synbuild:base}

# Chuck the syndev:base image if it exists.
SYNDEVBASE_EXISTS=`docker image ls -q ${BASEIMAGE} | wc -l`
if [ ${SYNDEVBASE_EXISTS} != "0" ]
then
    echo "Removing ${BASEIMAGE} image"
    docker image rm ${BASEIMAGE}
fi

# FIXME make pull a default true arg?
docker build --pull -t ${BASEIMAGE} -f docker/images/synapse/Dockerfile .
