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

NO_PRUNE=0
ONLY_BASE=0

# Parse optional flags before the positional TAG argument
while [ $# -gt 0 ]; do
  case "$1" in
    --no-prune)
      NO_PRUNE=1
      shift
      ;;
    --only-base)
      ONLY_BASE=1
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1"
      echo "Usage: $(basename $0) [--no-prune] [--only-base] [TAG]"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

TAG=${1:-}

[ -z ${TAG} ] && TAG=3.x.x-dev && echo "Tag not provided, defaulting tag to ${TAG}"

# Build target images. The builder cache prune is skipped when --no-prune is set
# so callers can integrate this script into iterative workflows without losing
# their BuildKit cache on every invocation.
if [ ${NO_PRUNE} -eq 0 ]; then
  docker builder prune -a -f
fi

BUILDARGS="--build-arg TAG=${TAG}"

COMMIT_ARGS=""
if command -v git > /dev/null 2&>1; then
  if COMMIT=$(git rev-parse HEAD 2> /dev/null); then
    COMMIT_ARGS="--build-arg COMMIT=$COMMIT"
  else
    echo "Failed to get current git commit."
  fi
fi

echo "Using $COMMIT_ARGS"

docker build --no-cache -t vertexproject/synapse:$TAG ${BUILDARGS} ${COMMIT_ARGS} --progress=plain -f docker/images/synapse/Dockerfile .

# The service variant images are not required by downstream advanced power-up
# builds; --only-base allows callers to build just the synapse base image.
if [ ${ONLY_BASE} -eq 0 ]; then
  docker build --no-cache -t vertexproject/synapse-aha:$TAG ${BUILDARGS} -f docker/images/aha/Dockerfile .
  docker build --no-cache -t vertexproject/synapse-axon:$TAG ${BUILDARGS} -f docker/images/axon/Dockerfile .
  docker build --no-cache -t vertexproject/synapse-cortex:$TAG ${BUILDARGS} -f docker/images/cortex/Dockerfile .
  docker build --no-cache -t vertexproject/synapse-jsonstor:$TAG ${BUILDARGS} -f docker/images/jsonstor/Dockerfile .
fi
