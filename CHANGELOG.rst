.. vim: set textwidth=79

.. _changelog:

*****************
Synapse Changelog
*****************

v3.0.0b3 - 2026-07-17
=====================

Model Changes
-------------
- Removed the ``it:exec:proc:cmd:history`` property.
- Renamed the ``it:cmd:history`` form to ``it:exec:command``, added the
  ``it:host:activity`` interface, and removed the ``:time`` property.
- Added the ``it:exec:command:output`` property to record the output of a
  command.
- Removed the ``pol:country:iso:3166:alpha3`` and
  ``pol:country:iso:3166:numeric3`` properties in favor of
  ``pol:country:codes``.
- Added the ``it:os:posix:cron`` form to model cron job entries configured on a
  host.
- Removed the ``risk:attack:compromise``, ``risk:extortion:compromise``, and
  ``risk:outage:attack`` properties.
- Added the ``inet:http:request:fetch`` property to record the
  ``it:exec:fetch`` event which caused the HTTP request.

Features and Enhancements
-------------------------
- All Synapse services booting from 3.0.0b3 must use fresh storage. Booting
  from v3.0.0b2 versions of service storage is not supported, and services will
  fail to boot.
- Added ``__slots__`` to the ``Node`` and ``Path`` runtime classes to reduce
  per-instance memory overhead.
- Added support for Storm package ``modules`` entries to load their Storm from
  a Python package asset (via ``package`` and ``path``) or a file (via
  ``path``), and removed the ``external_modules`` package definition section
  which those keys replace. Modules loaded this way are no longer automatically
  prefixed with the package name and must specify their fully qualified
  ``name``.
- Removed the cell drive spawn IO worker. The cell drive now always runs in-
  process.
- Storm package autodoc now renders a ``Dependencies`` section from the
  package's ``dependencies``.
- The ``Cell.initBackupStream()`` fini message now reports ``rawsize``, the
  uncompressed size of the backup archive contents.
- Reduced the maximum length of indexed UTF8 values in Cortex layers to 64
  bytes.
- ``Cell.initBackupStream()`` now generates the backup archive directly from
  the live LMDB slabs and streams it as a zip, without staging a full copy of
  the service on local disk. Removed the Cell ``backup:dir`` configuration
  option.
- Added the ``Cell.initBackupStream()`` API which takes a live backup and
  streams it as typed ``(type, info)`` messages
  (``init``/``data``/``fini``/``err``), and retooled
  ``synapse.tools.service.backup`` to accept either a directory (offline copy)
  or a telepath URL (live backup via ``initBackupStream()``).
- Renamed ``promote()``'s ``graceful`` argument to ``force`` and flipped the
  default so a bare ``promote()`` call performs a safe, coordinated leadership
  handoff. Pass ``force=True`` (or ``service.promote --failure``) to
  unilaterally promote without contacting the current leader; doing so while
  the old leader is still reachable will very likely render it unusable and
  require a restore from backup.
- Added ``cmpr``, ``limit``, and ``type`` arguments to
  ``$lib.view.getPropValues()`` and ``cmpr`` and ``type`` arguments to
  ``getPropCount()`` for prefix (``^=``) listing and counting of property
  values.
- Removed the ``synapse_version`` pkgdef field. A package's Synapse version
  requirement is now expressed as a reserved ``synapse`` entry in the new
  ``dependencies`` dict. Added ``title`` and ``conflicts`` pkgdef fields. Unmet
  non-optional dependencies now raise an error when a Storm package is loaded,
  rather than only logging.
- Added the ``$lib.vault.type`` Storm library for registering versioned vault
  type schemas that validate vault data, with automatic migration on version
  bumps.
- Removed the AHA service pool and Storm query mirror pool features, including
  the ``aha.pool.*`` and ``cortex.storm.pool.*`` Storm commands, the cron job
  ``--pool`` option, and the ``pool`` flag from the Extended HTTP API
  configuration.

Bugfixes
--------
- ``SYN_PROVISION_FOLLOWER`` is now parsed with ``envbool``, so values of ``0``
  or ``false`` disable follower provisioning instead of enabling it.
- Converted the Storm ``auth:user`` type ``roles()`` method into a dynamically
  generated ``roles`` property.
- ``synapse.lib.logging.watch`` called with ``last=0`` now streams only new
  records instead of replaying all previously stored logs.
- Fixed ``rstorm.getCell()`` raising ``AttributeError`` for rstorm ctors that
  are not real Cell subclasses (e.g. doc-only test doubles with a custom
  ``anit()``).
- Fixed several JSON Schema definitions in ``synapse.lib.schemas`` that used
  non-standard keywords (``minLen``, ``minlen``, ``minval``) which were
  silently ignored, so the intended length/range constraints were not enforced.
  As a result, Extended HTTP API method handlers (``methods.get``,
  ``methods.post``, etc.) must now be non-empty Storm queries.
- Changed the AHA service to require the ``dns:name`` (``SYN_AHA_DNS_NAME``)
  option and fail to start without it.
- ``synapse.tools.axon.get`` no longer leaves an empty file behind when a file
  fetch fails.
- Fixed a confusing error message when lifting an array property with a bare
  scalar value (e.g. ``syn:prop:type=ival``); the error now points to the array
  element lift syntax (``syn:prop:type*[=ival]``) instead of an internal
  implementation detail, and no longer leaks a raw Python TypeError for the ``~=``
  and ``^=`` comparators.

Notes
-----
- Removed the ``synapse.telepath.Client`` class; use
  ``synapse.telepath.ClientV2``.
- Feature-flag values advertised in a Cell's Telepath ``features`` dict (e.g.
  ``stormservice``) are now PEP 440 version strings (e.g. ``'1.0.0'``) instead
  of bare integers, and ``Proxy._hasTeleFeat()`` compares them via
  ``synapse.lib.version.matches()`` instead of integer ``>=``.
- Backups streamed via ``Cell.initBackupStream()`` are now zip archives rather
  than gzipped tarballs.
- Removed Telepath feature flags (``tellready``, ``dynmirror``, ``tasks``,
  ``shutdowndrain``, ``getAhaSvcsByIden``, ``unpack``, ``callpeers``) that have
  been unconditionally present on every 3.x Cell/Axon/AHA service since the
  Synapse 3.x major-version handshake makes them unreachable by any older peer.
  The corresponding feature-absent code paths were also removed, including the
  ``feats`` gate on ``Cell.getAhaProxy()``/``callPeerApi()``/``callPeerGenr()``
  and the pre-connect check in ``synapse.tools.aha.mirror``. Optic's cross-
  mirror ``sendStoryMesg``/``sendUIMessage`` peer fan-out
  (``synmods/optic/app.py``), which used the ``callpeers`` flag, is now
  unconditional.
- Removed the ``runBackup``, ``getBackups``, ``getBackupInfo``, ``delBackup``,
  ``iterBackupArchive``, and ``iterNewBackupArchive`` Cell APIs, the
  ``$lib.backup`` and ``$lib.cell.getBackupInfo()`` Storm APIs, and the
  ``synapse.tools.service.livebackup`` tool in favor of ``initBackupStream()``.
- Changed the AHA service to always start its provisioning listener now that
  ``dns:name`` is required. As such, ``aha:name`` and ``aha:network`` are no
  longer used to do implicit ``dns:name`` resolution.

Improved documentation
----------------------
- Removed Synapse 2.x.x model updates section from Synapse docs.
- Removed Python API section from Synapse docs.

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
