Changelog
=========

v0.0.55 - 2018-05-09
--------------------

## Bugs
- #769 - Add a ``time.sleep()`` call in the ``synapse.lib.net.Plex._runPollLoop`` loop which is executed when no events obtained from the selector. This prevents CPU usage from spiking on systems without Epoll enabled (mainly OSX).


v0.0.54 - 2018-05-01
--------------------

## Enhancements
- #740, #746 - Made OSX test runners run faster by compiling Python 3.6.5 once using pyenv and then use a venv per branch.
- #745 - Increase information included in the ``AuthDeny`` exception by ``Cortex.reqUserPerm()`` to include the username of the user who did not have the permission.

## Bugs
- #739 - The ``synapse.tools.easycert`` ``--importfile`` option was not properly parsing certificate paths.  This meant that real-world certificates were unable to be imported into a certstore.  This has been addressed.


v0.0.53 - 2018-04-27
--------------------

## Enhancements
- #734 - Add a smaller default LMDB map size for lmdb databases which do not need to be large.

## Bugs
- #733 - Fix cryotank indexing test races.
- #735 - Fix a race which can occur during ``synapse.lib.net.Plex`` teardown.
- #736 - Fix neuron test race conditions.


v0.0.52 - 2018-04-27
--------------------

## Summary

OSX Support is preliminary restored in this release.  Windows is still not supported, however we are aware of users successfully using Synapse under the Windows Subsystem for Linux (WSL) available in Windows 10.

## New Features
- #697, #722 - The ``CryoTank`` now supports selective field indexing using Synapse type normalization.  This allows for records to be retrieved based on indexed values.
A remote API has been added for this and is available via the ``CryoClient`` for managing indexing on tanks managed by a ``CryoCell``.
- #723 - Add a ``get:opers()`` command to Storm which allows the introspection of which registered storm operators are available to a ``Cortex``.
- #725 - Added a``Cortex`` RBAC system for controlling node creation, deletion, property setting and tagging.  Currently, this is applicable to users using SSL to share out Cortexes, since user authentication is done via SSL certificate common name.  This does require explicit configuration to use. See ``synapse.lib.iq.SynTest.getSslCore()`` for a configuration example.  The RBAC interface can also be configured via cmdr.
- #727 - Move from using ``select.Epoll()`` to ``selectors.DefaultSelector()`` for the global plex defined in ``synapse.lib.net``. This allows restoring OS X use of Synapse.

## Enhancements
- #724 - Add cell Ctor type when doing cell registration. This allows a  ``Neuron`` and ``CellPool`` to have awareness of what types of objects have registered with it.
- #726 - Refactored ``CryoCell`` and ``CryoClient``.

## Bugs
- #728 - Fix a race condition in cryotank index testing.
- #535, #730 - Fix Cmdr CLI loop for OSX.  Thanks @blackout for the bug report.
- #731, #732 - Fix unittests so that they run on OSX.

v0.0.51 - 2018-04-13
--------------------

## Enhancements
- #719 - When doing a type norm for ``time``, include the ``valu`` being normed in the ``BadTypeValu``.
- #720 - When a node is deleted using ``Cortex.delTufo()``, the node form, primary property, and current user scope are logged at the info level.  This also applies to nodes deleted via Storm and splices.
- #721 - Add test showing that a ``splice`` contains the current user.

v0.0.50 - 2018-04-08
--------------------

## New Features
- #714 - ``inet:addr`` type was modified to represent a URL like format to represent tcp/udp/icmp clients and servers.  The ``inet:client`` and ``inet:server`` types were added, which are subs of the ``inet:addr`` type.
- #714 - Added ``inet:servfile`` comp form.  This is the intersection of an ``inet:server`` and a ``file:bytes`` node.  It a file available from a given server over an arbitrary protocol.
- #714 - Added ``inet:download`` guid form to represent an instance of a ``inet:client`` downloading an arbitrary ``file:bytes`` from a ``inet:server`` at some point in time.
- #717 - Storm operators may now send status messages along with their results.  These messages are displayed after any nodes are printed.  This is a backwards-compatible change.  There are no built-in Storm operators which use this currently.

## Enhancements
- #709, #711, #712 - Move to CircleCi as a CI testrunner. Remove all Drone / Travis CI code.
- #715 - Remove the automatic ``EventBus`` event propagation from a ``Cortex`` to a loaded ``CoreModule``. This has an unnecessary performance impact and is not needed for a ``CoreModule`` to subscribe to events from the ``Cortex``. A ``CoreModule`` implementation has a reference to the ``Cortex`` directly and can listen for the events as needed.
- #717 - The ``SynTest.getDmonCore()`` API now sets the local scope variable ``syn:core`` to refer to the actual ``Cortex`` object which backs the ``Proxy`` object yielded by the API.  This allows test writers using that API to access the underlying ``Cortex`` to perform function calls which may not be possible to execute over the ``Proxy``.
- #714 - Update the ``it:av:sig`` form to be the intersection of a ``it:prod:soft`` and a ``str:lwr``.  Previously, this was a ``sepr`` type containing an ``ou:alias`` but that does not account for an organization having multiple products.  The ``it:av:filehit`` also was changed from a ``sepr`` to a ``comp`` type since signature names are not safe to use in seprs as sepr character may appear in the names.  There are no migrations in place for these modeling changes.  Please reach out to Vertex Project on Slack if you have data using these forms that requires migration.
- #714 - Update the ``synapse.models.inet.ipv6norm()`` (used for normalizing IPv6 types) now also returns a ``ipv4`` sub if the normalized address is in the IPv4 address space.
- #718 - Remove the Storm vartree implementation. It was incomplete and will be replaced in the future with an implicit pivot syntax which will achieve the same effect in a cleaner fashion.

## Bugs
- #710 - Fix a test which was leaking a CellPool object which was attempting a reconnect loop which would never reconnect.
- #716 - Normalize tags when calling ``Cortex.getTufosByTag`` or doing tag filtering in Storm.

v0.0.49 - 2018-03-26
--------------------
V0.0.49 is primarily a bugfix release to address regressions and issues from v0.0.47.

## Enhancements
- #706 - The ``Cortex.formNodeByProp()`` API will now call ``setTufoProps()`` on a node if it already exists and properties are passed into ``formNodeByProp``.  This allows properties to be added in a “last caller wins” scenario.
- #706 - The ``node:add`` splice now accepts a ``tags`` value which contains a list of tags to add to the node created by the splice.

## Bugs
- #705 - Fix an issue in ``Configable``\’s ``@confdef`` decorator helper for identifying config options in classes.  This method was previously skipping Telepath proxy objects during introspection; and a regression was introduced which didn’t properly skip non-callable object methods.  This caused  an issue when doing introspection on objects which had Telepath ``Proxy`` objects as the value of class attributes.  This regression has been fixed by properly skipping non-callable class members.
- #706 - Splice changes introduced in v0.0.47 were improperly wrapping messages. This meant that the ``Cortex.splice()`` and ``Cortex.splices()`` APIs required splice messages as though they came off of the ``EventBus``.  This required sending duplicate, redundant data over the network during remote calls.  This splice reactors now expect unpacked splices.  This does not affect splices written to splice files or splices converted to the new format, since those splices were already unwrapped.
- #707 - The Telepath socket multiplexor (``synapse.lib.socket.Plex``) had an issue added where xlist sockets may not have been properly culled from the list of Sockets maintained by the plex.  The xlist sockets were the same as the rlist sockets, so this has been simplified.  In addition, an identity check for fileno was changed to a equality check.

## Documentation
- #706 - Examples of all different``splice`` message forms have been added in a ``Cortex`` test ``test_cortex_splices``.  This can be used as an immediate reference to people doing manual splice creation.
- #708 - Added ``synapse.cryotank.CryoCell`` to the automatically generated ``Configable`` docs.


v0.0.48 - 2018-03-21
--------------------

## New Features
- #698 - Add ``source``, ``seen``, ``record`` and ``recref`` forms to allow for tracking data sources and references in a ``Cortex`` hypergraph.
- #698 - Add ``ou:meet``, ``ou:meet:attendee``, ``ou:conference``, and ``ou:conference:attendee`` forms to allow for tracking meetings and conferences, as well as their attendees.

## Enhancements
- #702 - ``synapse.lib.datapath`` now has a ``DataPath()`` class which is used to represent the steps in a given path. This allows pre-computation of a given datapath to reduce overhead when the same path may need to be parsed multiple times.

## Bugs
- #703 - Ensure that the ``AxonCell`` was sending the correct marshalled exceptions.
- #704 - Change the ``auth`` value of the ``Cortex`` configuration for a ``cell:pool`` to be a Base64 encoded version of the msgpack encoded auth dictionary.  This allows for configuring the ``cell:pool`` via a JSON ``Daemon`` configuration file.


v0.0.47 - 2018-03-14
--------------------

## Summary

There are a sizeable amount of changes included in v0.0.47.  A few items are highlighted here; please see the sections after the summary for a full list of new features and enhancements.

### Notable New features

