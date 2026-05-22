# vim:set ft=dockerfile:
ARG BASE_PYTHON_IMAGE=python:3.14.5-slim-trixie

FROM ${BASE_PYTHON_IMAGE} AS builder

ARG COMMIT

COPY synapse /build/synapse/
COPY pyproject.toml /build/pyproject.toml
COPY scripts/setcommit.py /build/setcommit.py
COPY docker/images/synapse/builder.sh /build/builder.sh

ENV PIP_ROOT_USER_ACTION="ignore"
RUN /build/builder.sh

# This image is only a reference image to use as a base image.
# It does not start any services.
FROM ${BASE_PYTHON_IMAGE} AS default

# Synapse defaults
ENV SYN_LOG_LEVEL="INFO"

# Ensure our usage and downstream usage of pip works and will not cache files.
ENV PIP_NO_CACHE_DIR="1"
ENV PIP_ROOT_USER_ACTION="ignore"

COPY --from=builder /build/dist /build/dist/
COPY docker/images/synapse/bootstrap.sh /build/bootstrap.sh

RUN /build/bootstrap.sh

VOLUME /vertex/storage
