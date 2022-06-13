#!/usr/bin/env bash

##############################################################################
#
# Push all the synapse images to a remote registry.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/push_all.sh
#
# The first argument is the tag to push.
# The second argument may be provided, which is the respository base to push
# too. The default docker registry will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1}

[ ! $TAG ] && echo "Tag not provided, exiting" && false

REGISTRY=${2-}

if [ $REGISTRY ]
then
    echo "Tagging images with alternative registry."
    docker tag vertexproject/synapse:${TAG} ${REGISTRY}vertexproject/synapse:${TAG}
    docker tag vertexproject/synapse-aha:${TAG} ${REGISTRY}vertexproject/synapse-aha:${TAG}
    docker tag vertexproject/synapse-axon:${TAG} ${REGISTRY}vertexproject/synapse-axon:${TAG}
    docker tag vertexproject/synapse-cortex:${TAG} ${REGISTRY}vertexproject/synapse-cortex:${TAG}
    docker tag vertexproject/synapse-cryotank:${TAG} ${REGISTRY}vertexproject/synapse-cryotank:${TAG}
    docker tag vertexproject/synapse-stemcell:${TAG} ${REGISTRY}vertexproject/synapse-stemcell:${TAG}
    docker tag vertexproject/synapse-jsonstor:${TAG} ${REGISTRY}vertexproject/synapse-jsonstor:${TAG}
fi

docker push ${REGISTRY}vertexproject/synapse:${TAG}
docker push ${REGISTRY}vertexproject/synapse-aha:${TAG}
docker push ${REGISTRY}vertexproject/synapse-axon:${TAG}
docker push ${REGISTRY}vertexproject/synapse-cortex:${TAG}
docker push ${REGISTRY}vertexproject/synapse-cryotank:${TAG}
docker push ${REGISTRY}vertexproject/synapse-stemcell:${TAG}
docker push ${REGISTRY}vertexproject/synapse-jsonstor:${TAG}