- A new data storage object, the ``CryoTank``, has been introduced.  This utilizes LMDB to perform fast storage and retrieval of structured records.  This can be used to quickly store and retrieve large feeds of data.
- A new service architecture has been implemented in Synapse.  This uses an asynchronous, generator based approach to networking and remote calling.  This has been utilized to reimplement the ``Axon`` storage (now ``AxonCell``), as well as implementing the networking protocol for the ``CryoTank``, the ``CryoCell``.  Detailed documentation for this service architecture will be included in future Synapse release.
- A new LMDB key-value store helper has been added, the ``KvStor``.  This is used to implement persist dictionary and set objects, which are used as helpers to the ``Cell``.  Previously, a service could use their own Cortex as a simple KV store, but that was potentially heavy thing to do.  This alternative is considerably lighter for these simple use cases.
- Storm now supports the use of subquery filters.  An example query is the following:  ``inet:dns:a -{ :ipv4 -> inet:ipv4 +cc=us } `` which will lift all ``inet:dns:a`` nodes, then filter nodes whose IPv4 address has a ``us`` country code. Detailed documentation for this will be added in a future Synapse release.

### Backwards Incompatible Changes

- A global socket multiplexor, implemented using EPOLL, has been added to Synapse.  This change means that Synapse will only work on Linux at the moment.  The Vertex Project does plan on restoring Windows and OSX support in a future release.
- The Cortex Splice format has changed, in order to support better filtration.  This requires that splice producers and splice consumers update simultaneously to v0.0.47.  If users have existing splice logs that need to be updated, a helper function has been written to to convert an existing splice log file to the new format.  See the notes below for additional information.
- The following Synapse components have been removed or altered significantly:
  * ``synapse.axon`` has been rewritten substantially.  In addition, it no longer imports ``synapse.lib.hashset`` using a star import.
  * ``synapse.lib.persist`` has been removed.  It is no longer used in core Synapse code.
  * ``synapse.lib.heap`` has been removed.  It contained an implementation error and is no longer used in core Synapse code.
  * ``synapse.lib.atomfile`` has been changed to currently only support Linux.

### Known Issues

- #700 - The ``axon:upload`` handler on the ``AxonCell`` can allow bytes to be stored twice in the same ``BlobStor``.  This may result in a ``BlobStor`` having bytes which the ``AxonCell`` does not have direct knowledge of.  No data is lost here, but extra disk space may be consumed.

## New Features
- #637, #650, #695 - Added ``synapse.lib.cell``.  This contains the ``Cell`` class and related helper classes.  The ``Cell`` is the base class for a microservices architecture.  Similar to a ``CoreModule``, the ``Cell`` is designed to be subclassed and have some functions overridden.  See ``Cell`` docstrings for additional notes.
- #637, #695 - Added ``synapse.neuron`` module. This contains the ``Neuron()`` class which is used as a service directory for Synapse ``Cell`` based services.  The ``Neuron`` is responsible for doing service provisioning and service name resolution.  Additional documentation related to Neuron, Cell architectures will be included in a future Synapse release.
- #650, #679 - The ``synapse.axon.Axon`` implementation was removed, and replaced by a new ``AxonCell`` and ``BlobCell`` implementations.  This decouples the ``Axon`` idea from the ``Cortex`` implementation, and makes the ``AxonCell`` solely responsible for storing files and doing retrieval by SHA256 hash.  The ``AxonCell`` acts as a indexing master, while multiple ``BlobCells`` need to be used in order to store files. The  ``AxonClient`` helper is available to interact with a ``AxonCell``, while the ``BlobClient`` is available to interact with the ``BlocCell``.  The use of this new storage implementation does require the deployment of a ``Neuron``, since these are all ``Cell`` based services.  Additional documentation related to Axon architecture will be included in a future Synapse release.
- #637, #654, #655, #674 - Added a new module, ``synapse.cryotank``. It contains a ``CryoTank()`` class, which is used for storing structured data (anything that can be msgpacked) into a LMDB database.  It also contains a ``CryoCell()`` class for creation, management, deletion of ``CryoTank`` objects, as well as for putting data into remote ``CryoTank``’s.  It has a ``CryoClient()`` helper object which can be used to interact with the remote ``CryoCell``.
- #648, #649, #672, #674, #675 - Added ``synapse.tools.cryo.cat`` to look at data from remote ``CryoTank``s, dump that data to disk in different formats, or add data to a remote ``CryoTank`` when reading data from stdin.
- #681 - Add ``cellpool:conf`` config option to the ``Cortex``.  This is a dictionary which takes three value, a ``auth`` blob for talking to a ``Neuron``, as well as the ``host`` and ``port`` used to connect to the ``Neuron``.  The configuration of a ``cellpool:conf``, and subsequentially ``axon:name``, is required in order to allow a ``Cortex`` to save bytes to a ``AxonCell`` using the ``formNodeByBytes()`` and ``formNodeByFd()`` APIs.
- #637 - Added ``RetnWait()`` to the ``synapse.lib.thread``.  This can (and should) be used as a context manager, which can emulate a synchronous callback occuring, while waiting for a local ``thread.event`` to be set.
- #650 - Added ``synapse.lib.lmdb``. This contains several LMDB related classes for future use with new Cortex storage layers.  The APIs for these objects should not be considered stable for third party use at this time.
- #637, #642, #658 - Added a new module, ``synapse.lib.net``, to handle asynchronous networking code.  This includes a new EPoll based multiplexer for Socket IO.  An instance of this plex is used as part of a global plex (located in ``synapse.glob``).  This change currently makes Synapse only compatible with Linux operating systems.  Eventually, we’ll re-add Windows and OSX support in a future release.
- #687 - Added ``ps:persona`` and ``ps:persona:has`` forms to represent the idea of a persona.
- #637 - Added a new way to marshall exceptions, ``synapse.common.getexcfo()`` which will be the preferred way to marshall exceptions moving forward for Synapse code.
- #636, #638, #676, #678, #689 - Added the ``synapse.lib.crypto`` module.  This contains several new modules.  ``synapse.lib.crypto.tinfoil`` contains a simple AESGCM encryption/decryption class called ``TinFoilHat``.  ``synapse.lib.crypto.ecc`` contains helpers for doing ECC key pair generation and doing ECDHE key exchange.  ``synapse.lib.crypto.vault`` contains a ``Vault()`` class. The ``Vault()`` can be used to store key pairs and do key signing locally.
- #634 - The Storm CLI command ``jointags()`` was split into ``jointags()`` and ``pivottags()`` which behave similarly to the ``pivot()`` and ``refs()`` commands, respectively. The old default behavior for ``jointags()`` was moved to ``pivottags()``, and the current ``jointags()`` behavior now reflects the old ``jointags(keep_nodes=1)`` behavior.
- #628, #659 - Added ``synapse.lib.kv``.  This module contains the ``KvStor()`` class; which implements a LMDB backed kv-store.  An instance of the ``KvStor()`` object can be used to get ``KvLook()``, ``KvDict()`` and ``KvSet()`` objects.  The ``KvLook`` can be used to do ``key=valu`` type storage, which is directly backed by the LMDB database.  The ``KvDict`` can be used for ``key=valu`` storage, but it also keeps a in-memory dictionary of the contents to avoid database lookups.  The ``KvSet`` can be treated similarly to a ``set()`` object, but addition and removal is backed by the LMDB database.
- #691 - Added a initial HTTP model for tracking to the ``inet`` model.  Added ``inet:http:request``, ``inet:http:response``, ``inet:http:header``, ``inet:http:param``, ``inet:http:reqhead``, and ``inet:http:reqparam`` forms.
- #606 - Added ``synapse.lib.membrane`` and ``Membrane()`` class.  The ``Membrane`` object can be used as a filter on the events fired by a ``EventBus`` to determine whether or not they are sent to a function provided to the ``Membrane()`` object.
- #606 - Added a ``membranes`` config option to the ``Cortex`` which applies rules to ``splice`` events and puts splices into a named ``Fifo`` for later consumption.

