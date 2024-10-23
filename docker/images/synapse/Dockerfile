# vim:set ft=dockerfile:

# This image is only a reference image to use as a base image with
# synapse and its dependencies pre-installed.  It does not start any
# services.

FROM vertexproject/vtx-base-image:dev-py311-10

ENV SYN_LOG_LEVEL="INFO"

COPY synapse /build/synapse/synapse
COPY README.rst /build/synapse/README.rst
COPY pyproject.toml /build/synapse/pyproject.toml

COPY docker/rmlist.txt /build/synapse/rmlist.txt
COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
RUN /build/synapse/bootstrap.sh

VOLUME /vertex/storage
