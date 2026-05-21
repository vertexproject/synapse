
.. _synapse_powerups:

Synapse Power-Ups
#################

Power-Ups are part of `The Vertex Project <https://vertex.link>`_'s commercial offering, Synapse Enterprise. Synapse Enterprise is an on-premises solution that includes `Optic (the Synapse UI) <https://synapse.docs.vertex.link/projects/optic/en/latest/index.html>`_ and all of the Power-Ups. The license includes unlimited users and does not limit the amount of data or number of instances you deploy. We take a white-glove approach to each deployment where we're with you every step of the way from planning deployment sizes to helping to train your analysts.

Feel free to `contact us <https://vertex.link/contact-us>`_ or `request a demo instance <https://vertex.link/request-a-demo>`_.

Power-Ups provide specific add-on capabilities to Synapse via Storm Packages and Services. For example, Power-Ups may
provide connectivity to external databases, third-party data sources, or enable functionality such as the ability to
manage YARA rules, scans, and matches.

For an introduction to Power-Ups from our analysts and seeing them in use, see the following video introducing them:

.. raw:: html

   <iframe width="560" height="315" src="https://www.youtube.com/embed/eb6wEYGRTyY" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

The Vertex Project is constantly releasing new Power-Ups and expanding features of existing Power-Ups. If you join the
``#synapse-releases`` channel in Synapse `Slack`_, you can get realtime notices of these updates!

.. _rapid-powerups:

Rapid Power-Ups
===============

Rapid Power-Ups are delivered to a Cortex as Storm packages directly, without requiring any additional containers to
be deployed. This allows users to rapidly expand the power of their Synapse deployments without needing to engage with
additional operations teams in their environments. For an introduction to Rapid Power-Ups and some information about
publicly available Power-Ups, see the following `blog <https://vertex.link/blogs/synapse-power-ups/>`_ post.

See the `Rapid Power-Ups List <https://synapse.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/index_packages.html>`_ for
a complete list of all available Rapid Power-Ups.

Getting Started with Rapid Power-Ups
------------------------------------

Vertex maintains a package repository which allows for loading public and private packages.

If you are a :ref:`synapse-ui` user, you can navigate to the **Power-Ups Tool** to register your Cortex and configure packages.

Alternatively, one can use the :ref:`syn-tools-storm` tool to get started with Rapid Power-Ups in their Cortex.

See our `blog article <https://vertex.link/blogs/synapse-power-ups/>`_ for a step-by step guide to registering your
Cortex to install the free ``synapse-misp``, ``synapse-mitre-attack``, and ``synapse-tor`` Power-Ups.

.. _advanced-powerups:

Advanced Power-Ups
==================

Advanced Power-Ups are enhancements to a Cortex which require the deployment of additional containers in order to run
their services.

Documentation for specific Advanced Power-Ups can be found here:

- `Synapse Backup <https://synapse.docs.vertex.link/projects/backup/en/latest/>`_
- `Synapse Fileparser <https://synapse.docs.vertex.link/projects/fileparser/en/latest/>`_
- `Synapse Maxmind <https://synapse.docs.vertex.link/projects/maxmind/en/latest/>`_
- `Synapse GCS <https://synapse.docs.vertex.link/projects/gcs/en/latest/>`_
- `Synapse Metrics <https://synapse.docs.vertex.link/projects/metrics/en/latest/>`_
- `Synapse Nettools <https://synapse.docs.vertex.link/projects/nettools/en/latest/>`_
- `Synapse NSRL <https://synapse.docs.vertex.link/projects/nsrl/en/latest/>`_
- `Synapse Playwright <https://synapse.docs.vertex.link/projects/playwright/en/latest/>`_
- `Synapse S3 <https://synapse.docs.vertex.link/projects/s3/en/latest/>`_
- `Synapse Search <https://synapse.docs.vertex.link/projects/search/en/latest/>`_
- `Synapse Sidepocket <https://synapse.docs.vertex.link/projects/sidepocket/en/latest/>`_
- `Synapse Swarm <https://synapse.docs.vertex.link/projects/swarm/en/latest/>`_
- `Synapse Yara <https://synapse.docs.vertex.link/projects/yara/en/latest/>`_
- `Synapse Axon Azure <https://synapse.docs.vertex.link/projects/axon-azure/en/latest/>`_

.. _video: https://vimeo.com/595344430
.. _Slack: https://v.vtx.lk/join-slack
