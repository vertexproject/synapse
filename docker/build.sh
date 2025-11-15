#!/usr/bin/env bash

##############################################################################
#
# Build and tag the suite of synapse images.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/build_all.sh
#
# The first argument may be provided, including the tag to build.
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1:-}

[ ! $TAG ] && echo "Tag not provided, defaulting tag to dev_build" && TAG=dev_build

# Build target images
docker builder prune -a -f

docker build --no-cache -t vertexproject/synapse:$TAG --build-arg TAG=${TAG} -f docker/images/synapse/Dockerfile .
docker build --no-cache -t vertexproject/synapse-aha:$TAG --build-arg TAG=${TAG} -f docker/images/aha/Dockerfile .
docker build --no-cache -t vertexproject/synapse-axon:$TAG --build-arg TAG=${TAG} -f docker/images/axon/Dockerfile .
docker build --no-cache -t vertexproject/synapse-cortex:$TAG --build-arg TAG=${TAG} -f docker/images/cortex/Dockerfile .
docker build --no-cache -t vertexproject/synapse-jsonstor:$TAG --build-arg TAG=${TAG} -f docker/images/jsonstor/Dockerfile .
