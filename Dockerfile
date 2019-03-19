# vim:set ft=dockerfile:

# This image is only a reference image to use as a base image with
# synapse and it's dependencies pre-installed.  It does not start any
# services.

FROM vertexproject/synapse-base-image2:py37

ENV SYN_LOG_LEVEL="WARNING"

COPY synapse /build/synapse/synapse
COPY setup.py /build/synapse/setup.py
COPY MANIFEST.in /build/synapse/MANIFEST.in
COPY synapse/docker/start-cron.sh /start-cron.sh

COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
RUN /build/synapse/bootstrap.sh
