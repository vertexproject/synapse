.. _vtx_300_changes:

Synapse 3.0.0 Feature Highlights
================================

This page highlights the new user-facing features and functionality introduced in
Synapse 3.0.0. It is the "what's new" view of the release; for the full
set of changes -- including backward-incompatible changes, removals, and migration guidance --
see the detailed topic notes in :ref:`vtx_300_index`.

Storm Query Language
--------------------

- **Virtual properties.** Parts of a property's value -- computed sub-values (the ``ip`` /
  ``port`` inside a ``sockaddr``, or the ``min`` / ``max`` / ``duration`` of an interval) or
  context bundled with the value (such as the ``currency`` of a price) -- can now be lifted,
  filtered, pivoted, and used in expressions directly with the leading- or inline-dot syntax
  (``inet:server.ip``, ``+:seen.max>2025``). See :ref:`vtx_300_storm-virtual-properties-syntax`
  and :ref:`vtx_300_datamodel-virtual-properties`.
- **Membership operators** (``in`` / ``not in``). These tests are now first-class in Storm
  expressions, e.g. ``if ($status in ["open", "pending"]) { ... }``. See
  :ref:`vtx_300_storm-syntax-operators`.
- **Inline value casting** (``as``). Interpret a value or property as a specific type inline,
  e.g. ``:somefield as inet:ip``, replacing the cast-into-a-variable-then-pivot pattern. See
  :ref:`vtx_300_storm-syntax-operators`.
- **Multi-target and virtual-property pivots.** A single pivot operator can name a parenthesized
  list of destination forms/props, or pivot into a virtual property. See
  :ref:`vtx_300_storm-syntax-operators`.
- **Form-aware node checks** (``$node.is()``). Renamed from ``$node.isform()``, it accepts a list
  of forms and matches subforms of a base form, so form checks compose with the new
  form-inheritance model. This can also check if a node implements an interface. See :ref:`vtx_300_storm-object-conventions`.
- **More flexible tag glob matching.** Tag glob wildcards now match zero-length segments, so a
  single pattern can match both a parent tag and its children. See :ref:`vtx_300_storm-tag-glob-matching`.
- **New and expanded Storm libraries.** ``$lib.file.frombytes()`` / ``fromhex()`` upload bytes to
  the Axon and return the deconflicted ``file:bytes`` node in one call; the ``$lib.lift`` library
  gains ``byPropAlts`` / ``byPropRefs`` / ``byTypeValue`` / ``byPropsDict`` for the alts,
  typed-value, and interface model; ``$lib.cortex`` adds Node ID (NID) helpers; ``$lib.pkg.state()`` exposes
  read-only package state; and ``$lib.utils.type()`` reports a value's type. See
  :ref:`vtx_300_storm-lib-new`.
- **ISO-8601 time rendering.** The ``repr()`` of time values is now ISO-8601, alongside
  microsecond-precision timestamps. See :ref:`vtx_300_datamodel-timestamps`.

Data Model
----------

- **Unified IP form** (``inet:ip``). A single form auto-detects IPv4 vs IPv6, simplifying
  pivots and queries that span both. See :ref:`vtx_300_datamodel-ip-unification`.
- **Typed property values.** Every property value now carries its type; ``node.get()`` returns
  a ``(type, value)`` pair, enabling consistent typed handling across the model. See
  :ref:`vtx_300_datamodel-typed-values`.
- **Interfaces and alts.** Forms inherit cross-cutting properties (``:seen``, ``:period``,
  ``:reporter``, contact fields, ...) by declaring interfaces, and ``alts`` lets a singular
  property auto-populate and deconflict its plural. See :ref:`vtx_300_datamodel-interfaces`.
- **Form inheritance (subforms).** A form can use a base form as its type and IS-A the base
  (for example ``it:host:windows:account`` / ``it:host:posix:account`` under ``it:host:account``),
  inheriting its properties and deconfliction. See :ref:`vtx_300_datamodel-form-inheritance`.
- **Microsecond timestamps.** Time values now have microsecond precision, preserving accuracy for
  high-resolution sources such as network flow data. See :ref:`vtx_300_datamodel-timestamps`.
