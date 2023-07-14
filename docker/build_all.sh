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
docker build --progress plain --pull -t vertexproject/synapse:$TAG -f docker/images/synapse/Dockerfile .
docker/build_image.sh aha $TAG
docker/build_image.sh axon $TAG
docker/build_image.sh cortex $TAG
docker/build_image.sh cryotank $TAG
docker/build_image.sh jsonstor $TAG
docker/build_image.sh stemcell $TAG
