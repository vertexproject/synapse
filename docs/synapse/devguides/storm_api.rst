.. _dev_storm_api:

Storm API Guide
###############

This Dev Guide is written by and for Synapse developers.


.. _dev_storm_apis:

Storm APIs
==========

Storm is available over Telepath and HTTP API interfaces.

Telepath
--------


``storm(text, opts=None)``
    synapse/autodocs/synapse.html#synapse.cortex.CoreApi.storm


``callStorm(text, opts=None)``
    synapse/autodocs/synapse.html#synapse.cortex.CoreApi.callStorm


``count(text, opts=None)``
    https://synapse.docs.vertex.link/en/latest/synapse/autodocs/synapse.html#synapse.cortex.Cortex.count


HTTP API
--------

HTTP APIS go here.



.. _dev_storm_opts:

.. _dev_storm_message:

Message Types
=============

The following messages may be yielded from the Storm runtime to a remote caller.

init
----

First message sent by a storm query runtime.

It includes the following keys:

task
    The task identifier (which can be used for task cancellation).

tick
    The epoch time the query execution started (in milliseconds).

text
    The storm query text.

Example::

    ('init',
     {'task': '8c90c67e37a30101a2f6a7dfb2fa0805',
      'text': '.created | limit 3',
      'tick': 1539221678859})


node
----

This represents a packed node (also called a ``pode``).

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

print
-----

The print event contains a message intended to be displayed to the caller.

It includes the following keys:
- mesg: The message to be displayed to the user.

Example::

    (print, {'mesg': 'I am a message!'})

This can be produced by users with the ``$lib.print()`` Storm API.

warn
----

The warn event contains data about a non-fatal errors encountered when processing something.

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

If the Storm runtime is cancelled for some reason, there will will be no ``err`` or ``fini`` messages sent.
This is because the task cancellation may tear down the channel and we would have an async task blocking on
attempting to send data to a closed channel.

Additional keys may also be present.

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
    The epoch time the query execution finished (in milliseconds).

took
    The amount of time it took for the query to execute (in milliseconds).

count
    The number of nodes yielded by the runtime.

Example::

    ('fini', {'count': 1, 'tock': 1539221715240, 'took': 36381})

.. note::

    If the Storm runtime is cancelled, there will will be no `err` or `fini` messages sent. This is
    because the task cancellation may tear down the channel and we would have an async task blocking
    on attempting to send data to a closed channel.

prov\:new
---------

Provenance messages

node\:edits
-----------

FIXME

node\:edits\:count
------------------

FIXME

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

csv\:row
--------

FIXME

look\:miss
----------

FIXME

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

        # Using lookup mode, the query text, before switching command mode with a | character,
        # will have its text scrapped for simple values such as FQDNs, IP Addresses, and Hashes
        # and attempt to lift any matching nodes.
        opts = {'mode': 'lookup'}

        # Using autoadds mode, the query text is scrapped like in lookup mode; and for any
        # values  which we try to lift that do not produce nodes, those nodes will be added
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

        opts = {'readonly': 'count'}

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

This is a set of rules that can be provided to the Storm runtime which dictate the tags that are included in the
packed nodes.

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
providing data to the runtime that is used with a ingest script, or to provide secrets to the Storm runtime so
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

The View iden in which to run the Storm query in. If not specified, the query will run in the users default view.

Example:

    .. code:: python3

        opts = {'view': 31ded629eea3c7221be0a61695862952}



