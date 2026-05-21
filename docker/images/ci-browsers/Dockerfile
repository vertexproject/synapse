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
# - xvfb entrypoint creation in boostrap.sh
# - node.js package installation pattern in bootstrap.sh
# - xvfb entrypoint configuration in DOCKERFILE

ARG CI_BASE_IMAGE

FROM ${CI_BASE_IMAGE:-vertexproject/synapse-ci:3.x.x-dev}

ENV DISPLAY=":99"

COPY docker/images/ci-browsers /build/ci-browsers

RUN /build/ci-browsers/bootstrap.sh

# Use the xvfb entrypoint
LABEL com.circleci.preserve-entrypoint=true
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/sh"]
