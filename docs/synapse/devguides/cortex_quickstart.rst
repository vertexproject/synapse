.. toctree::
    :titlesonly:

.. _dev_cortex_quickstart:

Cortex Development Quickstart
#############################

This guide is intended for developers looking to integrate Synapse components with other applications
by using the Telepath API.  Additionally, this guide will introduce developers to writing custom Cortex
modules in Python to allow custom data model extensions, Storm commands, ingest functions, and change hooks.
This guide assumes familiarity with deploying Cortex servers and the Storm query syntax.
For help on getting started, see :ref:`quickstart`.

For complete API documentation on all Synapse components see :ref:`apidocs`.

Remote Cortex Access
====================

A Cortex, like most synapse components, provides two mechanisms for remote API calls.
The HTTP/REST API and the Telepath API.  For additional documentation on the Cortex HTTP API, see :ref:`http-api`.
This guide will cover remote API calls using Telepath.

Telepath is an asynchronous, high-performance, streaming oriented, RPC protocol.
It is designed for minimum development effort and maximum performance.
Data is serialized using the highly efficient Message_Pack_ format which is not only more size efficient than JSON,
but allows serialization of binary data and supports incremental decoding for use in stream based protocols.

Telepath allows a client to connect to a Python object shared on a remote server and, in most instances,
call methods as though the object were local.
However, this means all arguments and return values must be serializable using Message Pack.

To connect to a remote object, the caller specifies a URI to connect and construct a Telepath Proxy.
In the following examples, we will assume a Cortex was previously setup and configured with the user ``visi``
and the password ``secretsauce`` running on port ``27492`` on the host ``1.2.3.4``.

Making a simple call
--------------------

Once a Telepath proxy is connected, most methods may simply be called as though the object were local.
For example, the ``getModelDict`` method on the ``CoreApi`` returns a Python dictionary
containing the details of the data model in the remote Cortex.

::

    import asyncio
    import synapse.telepath as s_telepath

    async def main():

        async with await s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/') as core:

            model = await core.getModelDict()

            for form in model.get('forms'):
                dostuff()

    if __name__ == '__main__':
        asyncio.run(main())

Like many objects in the Synapse ecosystem, a Telepath proxy inherits from ``synapse.lib.base.Base``.
This requires the ``fini`` method to be called to release resources and close sockets.
In the example above, we use the async context manager implemented by the ``Base`` class (``async with``)
to ensure that the proxy is correctly shutdown.  However, Telepath is designed for long-lived Proxy objects
to minimize API call delay by using existing sockets and sessions.  A typical app will create a telepath proxy
during initialization and only create a new one in the event that the remote Telepath server is restarted.

The above example also demonstrates that Telepath is designed for use with Python 3.11 asyncio.
However, the Telepath proxy can also be constructed and used transparently from non-async code as seen below.

::

    import synapse.telepath as s_telepath

    def main():

        core = s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/')
        model = core.getModelDict()

    if __name__ == '__main__':
        main()

The remainder of the examples in this guide will assume the use of an asyncio loop.

Generators and Yielding
-----------------------

Many of the Telepath APIs published by Synapse services are capable of yielding results as a generator
to facilitate incremental reads and time_to_first_byte_ (TTFB) optimizations.
In the remote case, this means the caller may receive and begin processing results before all of the results
have been enumerated by the server.  Any Python async generator method on a shared object may be iterated
by a client with full back_pressure_ to the server. This means a caller may issue a query which producesa very large
result set and consume the results incrementally without concern over client/server memory exhaustion due to buffering.
The following example demonstrates using the Cortex ``storm`` API to retrieve a message stream, which includes nodes in it.

::

    import asyncio
    import synapse.telepath as s_telepath

    async def main():

        async with await s_telepath.openurl('tcp://visi:secretsauce@1.2.3.4:27492/') as core:

            async for mesg in core.storm('inet:ipv4 | limit 10000'):

                # Handle node messages specifically.
                if mesg[0] == 'node':
                    node = mesg[1]
                    dostuff(node)
                
                else:
                    # Handle non-node messages.
                    do_not_node_stuff(mesg)

    if __name__ == '__main__':
        asyncio.run(main())

The ``storm()`` API is the preferred API to use for executing Storm queries on a Cortex.
It generates a series of messages which the caller needs to consume.

For API documentation on the full Cortex Telepath API, see CoreAPi_.


.. _time_to_first_byte: https://en.wikipedia.org/wiki/Time_to_first_byte
.. _back_pressure: https://en.wikipedia.org/wiki/Back_pressure#Backpressure_in_information_technology
.. _CoreApi: ../autodocs/synapse.html#synapse.cortex.CoreApi
.. _Message_Pack: https://msgpack.org/index.html
.. _Slack: https://v.vtx.lk/join-slack
