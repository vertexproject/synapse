# Synapse Changelog

## v3.0.0 - 2026-08-13

### Model Changes

- Updated ``econ:pricerange`` and ``econ:pricechange`` to normalize their own
  normalized values, which carry the fields they compute alongside the pair
  their constructors accept.

### Features and Enhancements

- Relaxed the Cell storage version requirement to ``>=3.0.0,<4.0.0`` so that
  storage created by a Synapse ``3.x`` release may be used by any later ``3.x``
  release.

### Bugfixes

- Fixed an Axon issue where deleting a file left its byte offset index rows in
  place, which could cause a subsequent byte range read of the same file to
  return a short or incorrect result.
- Fixed a bug where the ``syn.nodes`` feed renormalized a tag property value as
  new input rather than as the typed value it is, silently skipping a ``comp``
  typed tag property.
- Fixed a bug where ``copyto`` failed to copy nodes with array properties and
  dropped the virtual property values stored with a tag property value.
- Fixed a bug where a View which had a ``desc`` set could not have a ``quorum``
  configured, since the View definition schema did not allow the ``desc`` key.

## v3.0.0rc1 - 2026-08-12

### Model Changes

- ``inet:net`` and ``inet:cidr`` now repr IPv4-mapped IPv6 ranges with the
  embedded IPv4 dotted quad.
- ``inet:ip`` ``:type`` is now ``private`` for addresses in ``3fff::/20``.
- ``inet:ip`` ``:type`` and ``:scope`` now classify IPv4-mapped IPv6 addresses
  the same as the IPv4 address they embed.
- Added the it:log:event:host:name property.

### Features and Enhancements

- Synapse container images are now also published to the Vertex Hub registry at
  ``hub.vertex.link``, without the ``vertexproject/`` prefix (e.g.
  ``hub.vertex.link/synapse-cortex``).

### Bugfixes

- Fixed a bug where ``merge`` dropped the virtual property values stored with a
  property or tag property value.
- Fixed a bug where ``merge`` failed to merge nodes with array properties.
- ``$layer.getTombstones()`` now yields node ids as integers, matching
  ``$layer.getEdgeTombstones()`` and ``$node.nid``.
