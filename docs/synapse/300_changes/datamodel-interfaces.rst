.. _vtx_300_datamodel-interfaces:

Interfaces and the alts Behavior
================================

Synapse 3.0.0 makes interfaces a first-class part of the data model. Forms inherit
whole sets of cross-cutting properties by declaring ``interfaces=(...)``, certain
properties auto-relate a singular value to a plural companion via ``alts``, and a new
``syn:interface`` runt node exposes interfaces for introspection.

Forms inherit cross-cutting props via interfaces
------------------------------------------------

What changed
    Forms gain whole sets of properties by implementing interfaces declared with
    ``interfaces=(...)``. The core cross-cutting interfaces are: ``meta:observable``
    provides ``:seen`` (an ``ival``); ``meta:discoverable`` provides ``:discoverer`` and
    ``:discovered``; ``meta:reported`` provides ``:id``/``:ids``, ``:name``/``:names``,
    ``:desc``, ``:resolved``, ``:reporter``, ``:reporter:name``, ``:reporter:url``,
    ``:reporter:deprecated``, ``:reporter:supersedes``, ``:reporter:period``,
    ``:reporter:updated``, and ``:reporter:published``; ``base:event`` provides ``:time``;
    and ``base:activity`` provides ``:period``.

    Interfaces can themselves implement other interfaces (for example ``base:event`` and
    ``base:activity`` both implement ``meta:causal``, and ``meta:schedulable`` implements
    ``base:activity``). Several are marker (no-property) interfaces, such as
    ``meta:havable``, ``meta:usable``, and ``meta:achievable``. The model resolves which
    forms satisfy an interface, which is used for type matching and interface-typed edges.

Why
    Centralizing recurring property sets lets dozens of forms share identical,
    consistently typed properties, and lets edges and properties be declared against an
    interface rather than enumerating every form.

What you need to do
    When a property you expect (``:seen``, ``:period``, ``:reporter``) is not declared
    directly on a form, check which interfaces it implements -- the property likely comes
    from one of them. Note that ``.seen`` was a universal property in 2.x (set with the
    leading dot) and is now the secondary property ``:seen`` supplied by the
    ``meta:observable`` interface, so only forms implementing that interface carry it. For
    edges or properties that target an interface, any form implementing that interface is a
    valid target.

    ::

        // 2.x: .seen was a universal property present on every node
        [ inet:fqdn=vertex.link .seen=2023 ]

        // 3.x: :seen comes from the meta:observable interface
        [ inet:fqdn=vertex.link :seen=2023 ]
        // :period comes from base:activity, :reporter from meta:reported, etc.

The alts behavior on id/ids and name/names
------------------------------------------

What changed
    Properties can declare ``alts=(...)`` referencing companion properties. On
    ``meta:reported``, ``:id`` declares ``alts=('ids',)`` and ``:name`` declares
    ``alts=('names',)``, so the singular property and its plural array companion
    are treated as alternative locations for the value.

Why
    This lets a form carry a canonical primary id or name plus a deconflicting set of
    alternates, while authors generally set only the singular value -- avoiding manual
    management of the plural array.

What you need to do
    Set ``:id`` (or ``:name``); ``alts`` relates it to ``:ids``/``:names`` for you. A
    2.x ``risk:vuln`` that carried its CVE in ``:cve`` now records it via the
    ``meta:reported``-style ``:id`` property (``risk:vuln`` declares its own ``:id`` with
    the same ``alts=('ids',)`` behavior), and a list of identifiers maps to setting
    ``:id``/``:name`` plus the ``:ids``/``:names`` array companion.

    ::

        // 2.x: the CVE lived in the risk:vuln :cve property
        [ risk:vuln=* :cve=CVE-2021-44228 ]

        // 3.x: the canonical id is set via the meta:reported :id property
        [ risk:vuln=({"id": "CVE-2021-44228", "reporter:name": "nist"}) ]

The syn:interface runt node and interfaces introspection props
--------------------------------------------------------------

What changed
    A new ``syn:interface`` runt node surfaces every data-model interface for
    introspection, and the ``syn:form`` runt node gained an ``:interfaces`` array property
    (typed ``syn:interface``) listing the fully resolved set of interfaces a form
    implements. The ``syn:interface`` node also carries its own ``:interfaces`` array,
    listing the interfaces it inherits from.

Why
    Interfaces are central to the 3.x model, so they need a first-class introspection
    surface alongside ``syn:form`` and ``syn:prop``.

What you need to do
    Use ``syn:interface`` to enumerate model interfaces and pivot or inspect them; lift
    ``syn:form`` and read ``:interfaces`` to see which interfaces a form implements.

    ::

        // 3.x: enumerate a specific interface
        syn:interface=meta:observable

        // 3.x: find forms implementing a given interface
        syn:form:interfaces*[=meta:observable]
