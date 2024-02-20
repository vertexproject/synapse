.. _dev_storm_api:

Storm API Guide
###############


.. _dev_storm_apis:

Storm APIs
==========

Storm is available over Telepath and HTTP API interfaces. Both interfaces require a Storm query string, and may take
additional ``opts`` arguments.

Telepath
--------

There are three Storm APIs exposed via Telepath.

``storm(text, opts=None)``
    The Storm API returns a message stream. It can be found here storm_.

``callStorm(text, opts=None)``
    The callStorm API returns a message given by the Storm ``return( )`` syntax. It can be found here callStorm_.

``count(text, opts=None)``
    The count API returns a count of the number of nodes which would have been emitted by running a given query. It can
    be found here :ref:`http-api-cortex`.

HTTP API
--------

The HTTP API versions of the Storm APIs can be found here `Cortex HTTP API`_.

``/v1/api/storm``
    This API returns a message stream.

``/v1/api/storm/call``
    This API returns a message given by the Storm ``return( )`` syntax.

``/v1/api/storm/export``
    This API returns a stream of msgpack encoded data, which can be used as a `.nodes` file for later import.

.. _dev_storm_message:

Message Types
=============

The Telepath ``storm()`` and HTTP ``api/v1/storm`` APIs yield messages from the Storm runtime to the caller. These are
the messages that may be seen when consuming the message stream.

Each message has the following basic structure::

    [ "type", { ..type specific info... } ]

init
----

First message sent by a Storm query runtime.

It includes the following keys:

task
    The task identifier (which can be used for task cancellation).

tick
    The epoch time the query execution started (in milliseconds). This value is computed from the host time and may
    be affected by any changes in the host clock.

abstick
    The relative time that the query execution started (in milliseconds). This value is computed from a monotonic
    clock and can be used as a reference time.

text
    The Storm query text.

hash
    The md5sum of the Storm query text.

Example::

    ('init',
     {'task': '8c90c67e37a30101a2f6a7dfb2fa0805',
      'text': '.created | limit 3',
      'hash': '2d16e12e80be53e0e79e7c7af9bda12b',
      'tick': 1539221678859})


node
----

This represents a packed node. Each serialized node will have the following structure::

    [
        [<form>, <valu>],       # The [ typename, typevalue ] definition of the node.
        {
            "iden": <hash>,     # A stable identifier for the node.
            "tags": {},         # The tags on the node.
            "props": {},        # The node's secondary properties.
            "path": {},         # Path related information in the node.
            "tagprops": {},     # The node's tag properties.

            # optional
            "repr": ...         # Presentation values for the type value.
            "reprs": {}         # Presentation values for props which need it.
            "tagpropreprs": {}  # Presentation values for tagprops which need it.

        }
    ]

Example:

This example is very simple - it does not include repr information, or things related to path data::

    ('node',
     (('inet:fqdn', 'icon.torrentart.com'),
      {'iden': 'ae6d871163980f82dc1d3b06e784a80e8085493f68fbf2813c9681cb3e2630a8',
       'props': {'.created': 1526590932444,
                 '.seen': (1491771661000, 1538477660797),
                 'domain': 'torrentart.com',
                 'host': 'icon',
                 'issuffix': 0,
                 'iszone': 0,
                 'zone': 'torrentart.com'},
       'tags': {'aka': (None, None),
                'aka.beep': (None, None),}}))

For path and repr information, see the examples in the opts documentation :ref:`dev_storm_opts`.

ping
----

A keepalive message. This is sent periodically when the ``keepalive`` options is set. See :ref:`dev_storm_opts` for
more information.

print
-----

The print event contains a message intended to be displayed to the caller.

It includes the following key:

mesg
    The message to be displayed to the user.

Example::

    (print, {'mesg': 'I am a message!'})

This can be produced by users with the ``$lib.print()`` Storm API.

warn
----

The warn event contains data about issues encountered when performing an action.

It includes the following keys:

mesg
    The message to be displayed to the user.

The warn event may contain additional, arbitrary keys in it.

Example::

    ('warn',
     {'mesg': 'Unable to foo the bar.com domain',
      'domain': 'bar.com'})

This can be produced by users with the ``$lib.warn()`` Storm API.

err
---

The err event is sent if there is a fatal error encountered when executing a
Storm query. There will be no further processing; only a ``fini`` message sent
afterwards.

The err event does contain a marshalled exception in it. This contains the exception
type as the identifier; and several attributes from the exception.

The following keys are usually present in the marshalled information:

esrc
    Source line that raised the exception.

efile
    File that the exception was raised from.

eline
    Line number from the raising file.

ename
    Name of the function where the exception was from.

