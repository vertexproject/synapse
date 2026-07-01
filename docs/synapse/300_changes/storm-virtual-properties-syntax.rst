.. _vtx_300_storm-virtual-properties-syntax:

Virtual Properties in Storm
===========================

Synapse 3.0.0 introduces virtual properties: a way to address parts of a value directly in Storm.
A virtual property may be a computed sub-value (the ``ip`` / ``port`` inside a ``sockaddr`` value,
or the ``min`` / ``max`` / ``precision`` of an interval) or context bundled with the value (such
as the ``currency`` of a price). A virtual property is written by appending a dot and the virtual
name immediately after a property or form name, such as ``inet:server.ip`` or ``:seen.max``.

In 2.x, a leading-dot name such as ``.seen`` or ``.created`` was a "universal property" -- a property
available on every form. Synapse 3.0.0 removes universal properties; the leading dot now addresses
virtual properties and node meta properties. As a result ``.seen`` becomes the relative property
``:seen``, while ``.created`` keeps its leading dot (now a meta property of the node). The most
impactful change for existing queries is the removal of universal properties -- review that entry first.

.. seealso::

   For the data model mechanism behind virtual properties (how a type provides its "virts"),
   see :ref:`vtx_300_datamodel-virtual-properties`.

Universal properties removed
----------------------------

What changed
    In 2.x, a leading-dot name like ``.seen`` or ``.created`` was a universal property -- a property
    automatically available on every form. Synapse 3.0.0 removes universal properties; the leading dot is
    now used for virtual properties and node meta properties (see below). The two former universal
    properties change as follows:

    - ``.seen`` becomes the ordinary relative property ``:seen``, an interval (``ival``) property supplied
      by the ``meta:observable`` interface, so a form only carries ``:seen`` if it implements that interface.
    - ``.created`` is NOT renamed. It (and the new ``.updated``) is now a meta property of the node,
      still written with a leading dot (``.created``).

Why
    Universal properties were a special case attached to every form. Making ``.seen`` an interface-supplied
    property makes it model-driven and consistent with every other property, while the node-level
    ``.created`` / ``.updated`` meta properties are read with the same leading-dot syntax.

What you need to do
    Rewrite ``.seen`` as the relative property ``:seen`` (lifts, filters, pivots, and assignments). Leave
    ``.created`` (and ``.updated``) as leading-dot names -- they still work in 3.x, now as meta properties
    of the node.

    ::

        // 2.x universal properties
        inet:dns:a +.seen@=2021
        [ inet:dns:a=(vertex.link, 1.2.3.4) .seen=now ]

        // 3.x: .seen becomes the relative interface prop :seen
        inet:dns:a +:seen@=2021
        [ inet:dns:a=(vertex.link, 1.2.3.4) :seen=now ]

        // 3.x: .created stays a leading-dot name (now a node meta property)
        inet:dns:a.created>2020

Virtual properties on forms and properties
------------------------------------------

What changed
    A virtual property is written with a dot immediately after a property or form name, with no space before
    the dot. For example, on a ``sockaddr``-typed property you can address ``.ip`` and ``.port``, and on an
    interval (``ival``) property you can address ``.min``, ``.max``, and ``.precision``. Virtual properties can
    be used wherever a regular property can: lifting by form, lifting by relative property, filtering,
    pivoting, and reading in expressions and assignments. You can also use a variable for the virtual name,
    such as ``:period.$virt``.

    A leading dot at the start of a query (or after a space or an opening brace) is a "bare" virtual property:
    it reads a virtual of the current node's own primary value.

Why
    Virtual properties expose computed, structural, and bundled-context parts of a value without declaring a
    separate stored property, simplifying queries against compound values like ``sockaddr`` and interval
    properties such as ``:period`` and ``:seen``.

What you need to do
    Use ``<form-or-prop>.<virt>`` with no space before the dot, and prefix it as usual to filter or pivot.
    Note that a space before the dot changes the meaning: a dot following whitespace is read as a bare virtual
    property of the current node's value, not a virtual of the property just before it.

    ::

        // 2.x had no virtual-property syntax; ip/port and ival bounds
        // were not directly addressable as sub-properties.

        // 3.x
        inet:server.ip=1.2.3.4               // lift by virt
        inet:http:request:server.ip          // lift form virt
        entity:campaign +:period.min>=2020   // filter on ival min
        $start = :period.min                 // read in an expression
        inet:server.ip -> inet:ip            // pivot from a virt

Tag interval virtual properties
-------------------------------

What changed
    A tag's time interval has the virtual properties ``min``, ``max``, and ``duration``. To address one, wrap
    the tag name in parentheses and append the virtual with a dot, for example ``#(foo.bar).min``.
    (``precision`` is a virtual of an interval-typed property value, not of a tag interval, so
    ``#(foo.bar).precision`` is not valid.) The parentheses are required because a plain dot after a tag is
    read as another tag segment. This works for lifts, filters, sets, and expression reads; variable tags are
    supported (``#($tag).min``); and tag globs can match against an interval virtual.

Why
    In 2.x, the interval bounds of tag timestamps could not be addressed directly in Storm. The parenthesized
    form lets analysts lift, filter, and set the ``min`` / ``max`` of a tag's time interval while keeping
    multi-segment tag names (like ``cno.threat``) unambiguous.

What you need to do
    Parenthesize the tag to address an interval bound: ``#(cno.threat).min`` / ``.max`` / ``.duration``.
    Without the parentheses, ``#cno.threat.min`` is read as a longer tag name, so the parentheses are what
    make it a virtual property.

    ::

        // 2.x: no syntax to address a tag interval's min/max directly

        // 3.x
        #(cno.threat).min                       // lift nodes by the tag interval min
        entity:campaign +#(cno.threat).min=2020 // filter on the tag interval min
        [ test:str=foo +#(cno.threat).min=2020 ] // set the tag interval min
        $first = #(cno.threat).min              // read in an expression
