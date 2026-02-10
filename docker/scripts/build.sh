#!/usr/bin/env bash

##############################################################################
#
# Build and tag the suite of synapse images.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/build.sh
#
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1:-}

[ -z ${TAG} ] && TAG=3.x.x-dev && echo "Tag not provided, defaulting tag to ${TAG}"

# Build target images
docker builder prune -a -f

BUILDARGS="--build-arg TAG=${TAG}"

docker build --no-cache -t vertexproject/synapse:$TAG ${BUILDARGS} -f docker/images/synapse/Dockerfile .
docker build --no-cache -t vertexproject/synapse-aha:$TAG ${BUILDARGS} -f docker/images/aha/Dockerfile .
docker build --no-cache -t vertexproject/synapse-axon:$TAG ${BUILDARGS} -f docker/images/axon/Dockerfile .
docker build --no-cache -t vertexproject/synapse-cortex:$TAG ${BUILDARGS} -f docker/images/cortex/Dockerfile .
docker build --no-cache -t vertexproject/synapse-jsonstor:$TAG ${BUILDARGS} -f docker/images/jsonstor/Dockerfile .

# These images are used exclusively by CI pipelines
CI_BASE_IMAGE="vertexproject/synapse-ci:${TAG}"
echo "Building CI images for ${CI_BASE_IMAGE}"
docker build --no-cache -t $CI_BASE_IMAGE ${BUILDARGS} -f docker/images/ci/Dockerfile .
docker build --no-cache -t "${CI_BASE_IMAGE}-browsers" ${BUILDARGS} --build-arg CI_BASE_IMAGE=${CI_BASE_IMAGE} -f docker/images/ci-browsers/Dockerfile .
