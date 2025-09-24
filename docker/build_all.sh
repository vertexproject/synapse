#!/usr/bin/env bash

##############################################################################
#
# Build and tag the suite of synapse images.
#
# This is expected to be executed from the root of the repository; eg:
#
# ./docker/build_all.sh
#
# The first argument may be provided, including the tag to build.
# A default tag will be used if one is not provided.
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
# set -x # debugging

TAG="${1:-}"
[ -z "${TAG}" ] && echo "Tag not provided, defaulting tag to dev_build" && TAG="dev_build"

declare -a DOCKER_ARGS

# When building locally, a developer can override the base image via
# SYN_BASE_IMAGE="my_awesome_synapse_image" ./docker/build_all.sh
[ -n "${SYN_BUILD_BASE_IMAGE:-}" ] && DOCKER_ARGS+=('--build-arg' "BASE=${SYN_BUILD_BASE_IMAGE}")

# By default the script will always pull the newest base image from the registry.
# This way, once a new base image is updated in the registry, the release
# process will ensure the new base is used. When building locally, a developer
# might want to try a custom base image without uploading it first, and this
# behaviour will lead to a failure. The developer can disable image pulling by
# SYN_BUILD_PULL=0 ./docker/build_all.sh
[ "${SYN_BUILD_PULL:-1}" != "0" ] && DOCKER_ARGS+=('--pull')

# By default the script will disable cache during builds for stable CI
# behaviour. When building locally, a developer might speed things up:
# SYN_BUILD_USE_CACHE=1 ./docker/build_all.sh
[ "${SYN_BUILD_USE_CACHE:-}" != "1" ] && DOCKER_ARGS+=('--no-cache')

# To build locally on post-M1 Mac's with new docker, the following might be required:
# SYN_BUILD_PLATFORM="linux/amd64" ./docker/build_all.sh
[ -n "${SYN_BUILD_PLATFORM:-}" ] && DOCKER_ARGS+=('--platform' "${SYN_BUILD_PLATFORM}")

# Build target images
[ "${SYN_BUILD_USE_CACHE:-}" != "1" ] && docker builder prune --all --force

docker buildx build \
  "${DOCKER_ARGS[@]}" \
  --progress plain \
  --tag "vertexproject/synapse:${TAG}" \
  --file docker/images/synapse/Dockerfile \
  --load \
  .

docker/build_image.sh aha "${TAG}"
docker/build_image.sh axon "${TAG}"
docker/build_image.sh cortex "${TAG}"
docker/build_image.sh cryotank "${TAG}"
docker/build_image.sh jsonstor "${TAG}"
docker/build_image.sh stemcell "${TAG}"
