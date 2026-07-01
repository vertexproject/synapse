.. _vtx_300_breakingchanges:

Synapse 3.0.0 Breaking Changes
==============================

This page is an exhaustive catalog of backward-incompatible changes in Synapse 3.0.0 --
the inverse of the feature changelog. Each entry gives a terse "what breaks" and a
one-line fix, with a :ref: to the detail page that covers the full behavior, examples,
and edge cases. Group your audit by the areas below.

For the ordered, step-by-step upgrade procedure (backup, storage and model changes, config
cleanup, validation), see :ref:`vtx_300_migration`.

Storm language and libraries
----------------------------

Removed and relocated ``$lib`` libraries (see :ref:`vtx_300_storm-lib-removed`):

- ``$lib.user`` removed. Fix: use ``$lib.auth.users.get()`` (omit ``iden`` for the current user).
- ``$lib.str`` removed. Fix: use the ``str`` primitive's ``.join`` and backtick template strings.
- ``$lib.text()`` and its builder object removed. Fix: append to a list and ``(sep).join(list)``, or use backtick strings.
- ``$lib.true`` / ``$lib.false`` / ``$lib.null`` removed. Fix: use the literals ``(true)`` / ``(false)`` / ``(null)``.
- ``$lib.vars`` library (``get``/``set``/``del``/``list``/``type``) removed. Fix: use deref/setitem on ``$lib.vars``, assign ``$lib.undef`` to delete, and ``$lib.utils.type()`` for the type helper.
- ``$lib.bytes`` Axon-proxy methods (``put``/``has``/``size``/``hashset``/``upload``) removed. Fix: call the ``$lib.axon`` equivalents; ``$lib.bytes.fromints()`` remains; use ``$lib.file.frombytes()`` to make a ``file:bytes``.
- ``$lib.ps`` removed. Fix: use ``$lib.task.list()`` / ``$lib.task.kill()``.
- ``$lib.infosec.cvss`` node-mutating helpers (``calculate``/``calculateFromProps``/``vectToProps``/``saveVectToNode``) removed. Fix: compute with ``$lib.infosec.cvss.vectToScore()`` and set the vector/score props directly.
- ``$lib.inet.whois.guid`` (and the ``$lib.inet.whois`` library) removed. Fix: construct the remodeled whois record via a GUID-constructor (gutor) / pkgcommon helpers.
- ``$lib.notifications`` and ``$lib.projects`` removed. Fix: no direct replacement; redesign against the 3.x ``proj`` model and commands.
- ``$lib.gen`` public helpers removed and ``gen.*`` commands flattened/renamed (e.g. ``gen.risk.vuln`` -> ``gen.vuln``, ``gen.ou.org`` -> ``gen.org``). Fix: use the ten flat ``gen.*`` commands or a GUID-constructor (see :ref:`vtx_300_storm-lib-removed`).

Object access conventions (see :ref:`vtx_300_storm-object-conventions`):

- ``$node.form`` / ``$node.ndef`` / ``$node.value`` / ``$node.nid`` are now gtors (no parentheses); ``$node.repr()`` is still a method. Fix: drop the parentheses on the value accessors.
- ``$node.iden()`` removed; nodes are keyed by integer NID. Fix: use the ``$node.nid`` property and switch any stored/compared BUID hex to the NID.
- ``$lib.version.synapse`` and ``.commit`` are now gtors (no parentheses); ``.matches(...)`` is unchanged.
- Dict-like Storm objects (``$lib.globals``, ``$lib.env``) drop ``.get()``/``.set()``/``.list()``/``.pop()``. Fix: use deref/setitem and ``for`` iteration; delete by assigning ``$lib.undef``.
- ``.pack()`` removed from View, Layer, Trigger, CronJob, User, and Role objects (only ``$node.pack()`` remains). Fix: read the discrete named properties instead.
- ``$user.tell()`` and ``$user.notify()`` removed (notification subsystem gone). Fix: use a queue or external system.
- ``$node.isform()`` is renamed to ``$node.is()``, which accepts a list and matches across form inheritance. Fix: replace ``$node.isform(...)`` with ``$node.is(...)`` and prefer it over ``$node.form`` string equality.

Syntax and operator tightening (see :ref:`vtx_300_storm-syntax-operators`):

