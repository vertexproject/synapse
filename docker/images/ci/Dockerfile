# vim:set ft=dockerfile:
ARG TAG
FROM vertexproject/synapse:${TAG:-3.x.x-dev}

# Convenience - disable colors and have pip ignore root user actions by default.
ENV PYTHON_COLORS=0
ENV PIP_ROOT_USER_ACTION=ignore

COPY docker/images/ci /build/ci

RUN /build/ci/bootstrap.sh

# Make additional bin directories for the user and update PATH
RUN mkdir /root/bin && \
    mkdir -p /root/.local/bin

ENV PATH=/root/bin:/root/.local/bin:$PATH
