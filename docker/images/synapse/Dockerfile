# vim:set ft=dockerfile:

# This image is only a reference image to use as a base image with
# synapse and its dependencies pre-installed.  It does not start any
# services.

FROM vertexproject/vtx-base-image:py311

ENV SYN_LOG_LEVEL="INFO"

COPY synapse /build/synapse/synapse
COPY setup.py /build/synapse/setup.py
COPY MANIFEST.in /build/synapse/MANIFEST.in

COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
RUN /build/synapse/bootstrap.sh

VOLUME /vertex/storage
