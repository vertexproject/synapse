.. _adminguide:

Synapse Admin Guide
###################

This guide is designed for use by Synapse Administrators ("global admins"). Synapse Admins are typically
Synapse power-users with ``admin=true`` privileges on the :ref:`gloss-cortex` who are responsible for
configuration and management of a production instance of Synapse.

The Synapse Admin Guide provides important instructions and background information on topics related to
day-to-day Synapse administrative tasks, and focuses on using :ref:`gloss-storm` to carry out those tasks.

Synapse provides a number of additional methods that can be used to perform some or all of the tasks
described in this guide; however, these methods are **not** covered here. Additional methods include:

- :ref:`stormtypes-libs-header` that allow you to work with a broad range of objects in Synapse.
- Synapse tools that can be used from the host CLI (as opposed to the Storm CLI). Tools are available in
  the `synapse.tools`_ package of the :ref:`apidocs`. The :ref:`userguide` includes documentation on
  some of these :ref:`userguide_tools`.
- The :ref:`http-api`.

.. TIP::

  If you are a commercial Synapse user with the Synapse UI (Optic), see the `UI documentation`_ for
  information on performing Synapse Admin tasks using Optic. Optic simplifies many of Synapse's
  administrative tasks. However, we encourage you to review the information in this guide for
  important background and an overview of the relevant topics.

The Admin Guide is a living document and will continue to be updated and expanded as appropriate. The
current sections are:

.. toctree::
    :titlesonly:

    adminguides/powerups
    adminguides/usersroles
    adminguides/permissions
    adminguides/modelext
    adminguides/mirror

.. _synapse.tools: https://synapse.docs.vertex.link/en/latest/synapse/autodocs/synapse.tools.html
.. _UI documentation: https://synapse.docs.vertex.link/projects/optic/en/latest/index.html
