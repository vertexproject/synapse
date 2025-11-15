# vim:set ft=dockerfile:

# This image is only a reference image to use as a base image with
# synapse and its dependencies pre-installed.  It does not start any
# services.
#FROM vertexproject/vtx-base-image:py314
FROM python:3.14.0-slim-bookworm

ENV SYN_LOG_LEVEL="WARNING"

COPY synapse /build/synapse/synapse
COPY pyproject.toml /build/synapse/pyproject.toml

COPY docker /build/synapse/docker

RUN /build/synapse/docker/images/synapse/bootstrap.sh

VOLUME /vertex/storage
