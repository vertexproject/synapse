.. _vtx_300_datamodel-typed-names-ids:

Typed Name/Id Forms
===================

The single free-form 2.x ``:name`` string is replaced by a family of typed
name and id types -- a change that affects almost every port from 2.x.

Typed name and id types replace the untyped 2.x ``:name``
---------------------------------------------------------

What changed
    The 2.x model typed most ``:name`` properties as a bare ``str`` (with a
    few forms using ad-hoc per-domain string subtypes such as ``ou:name``).
    3.x splits names and ids across typed types: ``base:id`` (based on
    ``str``) for id strings, ``base:name`` (based on ``title``,
    case-insensitive and case-preserving) for generic names, and
    ``entity:name`` (based on ``base:name``) for actor, contact, and
    organization names.

    Properties across the model are now typed to the appropriate one. For
    example, ``:name`` and ``:reporter:name`` style properties on entity forms
    use ``entity:name``; the ``:id`` property on most forms uses ``base:id``;
    ``it:host:group`` ``:name`` uses ``base:name``; and ``it:host:account``
    ``:username`` uses ``entity:name`` while its ``:id`` uses ``base:id``. Some
    domain-specific forms further specialize ``:id`` (for example the POSIX and
    Windows subforms of ``it:host:account`` retype ``:id`` to OS-specific id
    types).

Why
    Distinct name and id types give each domain correct normalization and
    comparison semantics, and let properties and edges target the right kind of
    name instead of relying on one untyped string used everywhere.

What you need to do
    When porting a 2.x ``:name``, pick the domain-appropriate typed type:
    ``entity:name`` for actor, contact, and organization names; ``base:name``
    for generic names; and the domain-specific name or id type where the
    property now defines one. Setting these properties still accepts raw
    strings, so most ingest code does not change -- the difference is in
    normalization and comparison behavior.

    ::

        // 2.x: :name on ou:org was typed ou:name (a str subtype)
        [ ou:org=* :name="acme corp" ]

        // 3.x: :name on ou:org is typed entity:name (via the entity:contactable interface)
        [ ou:org=* :name="acme corp" ]

        // 3.x: :name on it:host:group is typed base:name
        [ it:host:group=* :name="administrators" ]
