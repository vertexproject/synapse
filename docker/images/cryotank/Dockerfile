# vim:set ft=dockerfile:
FROM synbuild:base

COPY docker/images/cryotank/entrypoint.sh /vertex/synapse/entrypoint.sh

EXPOSE 4443
EXPOSE 27492

ENTRYPOINT ["tini", "--", "/vertex/synapse/entrypoint.sh"]

HEALTHCHECK --start-period=10s --retries=1 --timeout=10s --interval=30s CMD python -m synapse.tools.healthcheck -c cell:///vertex/storage/
