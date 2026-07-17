#!/usr/bin/env bash

##############################################################################
#
# Smoke-test the suite of synapse images.
#
# This is expected to be executed from the root of the synapse directory; eg:
#
# ./docker/scripts/test.sh
#
# The first argument may be provided, which is the tag to test. A default tag
# will be used if one is not provided.
#
##############################################################################

set -e
set -u
set -o pipefail
set -x

TAG=${1:-}

[ -z ${TAG} ] && TAG=3.x.x-dev && echo "Tag not provided, defaulting tag to ${TAG}"

POLL_INTERVAL=2
TIMEOUT=300
CONTAINERS="test-aha test-axon test-cortex test-jsonstor"

stop_all() {
    for CNAME in ${CONTAINERS}; do
        docker stop ${CNAME} >/dev/null 2>&1 || true
    done
}
trap stop_all EXIT

# Up-front sanity check on the synapse base entrypoint.
docker run --rm --entrypoint python vertexproject/synapse:${TAG} -m synapse.servers.cortex --help

# Spin up the service-variant containers.
echo "Spinning up images"
docker run -d --rm --name test-aha -e "SYN_AHA_AHA_NETWORK=synapse.ci" -e "SYN_AHA_DNS_NAME=aha.synapse.ci" vertexproject/synapse-aha:${TAG}
docker run -d --rm --name test-axon vertexproject/synapse-axon:${TAG}
docker run -d --rm --name test-cortex vertexproject/synapse-cortex:${TAG}
docker run -d --rm --name test-jsonstor vertexproject/synapse-jsonstor:${TAG}

# Poll each container until its health check reports a decisive status. Match
# the pattern used by the per-project test scripts in projects/{name}/docker.
for CNAME in ${CONTAINERS}; do
    ELAPSED=0
    DSTATUS=
    while true; do
        DSTATUS=$(docker inspect ${CNAME} --format '{{.State.Health.Status}}')
        echo "[${ELAPSED}s] ${CNAME}: ${DSTATUS}"
        if [[ "${DSTATUS}" != "starting" ]]; then
            break
        fi
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        if [ "${ELAPSED}" -ge "${TIMEOUT}" ]; then
            echo "[!] Timeout after ${TIMEOUT}s waiting for ${CNAME}"
            docker logs ${CNAME} || true
            exit 1
        fi
        sleep ${POLL_INTERVAL}
    done

    docker logs ${CNAME}

    if [ "${DSTATUS}" != "healthy" ]; then
        echo "[!] ${CNAME} reported non-healthy status: ${DSTATUS}"
        exit 1
    fi
done

exit 0
