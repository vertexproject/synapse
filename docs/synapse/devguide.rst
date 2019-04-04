.. toctree::
    :titlesonly:

.. _devguide:

Synapse Developers Guide
########################

This guide is intended for developers looking to integrate Synapse components with other applications by using the Telepath API.  Additionally, this guide will introduce developers to writing custom Cortex modules in Python to allow custom data model extensions, storm commands, ingest functions, and change hooks.  This guide assumes familiarity with deploying Cortex servers and the Storm query syntax.  For help on getting started, see :ref:`quickstart`.

For complete API documentation on all Synapse components see :ref:`apidocs`.

Remote Cortex Access
====================

A Cortex, like most synapse components, provides two mechanisms for remote API calls.  The HTTP/REST API and the Telepath API.  For additional documentation on the Cortex HTTP API, see :ref:`http-api`.  This guide will cover remote API calls using Telepath.

Telepath is an asynchronous, high-performance, streaming oriented, RPC protocol.  It is designed for minimum development effort and maximum performance.  Data is serialized using the highly efficient Message_Pack_ format which is not only more size efficient than JSON, but allows serialization of binary data and supports incremental decoding for use in stream based protocols.

Telepath allows a client to connect to a Python object shared on a remote server and, in most instances, call methods as though the object were local.  However, this means all arguments and return values must be serializable using Message Pack.

To connect to a remote object, the caller specifies a URI to connect and construct a Telepath Proxy.  In the following examples, we will assume a Cortex was previously setup and configured with the user ``visi`` and the password ``secretsauce`` running on port ``27492`` on the host ``1.2.3.4``.

Making a simple call
--------------------

Once a Telepath proxy is connected, most methods may simply be called as though the object were local.  For example, the ``getModelDict`` method on the ``CoreApi`` returns a Python dictionary containing the details of the data model in the remote Cortex.::

    import asyncio
    import synapse.telepath as s_telepath

    async def main():

        async with await s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/') as core:

            model = await core.getModelDict()

            for form in model.get('forms'):
                dostuff()

    if __name__ == '__main__':
        asyncio.run(main())

Like many objects in the Synapse ecosystem, a Telepath proxy inherits from ``synapse.lib.base.Base``.  This requires the ``fini`` method to be called to release resources and close sockets.  In the example above, we use the async context manager implemented by the ``Base`` class (``async with``) to ensure that the proxy is correctly shutdown.  However, Telepath is designed for long-lived Proxy objects to minimize API call delay by using existing sockets and sessions.  A typical app will create a telepath proxy during initialization and only create a new one in the event that the remote Telepath server is restarted.

The above example also demonstrates that Telepath is designed for use with Python 3.7 asyncio.  However, the Telepath proxy can also be constructed and used transparently from non-async code as seen below.::

    import synapse.telepath as s_telepath

    def main():

        core = s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/')
        model = core.getModelDict()

    if __name__ == '__main__':
        main()

The remainder of the examples in this guide will assume the use of an asyncio loop.

Generators and Yielding
-----------------------

Many of the Telepath APIs published by Synapse services are capable of yielding results as a generator to facilitate incremental reads and time_to_first_byte_ (TTFB) optimizations.  In the remote case, this means the caller may receive and begin processing results before all of the results have been enumerated by the server.  Any Python async generator method on a shared object may be iterated by a client with full back_pressure_ to the server.  This means a caller may issue a query which returns a very large result set and consume them incrementally without concern over client/server memory exhaustion due to buffering a large result set.  The following example demonstrates using the Cortex ``eval`` API to retrieve nodes.::

    import asyncio
    import synapse.telepath as s_telepath

    async def main():

        async with await s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/') as core:

            async for node in core.eval('inet:ipv4 | limit 10000'):
                dostuff(node)

    if __name__ == '__main__':
        asyncio.run(main())

For API documentation on the full Cortex Telepath API, see CoreAPi_.

Developing Cortex Modules
=========================

Basics
------

A Cortex allows developers to implement and load custom modules by extending the ``synapse.lib.module.CoreModule`` class.  A ``CoreModule`` can be used to customize a Cortex in many ways, including:

* Data Model Extensions
* Custom Storm Commands
* Custom Ingest Functions

However, with great power comes great danger.  Bugs in a ``CoreModule`` subclass can easily cause a Cortex to crash or become unresponsive.  Cortex module developers must be familiar with the Python asynchronous programming paradigm.  The only exception is for simple data model extensions which only require a single method that returns a data model extension dictionary.