mesg
    The ``mesg`` argument to a SynErr exception, if present; or the ``str()`` exception.

Additional keys may also be present, depending on the exception that was raised.

Example::

    ('err',
     ('BadTypeValu',
      {'efile': 'inet.py',
       'eline': 294,
       'form': 'inet:fqdn',
       'mesg': 'FQDN failed to match fqdnre [^[\\w._-]+$]',
       'name': 'inet:fqdn',
       'valu': '1234@#'}))


fini
----

The last message sent by a Storm query runtime. This can be used as a key to stop processing messages or finalize
any sort of rollup of messages.

It includes the following keys:

tock
    The epoch time the query execution finished (in milliseconds). This value is computed from adding the ``took``
    value to the ``tick`` value from the ``init`` message.

took
    The amount of time it took for the query to execute (in milliseconds). This value is computed from the ``abstick``
    and ``abstock`` values.

abstock
    The relative time that the query execution finished at (in milliseconds). This value is computed from a monotonic
    clock and should always be equal to or greater than the ``abstick`` value from the ``init`` message.

count
    The number of nodes yielded by the runtime.

Example::

    ('fini', {'count': 1, 'tock': 1539221715240, 'took': 36381})

.. note::

    If the Storm runtime is cancelled for some reason, there will be no ``err`` or ``fini`` messages
    sent. This is because the task cancellation may tear down the channel and we would have an async task
    blocking on attempting to send data to a closed channel.


node\:edits
-----------

The ``node:edits`` message represents changes that are occurring to the underlying graph, as a result of running a
Storm query.

It includes the following key:

edits
    A list of changes made to a set of nodes.

Example::

    # Nodeedits produced by the following query: [(inet:ipv4=1.2.3.4 :asn=1)]

    ('node:edits',
     {'edits': (('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                 'inet:ipv4',
                 ((0, (16909060, 4), ()),
                  (2, ('.created', 1662578208195, None, 21), ()),
                  (2, ('type', 'unicast', None, 1), ()))),)})
    ('node:edits',
     {'edits': (('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                 'inet:ipv4',
                 ((2, ('asn', 1, None, 9), ()),)),
                ('371bfbcd479fec0582d55e8cf1011c91c97f306cf66ceea994ac9c37e475a537',
                 'inet:asn',
                 ((0, (1, 9), ()),
                  (2, ('.created', 1662578208196, None, 21), ()))))})


node\:edits\:count
------------------

The ``node:edits:count`` message represents a summary of changes that are occurring to the underlying graph, as a
result of running a Storm query. These are produced when the query ``opts`` set ``editformat`` to ``count``.

It includes the following key:

count
    The number of changes made to the graph as a result of a single ``node:edits`` event.

Example::

    # counts produced by the following query: [(inet:ipv4=1.2.3.4 :asn=1)]

    ('node:edits:count', {'count': 3})
    ('node:edits:count', {'count': 3})


storm\:fire
-----------

The ``storm:fire`` message is a arbitrary user created message produced by the ``$lib.fire()`` Storm API.
It includes the following keys:

type
    The type of the event.

data
    User provided data.

Example::

    # The following query produces an event
    $l = ((1), (2), (3)) $lib.fire('demo', key=valu, somelist=$l)

    # The event produced.
    ('storm:fire', {'data': {'key': 'valu', 'somelist': (1, 2, 3)}, 'type': 'demo'})


look\:miss
----------

The ``look:miss`` message is sent when the Storm runtime is set to ``lookup`` mode and the node that was identified
by the scrape logic is not present in the current View.

It includes the following key:

ndef
    A tuple of the form and normalized value.

Example::

    ('look:miss', {'ndef': ('inet:fqdn', 'hehe.com')})

    # The ipv4 value is presented in system mode.
    ('look:miss', {'ndef': ('inet:ipv4', 16909060)})

csv\:row
--------

The ``csv:row`` message is sent by the Storm runtime by the ``$lib.csv.emit()`` Storm API.

It includes the following keys:

row
    A list of elements that make up the row.

table
    A optional table name. This may be ``None``.

Example::

    # This query produces the following event: $lib.csv.emit(foo, bar, $lib.time.now())
    ('csv:row', {'row': ('foo', 'bar', 1662578057658), 'table': None})

    # This query produces the following event: $lib.csv.emit(foo, bar, $lib.time.now(), table=foo)
    ('csv:row', {'row': ('foo', 'bar', 1662578059282), 'table': 'foo'})

.. _dev_storm_call:

Storm Call APIs
===============

The Telepath ``callStorm()`` and HTTP API ``storm/call`` interfaces are designed to return a single message to the
caller, as opposed to a stream of messages. This is done using the Storm ``return( )`` syntax. Common uses for the call
interfaces include getting and setting values where the full message stream would not be useful.

