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

An exemplar dmon configuration file is located at synapse/docker/cortex/sqlite_dmon.json::

    $ python3 -m synapse.tools.dmon synapse/docker/cortex/sqlite_dmon.json

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

        $ docker build -t vertexproject/synapse -f <synapse_dir>/synapse/docker/synapse_dockerfile <synapse_dir>

- volumes
    - /syndata is exposed by default

- ports
    - no ports are exposed by default

Cortex image - Postgresql
~~~~~~~~~~~~~~~~~~~~~~~~~
This image will provide a synapse daemon config driven cortex backed into a postgres(9.5) database
by default.
It is the general image used for experimentation as it can also be easily configured to start
additional Cortexes with alternate storage backings as well.  By default each Cortex image is
configured to expose a Cortex object.

- build
    ::

        $ docker build -t vertexproject/core_pg -f <synapse_dir>/synapse/docker/cortex/postgres_9.5_dockerfile <synapse_dir>

- volumes
    - /syndata
    - /var/lib/postgresql/data for postgres data
- ports
    - 47322 - listener in the default /syndata/dmon.json
    - 5432 - for postgres
- use
    - /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup::

        $ docker run vertexproject/core_pg

Start Docker Cortex
~~~~~~~~~~~~~~~~~~~
Start a container using the Posgresql Cortex image just created::

    $ docker run vertexproject/core_pg

General Cortex Use
##################
Connecting to a Cortex will be a variant of::

    import synapse.telepath as s_telepath

    host = '172.17.0.2'
    port = 47322

    core = s_telepath.openurl( 'tcp:///core', host=host, port=port)

At this point 'core' is a proxy object to the Cortex being shared by the Synapse daemon running in the Docker container.

The normal Cortex apis can now be called::

    # make sure proxy is working normally...
    # this should return *something*
    forms = core.getTufosByProp('syn:core')

    # create an fqdn and store it
    fqdn = 'woot.com'
    new_tufo = core.formTufoByProp('fqdn', fqdn)

    # retrieve the shiny new fqdn
    ret_tufo = core.getTufosByProp('fqdn', fqdn)[0]

    print('formed, stored and retrieved a form: %r' % (new_tufo[0] == ret_tufo[0],))

Other Cortex Docker images
--------------------------
The other Docker images listed below are simpler examples of running a more basic Cortex without Postgresql.

core_ram
########
Provides a synapse daemon config driven cortex backed into ram.

- build
    ::

        $ docker build -t vertexproject/core_ram -f <synapse_dir>/synapse/docker/cortex/ram_dockerfile <synapse_dir>

- volumes
    - /syndata

- ports
    - 47322 - listener in the default /syndata/dmon.json

- use
    - /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup

    ::

        $ docker run vertexproject/core_ram

core_sqlite
###########
Provides a synapse daemon config driven cortex backed into a sqlite database by default.

- build
    ::

        $ docker build -t vertexproject/core_sqlite -f <synapse_dir>/synapse/docker/cortex/sqlite_dockerfile <synapse_dir>

- volumes
    - /syndata

- ports
    - 47322 - listener in the default /syndata/dmon.json

- use
    - /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup

    ::

        $ docker run vertexproject/core_sqlite

