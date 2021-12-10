.. _rapid-powerups:

Rapid Power-Ups
###############

Rapid Power-ups are designed to delivered to a Cortex as Storm packages. This allows users to rapidly expand the power
of their deployments without needing to deploy additional containers to their environments. For a introduction to
Rapid Power-ups and some information about publicly available Power-Ups, see the following
`blog <https://vertex.link/blogs/synapse-power-ups/>`_ post.


Available Rapid Power-Ups
-------------------------

The following Rapid Power-Ups are available:

- `Synapse-AlienVault <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-alienvault/index.html>`_
- `Synapse-Apollo <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-apollo/index.html>`_
- `Synapse-Censys <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-censys/index.html>`_
- `Synapse-Certspotter <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-certspotter/index.html>`_
- `Synapse-Crtsh <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-crtsh/index.html>`_
- `Synapse-Datadog <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-datadog/index.html>`_
- `Synapse-Flashpoint <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-flashpoint/index.html>`_
- `Synapse-Google-CT <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-google-ct/index.html>`_
- `Synapse-Google-Search <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-google-search/index.html>`_
- `Synapse-GreyNoise <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-greynoise/index.html>`_
- `Synapse-HybridAnalysis <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-hybridanalysis/index.html>`_
- `Synapse-Jira <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-jira/index.html>`_
- `Synapse-MISP (Free) <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-misp/index.html>`_
- `Synapse-MITRE ATT&CK (Free) <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-mitre-attack/index.html>`_
- `Synapse-MITRE-CVE <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-mitre-cve/index.html>`_
- `Synapse-PassiveTotal <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-passivetotal/index.html>`_
- `Synapse-Shodan <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-shodan/index.html>`_
- `Synapse-SpyCloud <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-spycloud/index.html>`_
- `Synapse-Tor (Free) <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-tor/index.html>`_
- `Synapse-Twitter <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-twitter/index.html>`_
- `Synapse-URLScan <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-urlscan/index.html>`_
- `Synapse-Utils <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-utils/index.html>`_
- `Synapse-Virustotal <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-virustotal/index.html>`_
- `Synapse-VMRay <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-vmray/index.html>`_
- `Synapse-VXIntel <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-vxintel/index.html>`_
- `Synapse-Whoxy <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-whoxy/index.html>`_
- `Synapse-ZETAlytics <https://commercial.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-zetalytics/index.html>`_


.. _rapid-powerups-getting-started:

Getting Started with Rapid Power-Ups
------------------------------------

Vertex maintains a package repository which allows for loading public and private packages.

If you are a :ref:`synapse-ui` user, you can navigate to the Power-Ups tab to register your Cortex and configure packages
directly from the UI.

Alternatively, one can use the `storm`_ tool can also be used.

First load the ``vertex`` package.

::

    storm> pkg.load https://packages.vertex.link/pkgrepo


Register the Cortex using ``vertex.register``.
This will create an account if one does not exist, and send a magic link to the email address
which can be used to log in.  For additional details run ``vertex.register --help``.

::

    storm> vertex.register <your email>


Once the registration has completed, the available packages can be viewed.

::

    storm> vertex.pkg.list


Storm packages can then be installed using the ``vertex`` package.
For additional details run ``vertex.pkg.install --help``.

::

    storm> vertex.pkg.install <pkgname>


Configuration
-------------

For Power-Ups that require an API key, the ``<pkgname>.setup.apikey`` command can be used
to set the key globally or for the current user, with the latter taking precedence.

Other configuration requirements are detailed in the individual package documentation.

.. _storm: https://synapse.docs.vertex.link/en/latest/synapse/userguides/syn_tools_storm.html