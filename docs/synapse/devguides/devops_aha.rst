.. _devops-aha:

Aha Service Discovery
=====================

The Aha service discovery is a native Synapse tool and protocol for doing
service discovery when multiple Synapse services are being deployed in a
environment. This page covers what how Aha works, what services the AhaCell
provides, and demonstrates a Cortex configuration using Aha.

How Aha Works
-------------

The Aha protocol is very simple. From a high level, the Aha service runs in a
standalone, mirror, or clustered mode of operation.

- A Synapse service built from a Cell (a Cortex, a Axon, a Storm Service, etc)
  can be configured to register itself with the Aha service with a given name.
- The Aha service stores the connection information from the Cell. By default,
  this is remote IP and and Telepath listening port.
- When a service or client wants to connect to a service for that name, it
  will connect the Aha server, lookup the name, and get back the connection
  information.
- The client will then make the actual Telepath connection using the connection
  information provided by the Aha server.

Configuring A Cell
------------------

There are several configuration options to setup on a Cell when deploying it
with Aha.

``aha:name``
    The name of the Cell to register itself as. This should be unique within
    a given Aha network. This is **required** for Aha registration to work.

``aha:registry``
    This is a string, or list of strings, representing Telepath URLs for the
    Aha servers the cell should register itself as. This is **required** for
    Aha registration to work.

``aha:network``
    The Aha network name used to register the Cell under. This acts like a
    namespace.

``aha:leader``
    If this is configured, and the Cell is active (a leader in a mirror or
    clustered deployement), it will also register itself with the Aha server
    with the name.

One of the following two configuration values must be set as well:

``dmon:listen``
    This is a string defining the Telepath listener. This takes takes
    precedence over any configured ``SYN_<cell>_TELEPATH`` values. The scheme
    will be used to dictate what scheme clients should use to connect to the
    Cell. The port value that the listener binds too will be the value that
    is given to the Aha service for clients to connect to. If the port value
    is zero (``0``), then an ephemeral port will be bound and used.

``aha:svcinfo``
    The ``svcinfo`` data can be used to provide the entire structure of the
    Telepath information that a client may use to connect to the service. This
    can include host, port, scheme, and other connection options. This allows
    the definition of a explicit host name, port, and scheme that can be used
    to connect to the service.  For example this could look like the following::

        aha:svcinfo:
          urlinfo:
            host: core.demo.net
            port: 30000
            schema: ssl
            ca: demonet

    This information is used by the Aha server instead of pulling port numbers,
    scheme and IP information dynamically.


Using Aha with Synapse Clients
------------------------------

Synapse clients which need to use ``aha://`` connections need to know how to
connect to the Aha server. This can be accomplished by loading a
``telepath.yaml`` file. This file contains locations of Aha servers that a
client may connect to in order to resolve names for. For example:

  ::

    $ cat ~/.syn/telepath.yaml
    version: 1
    aha:servers:
      - - tcp://demouser:demopass@aha.demo.link:8081/
      - - ssl://demo@0.aha.demo.net:33391/
        - ssl://demo@1.aha.demo.net:33391/
        - ssl://demo@2.aha.demo.net:33391/
    certdirs:
      - /home/user/special/certdir

This defines two sets of Aha servers and a list of additional certificate
directories. When this file is loaded via ``synapse.telepath.loadTeleEnv()``,
it registers the lists of Aha servers and list of certificate directories with
the Synapse process, and returns a callback function which will remove those
directories from the process.

In the above example, two sets of Aha servers are registered, and a additional
certificate directory.

Bootstrapping An Aha Environment
--------------------------------

The following shows an example of bootstrapping a local Aha instance, configuring a machine user and a client user
for it, adding a Cortex to the network and then connecting to the Cortex via Aha.

Start an Aha service:

    ::

        SYN_AHACELL_AHA_URLS=tcp://127.0.0.1:8081 SYN_AHACELL_DMON_LISTEN=tcp://0.0.0.0:8081 \
        SYN_AHACELL_AUTH_PASSWD=root python -m synapse.servers.aha cells/ahatcp

