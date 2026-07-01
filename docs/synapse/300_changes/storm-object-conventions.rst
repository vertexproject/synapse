.. _vtx_300_storm-object-conventions:

Storm Object Access Conventions
===============================

Synapse 3.0.0 standardizes how Storm objects expose their data. Zero-argument
value accessors become properties (gtors) accessed without parentheses,
dictionary-like objects move to the deref/setitem convention, and several
method-style accessors are removed. The entries below cover the changes most
likely to require updates to existing Storm.

Node identity accessors are now properties
-------------------------------------------

What changed
    On the Storm ``node`` object, ``form``, ``ndef``, ``value`` and ``nid`` are
    now read-only properties accessed WITHOUT parentheses. In 2.x
    ``form``, ``ndef`` and ``value`` were functions invoked with ``()``.
    ``$node.repr(...)`` remains a callable method.

    The ``$node.iden()`` method (which returned the BUID hex string) is removed.
    Nodes are now identified by an integer Node ID exposed as the ``$node.nid``
    property, which may be null for a node that is not yet persisted. A new
    ``$node.setValue(valu)`` method was also added for setting a node's primary
    value with deconfliction rules.

Why
    These are pure read accessors of a node's identity, so exposing them as
    properties is cleaner and matches the broader 3.x move of zero-argument
    getters to properties. The switch from ``iden`` to ``nid`` follows the layer
    storage change, where nodes are keyed by an integer NID rather than a BUID.

What you need to do
    Drop the parentheses on the value accessors and replace ``iden()`` with the
    ``nid`` property. Anywhere you stored, compared, or passed a node BUID hex
    string, switch to the integer NID.

    ::

        // 2.x
        $form = $node.form()
        $ndef = $node.ndef()
        $valu = $node.value()
        $iden = $node.iden()

        // 3.x
        $form = $node.form
        $ndef = $node.ndef
        $valu = $node.value
        $nid  = $node.nid
        $rep  = $node.repr()   // still a method

$node.is() accepts a list and respects form inheritance
-------------------------------------------------------

What changed
    ``$node.isform(name)`` is renamed to ``$node.is(name)``, which now accepts
    either a single form name or a list of names and returns true if the node
    matches ANY of them. It also matches across form inheritance: it tests
    membership against the form's ``formtypes`` rather than performing an
    exact string comparison. In 2.x ``isform`` did a literal equality check
    against a single name only.

Why
    3.x adds form inheritance, where a subform's type is a base form. A subform
    node's ``form`` string is the specific subform, so an exact-string check
    against the base form would miss it. Walking ``formtypes`` makes form checks
    correct under inheritance, and accepting a list removes the need for chained
    ``or`` checks.

What you need to do
    Use ``$node.is(<base-or-subform>)`` for form checks instead of switching
    on ``$node.form`` string equality; it now correctly returns true for
    subforms of the named base. Pass a list to test several forms at once.

    ::

        // 2.x: exact-string check, single name only
        if ($node.form() = "it:host:account") { }

        // 3.x: matches base + subforms, accepts a list
        if $node.is(it:host:account) { }
        if $node.is((inet:fqdn, inet:ip)) { }

Dict-like Storm objects use deref/setitem
-----------------------------------------

What changed
    ``$lib.globals`` and other dictionary-like Storm objects now use the
    deref/setitem/iter convention instead of ``.get()``, ``.set()``,
    ``.list()`` and ``.pop()`` methods. ``$lib.globals`` is now a dict-like
    object (typename ``global:vars``): read with ``$lib.globals.<name>``, write
    with ``$lib.globals.<name> = $valu``, delete by assigning ``$lib.undef``,
    and iterate with a ``for`` loop. The ``globals.get``, ``globals.set`` and
    ``globals.del`` permission keys are unchanged.

    The 2.x ``$lib.env`` library is likewise replaced by a dict-like object
    (typename ``environment:vars``) read via deref. It still requires admin
    privileges and still only exposes variables whose names start with
    ``SYN_STORM_ENV_``.

    More generally, definition-bearing dict-like Storm objects are read via
    attribute/deref access and no longer carry ``.get()``-style accessor
    methods.

Why
    Uniform deref/setitem access matches how all other Storm mappings behave and
    removes special-cased per-object method APIs.

What you need to do
    Rewrite method-style access to deref/setitem access.

    ::

        // 2.x
        $v = $lib.globals.get(mykey)
        $lib.globals.set(mykey, $v)
        $lib.globals.pop(mykey)
        for ($n, $v) in $lib.globals.list() { }
        $val = $lib.env.get("SYN_STORM_ENV_FOO")

        // 3.x
        $v = $lib.globals.mykey
        $lib.globals.mykey = $v
        $lib.globals.mykey = $lib.undef
        for ($n, $v) in $lib.globals { }
        $val = $lib.env.SYN_STORM_ENV_FOO

$lib.version.synapse and .commit are now properties
---------------------------------------------------

What changed
    In 2.x ``$lib.version.synapse()`` and ``$lib.version.commit()`` were
    functions called with parentheses. In 3.x they are gtors accessed without
    parentheses: ``$lib.version.synapse`` and ``$lib.version.commit``. In
    addition, ``$lib.version.synapse`` now returns a version string (for
    example ``3.0.0``) rather than a list of version integers.
    ``$lib.version.matches(...)`` remains a function and accepts either a
    version string or a list of version integers as its first argument.

Why
    They take no arguments and simply read a value, so property access is the
    natural form, and a single version string is the canonical representation.

What you need to do
    Drop the parentheses on ``synapse`` and ``commit``. If you previously
    treated ``$lib.version.synapse`` as a list (for example joining it with
    ``('.').join(...)`` or indexing into it), use the returned string directly.

    ::

        // 2.x
        $synver = $lib.version.synapse()
        if $lib.version.matches($synver, ">=2.9.0") { }

        // 3.x
        $synver = $lib.version.synapse
        if $lib.version.matches($synver, ">=3.0.0") { }

.pack() removed from View, Layer, User and Role objects
-------------------------------------------------------

What changed
    The ``pack()`` method was removed from most Storm objects. In 2.x it existed
    on Node, View, Layer, Trigger, CronJob, User and Role. In 3.x only
    ``$node.pack()`` remains. These objects now expose their fields as discrete
    named properties.

Why
    Exposing fields as named properties is clearer and avoids serializing
    internal structure that changed in 3.x.

What you need to do
    Replace ``.pack()`` calls with direct access to the object's named
    properties. ``$node.pack()`` is unchanged.

    ::

        // 2.x
        $info = $user.pack()
        $name = $info.name

        // 3.x
        $name = $user.name

$user.tell() and $user.notify() removed
---------------------------------------

What changed
    The ``tell()`` and ``notify()`` methods on the Storm User object (from
    ``$lib.auth.users.get()`` / ``.byname()``) are removed, alongside the
    removal of the ``$lib.notifications`` library.

Why
    Synapse 3.x removes the built-in user notification subsystem, so the
    per-user methods that pushed messages to a user are no longer available.

What you need to do
    Remove calls to ``$user.tell(...)`` and ``$user.notify(...)``. If you relied
    on inter-user messaging, implement it via your own Storm package state
    (e.g. a queue) or external tooling.

    ::

        // 2.x
        $user = $lib.auth.users.byname(bob)
        $user.tell("job complete")

        // 3.x: user notifications are no longer built in; use Optic notifications, a queue, or an external system