For this guide, we will assume a Python module named ``example`` with a ``CoreModule`` subclass named ``ExampleModule``.::

    import synapse.lib.module as s_module

    class ExampleModule(s_module.CoreModule):

        async def initCoreModule(self):
            # by this time we have a reference to the Cortex as self.core
            print('hello cortex!')

The ``initCoreModule`` method may be implemented in a ``CoreModule`` subclass to initialize internal data structures and register with additional Cortex subsystems.

Loading a Module
----------------

A Cortex module may be loaded into an existing Cortex by updating the cell.yaml file found (or created) in the Cortex storage directory.  Modules are added by appending their full Python import path to the “modules” key which expects a list.::

    modules:
        - example.ExampleModule

Once configured, the module will be loaded whenever the Cortex is started.::

    invisigoth@vertex00:~/git/synapse$ python -m synapse.servers.cortex /path/to/cortex
    starting cortex: /path/to/cortex
    hello cortex!
    ...cortex API (telepath): tcp://0.0.0.0:27492/
    ...cortex API (https): 4443

Data Model Extensions
---------------------

A ``CoreModule`` subclass may extend the Cortex data model by implementing the ``getModelDefs`` API.  This API allows the ``CoreModule`` to specify new types, forms, and properties within the data model.

Developers are encouraged to give their own model extensions a namespace prefix that clearly indicates that they are custom or specific to a given organization.  The Vertex Project has reserved the namespace prefix ``x:`` for custom model extensions and will never create mainline Synapse model elements within that namespace.  For our example, we will assume that Foo Corp is creating a custom model extension and has decided to namespace their model elements within the ``x:foo:`` prefix.::

    import synapse.lib.module as s_module

    class ExampleModule(s_module.CoreModule):

        def getModelDefs(self):

            # we return a tuple of (name, modeldef) tuples...

            return (

                ('foomodel', {

                    'types': (

                        # declare a type for our form primary property
                        ('x:foo:event', ('str', {'regex': '[a-z]{2}-[0-9]{5}'}), {
                            'doc': 'A custom event ID from some other system.'}),

                        ('x:foo:bar', ('int', {'min': 100, 'max': 10000}), {
                            'doc': 'A custom integer property with a fixed range.'}),
                    ),

                    'forms': (

                        # declare a new node type

                        ('x:foo:event', {}, (

                            # declare secondary properties
                            ('time', ('time', {}), {
                                'doc': 'The time of the custom event.'}),

                            ('ipv4', ('inet:ipv4', {}), {
                                'doc': 'The ipv4 associated with the custom event.'}),

                            ('bar', ('x:foo:bar', {}), {
                                'doc': 'The custom bar property associated with the custom event.'}),
                        )),
                    ),

                }),
            )

In the above example, we can see that the model extension implements a custom form ``x:foo:event`` with properties using a mix of existing types and custom types.  By using existing types where possible, the model extension easily integrates with the existing data model, allowing seamless pivots to and from the custom nodes.  Additionally, custom field specific to the deployment environment allow knowledge within the Cortex to be linked to external records.::

    cli> storm x:foo:event:time*range=(20190505, 20190506) -> inet:ipv4

The Storm query above returns all the ``inet:ipv4`` nodes associated with events on 2019/05/05.

As the mainline data model grows, so does the power of analysis using Synapse.  For data model extensions that are (or could be) generalized, we strongly encourage analysts and developers to discuss their data model ideas with Vertex for potential inclusion in the mainline model.  Check out the slack chat or email info@vertex.link for more info.

Custom Storm Commands
---------------------

A ``CoreModule`` subclass may extend the commands available in the Storm query language implementing the ``getStormCmds`` API to return ``synapse.lib.storm.Cmd`` subclasses.

.. warning::

    It is extremely important that developers are familiar with the Python 3.7 asyncio programming paradigm when implementing ``Cmd`` subclasses!  Any blocking API calls made from within a ``Cmd`` extension will block *all* execution for the entire Cortex and Telepath multiplexor!

A ``Cmd`` subclass implements several methods to facilitate both parsing and execution.  The Storm query runtime is essentially a pipeline of nodes being lifted, pivoted, and filtered.  A Storm operator or command may both receive and yield ``(synapse.lib.node.Node, synapse.lib.node.Path)`` tuples.  The main execution of a ``Cmd`` subclass is handled by the ``execStormCmd`` method which iterates over the ``(Node, Path)`` tuples it is given and yields ``(Node, Path)`` tuples as results.  This architecture allows Storm to chain commands and operations together in any way the analyst sees fit.

Using this pipeline, a command may (asynchronously) call external APIs and subsystems to:
* Enrich nodes by adding properties or tags
* Push nodes to external subsystems
* Query external APIs for additional / related nodes
* Add metadata to be returned along with the node