- Setting a tagprop virtual property such as ``[ +#foo.bar:_baz.precision=day ]``
  now confirms the tag ``add`` permission.
- ``$node.difftags()`` now confirms the tag ``add`` and ``del`` permissions
  when called with ``apply=(true)``.
- ``diff --tag`` now surfaces tags deleted in the view.
- ``$layer.delTombstone()`` now returns ``true`` or ``false`` as documented,
  and raises ``BadArg`` for an unknown tombstone type.
- ``$layer.delTombstone()`` now requires the ``add`` permission for the value
  the tombstone masks, and may only be called on the write layer of the current
  view.
- A whole node tombstone now clears the part-of-node tombstones it supersedes,
  so a layer push or a merge no longer silently drops them.
- Fixed the ``EDIT_PROP_TOMB``, ``EDIT_TAG_TOMB``, ``EDIT_TAGPROP_TOMB``, and
  ``EDIT_NODE_TOMB`` layer edits not removing a live value held by the same
  layer, which could leave a point lookup and an index scan disagreeing.
- Fixed a bug where ``movenodes`` stored a merged tag property value with the
  virtual properties of another layer value.
- Fixed a bug where ``$lib.layer.get().setStorNodeProp()`` did not record the
  storage type and hidden storage virtual properties of the value it set,
  omitting member type counts and ``ival`` side indexes.
- Fixed a bug where ``movenodes`` stored a merged property value with the
  storage type and virtual properties of another layer value, writing property
  index rows which lifts could not find.
- Fixed a bug where growing the LMDB map part way through a nexus transaction
  committed the partially applied writes, which could leave a layer with index
  rows and counts that no storage node or nexus log entry accounted for.
- Fixed a bug where deleting a node which carried edge tombstones decremented
  the live edge counts rather than the tombstone edge count.
- Fixed a bug where setting a tag on a node which did not yet exist in the
  write layer wrote the per-form tag index rows under the wrong abbreviation,
  causing ``<form>#<tag>`` lifts to miss the node.
- ``$lib.crypto.jwt.verify()`` now rejects a ``jwks_uri`` which resolves to an
  IPv6 address embedding a non-global IPv4 address, such as a ``64:ff9b::/96``
  NAT64 address for a private host, unless ``allowinternal`` is set.
- ``$lib.inet.ipv6.expand()`` now renders IPv4-mapped addresses with the
  embedded IPv4 dotted quad.
- Fixed an issue where a read worker would fail to apply a view or layer change
  made while it was behind the leader, and diverge from it.
- Fixed an issue where the OAuth V2 nexus handlers would attempt a write on a
  read-only Cortex.
- Fixed an issue where recomputing the layers of a forked View would attempt a
  write on a read-only Cortex.
- Fixed the ``entity:achieved`` default display column
  ``achievement::org::name`` which referenced a property that does not exist.
  It is now ``achievement::issuer::name``.
- Fixed Ival types not persisting or respecting the precision virtual property
  upon setting other virtual properties.

### Notes

- Updated the vendored ``email`` and ``json`` modules to the CPython 3.14.7
  release.
- Removed the `mdinclude` mdstorm directive. Every `mdinclude` fence has been
  inlined directly into its page's Markdown source instead of being spliced in
  at build time.
- Updated the vendored ``ipaddress`` module to the CPython 3.14.7 release.
- Removed Synapse patches for CVE-2024-7592 and CVE-2025-8194 since they were
  for Python versions that are no longer supported.

### Improved documentation

- The documentation bundle navigation now lists the ``v3.0.0b5`` and
  ``v3.0.0b6`` changelog entries.
- Updated the Docker image references in the deployment documentation to use
  the Vertex Hub registry (``hub.vertex.link``).
- Removed the CHANGELOG.md file at the root of the Synapse OSS repository. The
  Synapse changelog can now be found [here](https://github.com/vertexproject/synapse/blob/main/synapse/assets/docs/changelog.md)
  or at the [Vertex Hub](https://hub.vertex.link/docs/synapse/latest/changelog.md).
- Corrected the CLI tool documentation to note that the 2.x top-level
  ``synapse.tools.<name>`` module paths were removed in Synapse 3.0.0.
- Updated the Kubernetes deployment examples for Synapse 3, including the
  ``synapse.tools.service.healthcheck`` probe path and the ``v3.x.x`` image
  tags.

### Deprecations

- Removed the ``storNodeEditsNoLift()`` Layer API. Use ``storNodeEdits()``,
  which resolves the edits against the layer before they are applied.

## v3.0.0b6 - 2026-08-11

### Improved documentation

- Rebuilt the Synapse documentation bundle so it includes the ``v3.0.0b5``
  changelog.

## v3.0.0b5 - 2026-08-11

### Model Changes

- A property ``became`` in the ``v2map`` model dictionary is now relative to
  the entry form only when it is prefixed with ``:``, and may otherwise be a
  full property path.
- Added the ``:domain`` property to ``it:host`` to record the authentication
  domain as an ``inet:service:platform``.
- Added the ``inet:service:message -(about)> *`` light edge.
- The ``file:subfile:entry`` form no longer extends ``file:stored:entry`` and
  no longer has the ``:added``, ``:created``, ``:modified``, and ``:accessed``
  properties. The ``file:archive:entry`` form now extends ``file:stored:entry``
  directly and retains them.
- Added the ``file:subfile`` interface, implemented by the
  ``file:subfile:entry``, ``file:archive:entry``, ``file:mime:rar:entry``, and
  ``file:mime:zip:entry`` forms.
- Added the ``doc:published`` interface to the ``meta:story`` form.
- Added ``it:app:suricata:rule`` and ``it:app:suricata:matched`` forms.
- Added ``:extmodel`` to the ``syn:form``, ``syn:type``, and ``syn:tagprop``
  runt nodes.

### Features and Enhancements

- Added an ``advanced`` boolean to the Storm package definition, marking a
  package which is delivered by a deployed Storm service rather than installed.
  ``synapse.tools.storm.pkg.gen.reqSvcPkgProto()`` loads the package a service
  delivers and requires the flag.
- Added the ``hide`` Storm opt, which removes the message types it names from
  the output message stream. It is the inverse of ``show``, and setting both
  raises a ``BadArg``.
- Added the ``meta`` Storm opt. The Cortex does not interpret it; it is echoed
  back verbatim as the ``meta`` key of the ``init`` message so a caller can
  correlate a message stream with its own state, and it is recorded on the
  Storm query log entry when ``storm:log`` is enabled. It is omitted from
  ``init`` when the opt is not set.
- The Storm query ``opts`` dictionary is now validated against a JSON schema.
  Only documented opts are accepted; an unknown or wrongly typed opt raises
  ``SchemaViolation`` rather than being silently ignored. The same schema now
  validates the ``stormopts`` of a Storm dmon definition.
- The ``min`` and ``max`` commands now order values using the ordering defined
  by their type, allowing string properties to be ordered lexically and
  ``it:version`` properties to be ordered by version rather than raising
  ``BadCast``.
- Updated the allowed versions of the ``cryptography`` library.
- A Cortex leader now retrieves and registers Storm service packages and
  replicates them through the Nexus, so a mirror loads and persists a service
  package without connecting to the service.
- Added the ``getStormSvcPkgFile()`` Storm service API. A Cortex retrieves the
  files shipped by a service delivered Storm package into its Axon, by path,
  before the package ``onload`` runs.
- Added support for connecting ``synapse.tools.storm`` to a Cortex over the
  HTTP API using an ``https://<apikey>@host:port/`` URL. Added the ``--https-
  ca-dir``, ``--https-noverify``, and ``--https-proxy`` options.
- Added ``synapse.tools.storm.pkg.publish``, which builds the documentation and
  the Storm package from a YAML prototype, uploads any files it declares, and
  publishes it to the Vertex Hub.
- Added a ``files`` section to the Storm package format, which ships data files
  alongside a package by SHA256. ``synapse.tools.storm.pkg.gen`` generates the
  section from the ``files`` directory beside the package YAML file, walked
  recursively, keyed by each file's path relative to that directory, with each
  entry carrying the ``sha256`` of its contents. An entry may be declared in
  the package YAML file to carry additional fields for the file it names. The
  files are uploaded when pushing to a Cortex, and installing the package
  downloads them into the Cortex Axon.
- Added support for specifying a permission as either a dotted string or a list
  of permission parts to ``$user.allowed()``, ``$user.getAllowedReason()`` and
  the ``auth.user.allowed`` command.
- Improved the performance of array property lifts on views with multiple
  layers.
- Added ``$lib.vertex.packages.get()`` for retrieving package definitions from
  the Vertex Hub without installing them.
- The ``synapse.tools.storm.pkg.gen`` tool now allows ``--save`` together with
  ``--no-build``, which allows re-signing an already built Storm package with
  ``--signas``.
- ``synapse.tools.storm.pkg.doc`` now builds package docs natively from
  Markdown/mdstorm sources instead of RST/pandoc, dropping the pandoc
  dependency for building package docs.
- Added per-deployment Storm package encryption via the
  ``metadata.encryption.deploy`` key, built with the ``--encrypt-pubkey``
  option of ``synapse.tools.storm.pkg.gen`` using a deployment's RSA public
  key. A registered Cortex decrypts the package seed with its deployment RSA
  private key on install.
- ``mdstorm`` gained an ``mdinclude`` directive (replacing RST
  ``include::``/``literalinclude::``) and per-fence ``--mock-http`` on
  ``mdstorm`` (for documents with more than one HTTP cassette).
- Added ``synapse.tools.storm.pkg.doc``, a Sphinx-free Markdown documentation
  builder which renders a Storm package's ``docs/`` source tree into
  ``files/docs`` next to its pkgdef: ``mdtoc`` fence resolution into a nav tree
  + ``metadata.json``, and link/anchor/orphan-page validation.
- Added the ``$lib.crypto.jwt`` Storm library and ``crypto:jwt`` object for
  constructing, signing, and verifying JSON Web Tokens (JWTs). Supports the
  ``HS*``, ``RS*``, ``PS*``, and ``ES*`` algorithms, compact and flattened-JSON
  serialization, registered-claim validation (``exp`` / ``nbf`` / ``aud`` /
  ``iss`` / ``sub``), and JWK / JWKS keys including fetching a ``jwks_uri``
  over HTTPS.
- Added the ``$lib.crypto.ecc`` library to generate and load ECC keys as
  ``crypto:ecc:key`` objects which sign and verify bytes.
- Added the ``$lib.crypto.rsa`` library to generate and load RSA keys as
  ``crypto:rsa:key`` objects which sign and verify bytes (``pkcs1v15`` and
  ``pss`` padding).
- HTTP APIs now accept a user API key as the HTTP Basic auth username.
- Added encryption for the Storm queries within package modules and commands
  via a new ``metadata.encryption`` key. ``synapse.tools.storm.pkg.gen``
  enables this with the ``--encrypt`` option. The package ``codesign`` key has
  moved under a new top-level ``metadata`` key.
- The Synapse version parser now accepts an optional PEP 440 epoch prefix (for
  example ``3!1.2.3``) in version strings, including Storm package ``version``
  fields.
- Added the ``$lib.vertex`` Storm library and the ``vertex.register``,
  ``vertex.packages.list``, ``vertex.packages.versions``, and
  ``vertex.packages.install`` commands for registering a deployment with the
  Vertex Hub and installing subscription authorized packages.
- Added ``synapse.tools.utils.mdstorm``, a Markdown-native Storm-directive
  processor.

### Bugfixes

- Fixed the Storm library documentation handling of argument defaults. A list
  of scalar values may now be declared as an argument default, and string
  defaults are now quoted, so values such as ``=`` no longer render as
  ``cmpr==``.
- Fixed an issue where vault secrets could not be read from a Storm package
  module using ``asroot:perms`` on behalf of a user who only holds read
  permission on the vault.
- Fixed AHA hostname resolution for services which advertise a DNS name. AHA
  connected to a service using the name it was registered under rather than the
  hostname the service advertises, causing a TLS hostname mismatch, and a
  service could not resolve its user certificate when connecting to a service
  whose AHA registered hostname is a DNS name outside of the AHA network, such
  as the AHA service itself via ``aha://aha...``.
- All services now commit their dirty slabs after each nexus transaction rather
  than on the periodic slab sync loop, so an unclean shutdown can only leave
  the nexus log one entry ahead of the applied state.
- Set an explicit ``websocket_ping_timeout`` for the Cell HTTP API to avoid
  Tornado closing slow-but-alive websocket connections under load.
- Fixed heading levels in generated Storm package documentation
  (``docStormpkgMd``) so the Dependencies, Storm Commands, Storm Modules, and
  Endpoints sections nest directly under the page title, allowing the docs
  viewer to generate a table of contents for the page.
- Fixed ``mdstorm`` adding an extra blank line and unneeded 4-space indentation
  inside rendered fenced code blocks.
- Fixed an issue where a Storm query which raised an exception inside an edit
  block could cause the exception to be logged twice.
- Fixed an issue where a ``Daemon`` shutdown could log errors for telepath
  calls which were in flight on client link pools.
- Fixed ``$user.allowed()``, ``$user.getAllowedReason()`` and the
  ``auth.user.allowed`` command reporting an incorrect result when no
  ``gateiden`` was specified.
- Fixed a bug where a reverse array property lift on a view with multiple
  layers returned nodes in the wrong order.
- Enabled caching of parsed private keys in ``CertDir`` instead of re-parsing
  the CA key PEM on every certificate signature, and stopped blocking the event
  loop during ``AhaCell``/``ProvApi``/``EnrollApi`` CSR signing.
- Fixed several issues with graph projections in a view where nodes have been
  deleted. A projection could include light edges from the layers below the
  layer which deleted the node they belong to, and could raise an
  ``AttributeError`` when one of the existing nodes had been deleted in the
  view.
- Fixed an issue where node data belonging to a node which was deleted in a
  lower layer could be returned by ``$node.data.list()`` and
  ``$node.data.pop()``.
- Fixed a race in ``Cell`` teardown where the slab could close before the dmon,
  causing a still-streaming generator (eg ``AhaCell.getAhaTopo()``) to log an
  unhandled error.
- Fixed ndef references to runt nodes not resolving for wildcard and array
  pivots, such as ``syn:form=inet:flow :interfaces -> *``.
- Fixed ``CertDir`` CRL loading to treat an empty ``.crl`` envelope as a CA
  with no revocations, and to raise ``BadCertBytes`` naming the file when a
  ``.crl`` cannot be loaded.
- Fixed an issue where a nodedata or light edge tombstone edit did not remove
  the live rows in the same layer, causing ``$node.data.get()`` and
  ``$node.data.list()`` to disagree.
- Fixed an issue where lifting a tagprop by value could raise a ``KeyError``
  when a different tagprop of the same tag was deleted in an upper layer.
- Fixed an issue where a nodedata lift in a view with multiple layers could
  return a node deleted in an upper layer.
- An explicit pivot from a property to a form now normalizes the source value
  as the destination type when the property does not reference that form, which
  allows pivoting between disparate types which share values. Previously such a
  pivot returned no nodes.
- Fixed an issue where an edge deleted in a forked view could still be returned
  by edge walks, ``getEdges()`` and node exports.
- Fixed several errors logged during teardown when a caller bails out early on
  an Axon ``readlines()`` or ``csvrows()`` generator.
- Fixed mdstorm's mdstorm-setup Cortex boot to resolve axon/jsonstor peers via
  an ephemeral AHA network (matching rstorm), instead of a bare cell with no
  peers, so package onload hooks using ``$lib.axon``/``$lib.jsonstor`` complete
  correctly.
- Fixed ``docStormpkg``/``docStormpkgMd``/mdstorm's ``--load-pkg`` requiring a
  package's declared doc build artifacts to exist on disk when they are
  unrelated to the operation being performed.
- Fixed storm command argument parsing where some values would incorrectly be
  parsed as multiple arguments or terminate the argument list.
- Allowed the ``crypto:hash:ssdeep`` type to accept empty hash segments, such
  as the empty-file hash ``3::``.
- The ``it:version`` type now supports version-aware ordering and range
  comparisons (>=, <=, >, <, and range=) that follow PEP 440 and SemVer 2.0.0
  precedence, including pre-release, epoch, and dev/post handling (e.g.
  1.0.0-alpha sorts below 1.0.0). The ``it:semver`` type now retains pre-
  release information for ordering instead of discarding it, so pre-releases
  sort correctly (1.0.0-alpha < 1.0.0-beta < 1.0.0).

### Notes

- Removed the internal ``_loginfo`` Storm opt. The cron and extended HTTP API
  identifiers it carried now ride in the ``meta`` opt, recorded as a nested key
  rather than merged, so a caller cannot supply a field which reads as the
  Cortex own.
- Each value within a packed node ``props``, ``tags`` and ``tagprops`` is now a
  two element envelope, ``[<valu>, <info>]``, where the info dict may carry a
  ``t`` type name, an ``r`` repr and a ``v`` dict of virtual property
  envelopes. The ``reprs`` and ``tagpropreprs`` dictionaries and the flattened
  ``<name>.type``, ``<name>.<virt>`` and ``<name>.size`` keys are removed. An
  array property value is a list of member envelopes. A ``.nodes`` file
  exported by an earlier build carries the old shape and must be re-exported.
- The ``show`` Storm opt now filters every message type, including ``init``,
  ``fini`` and ``err`` which were previously sent regardless. An empty list now
  sends no messages rather than disabling filtering. A ``show`` list which
  omits ``err`` will silently discard query errors.
- The ``task`` Storm opt is now honored or rejected rather than silently
  dropped. Asking for an iden already in use by a running task, or asking for
  one from a runtime which is already promoted under a different iden, now
  raises ``BadArg`` as documented.
- A Storm service is now identified by its cell type. It must be added under
  the cell type name it reports, that name is unique for a Cortex, and
  ``service.del`` takes it. The service iden is removed, along with the
  ``svciden`` key in the Storm package definition schema and
  ``commands[].cmdconf``, the ``syn:cmd:svciden`` property, and the
  ``$modconf.svciden`` and ``$cmdconf.svciden`` variables. ``$lib.pkg.get()``
  and ``$lib.pkg.list()`` report the providing service as ``svcname``.
- A Storm service now delivers exactly one Storm package. ``_storm_svc_pkgs``
  is replaced by ``_storm_svc_pkg``, and ``getStormSvcInfo()``,
  ``_storm_svc_name`` and ``_storm_svc_vers`` are removed in favor of the cell
  type and the cell ``VERSION``.
- The HTTP API error codes now match the ``synapse.exc`` classes raised by the
  equivalent Telepath and Storm APIs. ``DupUser`` is now ``DupUserName``,
  ``DupRole`` is now ``DupRoleName``, ``NotAuthenticated`` is now ``AuthDeny``,
  ``MissingField`` is now ``SchemaViolation``, and ``BadHttpParam`` is now
  ``BadArg``. The ``NotAuthenticated``, ``BadHttpParam``, and ``MissingField``
  exceptions have been removed from ``synapse.exc``.
- ``$user.allowed()`` and ``$user.getAllowedReason()`` now use the permission's
  registered default when no ``default`` is specified, matching permission
  enforcement.
- The ``--push`` option of ``storm.pkg.gen`` no longer accepts a PkgRepo URL.
  Storm packages are published to the Vertex Hub over HTTP.
- Updated the Vertex Project CA certificates shipped in ``synapse/data/certs``
  for 3.0.0. Storm packages signed by the retired ``The Vertex Project
  Intermediate CA 00`` no longer verify.
- Node exports now emit the edges of each node, and the edge metadata, in a
  deterministic order.
- The Storm package definition schema now rejects unknown keys. A typo or stray
  key raises a ``SchemaViolation`` at ``reqValidPkgdef`` time rather than being
  silently ignored. The ``modconf``, ``cmdconf``, ``queryopts``, vault
  ``schema``, and ``optic`` values continue to allow arbitrary keys.
- Storm command argument lists are now terminated only by ``|``, ``}``, or end
  of query.

### Improved documentation

- Updated the Synapse glossary to reflect the 3.x data model and Storm
  behavior, and added a ``NID`` entry.
- Documented the ``it:domain`` removal and the ``file:bytes`` executable
  metadata move to ``file:mime:exe`` in the 3.0.0 changes.
- Corrected the Storm API guide: removed the ``mirror`` opt which no longer
  exists, documented the ``readpool`` opt, the ``nexsoffs`` key of the ``fini``
  message and the ``time`` key of the ``edits`` message, and fixed a ``show``
  opt example which named a message type that does not exist.
- Built the ``synapse`` docs bundle via the new ``synapse.tools.utils.doc``
  tool, and moved its docroot from ``docs/`` to ``docs/synapse/``. Absolute
  cross-bundle doc links to ``synapse`` drop the redundant ``synapse/`` path
  segment.
- Added a single-file ``docker compose`` orchestration example to the Synapse
  deployment guide, and documented creating a Cortex user, generating a user
  API key, and connecting the Storm CLI over HTTPS.
- Switched mdstorm's rendered Storm output to the ``stormdoc`` fenced code
  block language (not ``text``), keeping ``storm`` free for future Storm syntax
  highlighting.
- Rewrote ``docs/Makefile`` to build the docs bundle via
  ``synapse.tools.utils.doc`` instead of Sphinx.
- Converted all Synapse OSS documentation (``docs/``, ``README``) from
  reStructuredText to Markdown, replacing the Sphinx build.

### Deprecations

- Removed the ``synapse.tools.utils.autodoc`` documentation tool. Use
  ``synapse.tools.utils.mdstorm``, ``synapse.tools.storm.pkg.doc``, and
  ``synapse.tools.utils.doc``.
- Renamed the ``node:edits`` Storm message type to ``edits``. The message
  payload is unchanged.
- Renamed the ``show:storage`` sub-key of the ``node:opts`` Storm opt to
  ``storage``, matching the packed node key it populates.
- Removed the ``verbs`` sub-key of the ``node:opts`` Storm opt. A packed node
  now always carries the ``n1verbs`` and ``n2verbs`` light edge verb counts.
- Removed the ``editformat`` Storm opt and the ``node:edits:count`` message
  type it produced. Use the ``show`` opt to omit ``edits`` messages from the
  message stream.
- Removed the ``count`` key from the ``edits`` message. It counted the edits
  the layer returned rather than the edits carried by the message, and its only
  consumer was the removed ``editformat`` opt. Sum the per node edit lists to
  count them.
- Moved the ``nexsoffs`` and ``nexstimeout`` Storm opts under a single
  ``nexus`` opt as ``offset`` and ``timeout``.
- Removed the deprecated ``forms`` key from Storm package command definitions,
  along with the ``cmdformhints`` schema definition it referenced. Use
  ``cmdinputs`` instead.
- Removed the unused modules ``synapse.lib.encoding``, ``synapse.lib.ingest``,
  ``synapse.lib.interval``, ``synapse.lib.ratelimit``,
  ``synapse.lib.slaboffs``, ``synapse.lookup.iso3166``, and
  ``synapse.mindmeld``. Removed ten exceptions which were never raised from
  ``synapse.exc``: ``BadCtorType``, ``DupIndx``, ``ModAlreadyLoaded``,
  ``NoSuchAct``, ``NoSuchDecoder``, ``NoSuchEncoder``, ``NoSuchLift``,
  ``NoSuchOpt``, ``PathExists``, and ``StepTimeout``. Removed the ignored
  ``outp`` argument from ``Cell.initFromArgv()`` and ``Cell.execmain()``.
- Removed ``$lib.cell.hotFixesApply()``, ``$lib.cell.hotFixesCheck()``, and the
  Storm hotfix ladder they ran. The ``cortex:runtime:stormfixes`` global is no
  longer set on a new Cortex.
- Removed the Storm ``reindex`` command. It was a no-op reserved for future use
  that only emitted a warning, and has no replacement.
- Removed the ``aha:svcinfo`` Cell configuration option.
- The ``/api/v3/storm`` HTTP API now always streams newline delimited JSON and
  the ``stream`` option has been removed.
- Removed the Storm package definition schema ``docs`` key. A Storm package no
  longer carries inline ``docs`` in its package definition; its documentation
  is published to the Vertex Hub documentation viewer instead.
- Removed the Storm service ``add`` and ``del`` event hooks (
  ``_storm_svc_evts`` ). Use the Storm package ``onload`` and ``inits``
  sections.
- Removed the ``rstorm`` RST documentation pre-processor
  (``synapse.lib.rstorm`` and ``synapse.tools.utils.rstorm``) and the Sphinx
  build dependencies. Use ``synapse.tools.utils.mdstorm``,
  ``synapse.tools.storm.pkg.doc``, and ``synapse.tools.utils.doc``.
- Removed the ``inaugural`` Cell configuration option.

## v3.0.0b4 - 2026-07-24

### Model Changes

- Removed the `pol:election:time` property in favor of the `:period` property from the `base:activity` interface.
- Removed the `:loaded` and `:unloaded` properties from `it:exec:lib:load` and added the `it:exec:lib:unload` form to model library unload events.
- Replaced the per-def `prevnames` model key with a bundled v2-to-v3 model name map, exposed in the model dictionary as `v2map`.
- Comp type fields must reference a named type; inline `(type, opts)` field definitions are no longer supported.
- `inet:http:param:name` is now a `text` type (case-insensitive, case-preserving) instead of `str:lower`.

### Features and Enhancements

- The AHA service now registers itself in its own service registry and is included in the AHA service lists.

- Moved Storm package API endpoint definitions from a per-module `modconf.endpoints` key to a schema'd top-level `endpoints` key on the package definition.

- Renamed the `istype()` method on Storm typed values to `is()` for consistency with `$node.is()`.

- The type name in a Storm `<value> as <type>` cast may now be a format string. For example:

  ``` text
  $valu as `crypto:{$kind}`
  ```

- The Storm `<value> as <type>` cast may now be applied to individual elements inside a value list.

- Added the `SynTest.getTestCluster()` test helper and `TestCluster` class for booting a set of services on a single AHA network.

## v3.0.0b3 - 2026-07-17

### Model Changes

- Removed the `it:exec:proc:cmd:history` property.
- Renamed the `it:cmd:history` form to `it:exec:command`, added the `it:host:activity` interface, and removed the `:time` property.
- Added the `it:exec:command:output` property to record the output of a command.
- Removed the `pol:country:iso:3166:alpha3` and `pol:country:iso:3166:numeric3` properties in favor of `pol:country:codes`.
- Added the `it:os:posix:cron` form to model cron job entries configured on a host.
- Removed the `risk:attack:compromise`, `risk:extortion:compromise`, and `risk:outage:attack` properties.
- Added the `inet:http:request:fetch` property to record the `it:exec:fetch` event which caused the HTTP request.

### Features and Enhancements

- All Synapse services booting from 3.0.0b3 must use fresh storage. Booting from v3.0.0b2 versions of service storage is not supported, and services will fail to boot.
- Added `__slots__` to the `Node` and `Path` runtime classes to reduce per-instance memory overhead.
- Added support for Storm package `modules` entries to load their Storm from a Python package asset (via `package` and `path`) or a file (via `path`), and removed the `external_modules` package definition section which those keys replace. Modules loaded this way are no longer automatically prefixed with the package name and must specify their fully qualified `name`.
- Removed the cell drive spawn IO worker. The cell drive now always runs in-process.
- Storm package autodoc now renders a `Dependencies` section from the package's `dependencies`.
- The `Cell.initBackupStream()` fini message now reports `rawsize`, the uncompressed size of the backup archive contents.
- Reduced the maximum length of indexed UTF8 values in Cortex layers to 64 bytes.
- `Cell.initBackupStream()` now generates the backup archive directly from the live LMDB slabs and streams it as a zip, without staging a full copy of the service on local disk. Removed the Cell `backup:dir` configuration option.
- Added the `Cell.initBackupStream()` API which takes a live backup and streams it as typed `(type, info)` messages (`init`/`data`/`fini`/`err`), and retooled `synapse.tools.service.backup` to accept either a directory (offline copy) or a telepath URL (live backup via `initBackupStream()`).
- Renamed `promote()`'s `graceful` argument to `force` and flipped the default so a bare `promote()` call performs a safe, coordinated leadership handoff. Pass `force=True` (or `service.promote --failure`) to unilaterally promote without contacting the current leader; doing so while the old leader is still reachable will very likely render it unusable and require a restore from backup.
- Added `cmpr`, `limit`, and `type` arguments to `$lib.view.getPropValues()` and `cmpr` and `type` arguments to `getPropCount()` for prefix (`^=`) listing and counting of property values.
- Removed the `synapse_version` pkgdef field. A package's Synapse version requirement is now expressed as a reserved `synapse` entry in the new `dependencies` dict. Added `title` and `conflicts` pkgdef fields. Unmet non-optional dependencies now raise an error when a Storm package is loaded, rather than only logging.
- Added the `$lib.vault.type` Storm library for registering versioned vault type schemas that validate vault data, with automatic migration on version bumps.
- Removed the AHA service pool and Storm query mirror pool features, including the `aha.pool.*` and `cortex.storm.pool.*` Storm commands, the cron job `--pool` option, and the `pool` flag from the Extended HTTP API configuration.

### Bugfixes

- `SYN_PROVISION_FOLLOWER` is now parsed with `envbool`, so values of `0` or `false` disable follower provisioning instead of enabling it.
- Converted the Storm `auth:user` type `roles()` method into a dynamically generated `roles` property.
- `synapse.lib.logging.watch` called with `last=0` now streams only new records instead of replaying all previously stored logs.
- Fixed `rstorm.getCell()` raising `AttributeError` for rstorm ctors that are not real Cell subclasses (e.g. doc-only test doubles with a custom `anit()`).
- Fixed several JSON Schema definitions in `synapse.lib.schemas` that used non-standard keywords (`minLen`, `minlen`, `minval`) which were silently ignored, so the intended length/range constraints were not enforced. As a result, Extended HTTP API method handlers (`methods.get`, `methods.post`, etc.) must now be non-empty Storm queries.
- Changed the AHA service to require the `dns:name` (`SYN_AHA_DNS_NAME`) option and fail to start without it.
- `synapse.tools.axon.get` no longer leaves an empty file behind when a file fetch fails.
- Fixed a confusing error message when lifting an array property with a bare scalar value (e.g. `syn:prop:type=ival`); the error now points to the array element lift syntax (`syn:prop:type*[=ival]`) instead of an internal implementation detail, and no longer leaks a raw Python TypeError for the `~=` and `^=` comparators.

### Notes

- Removed the `synapse.telepath.Client` class; use `synapse.telepath.ClientV2`.
- Feature-flag values advertised in a Cell's Telepath `features` dict (e.g. `stormservice`) are now PEP 440 version strings (e.g. `'1.0.0'`) instead of bare integers, and `Proxy._hasTeleFeat()` compares them via `synapse.lib.version.matches()` instead of integer `>=`.
- Backups streamed via `Cell.initBackupStream()` are now zip archives rather than gzipped tarballs.
- Removed Telepath feature flags (`tellready`, `dynmirror`, `tasks`, `shutdowndrain`, `getAhaSvcsByIden`, `unpack`, `callpeers`) that have been unconditionally present on every 3.x Cell/Axon/AHA service since the Synapse 3.x major-version handshake makes them unreachable by any older peer. The corresponding feature-absent code paths were also removed, including the `feats` gate on `Cell.getAhaProxy()`/`callPeerApi()`/`callPeerGenr()` and the pre-connect check in `synapse.tools.aha.mirror`. Optic's cross-mirror `sendStoryMesg`/`sendUIMessage` peer fan-out (`synmods/optic/app.py`), which used the `callpeers` flag, is now unconditional.
- Removed the `runBackup`, `getBackups`, `getBackupInfo`, `delBackup`, `iterBackupArchive`, and `iterNewBackupArchive` Cell APIs, the `$lib.backup` and `$lib.cell.getBackupInfo()` Storm APIs, and the `synapse.tools.service.livebackup` tool in favor of `initBackupStream()`.
- Changed the AHA service to always start its provisioning listener now that `dns:name` is required. As such, `aha:name` and `aha:network` are no longer used to do implicit `dns:name` resolution.

### Improved documentation

- Removed Synapse 2.x.x model updates section from Synapse docs.
- Removed Python API section from Synapse docs.

## v3.0.0b2 - 2026-07-11

### Model Changes

- Updated the `ival` type repr to return a `<min> - <max>` string rather than a tuple of the min and max time reprs. Max-fill time bounds now collapse their filled tail into a `*` (e.g. `2025-12-31*`). The `ival` type also norms these repr forms back to the same value.
- Added the `meta:story` form to record a story document authored in markdown.
- Updated the `file:base`, `file:bytes`, `file:attachment`, `inet:fqdn`, `inet:ip`, `inet:url`, `inet:email`, `inet:email:message`, `inet:urlfile`, `inet:service:platform`, and `it:cmd` forms to implement the `meta:usable` interface.
- Added the `risk:loss` interface and `risk:loss:life`, `risk:loss:data`, and `risk:loss:funds` forms to record aggregate losses.
- Added the `it:exec:proc:parent` property to record the parent process which created a process.
- Array properties are now declared with the element type in the property typedef and the array container opts (`uniq`/`sorted`/`split`) under an `array` key in the property info dictionary. The `array` type is a prop-only structural container and may no longer be used as the base for a named type.
- Removed the `int:min0`, `int:min1`, and `byte:flags` types. Affected properties now use the `size`, `uint8`, or `uint32` types.
- Added the `size` type for non-negative sizes and counts, and the fixed-width integer types `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, and `uint64`.
- Removed the unused `daterange` type.
- Added the `activity`, `activity:day`, and `reported` ival types.
- Inline type opts are no longer permitted on properties; a property must reference a named type. A property that needs custom normalization opts (`regex`, `enums`, `names`, `precision`, ...) must be declared once as a named type and referenced by name.

### Features and Enhancements

- All Synapse services booting from 3.0.0b2 must use fresh storage. Booting from v3.0.0b1 versions of service storage is not supported, and services will fail to boot.
- Grouped Storm command `endpoints` help output by base URL.
- The `synapse.tools.aha.list` tool now takes an optional `--url` ( defaulting to the local AHA cell) instead of a required positional URL argument.
- Add the `synapse.tools.aha.del` tool to remove a service entry from the AHA registry.
- Renamed the Storm command `endpoints` `host` key to `url` to match the `modconf.endpoints` shape.
- Added an `Endpoints` section to generated Storm package documentation, listing each module's `modconf.endpoints` grouped by resolved base URL.
- The AHA service `aha:network` configuration option now defaults to `syn`.
- Synapse service docker containers now drop privileges to the `synuser` user (UID `999`) via `gosu` at startup when started as `root`, adjusting ownership of `/vertex/storage` before launching the service.
- Add the `SYN_PROVISION_FOLLOWER` environment variable to force an inaugural service to deploy as a follower of an existing leader of its type, including auto-enrolling an AHA server as a clone via multicast discovery.
- An active Cortex now discovers Storm services registered with AHA and automatically adds previously unknown ones using `aha://<type>...` URLs.
- Added a `telepath:port` configuration option to specify the telepath listening port while inheriting the provisioned hostname and CA.
- Added AHA managed leadership terms per service type to dynamically determine the leader on boot and enforce forced promotion retirement. Mirrors now follow the current AHA determined leader dynamically. Removed the cell `mirror` configuration option and added a `parent` option which explicitly overrides the AHA determined leader with a fixed upstream telepath URL.
- Added a unified `AhaClient` that tracks AHA service topology in near real-time via the new `getAhaTopo()` API and is now used by every service that connects to AHA.
- The Cortex `axon` and `jsonstor` configuration options have been removed. When deployed on an AHA network the Axon and JsonStor are located by service type via AHA; a standalone Cortex continues to use its embedded services.
- Added support for automatic AHA service provisioning via the `SYN_PROVISION_SECRET` environment variable, with the optional `SYN_PROVISION_HOST` environment variable to send discovery directly to a specific AHA host.
- AHA now enforces service type uniqueness: only one instance of a service type may register with an AHA deployment. Added `getAhaSvcByType` and `getAhaSvcsByType` APIs and `aha://<svctype>...` URL resolution.
- Added the `celltype` class variable used to set the service type reported in cell info, and normalized the AHA and JSONStor service types to `aha` and `jsonstor`.

### Bugfixes

- Reading your own API key metadata (`getApiKey`/`listApiKeys`) no longer requires the `auth.self.set.apikey` permission.
- Getting, modifying, or deleting a user's API key by iden now checks the permission against the key's owner, requiring `auth.user.set.apikey` for another user's keys. Only API key metadata (such as the name) was accessible this way; no secret key material was ever disclosed.
- Fixed `trigger.mod` incorrectly advertising `--form`/`--tag`/`--prop`, which are not editable trigger properties.
- Fixed a bug where `ival` tag timestamps were displayed as raw storage values instead of in the human-friendly repr format used for `ival` properties.

### Notes

- Services run from Docker containers now use structured logging by default.
- Updated the pinned version of the `msgpack` library to `>=1.2.1,<1.3.0`.

## v3.0.0b1 - 2026-06-30

### Model Changes

- Added new structural forms including `doc:reference`, protocol handshake forms, and the `ind:*` industry model.
- Edge verbs are now validated against the datamodel. Custom edge verbs must now be defined as extended model elements.
- Renamed many forms and properties (for example `ps:contact` to `entity:contact`, `media:news` to `doc:report`, and `hash:*` to `crypto:hash:*`).
- Replaced the `inet:web:*` forms with the `inet:service:*` platform and account model.
- Timestamps are now microseconds since epoch (previously milliseconds) and the time repr is now ISO-8601.
- Added virtual properties: computed sub-values of a property, or context bundled with the value (such as the currency of a price), that can be lifted, filtered, and pivoted.
- Added form inheritance and additional interfaces to the data model. (subforms).
- Merged the `inet:ipv4` and `inet:ipv6` forms into a single `inet:ip` form whose system value is a `(version, integer)` tuple.

### Features and Enhancements

- `$lib.view.list()` and `$lib.layer.list()` now only include views and layers the user can read. `$lib.view.get()` and `$lib.layer.get()` raise `NoSuchView` / `NoSuchIden` for an iden the user cannot read, rather than returning it.
- Added the `$as` key to dictionary guid constructors to name the form to build when a property type can resolve to more than one form.
- `cron.add` now takes a positional period string. Added a `cron.cleanup` command and an at-job `completed` flag.
- Storm macros now use the easy-permission model and are managed with the `macro.grant` command.
- Added the `$lib.file.frombytes()` and `$lib.file.fromhex()` APIs, new `$lib.lift` helpers, `$lib.cortex` Node ID helpers, and `$lib.pkg.state()`.
- Node edits are now deconflicted before being written to the Nexus log, reducing storage utilization.
- Layers now index nodes by an integer Node ID (NID) instead of a BUID, reducing index size and improving lift performance.
- Added tombstones, which allow deleting nodes and parts of nodes within a forked view and applying the deletions to the parent on merge. Deleted nodes are surfaced via the new `syn:deleted` runt node.
- Tag glob wildcards now match zero-length segments.
- Added inline value casting with the `as` clause, and support for multi-target and virtual-property pivots.
- Added the `in` and `not in` membership operators to Storm.
- Updated the default log timestamp format to ISO-8601 UTC with microsecond precision (for example `2026-02-13T10:38:24.545123Z`) for both structured and unstructured log output. Timestamps produced via `SYN_LOG_DATEFORMAT` are now rendered in UTC and support the `%f` directive for microsecond precision.

### Notes

- Synapse version reporting now uses PEP 440 strings: `synapse.version` is a string (previously an integer tuple), `synapse.lib.version.verstring` is removed, `getCellInfo()` no longer includes `verstring`, and `$lib.version.synapse` returns a string.
- Removed the `BadOperArg` exception class. Many Storm input-validation failures that raised `StormRuntimeError` in 2.x now raise `BadArg`.
- Permissions for setting or deleting a node property have been updated to no longer support full property path (`node.prop.set.<form>:<prop>`); only the modern form is checked (`node.prop.set.<form>.<prop>`).
- Permission changes: granular extended-model permissions collapsed to `model.admin`, `view.fork` is no longer granted by default, and `node.data.pop` was renamed to `node.data.del`.
- Cortex feed ingest now uses a single packed-node format and `addFeedData` no longer takes a format name.
- Removed the `cmdr` and `cellauth` tools and reorganized the command-line tools into namespaced subpackages.
- Removed Cortex Core modules and the `modules` config option, the layer `upstream` and `mirror` options, and the `syn:cron` and `syn:trigger` runt nodes.
- Removed several out dated Storm libraries and accessors, including the `$lib.bytes` Axon proxies, `$lib.user`, `$lib.vars`, `$lib.str`, and `$lib.true` / `$lib.false` / `$lib.null` (use bare literals).
- The HTTP API endpoints moved from the `/api/v1/` prefix to `/api/v3/`.
- Storm query `opts` changed: the node-output options `repr`, `links`, and `show:storage` moved under `node:opts`, `idens` was replaced by `nids`, and `opts` is now keyword-only on the Telepath Storm APIs.
- The minimum supported Python version is now 3.14.
- Synchronous Telepath usage is no longer supported; proxies are async-only.
