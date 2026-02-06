# vim:set ft=dockerfile:

# MIT License
#
# Copyright (c) 2019 Circle Internet Services, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Items coveraed by the MIT License include:
# - Several packages installed in bootstrap.sh
# - Additional bin directories and PATH manipulation in DOCKERFILE

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