- **Richer intervals.** Intervals gain ``*`` (ongoing) and ``?`` (unknown) sentinels, and
  time-plus-duration data collapses into a single ``:period`` interval. See
  :ref:`vtx_300_datamodel-intervals`.
- **Typed name/id forms.** Domain-specific name/id forms (``base:name``, ``entity:name``,
  ``base:id``, ...) replace the single untyped ``:name`` string. See
  :ref:`vtx_300_datamodel-typed-names-ids`.
- **New structural forms.** ``doc:reference`` models references to external content, and protocol
  handshakes/banners (``inet:tls:handshake``, ``inet:ssh:handshake``, ``inet:rdp:handshake``,
  ``inet:banner``) capture data previously stuffed into ``inet:flow`` text fields. See
  :ref:`vtx_300_datamodel-new-structural-forms`.
- **inet:service:* updates.** The ``inet:service:*`` platform model (available since 2.x) gains
  roles, membership, and reusable comment/label forms in 3.x, with more properties supplied
  through interfaces; the flat ``inet:web:*`` model is removed. See
  :ref:`vtx_300_datamodel-inet-service`.
- **New industry model** (``ind:*``). Industry data is split out into a dedicated model.
  See :ref:`vtx_300_datamodel-form-renames`.
- **Geospatial coordinate parsing.** Latitude/longitude values now accept degrees-minutes-seconds
  (DMS) input in addition to decimal degrees, and geolocation properties are consolidated under the
  ``geo:locatable`` interface. See :ref:`vtx_300_datamodel-gis-bbox`.

Administration
--------------

- **Tombstones.** Nodes and parts of nodes that exist in a parent view can now be deleted within a
  forked view: the deletions are hidden in the fork and applied to the parent on merge, with a new
  ``syn:deleted`` runt node surfacing fully-deleted nodes through the ``diff`` command, and Storm
  APIs to inspect and cancel staged deletions. See :ref:`vtx_300_admin-tombstones`.
- **Counts and cardinality tracking.** The Cortex now tracks per-form, per-property, per-value,
  array, tagprop, and edge-verb counts, available for sizing, introspection, and future query
  optimization. See :ref:`vtx_300_admin-counts-cardinality`.
- **Macro permissions.** Storm macros adopt the easy-permission model -- graded per-user/role
  read / edit / admin access via ``macro.grant`` -- replacing the single owning ``user`` field.
  See :ref:`vtx_300_storm-macros`.
- **Cron and trigger enhancements.** ``cron.add`` takes a concise positional period
  (``hourly@:30``), at-jobs expose a ``completed`` flag and a new ``cron.cleanup`` command for
  pruning finished jobs, and a single ``mod`` edit path (with an edits dict) can change any
  cron/trigger property. See :ref:`vtx_300_storm-cron-and-trigger-api`.

Deployment and Performance
--------------------------

- **NID layer storage.** Layers now index nodes by an integer Node ID (NID) rather than a 32-byte
  BUID, substantially reducing index sizes, speeding lifts, and adding migration flexibility. See
  :ref:`vtx_300_devops-layer-storage-nid`.
- **Deconflicted Nexus edits.** Node edits are deconflicted before being written to the Nexus log,
  reducing storage and letting downstream consumers read the Nexus log directly instead of
  aggregating per-layer edit logs. See :ref:`vtx_300_devops-nexus-deconfliction`.
- **Structured logging by default.** Synapse containers now emit JSON structured logs by default
  (set ``SYN_LOG_STRUCT=false`` to keep unstructured text). See :ref:`vtx_300_devops-logging`.
- **ISO-8601 UTC microsecond logging.** Structured and text log output now uses UTC ISO-8601
  timestamps with microsecond precision. See :ref:`vtx_300_devops-logging`.

APIs and Integration
--------------------

- **Streamlined model export.** ``CoreApi.getModelDef()`` returns the full model definition in a
  single call. See :ref:`vtx_300_misc-breaking-api`.
- **Edge-verb count breakdowns.** ``getEdgeVerbCount`` supports optional N1/N2 form breakdowns for
  edge introspection. See :ref:`vtx_300_admin-counts-cardinality`.
