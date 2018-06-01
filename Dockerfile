# vim:set ft=dockerfile:

# To Build:
#   docker build -t synapse:localdev .

# To Run:
#   docker run -it -p 47322:47322 synapse:localdev

FROM vertexproject/synapse-base-image:py36

# Copy Synapse Code
COPY . /root/git/synapse/

RUN cd /root/git/synapse && \
    # Install Synapse
    python setup.py develop && \
    # Create Dmon directory
    mkdir -p /syndata && cd /syndata && \
    python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core core_dmon_dir

VOLUME /syndata
VOLUME /root/git/synapse

EXPOSE 47322
ENTRYPOINT ["python", "-m", "synapse.tools.dmon", "/syndata/core_dmon_dir"]