## Enhancements
- #667 - Added subquery based filtration for Storm. Subqueries take all of the query nodes, apply either a positive or negative a filter to those nodes, and then add matching nodes back to the query results.
- #685 - Migrated ``ou:has``\* forms to a generic ``ou:org:has`` Xref form.  Add ``seen:min`` and ``seen:max`` secondary properties.
- #650 - Added ``genraises()`` API to ``synapse.lib.iq.SynTest``. This mimics the ``raises()`` API, but expects the function to be a generator. This consumes the generator in a bound local and expects that to raise.
- #650 - Added ``getAxonCore()`` API to ``synapse.lib.iq.SynTest`` to get a ``TstEnv`` instance which has a Axon, Cortex, Blob, Neuron, Daemon and clients configured already.
- #650 - Added ``synapse.common.ehex()``/``synapse.common.uhex()`` wraps around ``binascii.hexlify()`` and ``binascii.unhexlify()`` APIs.
- #650 - Added ``synapse.common.buid()`` to generate a 32 byte hash. Unlike the ``guid()`` API, this returns bytes.  It can take a msgpackable object to generate a stable buid.
- #650 - Added ``synapse.common.spin()`` to consume a generator and discard the results as fast as possible.
- #686 - Updated ``synapse.tools.autodoc`` to extract configable docs for a defined list of classes which use the ``initConfDefs()`` API to to define their config options.
- #650 - Added ``initConfDefs()`` API to ``synapse.lib.config.Configable()``. This function is executed during ``__init__``. It is intended to be overridden by implementers, and will replace use of the ``@confdef`` decorator function over time. Care must be taken by implementers when class mixing or inheriting that a new class properly calls or overrides  ``initConfDefs``.
- #650 - Updated ``synapse.lib.queue.Queue`` behavior to raise an exception (``IsFini`` or ``TimeOut``) when ``get()`` has no objects to return.  Previously this returned ``None``; however it was impossible to distinguish if the queue legitimately returned ``None`` or there was a timeout or if the ``Queue`` had been fini’d.
- #673, #681 - Changed the ``Cortex`` config option of ``axon:url`` to be ``axon:name``.  This is the name of the ``AxonCell`` resolve via the cores’ ``CellPool``.
- #670 - ``ou:hasalias`` form to note when a org has an alias or alternative name.
- #671, #687 - Migrated ``ps:has``\* forms to a single ``ps:person:has`` xref form.  Add ``seen:min`` and ``seen:max`` secondary properties.
- #631 - The ``synapse.async`` module was renamed to ``synapse.synasync`` in order to allow for future compatibility with Python 3.7.
- #637, #650 - Added ``iterfile()``, ``loadfile()`` and ``dumpfile()`` APIs to ``synapse.lib.msgpack``. These iterate over a file, load the contents of a file, and save a value to a file, respectively.
- #637 - Removed ``synapse.lib.heapfile``. It had implementation errors which caused issues with data recovery and is no longer used for backing ``Axon`` storage.  In addition, ``synapse.lib.persist`` was also removed since it is no longer being used.
- #637 - Added ``synapse.lib.const`` to store constants.
- #637 - The ``AtomFile`` implementations were simplified to use ``pread``/``pwrite`` and drop memory mapped file support.
- #637 - A new decorator API, ``inpool`` was added to fire functions in the synapse global thread pool.  This is available from ``synapse.glob``.  Assuming ``synapse.glob`` is imported as ``s_glob``, it can decorate functions as ``@s_glob.inpool``.
- #637 - The ``DmonConf()`` class has been updated to parse a ``cells`` directive, which can be used to launch ``Cell`` based objects. These objects are run in their own processes.
- #640, #641 - The ``SynTest`` helper function ``getLoggerStream()`` now yields a ``io.StringIO`` object which is mixed in with a ``threading.Event`` object. In addition, the ``getLoggerStream()`` now takes a second, optional, argument which must be a string.  When a log message containing that string is logged, the event will be set.  This allows writing tests which wait for a log message to be logged prior to continuing the test.
- #635 - Added  ``seen:min`` and ``seen:max`` secondary properties to ``inet:dns:req``.
- #632 - Added ``loadConfPath()`` API to ``syapse.lib.config.Configable`` to load configuration options from a JSON file at a given path.
- #629 - Changed the``digests()`` API in ``synapse.lib.hashset.HashSet()`` to return the digests in bytes instead hex.
- #627 - Added a ``waitall()`` API to ``synapse.lib.iq.TestSteps()`` to wait for all steps to complete.
- #626 - Added ``lockfile()`` API to ``synapse.common``. This is a helper for advisory locking around a file provided by the ``fcntl`` library.
- #620 - In Storm, lifts by form which are followed by a positive tag filter are now optimized to use a single lift-by-tag operation at the storage layer.
- #615 - The use of limits in the Storm query language has been normalized. For operators which consume the input set of nodes, a limit applies a maximum number of nodes to the output set. For operators which do not consume the input set of nodes, a limit applies to the maximum number of nodes added to the current working set.
- #619 - Add test showing that read-only properties can be set via ingest if they do not previously exist.
- #614 - Added a ``--importfile`` switch to the ``synapse.tools.easycert`` tool to assist with easily importing a certificate file to their certdir.
- #616 - Added ``isTufoProp()`` API to the ``DataModel`` to check to see if a property is a valid prop for the currently loaded data model.
- #600 - Splices format was changed to better encapsulate the splice to support filtering.  Old splice logs will not be replayable as is, and can be converted with ``synapse.lib.splices.convertSpliceFd()``.  This change is backwards incompatible with previous versions of synapse.
- #611 - Added ``seen:min`` and ``seen:max`` secondary properties to ``inet:urlredir``.
- #610 - Splice Pump producers have debug messages logged about splice consumption, errors, and remaining splices.

## Bugs
- #690 - Defvals passed to configuration options for ``synapse.lib.config.Configable`` will now smash existing values for a given option when they are set.
- #493, #677 - Removed unused (and not working) ``ssh://`` link implementation stub.
- #669 - Removed unused ``parse_macro_join`` function from ``synapse.lib.syntax``.
- #668 - Fix an issue where the ``inet:fqdn`` normalization would allow an internationalized domain to be stored after doing IDNA encoding, but would fail to render in the Storm CLI due to it actually being invalid Punycode.  The raw string is now returned if the string starts with ``xn--``.  This is a harsh reminder the world is not tidy.
- #657 - Fix race conditions related to ``Fifo`` resync/ack/push operations.
- #652 - The ``synapse.lib.queue.Queue`` object would accept additional data after it had either ``done()`` or ``fini()`` called on it.  This is no longer allowed.
- #651 - Fix a bug in ``synapse.lib.config.Configable`` where config options passed in during ``__init__`` were set prior to all confdefs being loaded.
- #637 - ``synapse.common.gendirs()`` would fail if the directories needed to be made by ``os.makedirs()`` already existed.  This has been fixed.
- #633 - Removed ``py`` command from the base CLI commands. This could be used to perform authenticated remote code execution as the process running the Daemon object that a user connected to.
- #623 - ``node:del`` events fired by ``Cortex.delTufo()`` were incorrectly setting the primary property on the ``node:del`` events. This was preventing tag deletion from working properly.
- #617 - Clean up ``Cortex`` fifo APIs to not automatically incref ``Fifo`` objects for every object access.
- #618 - Refactored ``Cortex.__init__()`` to allow using the ``syn:cortex`` alias to start up a ``Cortex`` via a ``Daemon`` properly.
- #616 - Fix bug in ``_initCoreFifo`` which prevented Fifo’s from being initialized on startup properly. Changed the ``syn:fifo`` node to a comp type.

## Documentation
- #630 - Updated docstrings in ``synapse.lib.sqlite``.


v0.0.46 - 2018-03-06
--------------------

## Bugs
- Pull in version bounds for third-party packages from the master branch. This addresses an immediate issue where Synapse fails to work with a pypi installation and Tornado 5.0.0 is installed.


v0.0.45 - 2018-02-13
--------------------

## New Features
- #661 - Added the ``inet:group`` form and type. This is analogous to the ``inet:user`` form for tracking a given group name.

## Enhancements
- #666 - Add ``ps:person:name:en`` and various ``name:en`` subprops props to distinguish between localized and English versions of names.
- #661 - The ``inet:web:group`` form was made more robust. The second field of the sepr type was renamed to ``:id`` to represent a site specific identifier, freeing the ``:name`` property up to represent a descriptive name of the group.  ``:name:en`` was added to provide for a English version of the name.  ``:signup``, ``:signup:ipv4`` and ``signup:ipv6`` props were added to track when groups were created.  ``:loc`` and ``:latlong`` props were added to allow for some location based tracking.  ``:seen:min`` and ``:seen:max`` secondary properties were added to track when a group was active.
- #662 - The python ``msgpack`` library was version locked to 0.5.1.
- #663 - Added ``:name:en`` and ``:realname:en`` secondary props to ``inet:web:acct`` for tracking English specific versions of a name.

## Bugs
- #624 - The ``ps:person`` was missing the ``:name:middle`` field. This has been added.
- #660 - The ``ou:member`` form was broken. This has been changed to be a Comp type and had the secondary property ``:end`` added to it.


v0.0.44 - 2018-01-11
--------------------

## Notices related to v0.0.44
The minimum version of msgpack used by Synapse has been upgraded to be at least 0.5.0. This is complicated by the fact that the ``msgpack-python package`` was renamed to ``msgpack`` by its maintainers. Installation of Synapse from PyPi using the sdist and wheel packages should upgrade msgpack in a working state, and docker image users should not be affected by this change. Users which directly use a checkout of the Synapse Github repository should uninstall msgpack-python and then install msgpack.  This can be done with the following commands (you may need to adjust them for your installation; accounting for aliases or the use of `python3`, etc):

- `python -m pip uninstall msgpack-python`
- `python -m pip install msgpack`