Example:

    The following example shows retrieving a user definition.

    .. code:: python3

        # Prox is assumed to be a Telepath proxy to a Cortex.
        >>> text = '$user = $lib.auth.users.byname($name) return ( $user )'
        >>> opts = {'vars': {'name': 'root'}}
        >>> ret = prox.callStorm(text, opts=opts)
        >>> pprint(ret)
        {'admin': True,
         'archived': False,
         'authgates': {'0b942d5f4309d70e5fa64423714e25aa': {'admin': True},
                       'cdf6f1727da73dbac95e295e5d258847': {'admin': True}},
         'email': None,
         'iden': '933a320b7ce8134ba5abd93aa487e1b5',
         'locked': False,
         'name': 'root',
         'roles': (),
         'rules': (),
         'type': 'user'}


    The following shows setting an API key for a Power-Up. There is no ``return`` statement, so the return value
    defaults to None.

    .. code:: python3

        # Prox is assumed to be a Telepath proxy to a Cortex.
        >>> text = 'foobar.setup.apikey $apikey'
        >>> opts = {'vars': {'apikey': 'secretKey'}}
        >>> ret = prox.callStorm(text, opts=opts)
        >>> print(ret)
        None


.. _dev_storm_opts:

Storm Opts
==========

All Storm API endpoints take an ``opts`` argument. This is a dictionary that contains metadata that is used by the
Storm runtime for various purposes. Examples are given using Python syntax.

debug
-----

If this is set to True, the Storm runtime will be created with ``$lib.debug`` set to True.

Example:

    .. code:: python3

        opts = {'debug': True}

editformat
----------

This is a string containing the format that node edits are streamed in. This may be ``nodeedits`` (the default value),
``none``, or ``count``.  If the value is ``none``, then no edit messages will be streamed. If the value is ``count``,
each ``node:edits`` message is replaced by a ``node:edits:count`` message, containing a summary of the number of edits
made for a given message.

Examples:

    .. code:: python3

        # Turn node:edit messages into counts
        opts = {'editformat': 'count'}

        # Disable node edits
        opts = {'editformat': 'none'}

idens
-----

This is a list of node iden hashes to use as initial input to the Storm runtime. These nodes are lifted after any
``ndefs`` options are lifted, but prior to regular lift operations which may start a Storm query.

Example:

    .. code:: python3


        idens = ('ee6b92c9fd848a2cb00f3a3618148c512b58456b8b51fbed79251811597eeea3',
                 'c5a67a095b71771d9663d691f0ab36b53ebdc14fbad18f23f95e923543156bd6',)
        opts = {'idens': idens}

keepalive
---------

This is the period ( in seconds ) in which to send a ``ping`` message from a Storm query which is streamiing results,
such as the Telepath ``.storm()`` API or the HTTP ``/v1/api/storm`` API endpoint. This may be used with long-running
Storm queries when behind a network proxy or load balancer which may terminate idle connections.

The keepalive value must be greater than zero.

Example:

    .. code:: python3


        keepalive = 2  # Send a keepalive message every 2 seconds
        opts = {'keepalive': keepalive}

limit
-----

Limit the total number of nodes that the Storm runtime produces. When this number is reached, the runtime will be
stopped.

Example:

    .. code:: python3

        opts = {'limit': 100}

mode
----

This is the mode that a Storm query is parsed in. This value can be specified to ``lookup``, ``autoadd``, and
``search`` modes to get different behaviors.

Example:

    .. code:: python3

        # Using lookup mode, the query text, before switching to command mode with a | character,
        # will have its text scrapped for simple values such as FQDNs, IP Addresses, and Hashes
        # and attempt to lift any matching nodes.
        opts = {'mode': 'lookup'}

        # Using autoadds mode, the query text is scrapped like in lookup mode; and for any
        # values which we try to lift that do not produce nodes, those nodes will be added
        # in the current view.
        opts = {'mode': 'autoadd'}

        # Using search mode, the query will be run through the Storm search interface.
        # This will lift nodes based on searching, which is enabled by the
        # Synapse-Search Advanced Power-up.
        opts = {'mode': 'search'}

ndefs
-----

This is a list of form and value tuples to use as initial input to the Storm runtime. These are expected to be the
already normalized, system mode, values for the nodes. These nodes are lifted before any other lift operators are
run.

Example:

    .. code:: python3

        ndefs = (
            ('inet:fqdn', 'com'),
            ('inet:ipv4', 134744072),
        )

        opts = {'ndefs': ndefs}


path
----

