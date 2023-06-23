#!/usr/bin/env bash

##############################################################################
#
# Optionally tag all the images with a new tag.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/retag_all.sh $currentTag $newTag
#
# The first argument is the current tag for the images.
# The second argument is the new iamge tag. If it is not provided, the script
# exits.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

CURRENT_TAG=${1-}
[ ! $CURRENT_TAG ] && echo "current tag not provided, exiting" && false

NEW_TAG=${2-}
[ ! $NEW_TAG ] && echo "new tag not provided, doing nothing" && exit

docker tag vertexproject/synapse:${CURRENT_TAG} vertexproject/synapse:${NEW_TAG}
docker tag vertexproject/synapse-aha:${CURRENT_TAG} vertexproject/synapse-aha:${NEW_TAG}
# docker tag vertexproject/synapse-axon:${CURRENT_TAG} vertexproject/synapse-axon:${NEW_TAG}
# docker tag vertexproject/synapse-cortex:${CURRENT_TAG} vertexproject/synapse-cortex:${NEW_TAG}
# docker tag vertexproject/synapse-cryotank:${CURRENT_TAG} vertexproject/synapse-cryotank:${NEW_TAG}
# docker tag vertexproject/synapse-stemcell:${CURRENT_TAG} vertexproject/synapse-stemcell:${NEW_TAG}
# docker tag vertexproject/synapse-jsonstor:${CURRENT_TAG} vertexproject/synapse-jsonstor:${NEW_TAG}
