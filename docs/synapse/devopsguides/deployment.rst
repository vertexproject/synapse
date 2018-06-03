Synapse Deployment Scenarios
============================

Hardware
--------
Currently Synapse may be run either natively or in a docker container.  Both options will be covered.
If performance is a consideration in testing please do not use a virtual machine and make sure
the resources allocated are appropriate for the performance needed.

Experimental Hardware
#####################
For an experimental setup we recommend at least 8GB ram and several terabytes of disk space.
Performance of the Synapse Hypergraph will drop considerably if the hardware resources are
out paced by the data being loaded.

Install
-------
Ubuntu 16.04 LTS is the recommended platform for installation. Installation via Docker is also
supported. Synapse is available at the following places:

    #. PyPi https://pypi.python.org/pypi/synapse
    #. Github https://github.com/vertexproject/synapse
    #. DockerHub https://hub.docker.com/r/vertexproject/synapse/

Ubuntu
######
Install the following prerequisites prior to using Synapse::

    $ sudo apt update

    $ sudo apt install -yq build-essential libffi-dev libssl-dev python3 python3-dev python3-pip python3-setuptools

    $ sudo -H pip3 install --upgrade pip setuptools wheel

The following commands assume your Synapse checkout will be in '~/synapse'::

    $ cd ~/
    $ sudo apt install unzip wget
    $ wget https://github.com/vertexproject/synapse/archive/master.zip
    $ unzip master.zip
    $ mv synapse-master synapse
    $ cd synapse
    $ sudo python3 setup.py develop

An exemplar dmon configuration file can be generated using the deploy tool::

    $ python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon_dir
    $ python -m synapse.tools.dmon dmon_dir

Docker
######
Synapse docker images are also based on Ubuntu 16.04 and install all relevant dependencies.

Unless otherwise stated Synapse tracks the latest stable release of Docker engine for Ubuntu 16.04
LTS.

General steps:

#. Create base Synapse image
#. Create a Postgresql backed Cortex image
#. Start Synapse

Synapse image
~~~~~~~~~~~~~
This image is intended to serve 2 functions

#. Provide a simple sandbox to get started with synapse
#. Base image to facilitate building other synapse ecosystem images

- build
    ::
        $ docker build -t vertexproject/synapse:localdev <synapse_dir>

- run a core on port 43722 (ephemeral storage)
    ::
        $ docker run -it -p47322:47322 vertexproject/synapse:localdev

- generate a dmon dir and map it in
    ::
        $ python -m synapse.tools.deploy --listen tcp://0.0.0.0:47322 cortex core dmon_dir
        $ docker run -it -p47322:47322 -v "$(pwd)"/dmon_dir:/syndata/dmon_dir vertexproject/synapse:localdev

- volumes
    - ``/root/git/synapse`` and ``/syndata`` are exposed by default

- ports
    - no ports are exposed by default
