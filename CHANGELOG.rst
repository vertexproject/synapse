.. vim: set textwidth=79

.. _changelog:

*****************
Synapse Changelog
*****************

v3.0.0b1 - 2026-06-30
=====================

Model Changes
-------------
- Added new structural forms including ``doc:reference``, protocol handshake
  forms, and the ``ind:*`` industry model.
- Edge verbs are now validated against the datamodel. Custom edge verbs must
  now be defined as extended model elements.
- Renamed many forms and properties (for example ``ps:contact`` to
  ``entity:contact``, ``media:news`` to ``doc:report``, and ``hash:*`` to
  ``crypto:hash:*``).
- Replaced the ``inet:web:*`` forms with the ``inet:service:*`` platform and
  account model.
- Timestamps are now microseconds since epoch (previously milliseconds) and the
  time repr is now ISO-8601.
- Added virtual properties: computed sub-values of a property, or context
  bundled with the value (such as the currency of a price), that can be lifted,
  filtered, and pivoted.
- Added form inheritance and additional interfaces to the data model.
  (subforms).
- Merged the ``inet:ipv4`` and ``inet:ipv6`` forms into a single ``inet:ip``
  form whose system value is a ``(version, integer)`` tuple.

Features and Enhancements
-------------------------
- ``$lib.view.list()`` and ``$lib.layer.list()`` now only include views and
  layers the user can read. ``$lib.view.get()`` and ``$lib.layer.get()`` raise
  ``NoSuchView`` / ``NoSuchIden`` for an iden the user cannot read, rather than
  returning it.
- Added the ``$as`` key to dictionary guid constructors to name the form to
  build when a property type can resolve to more than one form.
- ``cron.add`` now takes a positional period string. Added a ``cron.cleanup``
  command and an at-job ``completed`` flag.
- Storm macros now use the easy-permission model and are managed with the
  ``macro.grant`` command.
- Added the ``$lib.file.frombytes()`` and ``$lib.file.fromhex()`` APIs, new
  ``$lib.lift`` helpers, ``$lib.cortex`` Node ID helpers, and
  ``$lib.pkg.state()``.
- Node edits are now deconflicted before being written to the Nexus log,
  reducing storage utilization.
- Layers now index nodes by an integer Node ID (NID) instead of a BUID,
  reducing index size and improving lift performance.
- Added tombstones, which allow deleting nodes and parts of nodes within a
  forked view and applying the deletions to the parent on merge. Deleted nodes
  are surfaced via the new ``syn:deleted`` runt node.
- Tag glob wildcards now match zero-length segments.
- Added inline value casting with the ``as`` clause, and support for multi-
  target and virtual-property pivots.
- Added the ``in`` and ``not in`` membership operators to Storm.
- Updated the default log timestamp format to ISO-8601 UTC with microsecond
  precision (for example ``2026-02-13T10:38:24.545123Z``) for both structured
  and unstructured log output. Timestamps produced via ``SYN_LOG_DATEFORMAT``
  are now rendered in UTC and support the ``%f`` directive for microsecond
  precision.

Notes
-----
- Synapse version reporting now uses PEP 440 strings: ``synapse.version`` is a
  string (previously an integer tuple), ``synapse.lib.version.verstring`` is
  removed, ``getCellInfo()`` no longer includes ``verstring``, and
  ``$lib.version.synapse`` returns a string.
- Removed the ``BadOperArg`` exception class. Many Storm input-validation
  failures that raised ``StormRuntimeError`` in 2.x now raise ``BadArg``.
- Permissions for setting or deleting a node property have been updated to no
  longer support full property path (``node.prop.set.<form>:<prop>``); only the
  modern form is checked (``node.prop.set.<form>.<prop>``).
- Permission changes: granular extended-model permissions collapsed to
  ``model.admin``, ``view.fork`` is no longer granted by default, and
  ``node.data.pop`` was renamed to ``node.data.del``.
- Cortex feed ingest now uses a single packed-node format and ``addFeedData``
  no longer takes a format name.
- Removed the ``cmdr`` and ``cellauth`` tools and reorganized the command-line
  tools into namespaced subpackages.
- Removed Cortex Core modules and the ``modules`` config option, the layer
  ``upstream`` and ``mirror`` options, and the ``syn:cron`` and ``syn:trigger``
  runt nodes.
- Removed several out dated Storm libraries and accessors, including the
  ``$lib.bytes`` Axon proxies, ``$lib.user``, ``$lib.vars``, ``$lib.str``, and
  ``$lib.true`` / ``$lib.false`` / ``$lib.null`` (use bare literals).
- The HTTP API endpoints moved from the ``/api/v1/`` prefix to ``/api/v3/``.
- Storm query ``opts`` changed: the node-output options ``repr``, ``links``,
  and ``show:storage`` moved under ``node:opts``, ``idens`` was replaced by
  ``nids``, and ``opts`` is now keyword-only on the Telepath Storm APIs.
- The minimum supported Python version is now 3.14.
- Synchronous Telepath usage is no longer supported; proxies are async-only.
