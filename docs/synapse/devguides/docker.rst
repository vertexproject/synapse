Synapse Docker Builds
=====================

This doc details the docker builds and scripts used by Synapse.

Images
------

There are several images provided by the Synapse repository. These are built from an external image that is
periodically updated with core Synapse dependencies.

The images provided include the following:

    vertexproject/synapse
        This container just contains Synapse installed into it. It does not start any services.

    vertexproject/synapse-aha
        This container starts the Aha service.

    vertexproject/synapse-axon
        This container starts the Axon service.

    vertexproject/synapse-cortex
        This container starts the Cortex service.

    vertexproject/synapse-cryotank
        This container starts the Cryotank service.

    vertexproject/synapse-jsonstor
        This container starts the JSONStor service.

    vertexproject/synapse-stemcell
        This container launches the Synapse stemcell server.


Entrypoint Hooks
----------------

Synapse service containers provide two ways that users can modify the container startup process, in order to execute
their own scripts or commands.

A preboot hook can be set by mapping in a file at ``/vertex/preboot/run`` as a executable file. If this file is present,
the file will be executed prior to booting the service.



A concurrent hook can be set by mapping in a file at ``/vertex/concurrent/run`` as a executable file. If this file is
present, the file will be executed as a backgrounded task. This is done prior to starting up the Synapse service.


Building All Images
-------------------

Images are built using Bash scripts. All of the images can be built directly with a single command:

    ::

        $ ./docker/build_all.sh <optional_image_tag>

If the image tag is not provided, it will tag the images with ``:dev_build``.

Building a Specific Application Image
-------------------------------------

A specific application images can be built as well.

    ::

        $ ./docker/build_image.sh <application> <optional_image_tag>

        # Example of building a local Cortex image.

        $ ./docker/build_image.sh cortex my_test_image

If the image tag is not provided, it will tag the image with ``:dev_build``.

Building the ``vertexproject/synapse`` image
--------------------------------------------

The bare image with only Synapse installed on it can be built like the following:

    ::

        $ docker build --pull -t vertexproject/synapse:$TAG -f docker/images/synapse/Dockerfile .

        # Example of building directly with the tag mytag

        $ docker build --pull -t vertexproject/synapse:mytag -f docker/images/synapse/Dockerfile .
