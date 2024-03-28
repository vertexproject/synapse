.. _dev_architecture:

Synapse Architecture
####################

When viewed as a library, not just an application, Synapse is made of up a few core components and concepts.

Library Architecture
====================

The Synapse library is broken out in a hierarchical fashion. The root of the library contains application level code,
such as the implementations of the Cortex, Axon, Cryotank, as well as the Telepath client and server components.
There are also a set of common helper functions (common.py_) and exceptions (exc.py_). There are several submodules
available as well:

synapse.data
  Data files stored in the library.

synapse.lib
  The lib module contains many of the primitives used by applications in order to implement them.

synapse.lookup
  The lookup module contains various lookup definitions.

synapse.models
  The models directory contains the core Synapse data model definitions.

synapse.servers
  The servers module contains servers use to start and run Synapse applications.

synapse.tests
  This is test code. It also contains a useful helper ``synapse.tests.utils`` which defines our base test class.

synapse.tools
  The tools module contains various tools used to interact with the Synapse ecosystem.

synapse.vendor
  This contains third-party code and associated LICENSE files. This is for internal library use only; no external API
  stability is guaranteed for any libraries under this module.

Object hierarchies
==================

There is one base class that many objects inherit from, the ``Base`` (base.py_) class. The ``Base`` class provides a
few useful components (including, but not limited too):

- A way to do asynchronous object construction by override the ``__anit__`` method. This method is executed inside the
  python ioloop, allowing the object construction to do async function calls.  An implementer still needs to call
  ``await s_base.Base.__anit__(self)`` first in order to ensure that the ``Base`` is setup properly.
- A way to register object teardown methods and perform object teardowns via the ``onfini()`` and ``fini()``. These
  allow us to keep more granular control over how things are shut down and resources are released, versus relying solely
  on the garbage collector to handle teardowns properly.  Often times, order matters, so we need to be sure that things
  are torn down cleanly.  These routines can be registered during ``__anit__``.
- ``Base`` objects are made via await the call to the ``Base.anit()`` function.  If the ``__anit__`` function completed
  then the ``anitted`` attribute on the object will be True, otherwise it will be False.
- Context manager support. The ``Base`` object has native async context manager support, and upon exiting the context
  it will call ``fini()`` to do teardown. This pattern is convenient since it allows us to freely create ``Base``
  classes without having to remember to always have to tear them down.
- The ``Base`` contains helpers for implementing an observable design pattern, where functions can be registered as
  event handlers, and events can be fired on the object at will. This can be very powerful for signaling across
  disparate components which would be otherwise too heavy to have explicit callbacks for.
- The ``Base`` contains helpers for executing asyncio coroutines on the ioloop.  This is most commonly done via the
  ``schedCoroTask`` routine.  This will schedule the coroutine to run on the ioloop, register the task with the ``Base``
  and return the asyncio future. During ``Base`` fini, any coroutines still executing will be cancelled.  This makes it
  very easy to schedule free-running coroutines from any ``Base`` class.

There are a few very important classes which use the ``Base`` object:

- The Synapse ``Cell``.  This is a batteries included primitive for running an application.
- The Telepath ``Daemon``.  This serves as a RPC server component.
- The Telepath ``Proxy``. This serves as a RPC client component.

The ``Cell`` (cell.py_) is a ``Base`` implementation which has several components available to it:

- It is a ``Base``, so it benefits from all the components a ``Base`` has.
- It contains support for configuration directives at start time, so a cell can have well defined configuration
  options availble to it.
- It has persistent storage available via two different mechanisms, a LMDB slab for arbitrary data that is local to the
  cell, and a ``Hive`` for key-value data storage that can be remotely read and written.
- It handles user authentication and authorization via user data stored in the ``Hive``.
- The ``Cell`` is Telepath aware, and will start his own ``Daemon`` that allows remote access.  By default, the ``Cell``
  has a PF Unix socket available for access, so local telepath access is trivial.
- Since the ``Cell`` is Telepath aware, there is a base ``CellApi`` that implements his RPC routines.  ``Cell``
  implementers can easily sublcass the ``CellApi`` class to add additional RPC routines.
- The ``Cell`` also contains hooks for easily starting a Tornado webserver.  This allows us to trivially add web API
  routes to an object.
- The ``Cell`` contains a ``Boss`` which can be used to remotely enumerate and cancel managed coroutines.

Since the cell contains so much core management functionality, adding functionality to the Synapse ``Cell`` allows
**all** applications using a Cell to be immediately extended to take advantage of that functionality without having to
revisit multiple different implementations to update them.  For this reason, our core application components (the
``Axon``, ``Cortex``, and ``CryoCell``) all implement the ``Cell`` class.  For example, if we add a new user management
capability, that is now available to all those applications, as well as any others ``Cell`` implementations.

The application level components themselves have servers in the ``synapse.servers`` module, but there is also a generic
server for starting any cell, ``synapse.servers.cell``.  These servers will create the ``Cell``, and also add any
additional RPC or HTTP API listening servers as necessary.  Those are the preferred ways to run an application
implemented via a ``Cell``.

.. _arch-telepath:

Telepath RPC
============

The Telepath RPC protocol is a lightweight RPC protocol used in Synapse.  The server component, the previously mentioned
``Daemon``, is used to share objects. An object may or may not be Telepath aware. In the case that it is not aware, all
of its methods are exposed via Telepath. Objects which are Telepath aware, such as the ``Cell``, implement an API
interface that allows much more fine grained control over the the methods which are remotely available.

The base Telepath client is the ``Proxy`` class, this is used to connect to the Daemon.  The ``Proxy`` intercepts
attribute lookups to make and set remote method helpers at runtime, and sends those requests to the Daemon to be
serviced.  A *very* brief example of this is the following:

::

    import synapse.telepath as s_telepath

    url = 'tcp://user:secret@1.2.3.4:27492/someObject'

    async with await s_telepath.openurl(url) as proxy:

        # Make attribute called "someMethod" on the proxy
        # then send a task to the server called "someMethod"
        # with the argument of somearg=1234
        resp = proxy.someMethod(somearg=1234)
        # The resp is the result of calling the someMethod argument on
        # the object named someObject on the daemon.
        print(resp)

A few notes about Telepath:

- Telepath remote call arguments and server responses must be able to be serialized using the msgpack protocol.
- Telepath supports generator protocols; so a server API may be a synchronous or asynchronous generator.  From the
  proxy perspective, these are both considered asynchronous generators.
- The Telepath ``Proxy`` contains some helpers that allow is to be used from non-async code. These helpers run their
  API calls through the currently running ioloop, and will cause the client to make an ioloop if one is not currently
  running.
- Remote calls that raise exceptions on the server will have that exception serialized and sent back to the ``Proxy``.
  The ``Proxy`` will then raise an exception to the caller.
- Methods calls prefixed with a underscore (``_somePrivatMethod()`` for example) will be rejected by the ``Daemon``.
  This does allow us to protect private methods on shared objects.


.. _exc.py:                  https://github.com/vertexproject/synapse/blob/master/synapse/exc.py
.. _common.py:               https://github.com/vertexproject/synapse/blob/master/synapse/common.py
.. _cell.py:                 https://github.com/vertexproject/synapse/blob/master/synapse/lib/cell.py
.. _base.py:                 https://github.com/vertexproject/synapse/blob/master/synapse/lib/base.py
