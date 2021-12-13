.. _orch-hashistack:

Hashistack
==========

Hashicorp's Nomad and Consul can be used to run Synapse ecosystem components. We provide a few different examples that
can be used to help get an operations team up off the ground with using that platform for orchestration purposes.

Nomad
-----

Nomad is traditionally used as a job and scheduler, but it may also be used to execute longer running services. The use
of Nomad for running Synapse ecosystem components is fairly straightforward. The main consideration is in making sure
that jobs have persistent storage available to them as necessary.

The following example for running a Cortex has a few items of note.

- The use of a ``constraint`` directive to tie this job to a specific host. In this case, the constraint directive is
  using an AWS instance-id field in order to identify which host the job is supposed to be executed on.
- The docker configuration section maps in the local volume ``/data/vertex/synapse_core0`` to ``/vertex/storage``. This
  is the persistent storage for the Cortex.
- The docker port map names ``telepath`` and ``https`` ports.
- The Cortex service has several boot time configuration options by environment variables, including the default root
  password.
- The ``service`` blocks will be used to do registration with Consul, which will make the Cortex discoverable inside of
  the Nomad cluster, without needing to know hostname/IP or port information for accessing the service.

.. literalinclude:: cortex.hcl
    :language: text

A second example is shown below, this time for the Synapse Shodan Connector, a Storm Service. This example differs
mainly in that it shows how to use a ``cell.yaml`` file to do some boot time configuration.

- First, a ``template`` directive is used to push a YAML file to ``./local/cell.yaml`` when the job is deployed.
- Second, the Docker entrypoint has been replaced with shell script one-liner. This copies the data from
  ``./local/cell.yaml`` and over to ``/vertex/storage/cell.yaml``. This location would be the mapped in persistent
  storage location for the service.
- Last, after copying the file, the shell script launches the service process.
- In addition, this example also shows a place where an authentication username for Docker Hub (our container image
  repository) would be placed into the job file, so that the Docker daemon can retrieve the image.

.. literalinclude:: shodan.hcl
    :language: text

Consul and Telepath
-------------------

The Telepath client is aware of being able to resolve remote service locations via a Consul server. The Telepath
connection string must be formed like the following::

    tcp+consul://<user>:<password>@<service name>/<sharename>?consul=<url_consul_server>&consul_tag=telepath

For example, to connect to the Cortex (assuming the Consul server was available at ``consul.vpc.lan``) you could use
the following example::

    tcp+consul://root:secret@synapse-core01/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath

    # Invoking command from the command line
    python -m synapse.tools.cmdr "tcp+consul://root:secret@synapse-core01/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath"

From this, the Telepath Proxy looks up the ``synapse-core01`` service in the Consul catalog, and retrieves the first
entry from that service which matches the tag ``telepath``. It then uses the IP and Port from the catalog entry in order
to connect to the cortex. Another example would be using this to connect the Shodan service to the cortex::

    # Our Shodan Consul URL
    # tcp+consul://root:secret@synapse-shodan/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath

    # Add the service
    cli> storm service.add shodan "tcp+consul://root:secret@synapse-shodan/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath"
    Executing query at 2020/06/30 15:14:04.446
    added 39fc7c15165291e58a62978ee79e9329 (shodan): tcp+consul://root:secret@synapse-shodan/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath
    complete. 0 nodes in 1 ms (0/sec).

    # List the service
    cli> storm service.list
    Executing query at 2020/06/30 15:14:06.502

    Storm service list (iden, ready, name, url):
        39fc7c15165291e58a62978ee79e9329 True (shodan): tcp+consul://root:secret@synapse-shodan/*?consul=http://consul.vpc.lan:8500&consul_tag=telepath

    1 services
    complete. 0 nodes in 1 ms (0/sec).