The following example ``Cmd`` demonstrates consuming, potentially modifying, and yielding nodes based on command line options.::

    import synapse.lib.storm as s_storm
    import synapse.lib.module as s_module

    def dostuff(x):
        # just an example... :)
        return 10

    class ExampleCommand(s_storm.Cmd):
        '''
        This doc string becomes the command description.
        '''

        # we set the command name as a class local
        name = 'example'

        def getArgParser(self):
            # always use the parent getArgParser() not argparse!
            # ( we sublcass argparse classes to prevent them from
            # calling sys.exit() on --help and syntax error events)
            pars = s_storm.Cmd.getArgParser(self)
            pars.add_argument('--send-woot', default=False, action='store_true')
            return pars

        async def execStormCmd(self, runt, genr):
            # we get a synapse.lib.storm.Runtime instance and
            # a (synapse.lib.node.Node, synapse.lib.node.Path) generator

            async for node, path in genr:

                woot = dostuff(node)

                # we can send messages out to the caller/user
                await runt.printf('doing stuff...')

                if self.opts.send_woot:
                    # nodes returned from storm will include 'woot' metadata
                    path.meta('woot', woot)

                yield node, path

    class ExampleModule(s_module.CoreModule):

        def getStormCmds(self):
            # we return a list of StormCmd subclasses.
            return [ ExampleCommand ]

With the custom Storm command loaded, a storm user may get syntax help or send nodes through the command using standard Storm syntax.::

    invisigoth@vertex00:~/git/synapse$ python -m synapse.tools.cmdr tcp://visi:secretsauce@1.2.3.4:27492/
    cli> storm example --help

    usage: example [-h] [--send-woot]

        This doc string becomes the command description.
        

    optional arguments:
      -h, --help   show this help message and exit
      --send-woot

    complete. 0 nodes in 8 ms (0/sec).
    cli>
    cli>
    cli> storm inet:ipv4 | limit 10 | example

    doing stuff...
    inet:ipv4=1.2.3.4
            .created = 2019/04/04 01:49:21.428
            :asn = 0
            :loc = ??
            :type = unicast
    complete. 1 nodes in 2 ms (500/sec).
    cli>

Custom Ingest Functions
-----------------------

When no existing ingest format will suffice, a ``CoreModule`` may extend the Cortex ingest API by registering a parser function using the ``setFeedFunc`` method.  This ingest function may then be fed remotely using the ``addFeedData`` Telepath API.  This is commonly used to implement parsers for internal or 3rd party data structures.  The following example registers a feed function for a simple passive DNS data structure which includes a min and max observed timestamps.::

    import synapse.lib.module as s_module

    class ExampleModule(s_module.CoreModule):

        async def initCoreModule(self):
            # by this time we have a reference to the Cortex as self.core
            # still best to use a namespace prefix...
            self.core.setFeedFunc('x:foo:pdns', self._feedFooPdns)

        async def _feedFooPdns(self, snap, items):

            # we get a synapse.lib.snap.Snap to interface with the cortex
            # and a list of our pdns records ( to minimize round trips )
            for pdns in items:

                fqdn = pdns.get('fqdn')
                ipv4 = pdns.get('ipv4')

                tick = pdns.get('min_time_seen')
                tock = pdns.get('max_time_seen')

                node = await snap.addNode('inet:dns:a', (fqdn, ipv4))

                # the time window prop ".seen" will move outward to include
                # individual values when set to a single time...
                await node.set('.seen', tick)
                await node.set('.seen', tock)
                # the .seen property is now (tick, tock) or the min/max existing values...

Once registered and loaded, the feed function may be called remotely using ``CoreApi`` method ``addFeedData``::

    import asyncio
    import synapse.telepath as s_telepath

    # a list (of just one) custom pdns record
    data = [
        {
            'fqdn': 'vertex.link',
            'ipv4': '1.2.3.4',
            'min_time_seen': '2017/05/05 12:00:00.333',
            'max_time_seen': '2019/05/05 14:22:22.222',
        }
    ]

    async def main():

        async with await s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492') as core:

            # we can now feed our ingest function...
            await core.addFeedData('x:foo:pdns', data)

    if __name__ == '__main__':
        asyncio.run(main())

.. _time_to_first_byte: https://en.wikipedia.org/wiki/Time_to_first_byte
.. _back_pressure: https://en.wikipedia.org/wiki/Back_pressure#Backpressure_in_information_technology
.. _CoreApi: ./autodocs/synapse.html#synapse.cortex.CoreApi
.. _Message_Pack: https://msgpack.org/index.html
