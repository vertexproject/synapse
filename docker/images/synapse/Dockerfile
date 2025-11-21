# vim:set ft=dockerfile:

# This image is only a reference image to use as a base image.
# It does not start any # services.
FROM python:3.14.0-slim-trixie

ENV SYN_LOG_LEVEL="WARNING"

COPY synapse /build/synapse/synapse
COPY pyproject.toml /build/synapse/pyproject.toml

COPY docker /build/synapse/docker

RUN /build/synapse/docker/images/synapse/bootstrap.sh

VOLUME /vertex/storage
