.. _devops-aha:

Aha Service Discovery
=====================

The Aha service discovery is a native Synapse tool and protocol for doing
service discovery when multiple Synapse services are being deployed in a
environment. In order to utilize Aha, a few


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

Standing up an Aha Server
-------------------------

Aha goes here!


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

In the above example, two sets of aha servers are registered, and a additional
certificate directory.

Putting it Together
-------------------



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

A Synapse Cell does not need to be configured with a ``telepath.yaml`` file
if it is a Client which connects to