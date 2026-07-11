.. vim: set textwidth=79

.. _changelog:

*****************
Synapse Changelog
*****************

v3.0.0b2 - 2026-07-11
=====================

Model Changes
-------------
- Updated the ``ival`` type repr to return a ``<min> - <max>`` string rather
  than a tuple of the min and max time reprs. Max-fill time bounds now collapse
  their filled tail into a ``*`` (e.g. ``2025-12-31*``). The ``ival`` type also
  norms these repr forms back to the same value.
- Added the ``meta:story`` form to record a story document authored in
  markdown.
- Updated the ``file:base``, ``file:bytes``, ``file:attachment``,
  ``inet:fqdn``, ``inet:ip``, ``inet:url``, ``inet:email``,
  ``inet:email:message``, ``inet:urlfile``, ``inet:service:platform``, and
  ``it:cmd`` forms to implement the ``meta:usable`` interface.
- Added the ``risk:loss`` interface and ``risk:loss:life``, ``risk:loss:data``,
  and ``risk:loss:funds`` forms to record aggregate losses.
- Added the ``it:exec:proc:parent`` property to record the parent process which
  created a process.
- Array properties are now declared with the element type in the property
  typedef and the array container opts (``uniq``/``sorted``/``split``) under an
  ``array`` key in the property info dictionary. The ``array`` type is a prop-
  only structural container and may no longer be used as the base for a named
  type.
- Removed the ``int:min0``, ``int:min1``, and ``byte:flags`` types. Affected
  properties now use the ``size``, ``uint8``, or ``uint32`` types.
- Added the ``size`` type for non-negative sizes and counts, and the fixed-
  width integer types ``int8``, ``int16``, ``int32``, ``int64``, ``uint8``,
  ``uint16``, ``uint32``, and ``uint64``.
- Removed the unused ``daterange`` type.
- Added the ``activity``, ``activity:day``, and ``reported`` ival types.
- Inline type opts are no longer permitted on properties; a property must
  reference a named type. A property that needs custom normalization opts
  (``regex``, ``enums``, ``names``, ``precision``, ...) must be declared once
  as a named type and referenced by name.

Features and Enhancements
-------------------------
- All Synapse services booting from 3.0.0b2 must use fresh storage. Booting
  from v3.0.0b1 versions of service storage is not supported, and services will
  fail to boot.
- Grouped Storm command ``endpoints`` help output by base URL.
- The ``synapse.tools.aha.list`` tool now takes an optional ``--url`` (
  defaulting to the local AHA cell) instead of a required positional URL
  argument.
- Add the ``synapse.tools.aha.del`` tool to remove a service entry from the AHA
  registry.
- Renamed the Storm command ``endpoints`` ``host`` key to ``url`` to match the
  ``modconf.endpoints`` shape.
- Added an ``Endpoints`` section to generated Storm package documentation,
  listing each module's ``modconf.endpoints`` grouped by resolved base URL.
- The AHA service ``aha:network`` configuration option now defaults to ``syn``.
- Synapse service docker containers now drop privileges to the ``synuser`` user
  (UID ``999``) via ``gosu`` at startup when started as ``root``, adjusting
  ownership of ``/vertex/storage`` before launching the service.
- Add the ``SYN_PROVISION_FOLLOWER`` environment variable to force an inaugural
  service to deploy as a follower of an existing leader of its type, including
  auto-enrolling an AHA server as a clone via multicast discovery.
- An active Cortex now discovers Storm services registered with AHA and
  automatically adds previously unknown ones using ``aha://<type>...`` URLs.
- Added a ``telepath:port`` configuration option to specify the telepath
  listening port while inheriting the provisioned hostname and CA.
- Added AHA managed leadership terms per service type to dynamically determine
  the leader on boot and enforce forced promotion retirement. Mirrors now
  follow the current AHA determined leader dynamically. Removed the cell
  ``mirror`` configuration option and added a ``parent`` option which
  explicitly overrides the AHA determined leader with a fixed upstream telepath
  URL.
- Added a unified ``AhaClient`` that tracks AHA service topology in near real-
  time via the new ``getAhaTopo()`` API and is now used by every service that
  connects to AHA.
- The Cortex ``axon`` and ``jsonstor`` configuration options have been removed.
  When deployed on an AHA network the Axon and JsonStor are located by service
  type via AHA; a standalone Cortex continues to use its embedded services.
- Added support for automatic AHA service provisioning via the
  ``SYN_PROVISION_SECRET`` environment variable, with the optional
  ``SYN_PROVISION_HOST`` environment variable to send discovery directly to a
  specific AHA host.
- AHA now enforces service type uniqueness: only one instance of a service type
  may register with an AHA deployment. Added ``getAhaSvcByType`` and
  ``getAhaSvcsByType`` APIs and ``aha://<svctype>...`` URL resolution.
- Added the ``celltype`` class variable used to set the service type reported
  in cell info, and normalized the AHA and JSONStor service types to ``aha``
  and ``jsonstor``.

Bugfixes
--------
- Reading your own API key metadata (``getApiKey``/``listApiKeys``) no longer
  requires the ``auth.self.set.apikey`` permission.
- Getting, modifying, or deleting a user's API key by iden now checks the
  permission against the key's owner, requiring ``auth.user.set.apikey`` for
  another user's keys. Only API key metadata (such as the name) was accessible
  this way; no secret key material was ever disclosed.
- Fixed ``trigger.mod`` incorrectly advertising ``--form``/``--tag``/``--prop``, which are not
  editable trigger properties.
- Fixed a bug where ``ival`` tag timestamps were displayed as raw storage
  values instead of in the human-friendly repr format used for ``ival``
  properties.

Notes
-----
- Services run from Docker containers now use structured logging by default.
- Updated the pinned version of the ``msgpack`` library to ``>=1.2.1,<1.3.0``.

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
