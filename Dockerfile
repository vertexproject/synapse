# vim:set ft=dockerfile:

# Example Usage
#
# To Build:
#   docker build -t synapse:localdev .
#
# To Run a example Cortex on port 47322:
#   docker run -it -p47322:47322 vertexproject/synapse:localdev
#
# To create and run your own dmon
#   python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon_dir
#   docker run -it -p47322:47322 -v "$(pwd)"/dmon_dir:/syndata/dmon_dir vertexproject/synapse:localdev

FROM vertexproject/synapse-base-image:py36

COPY . /root/git/synapse/
RUN \
    # Install Synapse
    cd /root/git/synapse && \
    python setup.py develop && \
    # Create a default dmon directory
    mkdir -p /syndata && cd /syndata && \
    python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon_dir

VOLUME /syndata
VOLUME /root/git/synapse

ENTRYPOINT ["python", "-m", "synapse.tools.dmon", "/syndata/dmon_dir"]
