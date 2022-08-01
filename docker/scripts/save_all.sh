#!/usr/bin/env bash

##############################################################################
#
# Save all the synapse images to a single file.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/save_all.sh
#
# The first argument is the gzip file where images are saved.
# The second argument may be provided, which is the tag to save.
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

OUTFILE=${1}

TAG=${2:-}

[ ! $TAG ] && echo "Tag not provided, defaulting tag to dev_build" && TAG=dev_build

docker save vertexproject/synapse:${TAG} \
            vertexproject/synapse-aha:${TAG} \
            vertexproject/synapse-axon:${TAG} \
            vertexproject/synapse-cortex:${TAG} \
            vertexproject/synapse-cryotank:${TAG} \
            vertexproject/synapse-stemcell:${TAG} \
            vertexproject/synapse-jsonstor:${TAG} | gzip > $OUTFILE