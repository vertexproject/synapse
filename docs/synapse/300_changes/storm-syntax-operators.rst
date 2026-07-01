.. _vtx_300_storm-syntax-operators:

Storm Syntax and Operator Changes
=================================

Synapse 3.0.0 reworks several pieces of Storm syntax and adds new expression and
pivot operators. Some changes are additive (new ``in``/``not in`` operators, the
``as`` cast, multi-target pivots) while others are breaking and require you to
update existing queries, macros, and packages. Breaking changes are listed first.

No whitespace allowed before ``.`` in derefs and tag segments
-------------------------------------------------------------

What changed
    Dot-based dereferences and dotted tag segments now require the dot to
    immediately follow the preceding name, with no space. This applies to variable
    dereferences (``$var.attr``), set-item assignments, and dotted tag segments
    (``#tag.seg``). A dot that follows a space, an opening brace, or the start of the
    query is instead read as a leading-dot virtual property of the current node's value.

Why
    This keeps the two uses of the dot distinct: ``$var.attr`` / ``#tag.seg`` must hug
    their name, while a space before a ``.virt`` makes it a virtual-property read. It
    lets the virtual-property and tag-virtual syntax be used without ambiguity.

What you need to do
    Ensure variable dereferences and tag segments have no space before the dot. A space
    before a dot is now read as a separate leading-dot virtual property.

    ::

        // 2.x tolerated a space before the dot
        $foo .bar

        // 3.x: the dot must immediately follow the name
        $foo.bar          // variable deref
        #foo.bar          // tag segment
        .ip               // leading-dot = virtual prop of node value (space/start before dot)

New ``in`` and ``not in`` membership operators
----------------------------------------------

What changed
    Storm expressions now support ``in`` and ``not in`` membership comparison
    operators. They are usable anywhere an expression is evaluated -- inside
    ``$(...)`` math expressions, ``if (...)`` conditions, and ``while`` conditions.
    ``x in y`` returns true when ``x`` is contained in ``y`` (container types may
    define their own membership behavior, otherwise standard containment applies).
    ``not in`` is the negation, and may be written with a space between the two words.

Why
    Membership testing previously required awkward workarounds (manual iteration,
    list helpers, or regex). A first-class ``in`` / ``not in`` operator makes
    conditional logic far more readable.

What you need to do
    Use ``in`` / ``not in`` inside expressions for membership checks. These are
    expression operators, not lift/filter operators -- use them in ``if`` / ``while``
    / ``$(...)``, not as a bare pipeline filter.

    ::

        // 2.x: had to test membership manually
        $found = (false)
        for $item in $mylist {
            if ($item = $needle) { $found = (true) }
        }
        if $found { ... }

        // 3.x (list literals in expressions use brackets)
        if ($needle in $mylist) { ... }
        if ($status not in ["open", "pending"]) { ... }
        $ok = $($name in $allowed)

Inline value cast: ``<value> as <type>``
-----------------------------------------

What changed
    A new ``as`` cast clause lets a value or property be re-interpreted as a specific
    type inline. The cast applies to a base value (``<value> as <type>``) and to a
    relative property (``:prop as <type>``), and can be used in lift, filter, pivot,
    and expression contexts. At runtime it norms the value with the named type and
    yields a typed node reference, so you can pivot or compare a raw value or property
    as if it were of a given type, without first creating a node.

Why
    With merged types (for example ``inet:ip``), it is useful to coerce a value
    to a particular type for pivoting or comparison without first creating a node. The
    ``as`` clause makes that explicit and concise.

What you need to do
    Where you need to interpret a value or property as a specific type, use the
    ``as`` clause. This is new syntax with no 2.x equivalent; it is a cleaner
    alternative to ``$lib.cast(...)`` plus a pivot in some cases.

    ::

        // 2.x: cast into a variable, then pivot
        $ip = $lib.cast(inet:ipv4, :somefield)

        // 3.x: inline cast clause
        :somefield as inet:ip -> inet:ip

Pivot target lists and virtual-property pivot targets
-----------------------------------------------------

What changed
    Pivot syntax was generalized to accept a parenthesized list of targets and to
    support virtual-property targets. A single pivot operator can now name several
    destination properties or forms at once, and a pivot can target a virtual
    property.

Why
    Letting a pivot name several destination properties or forms at once -- and pivot
    into a virtual property -- removes the need to repeat the source set or union
    results manually, and pairs with the new virtual-property and merged-type model.

What you need to do
    Use a parenthesized list to pivot to multiple targets in one operator, or pivot
    into a virtual property. Existing single-target pivots are unchanged.

    ::

        // 2.x: one target per pivot operator
        inet:dns:a -> inet:ipv4
        inet:dns:aaaa -> inet:ipv6

        // 3.x: list of pivot targets, or a virtual-property target
        file:bytes -> (crypto:hash:md5, crypto:hash:sha1, crypto:hash:sha256)
        inet:flow -> inet:server.ip

Lookup-mode ``search`` interface and ``storm:interface:search`` removed
-----------------------------------------------------------------------

What changed
    The pluggable ``search`` Storm interface used by lookup mode, and the Cortex
    config option ``storm:interface:search`` that enabled it, are removed. In 2.x,
    lookup mode merged results from any package implementing the ``search`` interface
    and warned when it was disabled. In 3.x, lookup mode instead runs the scrape
    interface plus data-model lookup hints.

Why
    Lookup mode now resolves tokens deterministically by scraping known node forms and
    falling back to model-defined lookup-hint properties, removing the need for a
    separately configured external search backend and its on/off switch.

What you need to do
    Remove ``storm:interface:search`` from Cortex config; it is no longer recognized.
    If you relied on a package implementing the ``search`` Storm interface to enrich
    lookup mode, that mechanism is gone -- lookup mode now matches only via scrape plus
    model lookup hints. Move custom search logic into explicit Storm queries or commands.

    .. code-block:: yaml

        # 2.x cortex cell.yaml
        storm:interface:search: true

        # 3.x: storm:interface:search is no longer a valid Cortex config key; remove it.
        # lookup mode now uses scrape + model lookup hints automatically.
