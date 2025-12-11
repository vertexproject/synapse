#!/usr/bin/env bash

##############################################################################
# Docker image check script.
#
# Uses several tools ( trivy / grype / docker scout ) to generate reports for
# CVEs which may be present in a docker image.
# By default, this will pull the latest vertexproject/synapse:master image
# to check, and compare it against the previous stable release image.
#
# A single parameter ( a image name ) can be provided to check an arbitrary
# image. Example:
#
# ./scripts/image_check.sh vertexproject/synapse-foobar:master
#
# A second parameter ( a second image name ) can be provided to compare the
# first image to the second with docker scout compare. This will only compare
# the two images if the they have the same repo. Example:
#
# ./scripts/image_check.sh vertexproject/synapse-foobar:master vertexproject/synapse-foobar:v1.2.3
#
##############################################################################

set -e # exit on nonzero
set -u # undefined variables
set -o pipefail # pipefail propagate error codes
set -x # debugging

CHECK_IMAGE=${1:-vertexproject/synapse:master}
REFERENCE_IMAGE=${2:-vertexproject/synapse:v2.x.x}

docker pull $CHECK_IMAGE

docker scout cves --only-severity high,critical $CHECK_IMAGE
trivy image --ignore-status will_not_fix --severity HIGH,CRITICAL $CHECK_IMAGE
grype --ignore-states wont-fix $CHECK_IMAGE  | grep -iv negligible

IFS=':' read -ra CHECK_PREFIX <<< $CHECK_IMAGE
IFS=':' read -ra REFERENCE_PREFIX <<< $REFERENCE_IMAGE

if [ ${CHECK_PREFIX[0]} == ${REFERENCE_PREFIX[0]} ]
  then
    echo "Checking ${CHECK_IMAGE} vs reference image ${REFERENCE_IMAGE}."
    docker pull $REFERENCE_IMAGE
    docker scout compare --to $REFERENCE_IMAGE $CHECK_IMAGE
fi
