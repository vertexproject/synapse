#!/bin/bash

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
# set -x # debugging

TAG=$1

BASEIMAGE=synbuild:base

[ ! $TAG ] && echo "Tag not provided, defaulting tag to dev_build" && TAG=dev_build

# Chuck the syndev:base image if it exists.
SYNDEVBASE_EXISTS=`docker image ls -q ${BASEIMAGE} | wc -l`
if [ ${SYNDEVBASE_EXISTS} != "0" ]
then
    echo "Removing syndev:base image"
    docker image rm ${BASEIMAGE}
fi

# FIXME make pull a default true arg?
docker build --pull -t ${BASEIMAGE} -f docker/images/synapse/Dockerfile .

# Build target images
docker build -t vertexproject/synapse-aha:$TAG -f docker/images/aha/Dockerfile .
docker build -t vertexproject/synapse-axon:$TAG -f docker/images/axon/Dockerfile .
docker build -t vertexproject/synapse-cortex:$TAG -f docker/images/cortex/Dockerfile .
docker build -t vertexproject/synapse-cryotank:$TAG -f docker/images/cryotank/Dockerfile .
docker build -t vertexproject/synapse-jsonstor:$TAG -f docker/images/jsonstor/Dockerfile .
docker build -t vertexproject/synapse-stemcell:$TAG -f docker/images/stemcell/Dockerfile .

# Tag the base image as well
docker tag ${BASEIMAGE} vertexproject/synapse:$TAG
