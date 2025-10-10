#!/usr/bin/env bash

##############################################################################
#
# Build and tag a specific synapse image.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/build_image.sh cortex
#
# The first argument is the server (in docker/images) to build.
# A second argument may be provided, including the tag to build.
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
# set -x # debugging

IMAGE="${1:-}"
if [ "${IMAGE}" == "synapse" ]
then
    echo "The vertexproject/synapse image is not built with this script."
    false
fi

IMAGE_DIR="docker/images/${IMAGE}"
[ ! -d "${IMAGE_DIR}" ] && echo "${IMAGE_DIR} does not exist." && false

TAG="${2:-}"
[ -z "${TAG}" ] && echo "Tag not provided, defaulting tag to dev_build" && TAG="dev_build"

declare -a DOCKER_ARGS

# When building locally, a developer can override the base image via
# SYN_BUILD_BASE_IMAGE="my_awesome_synapse_image" ./docker/build_image.sh cortex
[ -n "${SYN_BUILD_BASE_IMAGE:-}" ] && DOCKER_ARGS+=('--build-arg' "BASE=${SYN_BUILD_BASE_IMAGE}")

# By default the script will always pull the newest base image from the registry.
# This way, once a new base image is updated in the registry, the release
# process will ensure the new base is used. When building locally, a developer
# might want to try a custom base image without uploading it first, and this
# behaviour will lead to a failure. The developer can disable image pulling by
# SYN_BUILD_PULL=0 ./docker/build_image.sh cortex
[ "${SYN_BUILD_PULL:-1}" != "0" ] && DOCKER_ARGS+=('--pull')

# By default the script will disable cache during builds for stable CI
# behaviour. When building locally, a developer might speed things up:
# SYN_BUILD_USE_CACHE=1 ./docker/build_image.sh cortex
[ "${SYN_BUILD_USE_CACHE:-}" != "1" ] && DOCKER_ARGS+=('--no-cache')

# To build locally on post-M1 Mac's with new docker, the following might be required:
# SYN_BUILD_PLATFORM="linux/amd64" ./docker/build_image.sh cortex
[ -n "${SYN_BUILD_PLATFORM:-}" ] && DOCKER_ARGS+=('--platform' "${SYN_BUILD_PLATFORM}")

# Build target image
echo "Building from docker/images/${IMAGE}/Dockerfile"
[ "${SYN_BUILD_USE_CACHE:-}" != "1" ] && docker builder prune --all --force

docker buildx build  \
    "${DOCKER_ARGS[@]}" \
    --progress plain \
    --tag "vertexproject/synapse-${IMAGE}:${TAG}" \
    --file "docker/images/${IMAGE}/Dockerfile" \
    --load \
    .
