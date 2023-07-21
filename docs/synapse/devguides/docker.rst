.. _dev_docker_builds:

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

        $ docker build --progress plain --pull -t vertexproject/synapse:$TAG -f docker/images/synapse/Dockerfile .

        # Example of building directly with the tag mytag

        $ docker build --progress plain --pull -t vertexproject/synapse:mytag -f docker/images/synapse/Dockerfile .

.. _dev_docker_working_with_images:

Working with Synapse Images
---------------------------

Developers working with Synapse images should consider the following items:

* The Synapse images are not locked to a specific Python version. The
  underlying Python minor version or base distribution may change. If they do
  change, that will be noted in the Synapse changelog. If you are building
  containers off of a floating tag such as ``vertexproject/synapse:v2.x.x``,
  make sure you are reviewing our :ref:`changelog` for items which may affect
  your use cases. Python patch level updates will not be included in
  the changelogs.

* The ``synapse`` package, and supporting packages, are currently installed
  to the distribution Python environment. The version of ``pip`` installed in
  the containers is PEP668_ aware. If you are installing your own Python
  packages to the distribution Python environment with ```pip``, you will
  need to add the ``--break-system-packages`` argument::

    python -m pip install --break-system-packages yourTargetPackage

.. _dev_docker_verification:

Verifying container image signatures
------------------------------------

Synapse docker images which are release tagged ( e.g. ``v2.1.3`` or
``v2.x.x`` ) are accompanied with cosign_ signatures which can be used to
assert that the image was produced by The Vertex Project. Branch builds, such
as development ``master`` tags are not guaranteed to be signed.

You can use the Python script ``synapse.tools.docker.validate`` to confirm
that a given image has a ``cosign`` signature which was signed by a Vertex Project
code signing certificate; and then confirm that the ``cosign`` signature was signed
by the certificate. This does require having ``cosign`` version v2.x.x available.

The following shows an example of verifying a signed image, referenced by its registry
content hash::

    $ python -m synapse.tools.docker.validate vertexproject/synapse@sha256:4ec5d97e1bbdb49971f5c1d520a81371021ef4c84f932d9ef23a635a099cb53b
    Verifying: vertexproject/synapse@sha256:4ec5d97e1bbdb49971f5c1d520a81371021ef4c84f932d9ef23a635a099cb53b
    Using Cosign with GitVersion:    v2.1.0
    Loading certdir from /your/python/site-lib/synapse/synapse/data/certs
    Verified certificate embedded in the signature.
    Cosign output:
    [{'critical': {'identity': {'docker-reference': 'index.docker.io/vertexproject/synapse'},
                   'image': {'docker-manifest-digest': 'sha256:4ec5d97e1bbdb49971f5c1d520a81371021ef4c84f932d9ef23a635a099cb53b'},
                   'type': 'cosign container image signature'},
      'optional': {'Subject': '',
                   'commit': '07ab34bbeb04cf0e96e7ba7b65c5a7d7baeda151',
                   'jobid': '9b78fab5-d364-43b3-8fb0-3f0c82a795cd'}}]
    Verified: vertexproject/synapse@sha256:4ec5d97e1bbdb49971f5c1d520a81371021ef4c84f932d9ef23a635a099cb53b

Devops teams can use this tool_ as the basis to create or update an admissions
controller that can ensure that only signed images are allowed to be used in
their environments.

.. _PEP668: https://peps.python.org/pep-0668/
.. _cosign: https://www.sigstore.dev/
.. _tool: https://github.com/vertexproject/synapse/blob/master/synapse/tools/docker/validate.py
