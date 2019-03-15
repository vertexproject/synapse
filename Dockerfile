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

FROM vertexproject/synapse-base-image2:py37

ENV SYN_DMON_LOG_LEVEL="WARNING"

COPY synapse /build/synapse/synapse
COPY setup.py /build/synapse/setup.py
COPY MANIFEST.in /build/synapse/MANIFEST.in
COPY synapse/docker/start-cron.sh /start-cron.sh

COPY docker/bootstrap.sh /build/synapse/bootstrap.sh
RUN /build/synapse/bootstrap.sh

# Optional entry point that can be used to run commands via cron
# See https://github.com/vertexproject/cron-docker-image/tree/master/debian
# for notes on its usage.
# ENTRYPOINT ["/start-cron.sh"]
# Example command:
# docker run --rm -it --entrypoint /start-cron.sh <imagename> "\* \* \* \* \* date >> /var/log/cron.log 2>&1"