Add a user to the Aha service. There needs to be a user that a Cell can use to
connect and register itself to to the Aha server:

    ::

        # Add a user to the Aha cell.
        python -m synapse.tools.cellauth cell://./cells/ahatcp modify --adduser reguser

        # Give the user a password.
        python -m synapse.tools.cellauth cell://./cells/ahatcp modify --passwd secret reguser

        # Grant it the permissions for authenticating with Aha and registering a service.
        python -m synapse.tools.cellauth cell://./cells/aha001modify \
        --addrule aha.service.add reguser

Start up a Cortex, configured to register itself with the Aha service. This Cortex is binding a listener on port 0,
so the OS will assign the listening port for us:

    ::

        SYN_CORTEX_DMON_LISTEN=tcp://0.0.0.0:0/ SYN_CORTEX_HTTPS_PORT=8443 SYN_CORTEX_AHA_NAME=ahacore \
        SYN_CORTEX_AHA_REGISTRY=tcp://reguser:secret@127.0.0.1:8081/ SYN_CORTEX_AHA_NETWORK=demonet \
        SYN_CORTEX_AUTH_PASSWD=root python -m synapse.servers.cortex cells/ahacore01

The ``synapse.tools.aha.list`` utility can be used to inspect the services that have been registered with a given
Aha cell.

    ::

        $ python -m synapse.tools.aha.list cell://./cells/ahatcp
        Service              network                        online scheme host                 port   connection opts
        ahacore              demonet                        True   tcp    127.0.0.1            45463

Now we can add a client user to the Aha cell so that they can look up the Cell

    ::

        # Add a client user to Aha.
        python -m synapse.tools.cellauth cell://./cells/ahatcp modify --adduser alice

        # Give them a password
        python -m synapse.tools.cellauth cell://./cells/ahatcp modify --passwd secret alice

        # Allow the client to lookup services
        python -m synapse.tools.cellauth cell://./cells/ahatcp modify \
        --addrule aha.service.get alice

The clients ``telepath.yaml`` file will need to include the Aha server location.

    ::

        $ cat ~/.syn/telepath.yaml
        version: 1
        aha:servers:
          - - tcp://alice:secret@127.0.0.1:8081/

Now the user can connect to the Cortex by resolving its IP and port via the Aha server.

    ::

        python -m synapse.tools.cmdr aha://root:root@ahacore.demonet/

This will lookup the ``ahacore.demonet`` service in the Aha service, and then connect to the Cortex using the information
provided by Aha.

Using Aha with Custom Client Code
---------------------------------

Custom Synapse client which expects to utilize Aha servers for doing service
discovery can easily configure the aha services by loading the same
``telepath.yaml`` file that is used by CLI tools.

Example code loading ``telepath.yaml`` ::

    import contextlib
    import synapse.common as s_common
    import synapse.telepath as s_telepath

    async def main(argv):

        # Get the full path to the default telepath.yaml file
        path = s_common.getSynPath('telepath.yaml')

        # Create a exitstack
        async with contextlib.AsyncExitStack() as ctx:

            # Load the telepath environment. If the file
            # Exists, then the return value will be an
            # async callback.
            telefini = await s_telepath.loadTeleEnv(path)

            if telefini is not None:

                # register the callback to be executed
                ctx.push_async_callback(telefini)

            # Now that the telepath environment is setup, we can
            # connect to aha:// URLs if they are provided.
            async with await s_telepath.openurl(argv[0]) as proxy:

                await doStuff(proxy)

        return 0

    async def doStuff(proxy):
        pass

    sys.exit(asyncio.run(main(sys.argv[1:]))))

A Synapse Cell does not need to be configured with a ``telepath.yaml`` file if it is a Client which registers itself
with an Aha server during startup.


The Aha Server as a TLS CA
--------------------------

The Aha server also has the ability to work as a Certificate Authority. Can be
used to create a new TLS CA for a given Aha network, and then perform
certificate request signing. This can be used in conjunction with devops
practices to enable an entire network of Synapse based services to utilize TLS
and Telepath together.

Bootstrapping AHA with TLS
--------------------------

The following steps show bootstraping an Aha cell and using TLS to secure the connections between the services.
This example assumes that everything is locally hosted, so no DNS names are used here.

