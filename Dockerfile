# vim:set ft=dockerfile:

# Example Usage
#
# To Build:
#   docker build -t vertexproject/synapse:localdev .
#
# To Run a example Cortex on port 47322:
#   docker run -it -p47322:47322 vertexproject/synapse:localdev
#
# To create and run your own dmon (do not create the dmon dir inside synapse dir)
#   python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon_dir
#   docker run -it -p47322:47322 -v "$(pwd)"/dmon_dir:/syndata/dmon_dir vertexproject/synapse:localdev

FROM vertexproject/synapse-base-image2:py36-v0.1.0-a1

ENV SYN_DMON_LOG_LEVEL="WARNING"
COPY . /root/git/synapse/
RUN set -ex && \
    # Install Synapse
    cd /root/git/synapse && \
    python setup.py develop && \
    # Create a default dmon directory
    mkdir -p /syndata && cd /syndata && \
    python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon

VOLUME /syndata
VOLUME /root/git/synapse
WORKDIR /root/git/synapse
EXPOSE 47322

ENTRYPOINT ["python", "-m", "synapse.tools.dmon", "/syndata/dmon"]
# Optional entry point that can be used to run commands via cron
# See https://github.com/vertexproject/cron-docker-image/tree/master/debian
# for notes on its usage.
# ENTRYPOINT ["/root/git/synapse/synapse/docker/start-cron.sh"]
# Example command:
# docker run --rm -it --entrypoint /root/git/synapse/synapse/docker/start-cron.sh <imagename> "\* \* \* \* \* date >> /var/log/cron.log 2>&1"