- Inbound pivot/join (``<-`` / ``<+-``) now only accepts ``*``; named-property inbound variants removed. Fix: rewrite ``<- <prop>`` as ``<- *``.
- Property names -- including wildcard and relative forms -- no longer allow ``.`` segments. Fix: use colon sub-props or the virtual-property dot.
- No whitespace allowed before ``.`` in derefs and tag segments; a space before a dot now parses as a leading-dot virtual property. Fix: make derefs/tag segments hug the dot (``$var.attr``, ``#tag.seg``).
- The lookup-mode ``search`` Storm interface and the ``storm:interface:search`` Cortex config key are removed. Fix: remove the config key; lookup mode now uses scrape plus model lookup hints.
- (Additive, non-breaking: ``in`` / ``not in`` operators, the ``as`` cast, parenthesized multi-target pivots, virtual-property pivot targets.)

Other Storm-surface changes:

- Tag glob wildcards now allow zero-length matches: ``#foo*`` / ``#foo**`` now match a bare ``#foo`` (see :ref:`vtx_300_storm-tag-glob-matching`). Fix: audit globs that relied on a wildcard forcing at least one character; match the specific tag directly if a non-empty segment is required.
- Storm macro definitions drop the ``user`` field (and ``enabled``/``stormopts``); only ``creator`` remains, with an easy-permissions block (see :ref:`vtx_300_storm-macros`). Fix: read ``creator`` instead of ``user``; manage access with ``macro.grant`` / ``$lib.macro.grant()``.
- Cron/trigger commands, ``$lib`` APIs, and Storm objects consolidated onto a dict-based edit path and a new period syntax (see :ref:`vtx_300_storm-cron-and-trigger-api`). Fix: ``cron.add <period> <query>``; ``cron.move``/``enable``/``disable`` and ``trigger.enable``/``disable`` fold into ``cron.mod``/``trigger.mod --enabled``; ``$cron``/``$trig`` ``.set()``/``.pack()``/``.move()`` removed in favor of named-property assignment; cdef ``query`` key renamed to ``storm``.
- ``$lib.inet.http`` request methods drop ``ssl_verify`` and ``ssl_opts``; all TLS settings move into one ``ssl`` dict (see :ref:`vtx_300_storm-http-ssl-options`). Fix: ``ssl_verify=$x`` becomes ``ssl=({"verify": $x})``.
- In a forked view, ``delnode`` and node-edit deletes (``[ -:prop ]``, ``[ -#tag ]``) against data that lives in a parent layer now record a *tombstone* that hides the parent data instead of silently no-op'ing; the deletion is applied to the parent only on merge, and a new ``syn:deleted`` runt node surfaces fully-deleted nodes via ``diff`` (see :ref:`vtx_300_admin-tombstones`). Fix: expect a delete in a fork to hide parent data and to propagate on merge, and use the ``$layer`` tombstone APIs to inspect or cancel a staged deletion. Relatedly, ``$layer.getNodeData()`` now yields a third ``istombstone`` element per tuple and is keyed by the integer ``nid`` rather than the node iden.

Data model
----------

- Property values now carry their type (typed values), enabling consistent type-based handling across the model (see :ref:`vtx_300_datamodel-typed-values`). Fix: assign nodes (not bare strings) for form/interface-typed properties. (The Python ``Node.get`` return shape also changed -- see APIs and integration below.)
- ``inet:ipv4`` and ``inet:ipv6`` merged into a single ``inet:ip`` whose value is a ``(version, int)`` tuple; ``inet:cidr4``/``inet:cidr6`` -> ``inet:net`` (see :ref:`vtx_300_datamodel-ip-unification`). Fix: lift/prop on ``inet:ip`` (constrain via the ``version`` prop).
- Time type and ``synapse.lib.time`` now use epoch microseconds (not millis), and the time repr is ISO-8601 (``2021-01-15T03:04:05.678Z``) (see :ref:`vtx_300_datamodel-timestamps`). Fix: multiply 2.x epoch-millis by 1000; stop string-matching the old ``YYYY/MM/DD`` repr.
- Universal properties are removed; ``.seen`` becomes the interface-supplied relative property ``:seen`` (only on forms implementing ``meta:observable``), and ``.created``/``.updated`` remain leading-dot names but are now node meta properties (see :ref:`vtx_300_datamodel-interfaces`, :ref:`vtx_300_datamodel-intervals`, :ref:`vtx_300_storm-virtual-properties-syntax`). Fix: rewrite ``.seen`` as ``:seen``; leave ``.created``/``.updated`` as leading-dot reads.
- Activity forms collapse ``:time`` + ``:duration`` into a single ``:period`` interval (with ``*`` ongoing / ``?`` unknown sentinels); interval bounds are addressed via ``.min``/``.max``/``.duration``/``.precision`` virtuals (see :ref:`vtx_300_datamodel-intervals`, :ref:`vtx_300_storm-virtual-properties-syntax`). Fix: map a point-time + duration onto ``:period=(<ts>, ?|<end>|*)``.
- Light-edge verbs must be modeled and are validated on write; ad-hoc verbs raise ``NoSuchEdge``. Extended verbs must be registered via ``$lib.model.ext.addEdge`` and begin with ``_``. The ``$lib.model.edge`` key-value store and ``$lib.model.ext.addUnivProp``/``delUnivProp`` are removed (see :ref:`vtx_300_datamodel-extended-model`). Fix: register ``_verbs`` ahead of time; add extended props to specific forms via ``addFormProp``.
- Many form/property renames (e.g. ``hash:*`` -> ``crypto:hash:*``, ``it:account`` -> ``it:host:account``, ``ps:contact`` -> ``entity:contact``, ``media:news`` -> ``doc:report``, ``ou:campaign``/``ou:goal`` -> ``entity:campaign``/``entity:goal``, ``inet:whois:rec`` -> ``inet:whois:record``); plus typed ``base:id``/``base:name``/``entity:name`` types replacing the untyped 2.x ``:name`` (see :ref:`vtx_300_datamodel-form-renames`, :ref:`vtx_300_datamodel-typed-names-ids`). Fix: update to the new names; some remodels (``entity:campaign``/``entity:goal``) are not one-to-one -- confirm the migration path.
- Removed forms: ``inet:ssl:cert`` (use the ``inet:tls:*`` family), ``it:av:filehit``/``it:av:sig`` (use ``it:av:scan:result``), ``inet:whois:contact``/``inet:whois:email``/``inet:whois:ipcontact`` (use ``entity:contact`` in a record ``:contacts`` array), and the ``risk:availability`` taxonomy (use a ``meta:score`` prop) (see :ref:`vtx_300_datamodel-removed-forms`).
- The entire flat ``inet:web:*`` model is removed and replaced by the platform-oriented ``inet:service:*`` family (see :ref:`vtx_300_datamodel-inet-service`). Fix: build an ``inet:service:platform`` first, then ``inet:service:account``/``message``/``channel``/``relationship``/``login``; there is no ``:user`` prop.
- Geospatial ordering is stated explicitly and DMS parsing added: ``geo:latlong`` is latitude-first, ``geo:bbox`` is longitude-first ``(xmin,xmax,ymin,ymax)``, and common geolocation props move onto the ``geo:locatable`` interface (``place:``-prefixed except on ``geo:place`` itself) (see :ref:`vtx_300_datamodel-gis-bbox`). Fix: do not assume ``geo:bbox`` follows latlong ordering; use ``place:``-prefixed props on non-``geo:place`` locatable forms.

Administration and permissions
------------------------------

- The ``syn:cron`` and ``syn:trigger`` runt-node forms are removed (see :ref:`vtx_300_admin-runt-nodes-removed`). Fix: enumerate via ``cron.list``/``cron.stat`` and ``trigger.list`` (or ``$lib.cron.list()`` / ``$lib.trigger.list()`` and filter on object properties).
- Cortex Core (in-process Python) modules are removed: the ``modules`` config key and ``getCoreMod()``/``getCoreMods()``/``loadCoreModule()`` are gone, and ``synapse/lib/module.py`` / ``modules.py`` no longer exist (see :ref:`vtx_300_admin-core-modules-removed`). Fix: remove the ``modules`` key; reimplement as a Storm package or ``$lib.model.ext.*``.
- Permission renames/removals (see :ref:`vtx_300_admin-permissions`):

  - Granular extended-model permissions (``model.form.add``, ``model.prop.*``, ``model.univ.*``, ``model.edge.*``, ``model.tagprop.*``, etc.) collapse to a single ``model.admin``.
  - ``view.fork`` no longer defaults to allow. Fix: grant it explicitly (e.g. to the ``all`` role) to restore 2.x behavior.
  - ``proj:project`` no longer creates an authgate and ``('project', ...)`` permissions are gone. Fix: govern project nodes via standard ``node``/``view``/``layer`` permissions.
  - ``storm.macro.admin``/``storm.macro.edit`` renamed to top-level ``macro.admin``/``macro.edit`` (``storm.macro.add`` stays).
  - ``node.data.pop`` renamed to ``node.data.del`` (and ``node.data.del.<key>``).
  - ``node.prop.set``/``node.prop.del`` no longer honor the full property path (``node.prop.set.<form>:<prop>``); only the form name plus relative property name is checked. Fix: migrate full-path grants to ``node.prop.set.<form>.<prop>`` / ``node.prop.del.<form>.<prop>``.
  - Cortex-gated wildcard ``layer.read.<layer>``/``layer.write.<layer>`` removed. Fix: grant ``layer.write`` on the specific layer's authgate (``--gate <layeriden>``).
  - The standalone ``layer.read`` permission is removed entirely; layer read access is derived from View read access -- a user who can read any View a layer belongs to (or who is admin of the layer's own auth gate) may read that layer. Fix: grant ``view.read`` on a View that uses the layer instead of granting ``layer.read``.
  - ``$lib.view.list()`` and ``$lib.layer.list()`` return only the Views and layers the calling user can read, and ``$lib.view.get(<iden>)`` / ``$lib.layer.get(<iden>)`` raise ``NoSuchView`` / ``NoSuchIden`` for an iden the user cannot read instead of returning it, so an unreadable View or layer is indistinguishable from one that does not exist. Fix: grant ``view.read`` to enumerate or fetch a View/layer.
  - Deprecated ``storm.asroot.cmd.<name>``/``storm.asroot.mod.<name>`` definitions removed. Fix: declare needed perms via the package ``asroot:perms`` key.

DevOps and configuration
------------------------

- Removed/changed Cortex and Cell config keys (an unknown key is rejected at boot) (see :ref:`vtx_300_devops-storage-config-changes`): removed ``modules``, ``layers:lockmemory``, ``layers:logedits``, ``cron:enable``, ``trigger:enable``, ``layer:lmdb:map_async``, ``layer:lmdb:max_replay_log``, ``provenance:en``, ``auth:ctor``, ``auth:conf``, ``nexslog:async``, ``cell:ctor``; ``layers:cache:size`` now sizes the NID cache. Fix: delete the removed keys from ``cell.yaml`` and ``SYN_*`` env vars before upgrading.
- Per-layer ``mirror`` and ``upstream`` follower options removed (see :ref:`vtx_300_devops-layer-sync-pushpull`). Fix: use Cortex-level ``mirror`` for full-service replication or layer push/pull (``layer.push.add`` / ``layer.pull.add``) for layer-to-layer sync.
- Feed ingest standardized on a single packed-node format: the feed-format registry is gone and ``addFeedData`` drops the leading format-name argument (now ``addFeedData(items, *, viewiden=None, reqmeta=True)``); the ``synapse.tools.cortex.feed`` CLI drops ``--format``/``-f`` (see :ref:`vtx_300_devops-feed-single-format`). Fix: pass just the items list (and ``reqmeta=False`` if there is no export-meta header); convert custom feed formats to packed nodes.
- Minimum Python is now 3.14, pinned to ``>=3.14,<3.15`` (see :ref:`vtx_300_devops-python-version`). Fix: provision Python 3.14.x for every venv, CI runner, and host importing ``synapse``.
- CLI tools relocated into namespaced subpackages (the 2.x top-level shims are deleted), ``cmdr`` and ``cellauth`` removed, and Cryotank/Hive/gendocs tooling removed (see :ref:`vtx_300_devops-cli-tools`). Fix: use the dotted paths (e.g. ``csvtool`` -> ``cortex.csv``, ``pushfile`` -> ``axon.put``, ``backup`` -> ``service.backup``); use the Storm CLI (``synapse.tools.storm``) in place of ``cmdr`` and ``moduser``/``modrole`` in place of ``cellauth``.

APIs and integration
--------------------

- Synchronous Telepath is removed -- proxies are async-only (see :ref:`vtx_300_devops-telepath-async-only`). Fix: ``await s_telepath.openurl(...)``, ``await`` every call, iterate generators with ``async for`` (or ``await .list()``); drive from ``asyncio.run()``. ``synapse.glob.sync()`` / ``synchelp()`` no longer exist.
- ``CoreApi`` method removals (see :ref:`vtx_300_misc-breaking-api`): ``addNode``, ``addNodes``, ``addUnivProp``, ``delUnivProp``, ``getCoreMods``, ``getFeedFuncs``, ``getFormsByPrefix``, ``iterUnivRows``, ``syncIndexEvents``, ``syncLayerNodeEdits``, ``syncLayersEvents``. Fix: add nodes via Storm/``callStorm``; add extended props via ``$lib.model.ext``; replicate via Cortex mirroring / layer push-pull.
- ``CellApi`` Hive accessors (``getHiveKey``/``getHiveKeys``/``listHiveKey``/``setHiveKey``/``popHiveKey``/``saveHiveTree``) and name-based auth helpers (``getAuthInfo``/``addAuthRule``/``delAuthRule``/``setAuthAdmin``) removed (see :ref:`vtx_300_misc-breaking-api`). Fix: use the iden-based auth APIs (``getUserDefByName`` + ``addUserRule``/``delUserRule``/``setUserAdmin``); there is no Hive replacement.
- ``CoreApi.getModelDefs()`` (plural list) replaced by ``getModelDef()`` (singular dict) (see :ref:`vtx_300_misc-breaking-api`). Fix: consume one model-definition object instead of iterating a list.
- All versioned HTTP API endpoints moved from the ``/api/v1/`` prefix to ``/api/v3/`` (the ``/api/v0/`` health endpoints are unchanged); there are no ``/api/v1/`` or ``/api/v2/`` compatibility aliases (see :ref:`vtx_300_misc-http-api-v3`). Fix: update HTTP clients and proxy rules to the ``/api/v3/`` prefix (e.g. ``/api/v1/storm`` -> ``/api/v3/storm``).
- Several Cortex HTTP endpoints now accept API key auth only (the ``X-API-KEY`` header) and reject HTTP Basic and session-cookie auth: ``/api/v3/storm`` (plus ``/call`` and ``/export``), ``/api/v3/model`` (plus ``/norm``), the user-defined ``/api/ext/*``, and the Cortex file endpoints ``/api/v3/axon/files/*`` (see :ref:`vtx_300_misc-http-api-v3`). Fix: authenticate these endpoints with an API key; Basic / session callers now receive ``401``.
- HTTP ``POST /api/v1/storm/nodes`` removed (see :ref:`vtx_300_misc-breaking-api`). Fix: use ``/api/v3/storm`` and filter for ``('node', ...)`` messages, or ``/api/v3/storm/call`` for a single return value.
- Version reporting now uses PEP 440 strings: ``synapse.version`` is a string (was an integer tuple), ``synapse.lib.version.verstring`` is removed, ``getCellInfo()`` no longer includes ``verstring``, and ``$lib.version.synapse`` returns a string (see :ref:`vtx_300_misc-breaking-api`). Fix: parse the string via ``synapse.lib.version.parse()`` / ``release()`` and use ``synapse.version`` in place of ``verstring``.
- The ``BadOperArg`` exception class is removed and many Storm input-validation failures now raise ``BadArg`` instead of ``StormRuntimeError`` (see :ref:`vtx_300_misc-breaking-api`). Fix: catch ``BadArg`` (or the base ``SynErr``) rather than ``BadOperArg`` / ``StormRuntimeError`` for those cases.
- ``Node.get(prop)`` now returns a ``(type, value)`` pair rather than a bare value (and an array property returns a list of such pairs), reflecting typed property values (see :ref:`vtx_300_datamodel-typed-values`). Fix: in Python tests and tooling, stop comparing ``Node.get(prop)`` against a raw value -- compare the full pair, index ``[1]`` for the value, or use the ``propeq`` test helper (which unwraps the value, or compares the full pair when you pass ``type=``).