The ``synapse.lib.heap.Heapfile`` and ``synapse.axon.Axon`` structures are planned to undergo a significant rewrite, possibly landing as early as v0.0.45. These rewrites will not be backwards compatible, in order to account for design issues in these structures. If you are using these classes for doing data storage, please reach out to us via Slack as soon as possible (see https://github.com/vertexproject/synapse/blob/master/README.rst for a link to join our Synapse Slack chatroom).

## New Features
- #592 - Added GUID type ``it:auth:passwdhash`` to store password hashes without requiring the plaintext password.
- #604 - Added ``synapse.lib.atomic.Counter()`` class as a thread safe counter object.
- #595 - Added the ``rcode`` secondary property to the ``inet:dns:look`` form to allow encoding the DNS response code for a given lookup.
- #595 - The ``it:dev:regkey`` type is now a lowercased string.  Existing ``it:dev:regkey`` and ``it:dev:regval:key`` values will be automatically lowercased as a model migration.
- #607 - Added ``Axon.getAxonStatus()`` and ``AxonHost.getAxonHostStatus()`` APIs to get runtime information about Axons.

## Enhancements
- #591 - Removed the Cortex CLI command ``nextseq`` in favor of using the Storm macro command ``nexttag()``.
- #591 - Add Storm test coverage.
- #593 - Added ``puts()`` API to the ``synapse.lib.fifo.Fifo`` object to the ``Fifo`` structure to allow for bulk object adding.
- #596 - Added Axon tests to show a clone sync operation restarting after a persist offset file is removed.
- #601 - Ensure the ``synapse.lib.heap.Heap`` file storage only grows upward and cannot be resized down by replaying a resize event.
- #602 - Set backoff / backoff-retry values for the Drone ci configuration for the git plugin.
- #603 - The ``synapse.lib.tags.tufoHasTag()`` and ``synapse.lib.tufo.tagged()`` APIs were equivalent functions. ``tufoHasTag`` has been removed.
- #598, #609 - Updated msgpack-python>=0.4.8 to ``msgpack=>0.5.1`` as a dependency.
- #598 - Updated ``synaspe.lib.msgpack.Unpk`` msgpack unpacker helper to use the new ``tell()`` API introduced in msgpack 0.5.0.
- #598 - Added a future-proofing msgpack test to ensure we break when the msgpack python API eventually changes to assuming a strict utf8 compliance and can then versionlock our use of msgpack.
- #605 - Added simple integrity checking to the ``synapse.lib.heap.HeapFile`` structure.

## Bugs
- #591 - ``synapse.lib.cache.KeyCache`` behavior updated to no longer store cache valus if they are None.  If None was cached, that value was unable to be updated later.
- #594, #597 - Fix Ingest user docs which were using outdated forms. Thanks @tn3rt for the bug report!
- #599 - Fix ``AxonMixin.eatfd()`` and ``AxonMixin.eatbytes()`` to allow file descriptors and bytes which have zero bytes to be consumed.

## Documentation
- #605 - Rewrote API docstrings for ``synapse.lib.heap.HeapFile``.


v0.0.43 - 2018-01-02
--------------------

## New Features
- #590 - Added ``synapse.lib.remcycle.fetch()`` API which allows retrieving a URL using Tornado and executing a user provided callback to process the response.

## Enhancements
- #589 - Added the ability to set a ``tags`` directive in an Ingest ``forms`` definition; which allows setting per-form tags without adding the tags to the current or child scopes.


v0.0.42 - 2017-12-29
--------------------

## New Features
- #588 - Added a RFC2822 address parser and type/form, ``inet:rfc2822:addr``.  This normalizes and parses string identifiers and attempts to extract email addresses as a secondary property.

## Bugs
- #587 - Make `synapse.lib.msgpack` helper functions resilient to unmatched unicode surrogate characters. This also affects the ``synapse.lib.socket.Socket`` and ``synapse.lib.persist.Dir`` msgpack unpackers. This is done by passing ``unicode_errors='surrogatepass'`` to the msgpack pack/unpack functions. This makes synapse more resilient to malformed string data which may be encountered in the real world.

## Documentation
- #587 - Removed ``synapse.statemach``.  It was previously used for providing object persistence at an API level but has been unused within Synapse and was generally not a safe tool to use for third party use.


v0.0.41 - 2017-12-28
--------------------

## New Features
- #574 - Added ``EventBus.onWith()`` API.  This is a context manager which acts like ``.on()``, but the callback is removed when the context manager is exited.
- #575 - Added ``synapse.lib.iq.CmdGenerator()`` class to allow testing CLI command loops using unittest mock.
- #577 - Added ``synapse.lib.certdir.genClientCert()`` API to allow creation of a PKCS12 certificate bundle for a user certificate, private key and CA cert.
- #577 - Added a ``--p12`` option to the easycert tool.  This allows a user to bundle their certificate, private key and CA cert into a PKC12 formatted file.
- #578 - Added the Storm macro syntax ``<-`` to represent a ``join()`` operation.

## Enhancements
- #576 - The ``Daemon`` now fini's ``EventBus()`` objects in LIFO order when it is fini'd. In other words, objects created in a dmon configuration are torn down in reverse order that they are created.
- #576, #581 - Increased test coverage for CLI related tests.
- #577 - Updated tests for ``synapse.lib.certdir`` to ensure that the certificates made by ``certdir`` were correct.
- #577 - Updated tests for ``synapse.tools.easycert`` to ensure that the certificates made by ``easycert`` were correct.
- #578 - Updated the storm ``join()`` operator syntax to behave exactly like the ``pivot()`` operator with respect to source and destination properties. ``join()`` still is an additive operator which does not consume the source nodes.
- #583 - ``synapse.lib.remcycle.Hypnos`` now registers and persists ingest definitions as ``syn:ingest`` nodes in its Cortex.

## Bugs
- #579 - Fix a reference to ``onCtx`` (the original name for the ``EventBus.onWith()`` function).
- #584 - ``Cortex`` Storage backings had different behaviors when limit=0 was passed to functions which joined rows together to make tufos.  This has been fixed, so that a limit=0 API parameter will return 0 rows.

## Documentation
- #573 - Added telepath docstrings for ``evalurl()``.
- #577 - Rewrote API documentation for ``synapse.lib.certdir``.
- #586 - Updated the Storm ``join()`` documentation to reflect changes to its arguments.


v0.0.40 - 2017-12-11
--------------------

## New Features
- #564 - Added a ``int:2:str10`` typecast to convert a integer value to the base10 string value.
- #569 - The Telepath ``Proxy`` object now fires the local event ``tele:sock:runsockfini`` when the Proxy is attempting to reconnect to its remote ``Daemon``. This can be hooked by implementers to detect the loss of an existing connection to a remote ``Daemon``.
- #572 - The ``synapse.axon.AxonCluster`` helper object is now a subclass of ``EventBus``. This will now automatically close its corresponding ``SvcProx`` instance on its own ``.fini()``.
- #572 - Added the ``synapse.lib.iq.objhierarchy()`` function to extract a type hierarchy from nested tufo-style objects.  This can be a useful for debugging.

## Enhancements
- #565 - Increase Tornado related test timeouts from 5 to 30 seconds.
- #570 - Additional debug logging added to ``synapse.axon.Axon`` actions.
- #572 - Additional debug logging added to ``synapse.lib.persist.Dir`` actions.

## Bugs
- #561 - When a telepath Proxy object is made, by default it will create its own socket Plex object.  This Plex is now fini’d when the proxy is fini’d.
- #568 - Add ``synapse.glob`` to ``synapse.lib.socket`` imports to fix a missing reference.
- #567- The ``synapse.lib.persist.Dir.items()`` method yielded offsets which could switch from being relative offsets to being absolute offsets.  This has been changed to always yield absolute offsets.
- #570 - The ``synapse.axon.Axon._fireAxonClone`` thread now uses the ``tele:sock:runsockfini`` event to detect that a disconnect has occurred for its remote Proxy, and uses that to break out of its innermost ``synapse.lib.persist.Dir.items()`` loop.  The previous behavior would fail to reconnect if part of an Axon cluster went down and then came back up, as the Proxy contained potentially invalid link information instead of getting an updated link tufo from the Axon’s ServiceBus.
- #571 - Fini ``Axon`` threads after calling ``self.syncdir.fini()`` to ensure that any threads which are in the real time event pump from the syncdir can safely close their resources before attempting to stop any threads.

## Documentation
- #572 - Miscellaneous API docstring improvements.

v0.0.39 - 2017-12-11
--------------------

## New Features
- #553 - Synapse Docker images will now have ``-debug`` images available as well for all master and tagged builds.  This image is built off of the ``vertexproject/pydebug:3.6-slim`` image. This image has full GDB support for Python enabled.  See https://github.com/vertexproject/pydebug for more information.

## Enhancements
- #551 - Make 4096 bit RSA keys by default when using the ``synaspse.tools.easycert`` tool. Thanks @galyac!
- #550 - Add additional debug logging to Synapse when starting up a Cortex, executing remote methods via Telepath and around SSL errors.
- #554 - Validate the Storm ``tree()`` ``recurlim`` argument is greater than or equal to zero.
- #557 - ``inet:dns:look:tcp4:ipv4`` and ``inet:dns:look:tcp4:udp4`` sub properties of ``port`` and ``ipv4`` have been added, so a DNS response can be recorded from a server even if the server source port is unknown.
- #559 - Add a limit parameter to the Storm ``totags()`` operator.
- #560 - Add unit test for ``synapse.lib.dark``.

## Bugs
- #555 - Set the x509 extension number of certificates made by ``synaspse.tools.easycert`` to version 3 (0x02).  This allows Chrome to validate the certificates starting in Chrome 63.
- #558 - When an exception is raised during the ``synapse.lib.socket.Plex._plexMainLoop`` call to ``select.select()``, perform a check to see if any sockets are fini'd or have fileno() == -1 and perform a cleanup operation on that socket. This can reduce a race condition where a bad socket can get wedged and prevent the multiplexor from working correctly.
- #558 - Change the ``synapse.link.ssl.Socket.send()`` implementation to call ``self.sock.send()`` itself instead of calling through the default ``Socket.send()`` method.  This allows us to properly catch ``SSLWantReadError`` and ``SSLWantWriteError`` exceptions; instead of allowing teh default method to catch them as ``OSError`` exceptions and fini the socket.  The previous behavior lead to SSL Sockets being unstable.
- #556 - Fix the Storm filter function for ``+range()`` so that filter operator works properly.
- #562 - Fix the Storm filter function for ``+in()`` so that filter operator works properly.

## Documentation
- #552 - Add documentation for the Storm operators to the user guide: ``pivot()``, ``join()``, ``refs()``, ``fromtags()``, ``totags()``, ``jointags()``, and ``tree()``.


v0.0.38 - 2017-12-01
--------------------

## New Features
- #545 - Added storm macro function ``get:tasks`` and an API for introspecting tasks which have been registered on a Cortex.

## Enhancements
- #544 - Added new fields (``url`` and ``whois:fqdn``) to ``whois:contact``.
- #547 - Enabled pyup monitoring for Synapse release notes and added config file to disable pyup update checks.
- #549 - Removed ``cryptography`` from setup.py.

## Documentation
- #548 - Added CHANGELOG.md to maintain release notes within the repository.

v0.0.37 - 2017-11-29
--------------------

## New Features
- #542 - The ``Daemon`` now automatically calls ``item.fini()`` for items which are made from a Daemon configuration which are EventBus objects when the Daemon is ``fini()``'d. This allows the Daemon to tear down all instances of eventbus objects which it makes without having to share the object and set the ``onfini`` option when configuring the share.

## Enhancements
- #541 - Added ``exe``, ``proc`` and ``host`` secondary properties to the ``inet:dns:look`` format to allow capturing a DNS lookup which may have originated from a file, process or a host.
- #540 - When the socket multiplexer does an ``accept()`` call, the remote ip and port are logged at the debug (``logging.DEBUG``) log level.

## Bugs
- #58, 537 - Fixed IPv6 type norm() operations for OSX by using the ``ipaddress`` library instead of the ``s_socket.inet_ntop()`` function.
- #543 - Recent changes to pytest (included in the base image used for doing CI testing) changed how logging is performed.  This disables those pytest changes.

v0.0.36 - 2017-11-27
--------------------

## New Features
- #529 - Synapse Docker container ``vertexproject/synapse`` is now built off of a base container, ``vertexproject/synaspe-base-image:py36``.  This container is hosted from https://github.com/vertexproject/synapse-base-image and is also used for CI testing.  The synapse-base-image contains all of the dependencies required for Synapse, as well as having software updated via `apt-get`.  The base container also has ``:py35`` and ``:py34`` tags available as well.
- #523 - Added ``Cortex.extCoreFifo()`` to put of a list of items in a named Cortex FIFO.
- #523 - Added ``DataModel.addPropTypeHook()`` to allow a DataModel user to fire a function whenever a type is used to define a property.  This can be used to define callbacks by a ``CoreModule``.
- #523, #538 - Added ``synapse.lib.db`` to handle pooled connections to databases.  Added ``synapse.lib.sqlite`` to handle SQLite specific DB optimizations.
- #523 - Added ``synapse.lib.gis`` to handle geospatial computations.
- #523 - Added ``synaspe.lib.iq.TestSteps`` helper.  This allows for for interlocking events for multithreaded tests.
- #523 - Multiple improvements to ``CoreModule``’s.  They may now get a unique ``_mod_iden`` property by an implementor.  This value can be retrieved with the ``CoreModule.getModIden()`` API.  Added ``getModProp()`` and ``setModProp()`` APIs so that the CoreModule can store data in the attached ``Cortex`` object.  Added a ``finiCoreModule()`` API which is automatically registered as a fini function for the CoreModule.  CoreModule implementors can override this API in order to have resources torn down automatically.
- #523 - Added ``synapse.lib.revision`` module to provide helpers for doing revision path enforcement.
- #523 - Added ``syn:alias`` node types to allow for a global GUID alias for a given iden.
- #523 - Added ``synapse.models.geospace.LatLongType`` and ``synapse.models.geospace.DistType`` for normalizing Latitude/longitude data and distances.
- #523 - Added ``geo:nloc`` form to allow tracking the physical location of a given node over time.
- #539 - Added ``inet:wifi:ap`` node type to allow the intersection of a SSID and a BSSID value.
- #539 - Added ``tel:mob:imid`` form to represent the knowledge of an IMEI and IMSI together.
- #539 - Added ``tel:mob:imsiphone`` node type to represent the knowledge of an IMEI and a telephone together.

## Enhancements
- #528 - When a property value is included in the Storm ``stats()`` operator, that value is now normed using ``getPropNorm()``.
- #529, #532 - The ``SvcProxy`` now refires ``syn:svc:init`` and ``syn:svc:fini`` events, so users of the SvcProxy may now react to those events to know that a service has been added or removed from the ``SvcBus``.
- #534 - Log messages  for exceptions which occur on the ``EventBus`` which cause an exception in ``dist()`` function now include the repr of the ``EventBus`` object so it is clear what type of object had the error, and the mesg itself.
- #534 - ``traceback.print_exc()`` calls have been replaced by `logger.exception()`` calls so traceback information is directed through logging mechanisms, instead of being printed to stdout.
- #534 - The ``Axon.has()`` api now validates the ``hvalu`` parameter is not None before querying the Axon db via getTufosByProp, to ensure that we are not returning an arbitrary ``axon:blob`` tufo.
- #523 - ``Cortex.formTufoByProp()`` will now fire ``node:set:prop`` events for each property in a newly created node.  This does not affect splice generation.
- #523 - ``Cortex.delTufo()`` will now fire ``node:set:prop`` events for each secondary property in the deleted node to indicate the new-valu is None.
- #523 - Added ``SynTest.getDirCore()`` and ``SynTest.getTestSteps()`` helpers for getting directory backed Cortexes and TestStep objects, respectively.
- #523 - ``CoreModule.getModPath()`` Now returns None if the Cortex the module is loaded in is not a directory backed Cortex.
- #523 - ``synapse.lib.queue.Queue`` now has a ``size()`` API and a ``__len__`` implementation which allows inspection of how many items are in the internal ``collections.deque`` object.
- #523 - Added ``synapse.lib.scope.pop()`` and ``synapse.lib.scope.Scope.pop()`` methods, which allow either a thread or object local scope to have a named object pop’ed out of it, similar to ``dict.pop()``.
- #523 - Storm syntax integer parser now supports parsing negative values (starting with a ``-`` sign), parsing values which start with ``0x`` as hex values, parsing values which start with ``0b`` as binary strings, and parsing floats properly.
- #539 - ``CompType`` forms now accept dictionary of values as input.  They keys which map to fields and optfields are used to form the node.
- #539 - Added ``ipv4``, ``tcp4``, and ``udp4`` secondary properties to ``inet:dns:look``.  These represent the IP address which requested the look, and the servers which may have responded to the look.

## Bugs
- #529 - The ``SvcProxy`` object was incorrectly registering services by name, as well as tags, in its' ``ByTag`` helper.  This was causing the ``SvcProxy`` to think additional services were still available after they were no longer available to the ``SvcBus``.  This has been corrected, and the ``SvcProxy`` no longer misuses the ``ByTag`` helper.
- #531 - The atexit handler for the ``EventBus`` had a bad reference which could have triggered a NameError on shutdown.  This has been fixed.
- #533 - Change the ``Axon`` test test_axon_host_spinbackup to use waiters on ``syn:svc:init`` events to address a race condition.
- #534 - Additional proxy objects are fini'd during Axon tests.
- #523 - ``Socket.send()`` now catches ``OSError`` and ``ConnectionError`` exceptions and fini’s the socket if they occur.

## Documentation
- #527 - Added Storm documentation for the ``stats()`` operator.
- #534 - Docstrings for ``synapse.lib.persist.Dir.items()``, ``synapse.lib.service.SvcProxy.callByTag``, ``synapse.lib.service.runSynSvc`` have been rewritten.


v0.0.35 - 2017-11-16
--------------------

## New Features
- #524 - The Cortex class has a new API ``getCoreMods``, which returns a list of the currently loaded CoreModules in the Cortex.

## Enhancements
- #522 - Exceptions raised  during the thread Pool ``_run_work`` function are logged with additional information about what failed to run.

## Bugs
- #522 - The ``synapse.lib.msgpack.en()`` function's use of the global msgpack.Packer object was wrapped in a try/except block; so that in the event of an exception during packing, we call the ``reset`` method to clear internal buffers of the object.  It was possible that a serialization failure leaves data in the object, which would then be passed along to a subsequent caller.  See https://github.com/msgpack/msgpack-python/issues/258 for example code showing this issue.
- #522 - Ensure that the axonbus Proxy objects made by Axon and Axonhost objects are fini'd.
- #522 - Fini more objects during Axon and Telepath tests which were not properly fini'd.
- #525 - The Axon ``_fireAxonClones`` function did not wait for its existing clones to come online (since they are handled by threads) befor entering the ``_findAxonClones`` routine.  This could have caused the Axon to attempt to make additional clones for itself until the number of clones the Axon had loaded met the ``axon:clones`` option.  The ``_fireAxonClones`` clones routine now waits 60 seconds for each previously known clone to come online before attempting to bring new clones online for itself.
- #526 - Pypi package had included a `scripts` package.  This included development related scripts and was not intended for redistribution; and it collides with an existing `scripts` package on Pypi.

## Documentation
- #522 - Update docstrings for ``telepath.openurl`` and ``telepath.openlink`` APIs.
dditional clones for itself until the number of clones the Axon had loaded me

v0.0.34 - 2017-11-10
--------------------

## New Features
- #504 - Universal node properties, ``tufo:form`` and ``node:created``, are now model properties.  Those properties do not have a form associated with them.  In addition, the universal node property ``node:ndef`` was added.  This is the guid derived from the primary property and primary property together, giving a way to universally represent a node value in a anonymous form. Universal properties are now added to the the datamodel documentation generated by autodoc.  The associated migration for adding ``node:ndef`` values to nodes migrates all forms loaded into the Cortex datamodel at the time of startup. Depending on the size of a Cortex, this migration may take a long time to complete and it is encouraged that large (10 million+ node) Cortexes have a test migration done on a backup of the Cortex.
- #515 - Add a ``inet:addr`` type, which normalizes both IPV4 and IPV6 values to a single IPV6 value, which will produce a IPV4 sub if the address is part of the v6 -> v4 mapped space.
- #515 - Add a ``inet:dns:req`` form to record a DNS request which was made by an IP at a given time.
- #515 - Add a ``inet:dns:type`` type to enumerate different types of DNS requests.

## Enhancements
- #516 - The ``task:<taskname>`` events fired by the Storm task() operator includes all the nodes in the current query set under the ``nodes`` value, instead of firing a single event per node under the ``node`` key.
- #504 - The msgpack helpers, ``synapse.common.msgenpack``, ``synapse.common.msgunpack`` and ``synapse.common.msgpackfd`` were removed. They are duplicates of functionality present in ``synapse.lib.msgpack`` content.  They are replaced by ``synpase.lib.msgpack.en``, ``synapse.lib.msgpack.un`` and ``synapse.lib.fd respectively``.

## Bugs
- #517 - The ``Cortex.delTufoTag`` API did not return the tufo to the caller.  It now returns the modified tufo to the caller.
- #518 - Ensure Axon resources are fini'd during Axon related tests.
- #519 - The tests for normalizing the string ``'now'`` as a ``time`` type are more forgiving of system load.

## Documentation
- #512 - Added style guide notes to prefer returning None over raising exceptions.
- #513 - Added filter documentation for storm
- #520 - Added a link to the Synapse slack chat to the readme.rst file. Invite your friends, they're welcome here!

v0.0.33 - 2017-11-07
--------------------

## New Features
- #502 - Added the ``dir:///`` handler for opening a Cortex (currently SQLite backed) by file path.
- #502 - Added a Telepath reminder API to facillitate server side statefullness on Proxy reconnect.
- #502 - Added a Cortex metadata directory configable option and helpers for CoreModules to access that directory.
- #507 - Added ``inet:dns:rev6`` form for recording IPV56 PTR lookups.

## Enhancements
- #502 - Added a reqPerm() API helper to require a user have a given permission.
- #502 - Removed old/broken session management code.

## Bugs
- #170, #501 - Replaced the Python ``re`` module with ``regex``.  This addresses a unicode parsing error in the ``re`` module which prevented the correct identification of some punycode encoded FQDN values.
- #508 - Add a signal handler for ``SIGTERM`` to the ``Eventbus.main()`` function.  This allows for gracefully shutting down a dmon which was started in a Docker contain.  Previously, ``SIGTERM`` was not caught and caused the Python process to close ungracefully.
- #509 - Removed Python 3.7 from test matrix until ``synapse.async`` library is removed.
- #509 - Fixed a bug in formTufoByProp which allowed the formation of nodes which were valid props, but not actually forms.
- #509 - Fixed a bug in storm that prevented setting read-only properties on nodes which may not have had the read-only property present.

## Documentation
- #503 - Added docstrings to inet.py, dns.py and files.py models.
- #505 - Added link to docker for the ``vertexproject/synapse`` images.
- #510 - Added docs for running PostgreSQL cortex tests manually with Docker.
- #511 - Added code style guidelines to indicate the preference of the ``regex`` module over the use of ``re``.

v0.0.32 - 2017-10-31
--------------------

## New Features
- #480 - Added a fully asynchronous push FIFO structure in order to support future Synapse built services.
- #490 - Added a ``make:json`` typecast which can be used to cast an object into a JSON string.
- #492 - Added a JSONL to messagepack tool.  ``synapse.tools.json2mpk`` can be used to convert a JSONL file to a stream of messagepack's blobs.
- #496 - Added a ingest helper ``setGestFunc`` to the IngestApi mixin. This allows a function to be registered which performs data ingest without relying on a full ingest definition being created.
- #480 - Configable objects have a new method, `reqConfOpts()`. This method checks all configabl options; if an option has the property 'req' which evaluates to True and the value is not set on the object, a ReqConfOpt exception is thrown. This can be used to enforce an object to have specific configuration options set.

## Enhancements
- #490 - Ensured Synapse was generating pretty JSON strings in places where a human may end up reading the JSON directly.
- #497 - Made axon exception logging more verbose.
- #489 - Docker images are now built in DockerCloud using a Dockerfile contained in the Synapse repository.  The ``vertexproject/synapse`` image will use the ``python:3.6.3-slim`` base image moving forward, as to keep container size smaller.
- #480 - During a graceful shutdown, an atexit handler will now attempt to ``fini()`` all EventBus objects which have not been fini()'d and have had the ``self._fini_atexit`` flag set to True on them.
- #480 - AtomFile objects may now be truncated to reduce their size.


## Bugs
- #487 - Removed Python 2.7 from the list of suppported Python versions in setup.py trove classifiers.
- #491 - Fixed a race condition in splicepump tests for ``node:created`` values.
- #494 - Added a minimum and maximum value for the ``IntType`` integer value to ensure it is bound within a signed 64big value.  This is reflective of storage limitations of the SQLITE and PSQL storage backings.  This ensures that we cannot make a node in one storage backing that cannot be moved to another storage backing because of storage-specific issues.
- #499 - The storm pivot operator was not runt-node aware; so it was unable to pivot to runt nodes.  This has been fixed.
- #498 - Telepath's ``Proxy`` object was unable to successfully reconnect to a shared object if the Proxy object had event handlers registered to it.  The order of operations for handling a reconnection has been changed to allow this to function properly.

## Documentation
- #488 - Updated scheduler persec/loop function docstrings to clarify the return values and ability to cancel future tasks.


v0.0.31 - 2017-10-27
--------------------

## New Features
- #477 - Added ``node:created`` universal TUFO property. This is set when a node is created via formNodeByProp, and enables lifting/sorting nodes by the time they are created.  Existing nodes will have ``node:created`` props set on them based on the Cortex timestamp value of their ``node:form`` property. Since this requires lifting every ``tufo:form`` row in a Cortex, it is reccomended that this is first tested in a copy of any production cortexes before doing a production deployment; so any neccesary outage windows can be planned.
- #484 - The Cortex ``axon:url`` configable option now accepts a URL to a service bus.  It will create an AxonCluster object if that is the case.

## Enhancements
- #478 - Properties which are read-only will be able to be set on a node if that property does not exist on the node.
- #485 - Test context managers in ``synapse.lib.iq`` now properly clean up after themselves in the event of a test failure/error.
- #485 - Added setTstEnvars context manager to the SynTest class to enable running tests with specific environmental variables set.

## Bugs
- #459, #478 - Refactor how nodes are created using formTufoByProp. This has the impact that nodes automatically created via the autoadds mechanism will now have any secondary properties available added to them from the process of doing data normalization.

## Documentation
- #483 - Remove outdated readme examples
- #486 - Add docstrings to inet:iface properties.

v0.0.30 - 2017-10-23
--------------------

## New Features
- #473 - Added ``it:prod:soft``, ``it:prod:softver``, ``it:hostsoft`` types and associated forms, to allow tracking software, versions of software and software installed on a given host.
- #473 - Added ``it:semver`` data type for doing type normalization of Semantic Version numbers.  Added helper functions for both Semantic version parsing and generic version parsing to ``synapse.lib.version``
- #473 - Added ``it:version:brute`` typecast to attempt parsing a version string into a normalized system value that can be used to do ordered comparison of version strings.
- #476 - Added ``inet:iface`` type and form for modeling a network interface on a particular device being bound to a particular IP, host, phone or wifi SSID.  Added ``inet:wifi:ssid`` type.
- #476 - Added ``ps:contact`` type and form to act as a conglomerate of contact information for a individual.
- #476 - Added ``tel:mob:tac``, ``tel:mod:imei`` and ``tel:mob:imsi`` types and forms for modeling cellphone related information.  This includes parsing and validation of pre-2004 IMEI/IMSI numbers.
- #482 - Moved test helper functions from ``synapse.tests.common`` to ``synapse.lib.iq`` so other users of Synapse can reuse our pre-existing test helpers (SynTest, TestEnv and TstOutput).

## Enhancements
- #465 - Added ``axon:listener``, ``axon:tags`` and ``axon:syncopts`` to the AxonHost class, so these default values can be passed to Axons made by an AxonHost.
- #479 - Add test for calling the storm ``task()`` operator on a remote cortex with a local calback handler.

## Bugs
- #475 - Changed PropValuType to use reqPropNorm instead of getPropNorm to enforce that the property referred to BY the type must be a modeled property.


v0.0.29 - 2017-10-19
--------------------

## New Features
-  #471 - The dmon tool, ``synapse.tools.dmon`` can now accept the log level via a environmental variable, ``SYN_DMON_LOG_LEVEL``.  This can be added as an environmental variable in a docker compose file using the Vertex Project Synapse Docker images to configure the logging level.

## Enhancements
- #467 - Added ``it:exec:proc:path``, ``it:exec:proc:src:proc`` and ``it:exec:proc:src:exe`` properties to the ``it:exec:proc`` form. Removed the ``it:exec:subproc`` form since it is not needed with the ``:src:`` properties on ``it:exec:proc``.
- #467 - Removed the computer science model (``compsci.py``) since it was superseded by the host execution model.
- #467 - Added ``inet:flow:src:exe`` and ``inet:flow:dst:exe`` properties to ``inet:flow`` to allow modeling data between ``file:bytes`` nodes.
- #468, #469, #472 - Added pytest-xdist to the testrunner.sh script to speed up local (dev) test runs of synapse.
- #470 - Remove unnecessary docker related functionality.

## Bugs
- #466, #474 - Fixed bug in non-blocking SSL link which would sometimes prevent data from being transmitted

## Documentation
- #462 - Added documentation for the host execution model in ``infotech.py``.

v0.0.28 - 2017-10-16
--------------------

## New Features
- #456 - A global thread pool has been added to Synapse and a Task object convention added for executing tasks in the pool. This is in preparation of future feature support.

## Enhancements
- #461 - The storm query operator ``refs()`` now also lifts nodes by prop-valu combination in order to get nodes which may refer to the source nodes. This allows identifying XREF nodes which point TO the inbound node.
- #463 - The TimeType now norms the string "now" as the current system time.
- #464 - Added a "guid" helper for Ingest to assist in making GuidType nodes without having to form strings out of variables.


v0.0.27 - 2017-10-12
--------------------

## New Features
- #446, #450 - Adds the ability for GuidType nodes to normalize a list of items, in order to generate stable guids for potentially re-encounterable data.  This only works when generating a property norm value (getPropNorm) and does not work for purely type normalization (getTypeNorm).  Storm keyword list argument parsing can be used to generate stable GUID using the CLI, Ingest or Storm mechanisms.
- #452 - Synapse now stores the current version of the Synapse library in the Cortex blob store at the end of Cortex initialization. This was done in order to prepare for eventually enforcing required upgrade paths for data migrations or other features.
- #447 - Added the new form ``inet:web:postref`` XREF to track an ``inet:web:post`` which refers to another node.
- #447 - Added the new form ``inet:web:action`` GUID to to track an arbitrary action by an ``inet:web:acct`.  The actions tracked by this are by defined by [Synapse] user convention.
- #447 - Added the new form ``inet:web:actref`` XREF to track how an ``inet:web:action`` may have interacted with another node.
- #454 - Added the ``inet:web:chprofile`` GUID to track previous values of a ``inet:web:acct`` node, representing changes to user accounts or profiles.
- #454 - Added the ``inet:web:post:repost`` property to track the concept of a ``inet:web:post`` being a copy of another post.
- #455 - Added a pair of Storm (and Cortex) Configable options to enable and set logging levels for Storm queries.  These are ``storm:query:log:en`` and ``storm:query:log:level``.  This logs what the query is and what the user execution context was.
- #426 - Axon and AxonHost objects are now Configable objects with configuration definitions that are used to define their behavior.

## Enhancements
- #442 - Python 2.7 support dropped from Synapse.
- #447 - Migrated all inet:net* forms to the inet:web:* space.  The following is a map of the migrated forms and their corresponding new forms:
```
('inet:netuser', 'inet:web:acct')
('inet:netgroup', 'inet:web:group')
('inet:netmemb', 'inet:web:memb')
('inet:follows', 'inet:web:follows')
('inet:netpost', 'inet:web:post')
('inet:netfile', 'inet:web:file')
('ps:hasnetuser', 'ps:haswebacct')
('ou:hasnetuser', 'ou:haswebacct')
```
These forms will automatically be migrated in existing Cortexes. If XREF types were used to point to any of these forms and the cortex was not first migrated to v0.0.26, the XREF type migration will fail.  It is recommended that users first upgrade to v0.0.26 prior to upgrading to v0.0.27.
- #447 - Added Storage.updateProperty() and Storage.updatePropertyValu() APIs to the Cortex storage layer for doing bulk property and property-by-value updates.  These are explicitly NOT exposed in the Cortex class.
- #449 - Thinned out some components of the EventBus class for performance reasons.  This did result in the removal of the synapse.eventbus.on() decorator for decorating functions to be used as event callbacks.
- #456 - Removed unused Synapse modules: synapse.hivemind, synapse.mindmeld, synapse.lib.moddef.
- #426 - Logging in tests is now controlled by the environmental variable ``SYN_TEST_LOG_LEVEL`` which, as an integer, will set the logging level used by the root logger.
- #426 - The environmental variable ``SYN_TEST_SKIP_LONG`` can be set to a non-zero integer to skip potentially long running tests.  This can shave up to a minute of test execution time.
- #426 - Axons now have the in-memory cache enabled on their Cortex by default.
- #458 - The ``inet:web:acct:occupation`` property has been changed from a ``str:txt`` type to ``str:lwr`` to allow for better foldability between user-declared occupations.

## Bugs
- #443 - Make the daemon return more useful error messages when an exception has occurred during execution of a remote request.
- #444, #445 - Allow an inet:srv4 type to accept an integer string as input. Also adds additional boundary checking when norming an ip:port string to ensure that irreversible inputs are not accepted.
- #453 - Cleaned up skifIfNoInternet() test helpers.  They will now be allowed to fail unless the ``SYN_TEST_SKIP_INTERNET`` environmental variable is set to a non-zero integer.
- #426 - The synapse.lib.heap.Heap class was not properly responding to ``heap:resize`` events. This was remedied.
- #426 - Wrapped a .items() iterator in synapse.daemon.OnHelp with a list to prevent a RuntimeError.
- #426 - Fix the synapse.lib.service.SvcProxy.getSynSvcs() method to return a Telepath safe list instead of a dict.values() view object.
- #426 - Fix the synapse.lib.service.SvcProxy.__init__ to strap in event handlers AFTER initializing instance variables to avoid a race condition on startup.
- #426 - AxonHost now waits before advertising itself on the bus, and properly calculates the number of axons it needs to make.  This addressed an issue where the AxonHost was generating a non-deterministic number of Axons.
- #426 - The Axon’s thread to make clones for itself on a ServiceBus now waits until a remote clone is made.  This addressed an issue where the Axon would make extra clones for itself.

## Documentation
- #448 - Added in-model documentation for the file: model defined in files.py.
- #451 - Added user guide information for Storm lift operations, lift(), guid() and alltags().
- #426 - Docstrings in the synapse.axon module were rewritten or added when needed.

v0.0.26 - 2017-09-26
--------------------

## New Features
- #438 - Added PropValu datatype to synapse.  This allows a secondary (or primary) property to be modeled as a string in the form `property=<repr valu>`.  This type also yields sub of "prop" representing the property, and "strval" or "intval" being the system normalized value of the property.  This allow for node creation where a reference to another node property is needed but cannot be defined up front in the model.  The additional subs allow for filtering/pivoting operations on nodes which use the PropValu type.  A simple example of the string form for a PropValue is `inet:ipv4=1.2.3.4`. A more complex example of the string form for a PropValu is `inet:passwd=oh=my=graph!`
- #438 - XREF types have been updated to use the PropValu datatype instead of storing data in the property columns. This removes any extra-model data from the property columns in Cortex rows, and allows the implementation of pivotable XREF nodes. The string syntax for XREF creation was changed to be in line with the Comp datatype syntax, which looks now looks like ``. This will affect any ingests or programmatic creation of xref nodes done by users.  An example of the string form of a Xref now looks like the following: `(98db59098e385f0bfdec8a6a0a6118b3,"inet:passwd=oh=my=graph!")`.  Note that the PropValue portion of the value is quote delimited.

## Enhancements
- #438 - The `refs()` storm operator is updated to be aware of secondary properties which are PropValu types and will pivot off of them, even if the props themselves are not forms.
- #438 - The file:imgof and file:txtref nodes no longer have glob property xref:*, instead :xref is now a PropValu and has the additional :xref:prop, :xref:intval and :xref:strval secondary props.  This does require a data migration, so deployment of v0.0.26 should be tested on Cortexes which use those forms prior to production use.
- #438 - Migrated unittests to using getRamCore() helper when possible.
- #438 - Added unittest self.len() helper.  Started some migration there.
- #439 - Cleaned up Socket() class implementation to be better, stronger and faster.
- #440 - Moved the syn:type, syn:form and syn:prop forms (and other items declared in DataModel) to be part of the "syn" model.  These core elements are now themselves introspect-able.
- #440 - Added syn:prop:base and syn:prop:relname to syn:prop nodes, so those nodes can now be lifted by a basename or a relative property name.
- #441 - Added Python 3.7 RC1 to the test matrix.  Pinned postgres test image to postgres:9.6.
- The Storm runtime now respects the `storm:limit:lift` configable value as the default limit when lifting nodes.

## Bugs
- #440 - Changed how runtime nodes (runts) used to represent the data model in a cortex are created.  These are now made from the type and property definitions based on the loaded data model; having been guided by the data model being processed.  This restores things like "syn:prop:form" which was accidentally dropped from nodes.

v0.0.25 - 2017-09-19
--------------------

## New Features
- #404 - Added model for inet:web:netlogon to track netuser's logging into services.
- #433 - Added inet:dns:mx, inet:dns:cname, inet:dns:soa, inet:dns:txt node types for recording different DNS responses.
- #436 - Added the ability to define triggers. Triggers are predefined actions which can react to events and trigger storm queries, in order to automate activities and actions.
- #436 - Rewrote the user authentication system to be more integrated with Cortex (and used within the trigger subsystem).  This allows adding user roles and permissions to add, delete, or update nodes.

## Enhancements
- #404 - Added inet:whois:nsrec comp nodes to track nameserver's associated with whois record.  This removed the inet:whois:rec:ns* properties and migrates existing props into the new nodes.

## Bugs
- #437 - Fix the tag interval filtering in the Storm query system.

## Documentation
- #435 - Rewrote docstrings for synapse.lib.queue subsystem.

v0.0.24 - 2017-09-14
--------------------

## Enhancements
- #430 - CortexTest class was split into CortexBaseTest and CortexTest.  CortexBaseTest is used for running the
  basic_core_expectations tests with the different storage backing; and CortextTest is used for more generic API tests.
  This allows running the basic test suite against the different storage types without running the entire test suite, in
  order to isolate possible storage related issues.
- #434 - Migrated from using nosetestes to using py.test as the Synapse testrunner for CI.

## Bugs
- #422 - Fixed the order of autoadds being added to the DB during the addTufoEvents / addTufoEvent Cortex API.  This
  could manifest itself as tufos made by these events to not contain their properties.
- #428 - Fix a issue with the LMDB cortex where parameters passed to pylmdb were not bool types (as that library
  expected), causing the parameters to be ignored in effect.

