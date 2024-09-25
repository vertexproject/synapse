# vim:set ft=dockerfile:
FROM vertexproject/vtx-base-image:dev-py311-10

COPY synapse /build/synapse/synapse
COPY README.rst /build/synapse/README.rst
COPY pyproject.toml /build/synapse/pyproject.toml

COPY docker/rmlist.txt /build/synapse/rmlist.txt
COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
COPY docker/images/aha/entrypoint.sh /vertex/synapse/entrypoint.sh

RUN /build/synapse/bootstrap.sh

EXPOSE 4443
EXPOSE 27492

VOLUME /vertex/storage

ENTRYPOINT ["tini", "--", "/vertex/synapse/entrypoint.sh"]

HEALTHCHECK --start-period=10s --retries=1 --timeout=10s --interval=30s CMD python -m synapse.tools.healthcheck -c cell:///vertex/storage/
