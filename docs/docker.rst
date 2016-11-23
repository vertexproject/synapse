
Synapse + Docker
================

Synapse docker images are based on Ubuntu 16.04

synapse
-------
    This image is intended to serve 2 functions

    1. Provide a simple sandbox to get started with synapse
    2. Base image to facilitate building other synapse ecosystem images

    build::

        $ docker build -t vertexproject/synapse -f <synapse_dir>/synapse/docker/synapse_dockerfile <synapse_dir> 
    
    volumes
      - /syndata is exposed by default

    ports
      - no ports are exposed by default

    use::

        $ docker run -it vertexproject/synapse /bin/bash

cortex docker images
====================
Basic synapse dmon config driven cortices that expose a cortex object

connecting to any of the cortices below will be a variant of::

    import synapse.telepath as s_telepath

    host = '172.17.0.2'
    port = 47322

    core = s_telepath.openurl( 'tcp:///core', host=host, port=port)

At this point 'core' is a proxy object to the cortex being shared by the synapse daemon running in the docker container.

The normal cortex apis can now be called::

    # make sure proxy is working normally...
    # this should return *something*
    forms = core.getTufosByProp('syn:core')

    # create an fqdn and store it
    fqdn = 'woot.com'
    new_tufo = core.formTufoByProp('fqdn', fqdn)
    
    # retrieve the shiny new fqdn
    ret_tufo = core.getTufosByProp('fqdn', fqdn)[0]

    print('formed, stored and retrieved a form: %r' % (new_tufo[0] == ret_tufo[0],))
    

core_ram
--------
    Provides a synapse daemon config driven cortex backed into ram.

    build::

        $ docker build -t vertexproject/core_ram -f <synapse_dir>/synapse/docker/cortex/ram_dockerfile <synapse_dir>

    volumes
        - /syndata is still available

    ports
        - 47322 - listener in the default /syndata/dmon.json

    use
        /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup
        ::

        $ docker run vertexproject/core_ram 

core_sqlite
-----------
    Provides a synapse daemon config driven cortex backed into a sqlite database by default.

    build::

        $ docker build -t vertexproject/core_sqlite -f <synapse_dir>/synapse/docker/cortex/sqlite_dockerfile <synapse_dir>

    volumes
        - /syndata is still available

    ports
        - 47322 - listener in the default /syndata/dmon.json

    use
        /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup
        ::

        $ docker run vertexproject/core_sqlite

core_pg
-------
    Provides a synapse daemon config driven cortex backed into a postgres(9.5) database by default.

    build::

        $ docker build -t vertexproject/core_pg -f <synapse_dir>/synapse/docker/cortex/postgres_9.5_dockerfile <synapse_dir>

    volumes
        - /syndata is still available
        - /var/lib/postgresql/data for postgres data

    ports
        - 47322 - listener in the default /syndata/dmon.json
        - 5432 - for postgres

    use
        /syndata/dmon.json is the synapse dmon conf file used by the image.  This can be modified or mapped in at container startup
        ::

        $ docker run vertexproject/core_pg


servicebus
-----------------
    #TODO
