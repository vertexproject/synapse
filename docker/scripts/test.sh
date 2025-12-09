#!/usr/bin/env bash

##############################################################################
#
# Test the suite of synapse images
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/scripts/test_all.sh
#
# The first argument may be provided, which is the tag to test.
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

TAG=${1:-}

[ -z ${TAG} ] && TAG=3.x.x-dev && echo "Tag not provided, defaulting tag to ${TAG}"

# Spin up our containers
echo "Spinning up images"

docker run --rm -it --entrypoint python vertexproject/synapse:${TAG} -m synapse.servers.cortex --help
dstatus00=$?
if [ $dstatus00 != "0" ]; then exit 1; fi
docker run --rm -d --name test-aha -e "SYN_AHA_AHA_NETWORK=synapse.ci" vertexproject/synapse-aha:${TAG}
docker run --rm -d --name test-axon vertexproject/synapse-axon:${TAG}
docker run --rm -d --name test-cortex vertexproject/synapse-cortex:${TAG}
docker run --rm -d --name test-jsonstor vertexproject/synapse-jsonstor:${TAG}

# Let them run and allow health checks to fire
DELAY=45
echo "Sleeping ${DELAY} seconds.."
sleep ${DELAY}

echo "Docker information"

docker container ls -a

docker logs test-aha
docker logs test-axon
docker logs test-cortex
docker logs test-jsonstor

dstatus01=`docker inspect test-aha --format '{{.State.Health.Status}}'`
dstatus02=`docker inspect test-axon --format '{{.State.Health.Status}}'`
dstatus03=`docker inspect test-cortex --format '{{.State.Health.Status}}'`
dstatus04=`docker inspect test-jsonstor --format '{{.State.Health.Status}}'`

docker stop test-aha
docker stop test-axon
docker stop test-cortex
docker stop test-jsonstor

if [ $dstatus01 != "healthy" ]; then exit 1; fi
if [ $dstatus02 != "healthy" ]; then exit 1; fi
if [ $dstatus03 != "healthy" ]; then exit 1; fi
if [ $dstatus04 != "healthy" ]; then exit 1; fi

exit 0