If this is set to True, the ``path`` key in the packed nodes will contain a ``nodes`` key, which contains a list of
the node iden hashes that were used in pivot operations to get to the node.

Example:

.. code:: python3

    opts = {'path': True}

    # A Storm node message with a node path added to it, from the query inet:ipv4 -> inet:asn.

    ('node',
     (('inet:asn', 1),
      {'iden': '371bfbcd479fec0582d55e8cf1011c91c97f306cf66ceea994ac9c37e475a537',
       'nodedata': {},
       'path': {'nodes': ('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                          '371bfbcd479fec0582d55e8cf1011c91c97f306cf66ceea994ac9c37e475a537')},
       'props': {'.created': 1662493825668},
       'tagprops': {},
       'tags': {}}))


readonly
--------

Run the Storm query in a readonly mode. This prevents editing the graph data, and only allows a small subset of
whitelisted Storm library functions to be used.

Examples:

    .. code:: python3

        opts = {'readonly': True}

repr
----

If this is set to True, the packed node will have a ``repr`` and ``reprs`` key populated, to contain human friendly
representations of system mode values.

Example:

.. code:: python3

    opts = {'repr': True}

    # A Storm node message with reprs added to it.

    ('node',
     (('inet:ipv4', 134744072),
      {'iden': 'ee6b92c9fd848a2cb00f3a3618148c512b58456b8b51fbed79251811597eeea3',
       'nodedata': {},
       'path': {},
       'props': {'.created': 1662491423034, 'type': 'unicast'},
       'repr': '8.8.8.8',
       'reprs': {'.created': '2022/09/06 19:10:23.034'},
       'tagpropreprs': {},
       'tagprops': {},
       'tags': {}}))


scrub
-----

This is a set of rules that can be provided to the Storm runtime which dictate which data should be included or
excluded from nodes that are returned in the message stream. Currently the only rule type supported is ``include`` for
``tags``.

Example:

    .. code:: python3

        # Only include tags which start with cno and rep.foo
        scrub = {'include': {'tags': ['cno', 'rep.foo',]}}
        opts = {'scrub': scrub}

        # Do not include any tags in the output
        scrub = {'include': {'tags': []}}
        opts = {'scrub': scrub}


show
----

A list of message types to include in the output message stream. The ``init``, ``fini``, and ``err`` message types
cannot be filtered with this option.

Example:

    .. code:: python3

        # Only node and warning messages.
        opts = {'show': ['node', 'warning']}

        # Only include required messages.
        opts = {'show': []}

show:storage
------------

A boolean option which, when set to ``true``, instructs the Storm runtime to add a ``storage`` key to each yielded node
which contains a raw breakdown of storage nodes which can be used to determine which parts of the node are stored in
which layer within the view.

Example:

    .. code:: python3

        opts = {'show:storage': True}

task
----

A user provided guid that is used as the task identifier for the Storm runtime. This allows a user to have a
predictable identifier that they can use for task cancellation.

The Storm runtime will raise a ``BadArg`` value if the ``task`` iden is associated with a currently running task.

Example:

    .. code:: python3

        # Generate a guid on the client side and provide it to the Cortex
        import synapse.common as s_commmon
        task_iden = s_common.guid()
        opts = {'task': task_iden}

user
----

The User iden to run the Storm query as. This allows a user with the permission ``impersonate`` to run a Storm
query as another user.

Example:

    .. code:: python3

        opts = {'user': 6e9c8de2f1aa39fee11c19d0974e0917}

vars
----

A dictionary of key - value pairs that are mapped into the Storm runtime as variables. Some uses of this include
providing data to the runtime that is used with an ingest script, or to provide secrets to the Storm runtime so
that they will not be logged.

Example:

    .. code:: python3

        # A secret key - A good example of this is configuring a Rapid Power-Up.
        vars = {'secretkey': 'c8de2fe11c19d0974e091aa39fe176e9'}
        opts = {'vars': vars}

        # Some example data that could be used in a Storm ingest script.
        records = (
            ('foobar.com', '8.8.8.8', '20210810'),
            ('bazplace.net', '1.2.3.4', '20210810'),
        )
        vars = {'records': records}
        opts = {'vars': vars}

view
----

The View iden in which to run the Storm query in. If not specified, the query will run in the user's default view.

Example:

    .. code:: python3

        opts = {'view': 31ded629eea3c7221be0a61695862952}


.. _storm: ../autodocs/synapse.html#synapse.cortex.CoreApi.storm

.. _callStorm: ../autodocs/synapse.html#synapse.cortex.CoreApi.callStorm

.. _count: ../autodocs/synapse.html#synapse.cortex.Cortex.count

.. _Cortex HTTP API: ../httpapi.html#cortex