## Documentation
- #422 - The inet:dns model docstrings were updated to be more comprehensive.

v0.0.23 - 2017-09-14
--------------------

## New Features
- #423 - Added ephemeral runtime-only nodes as a concept to Synapse.  The data model has been migrated to utilize these for loading and storing the data model, so the data model (syn:type, syn:prop, syn:form) itself no longer lives within the Cortex database itself. This makes data model updates much easier, requiring only data migration functions to be written for future updates.  This does mean that custom models are no longer persistent and are required to be loaded into a Cortex to be made available.

- #423 - Added a initial model for capturing software execution knowledge on hosts.  These models are primarily comp types, which allow modeling varying levels of knowledge which may be available from different data sources.

## Enhancements
- #423 - The setModlVers API was moved to the Storage layer (and simply called through by the Cortex) to allow hooking model revision function execution with events, to allow for easier testing of Model data changes requiring data migrations.
- #429 - Updated .drone.yml to run all tests in parallel again to take advantage of infrastructure updates.

## Bugs
- #421 - Fixed getConfDefs() API in Configable.  Made it so that default values (defval) items are copy.deepcopy'd, so that mutable defval's are not overwritten by later use.
- #425 - Prevent the Ingest tool from attempting to ingest data to a remote Cortex connected to over Telpath.   Attempting to do so previously would result in a esoteric error message.  This means that the --sync option must be used when syncing data up to a remote Cortex.

