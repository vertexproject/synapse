# vim:set ft=dockerfile:
FROM vertexproject/synapse-base-image:py36

ENV SYN_DMON_LOG_LEVEL="WARNING"

COPY . /root/git/synapse
RUN mkdir /syndata \
 && cd /root/git/synapse && python setup.py install \
 && cp synapse/docker/cortex/ram_dmon.json /syndata/dmon.json

VOLUME /syndata
VOLUME /root/git/synapse

WORKDIR /root/git/synapse
EXPOSE 47322
ENTRYPOINT ["python", "-m", "synapse.tools.dmon", "/syndata/dmon.json"]