Setup a few directories::

    mkdir -p cells/aha
    mkdir -p cells/ahacore02/certs

Start an Aha Cell ::

    SYN_LOG_LEVEL=DEBUG SYN_AHACELL_AHA_ADMIN=admin@demo.net \
    python -m synapse.servers.aha cells/aha

This also creates an admin user named ``admin@demo.net`` in the Cell.

Connect to the Aha cell and generate a CA for the Aha network and a server certificate for the Aha cell ::

    python -m synapse.tools.aha.easycert -a cell://./cells/aha --ca demo.net

    python -m synapse.tools.aha.easycert -a cell://./cells/aha --server \
    --network demo.net aha.demo.net

The server private key would have been saved to the users default certdir directory, so we can copy it over Cell
certificate directory::

    mv ~/.syn/certs/hosts/aha.demo.net.key cells/aha/certs/hosts/aha.demo.net.key

Restart the Aha Cell with TLS::

    SYN_AHACELL_DMON_LISTEN="ssl://0.0.0.0:8081/?ca=demo.net&hostname=aha.demo.net" \
    SYN_AHACELL_AHA_ADMIN="admin@demo.net" python -m synapse.servers.aha cells/aha

Add groups to the Aha Cell and grant them permissions::

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --addrole aha_svc

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --addrole aha_user

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --addrule aha.service.get aha_user

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --addrule aha.service.add aha_svc

Add a user for the Cortex to register with, and a client user for connecting to Aha for doing service lookups::

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --adduser core02@demo.net

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --grant aha_user core02@demo.net

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --grant aha_svc core02@demo.net

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --adduser bob@demo.net

    python -m synapse.tools.cellauth "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    modify --grant aha_user bob@demo.net

Setup CA, server and user certificates for the Cortex::

    # Get a copy of the demo.net CA certificate
    python -m synapse.tools.aha.easycert -a "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    --certdir cells/ahacore02/certs/ --ca demo.net

    # Server certificate for ahacore02.demo.net
    python -m synapse.tools.aha.easycert -a "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    --certdir cells/ahacore02/certs/ --network demo.net --server core02.demo.net

    # User certificate for core02@demo.net
    python -m synapse.tools.aha.easycert -a "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    --certdir cells/ahacore02/certs/ --network demo.net core02@demo.net

Setup a client certificate for bob@demo.net::

    python -m synapse.tools.aha.easycert -a "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net" \
    --network demo.net bob@demo.net

Startup the Cortex using TLS::

     SYN_LOG_LEVEL=DEBUG  SYN_CORTEX_AHA_ADMIN="admin@demo.net" SYN_CORTEX_HTTPS_PORT=8443 \
     SYN_CORTEX_DMON_LISTEN="ssl://0.0.0.0:0/?ca=demo.net&hostname=core02.demo.net" \
     SYN_CORTEX_AHA_REGISTRY="ssl://127.0.0.1:8081/?hostname=aha.demo.net&certname=core02@demo.net" \
     SYN_CORTEX_AHA_NAME=core02 SYN_CORTEX_AHA_NETWORK=demo.net \
     python -m synapse.servers.cortex cells/ahacore02

Add the bob@demo.net user to the Cortex::

    python -m synapse.tools.cellauth "aha://admin@core02.demo.net/" modify --adduser bob@demo.net
    # And make him a admin so he can do things on the Cortex
    python -m synapse.tools.cellauth "aha://admin@core02.demo.net/" modify --admin bob@demo.net

One the Cortex is up, it should register itself with the Aha Cell::

    python -m synapse.tools.aha.list "ssl://admin@127.0.0.1:8081/?hostname=aha.demo.net"
    Service              network                        online scheme host                 port   connection opts
    core02               demo.net                    True   ssl    127.0.0.1            36283  {'name': 'core02.demo.net'}

Update the client telepath.yaml file for the new Aha server::

    version: 1
    aha:servers:
      - - ssl://bob@127.0.0.1:8081/?hostname=aha.demo.net

Now Aha can be used to connect to the Cortex::

    python -m synapse.tools.cmdr "aha://bob@core02.demo.net/"

TODO
----

SVCINFO notes
