# vim:set ft=dockerfile:
ARG TAG
FROM vertexproject/synapse:$TAG

COPY docker/images/axon/entrypoint.sh /vertex/synapse/entrypoint.sh

EXPOSE 4443
EXPOSE 27492

VOLUME /vertex/storage

ENTRYPOINT ["tini", "--", "/vertex/synapse/entrypoint.sh"]

HEALTHCHECK --start-period=10s --retries=1 --timeout=10s --interval=30s CMD python -m synapse.tools.service.healthcheck -c cell:///vertex/storage/
