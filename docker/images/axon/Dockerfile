# vim:set ft=dockerfile:

# Example Usage
#
# To Build:
#   docker build -t vertexproject/synapse-axon -f docker/images/axon/Dockerfile .

FROM vertexproject/synapse-base-image2:py37

COPY synapse /build/synapse/synapse
COPY setup.py /build/synapse/setup.py
COPY MANIFEST.in /build/synapse/MANIFEST.in

COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
COPY docker/images/axon/entrypoint.sh /vertex/synapse/entrypoint.sh

RUN /build/synapse/bootstrap.sh

EXPOSE 4443
EXPOSE 27492

VOLUME /vertex/storage

ENTRYPOINT /vertex/synapse/entrypoint.sh
