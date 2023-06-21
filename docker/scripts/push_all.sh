#!/usr/bin/env bash

##############################################################################
#
# Push all the synapse images to a remote registry.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/push_all.sh
#
# The first argument is the tag to push.
# The second argument is the registry to push to.
# The third argument is the place where image digests are written to, one line
# per image.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1}
REGISTRY=${2}
DIGESTFILE=${2}

[ ! $TAG ] && echo "Tag not provided, exiting" && false
[ ! $REGISTRY ] && echo "registry not provided, exiting" && false
[ ! $DIGESTFILE ] && echo "digestfile not provided, exiting" && false

echo "Tagging images with alternative registry."
docker tag vertexproject/synapse:${TAG} ${REGISTRY}vertexproject/synapse:${TAG}
docker tag vertexproject/synapse-aha:${TAG} ${REGISTRY}vertexproject/synapse-aha:${TAG}
docker tag vertexproject/synapse-axon:${TAG} ${REGISTRY}vertexproject/synapse-axon:${TAG}
docker tag vertexproject/synapse-cortex:${TAG} ${REGISTRY}vertexproject/synapse-cortex:${TAG}
docker tag vertexproject/synapse-cryotank:${TAG} ${REGISTRY}vertexproject/synapse-cryotank:${TAG}
docker tag vertexproject/synapse-stemcell:${TAG} ${REGISTRY}vertexproject/synapse-stemcell:${TAG}
docker tag vertexproject/synapse-jsonstor:${TAG} ${REGISTRY}vertexproject/synapse-jsonstor:${TAG}

docker push ${REGISTRY}vertexproject/synapse:${TAG}
docker push ${REGISTRY}vertexproject/synapse-aha:${TAG}
docker push ${REGISTRY}vertexproject/synapse-axon:${TAG}
docker push ${REGISTRY}vertexproject/synapse-cortex:${TAG}
docker push ${REGISTRY}vertexproject/synapse-cryotank:${TAG}
docker push ${REGISTRY}vertexproject/synapse-stemcell:${TAG}
docker push ${REGISTRY}vertexproject/synapse-jsonstor:${TAG}

# Record the pushed files
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse:${TAG} > $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-aha:${TAG} >> $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-axon:${TAG} >> $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-cortex:${TAG} >> $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-cryotank:${TAG} >> $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-stemcell:${TAG} >> $DIGESTFILE
docker image inspect --format='{{index .RepoDigests 0}} ${REGISTRY}vertexproject/synapse-jsonstor:${TAG} >> $DIGESTFILE

echo "image digests:"
cat $DIGESTFILE
