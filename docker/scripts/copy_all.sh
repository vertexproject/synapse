#!/usr/bin/env bash

##############################################################################
#
# Copy all images from one registry to another registry using cosign
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/copy_all.sh
#
# The first argument is the tag to push.
# The second argument is the source registry for the images.
# The third argument is the registry where images and signature sare copied too
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1}
REGISTRY=${2}
DESTREG=${2}

[ ! $TAG ] && echo "Tag not provided, exiting" && false
[ ! $REGISTRY ] && echo "registry not provided, exiting" && false
[ ! $DESTREG ] && echo "secondary registry not provided, exiting" && false

cosign copy ${REGISTRY}vertexproject/synapse:${TAG} ${DESTREG}vertexproject/synapse:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-aha:${TAG} ${DESTREG}vertexproject/synapse-aha:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-axon:${TAG} ${DESTREG}vertexproject/synapse-axon:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-cortex:${TAG} ${DESTREG}vertexproject/synapse-cortex:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-cryotank:${TAG} ${DESTREG}vertexproject/synapse-cryotank:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-stemcell:${TAG} ${DESTREG}vertexproject/synapse-stemcell:${TAG}
cosign copy ${REGISTRY}vertexproject/synapse-jsonstor:${TAG} ${DESTREG}vertexproject/synapse-jsonstor:${TAG}