## Documentation
- #424 - Docstrings for the synaspe.lib.config.Config class were written to clarify that class APIs and add notes about possible race conditions when using onSetConfOpt handlers to respond to configable events.

v0.0.22 - 2017-09-11
--------------------

## New Features
- #395 - Add formTufosByProps() API to the Cortex() class to do bulk tufo creation.  This has significant performance for doing bulk tufo creation by utilizing a single storage layer transaction.
- #359, #405 - All splices now represent atomic actions.  This is a breaking change from v0.0.21, since the node:set events no longer multiple props, but instead a single prop per event.  This requires an ecosystem wide upgrade for users utilizing the splice subsystem.
- #408 - Provisional task() operator added to the storm runtime.  This fires events in the form of "task:<name>" on the storm core eventbus.  This behavior may change in the future.
- #409, #414, #416 - Synapse model properties which had req=1 set on them now actually require that property to be present when model enforcement is in place.  This check occurs after node:form events, allowing code to hook the node formation process and provide required properties or set them as needed.
- #417 - Added a tree() operator to storm for doing recursive pivot operations on a set of nodes.
- #419 - Added a delprop() operator to storm to remove properties from nodes.

## Enhancements
- #410 - pivot() operator syntax updated to match that of the macro syntax operator.  This may be a breaking change for any programmatic use of the pivot operator syntax.
- #411 - Added pycodestyle checks to CI builds to identify code style issues.
- #412 - Fix resourcewarnings with unclosed file handles.

