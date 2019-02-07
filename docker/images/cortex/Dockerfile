# vim:set ft=dockerfile:

# Example Usage
#
# To Build:
#   docker build -t vertexproject/synapse-cortex -f docker/images/cortex/Dockerfile .
#
# To Run a example Cortex on port 27492:
#   docker run -it -p 27492:27492 vertexproject/synapse-cortex

FROM vertexproject/synapse-base-image2:py37

COPY synapse /build/synapse/synapse
COPY setup.py /build/synapse/setup.py
COPY MANIFEST.in /build/synapse/MANIFEST.in

COPY docker/images/cortex/bootstrap.sh /build/synapse/bootstrap.sh
COPY docker/images/cortex/entrypoint.sh /vertex/synapse/entrypoint.sh

RUN /build/synapse/bootstrap.sh

EXPOSE 80
EXPOSE 443
EXPOSE 27492

VOLUME /vertex/cortex
ENV SYN_CORTEX_HOST 0.0.0.0
ENTRYPOINT /vertex/synapse/entrypoint.sh
