.. _synapse-docker-images:

Synapse Docker Images
=====================

There are several docker images published for Synapse that can be directly used for testing and deployment. By default,
the images use Python 3.8.


.. note::
    Vertex does **not** publish a ``latest`` tag for any of our Docker repositories. Vertex uses Docker tags based on
    git branch names, git release tags, and dynamic Docker tags that track the latest tagged release.


Application Specific Images
---------------------------
The application specific images contain entry point scripts which launch their respective Synapse application Cells
from the ``/vertex/storage`` directory. The details for these images can be found on Dockerhub:

- `Aha <https://hub.docker.com/repository/docker/vertexproject/synapse-aha>`_
- `Axon <https://hub.docker.com/repository/docker/vertexproject/synapse-axon>`_
- `Cortex <https://hub.docker.com/repository/docker/vertexproject/synapse-cortex>`_
- `Cryotank <https://hub.docker.com/repository/docker/vertexproject/synapse-cryotank>`_

The following images are available::

    # Tags based on Git branches. The Master tag is always available.
    vertexproject/synapse-aha:master
    vertexproject/synapse-axon:master
    vertexproject/synapse-cortex:master
    vertexproject/synapse-cryotank:master

    # Two tag images are shown as an example.
    # Each git tag has an associated docker image made for it.
    vertexproject/synapse-aha:v2.28.1
    vertexproject/synapse-axon:v2.28.1
    vertexproject/synapse-cortex:v2.28.1
    vertexproject/synapse-cryotank:v2.28.1

    # There are major version tags which always track the latest release.
    vertexproject/synapse-aha:v2.x.x
    vertexproject/synapse-axon:v2.x.x
    vertexproject/synapse-cortex:v2.x.x
    vertexproject/synapse-cryotank:v2.x.x


Synapse Image
-------------

The generic Synapse image does not have any Synapse specific application entrypoint defined, executing it will drop a
user into the Python interpreter. The ``-py37`` tags use Python 3.7. It can be found on Dockerhub at
`Synapse <https://hub.docker.com/r/vertexproject/synapse>`_.

The following images are available::

    # Tags based on Git branches. The Master tag is always available.
    vertexproject/synapse:master
    vertexproject/synapse:master-py37

    # Two tag images are shown as an example.
    # Each git tag has an associated docker image made for it.
    vertexproject/synapse:v2.28.1
    vertexproject/synapse:v2.28.1-py37

    # There are major version tags which always track the latest release.
    vertexproject/synapse:v2.x.x
    vertexproject/synapse:v2.x.x-py37


Base Image
----------

The aforementioned images are built off of a base image which contains Python dependencies. This is available in Python
3.7 and Python 3.8 versions. It can be found on Dockerhub at
`Synapse Base Image 3 <https://hub.docker.com/r/vertexproject/synapse-base-image3>`_.

The following images are available::

    vertexproject/synapse-base-image3:py38
    vertexproject/synapse-base-image3:py37