## Bugs
- #399 - Fix Cortex.__init__() on Python 2.7 where a list comprehension smashed function locals.  This prevented configable options from being set at initialization.
- #401 - Fix setTufoProps() to add nodes created from secondary properties when appropriate.

## Documentation
- #403 - Initial docs for Ingest subsystem,
- #408, #420 - Updates to Storm runtime documentation.
- #418 - Added markdown template to release documentation.

v0.0.21 - 2017-08-14
--------------------

## New Features
N/A

## Enhancements
- #299, #381, #392 - Update model enforcement to prevent nodes from being created which are not valid types.
- #391 - Add bumpversion support for doing release cutting.
- #394 - Add log messages when doing model revision migration.

## Bugs
- #396 - Fix a bug with Configable objects with telepath proxy attributes.
- #397 - Add a model revision to fix inet:urlfile comp type nodes to address a issue from #333.

## Documentation
- #391 - Start release process documentation
- #393 - Additional user guides


v0.0.21 - 2017-08-09
--------------------

The 0.0.20 release is not small - so here are some notes for it!

Since there are significant changes to how we handle models and storage layers in this version, we recommend that you make a backup of any production Cortexes you have before deploying this, and test your systems prior to deployment.

-- vEpiphyte

## New Features

- #277 - Add the ability to load python modules via dmon.
- #275 - All Synapse core models have been cutover to using CoreModule implementations for doing model revisioning.
- #274 - Optional Time boundaries added to tags for doing timeboxing of tags.
- #279 - Added columns support and additional help framework for cmdr CLI
- #285 - Easycert tool now makes server certificates with the subjectAltName (SAN) field populated.  Tell your fiends - this a way easier tool to use to make SAN certs than using the openssl binary itself.  This allows certificate pairs to be used in chrome 58+.
- #177 - Added a ndef() function to synapse.lib.tufo to get a tufo type and primary prop.
- #286 - Easycert tool can make PKCS12 client certs.
- #333 - Comp types now support optional kw fields, allowing recording of varying levels of knowledge for a given type.
- #321 - SSL Support added to the webapp
- #289, #290, #301 - Add support for a blob key/value store to the Cortex which exists separately from the Row layer storage.
- #291, #292, #301 - Add support for storage layers to be revisioned independently of models.
- #300, #342 - Add support for sending BODY content via remcycle
- #348, #350 - Add a guid() operator to storm for lifting a node by iden.
- #358 - Add a delTufoProp() API to cortex for deleting a tufo property.  This changed splice contention and event handlers, node:set is no longer fired; node:prop:set and node:prop:del are now fired.
- #374, #378 - Add a new limit() operator for Storm.
- #320, #362 - Storage layers are now separated from the Cortex class by an API boundary.  This allows for future custom storage layers to be implemented easily.
- #319, #262 - Add dumprows and loadrows tools to dump a cortex to a savefile or create a new storage object from a existing savefile.

## Improvements
- #282 - Code style cleanup
- #293 - Prevent reference databases used in tests from being modified accidently.
- #288, #296, #332 - Storm setprop operator (and prop edit mode) now respect relative prop values.  Addnode also uses relative props now.
- #272, #342 - Rewrote remcycle tests to no longer require external resources. They run consistently now.
- #302, #342 - Remcycle now uses configable definitions in a consistent manner.
- #364 - Restored pre v0.0.15 axon path behaviors.
- #378 - Add a plan step to storm query parsing - allows for future optimizations.
- #338, #362 - Configable objects may now use a decorator to declare all of their options, which will be loaded at runtime.

## Bugfixes
- #276 - Fixes for eq/lt/le/gt/ge operators in storm
- #236, #295 - Allow cache disable on a cortex to actually clear the cache.
- #287, #294 - Fix delnode storm operator and delTufo() API
- #347, #349 - File:bytes nodes created from seed ctors (file:bytes:md5, file:bytes:sha1, etc) now have stable guids. Previously guids were case sensitive.
- #335, #352 - Fix cmdr quit function on Python 2.7
- #345, #351 - Fix inet:cidr range lookups.
- #367, #370 - Regex macro filter "~=" accidently ate whitespace.  This is fixed.
- #380, #382 - Fix a issue with tag caches upon tag deletion.
- #378 - Fix for comp type arg parsing in long form storm operators.
- #339, #346 - Fix for inet:url:ipv4 and inet:url:fqdn parsing.
- #354, #355 - Fix for inet:tcp4 / inet:udp4 :ipv4 and :port parsing. Also make ipv6 repr's consistent.

## Documentation
- #273, #278 - Initial performance benchmarks for Synapse
- #281, #283 - Initial User Guide for Synapse
- #284 - Change docs to using the easier to read RTD theme.
- #368 - ADditional User Guide documentation.
- #338, #362 - Automatic documentation is now generator for configable objects, detailing their options.
- #323, #324, #362 - Synapse devops documentation moved together.
