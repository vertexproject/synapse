.. _vtx_300_storm-lib-removed:

Removed and Relocated Storm Libraries
=====================================

Synapse 3.0.0 removes a number of Storm libraries that were either deprecated proxies, superseded
by language features, or rolled into a more canonical surface. This page lists the removals most
2.x callers are likely to hit and how to port each one.

``$lib.user`` removed
----------------------

What changed
    The ``$lib.user`` library is removed. The current user is now obtained from
    ``$lib.auth.users.get()``, whose ``iden`` argument may be omitted to return the
    current user. The returned ``auth:user`` object exposes ``.iden``,
    ``.name``, ``.vars``, ``.profile``, and ``.allowed(permname, [gateiden], [default])``.

Why
    Consolidates user access under the existing ``$lib.auth.users`` surface (which already
    gets, lists, and adds users) rather than maintaining a separate current-user library.

What you need to do
    Replace ``$lib.user.X`` with ``$lib.auth.users.get().X``. Capturing the user once is usually
    cleaner than re-fetching it.

    ::

        // 2.x
        $name = $lib.user.name
        if $lib.user.allowed(power-ups.foo.user) { }
        $v = $lib.user.vars.mykey

        // 3.x
        $user = $lib.auth.users.get()
        $name = $user.name
        if $user.allowed(power-ups.foo.user) { }
        $v = $user.vars.mykey

``$lib.str`` removed
--------------------

What changed
    The ``$lib.str`` library, which provided ``join(sep, items)``, ``concat(*args)``, and
    ``format(text, **kwargs)``, is removed. The ``str`` primitive retains a ``.join`` method.

Why
    These were superseded by methods on the ``str`` primitive and by backtick template strings,
    so the standalone library was redundant.

What you need to do
    Use the ``.join`` method on a separator string, and use backtick strings for interpolation.

    ::

        // 2.x
        $s = $lib.str.join('.', $parts)
        $msg = $lib.str.format('hi {name}', name=$n)

        // 3.x
        $s = ('.').join($parts)
        $msg = `hi {$n}`

``$lib.text()`` removed
-----------------------

What changed
    The ``$lib.text()`` function and the ``text`` Storm object it returned are removed. In 2.x
    ``$lib.text()`` returned a mutable builder you appended strings to; it was already documented
    as deprecated.

Why
    Storm now favors backtick template strings for interpolation and plain lists plus
    ``(sep).join(list)`` for accumulation, which makes the dedicated builder object redundant. This
    aligns with the ``$lib.str`` removal above.

What you need to do
    Append to a list and join it, or build a backtick string for interpolation.

    ::

        // 2.x
        $t = $lib.text("start")
        $t.add(" more")
        $out = $t.str()

        // 3.x
        $parts = (["start", " more"])
        $out = ('').join($parts)

``$lib.true`` / ``$lib.false`` / ``$lib.null`` removed
------------------------------------------------------

What changed
    The ``$lib.null``, ``$lib.true``, and ``$lib.false`` accessors on ``$lib`` are removed.

Why
    Storm has first-class ``true`` / ``false`` / ``null`` literals, so the library accessors are
    redundant.

What you need to do
    Use ``(true)`` / ``(false)`` / ``(null)`` as standalone literals, and bare ``true`` /
    ``false`` / ``null`` inside expressions and comparisons.

    ::

        // 2.x
        $ok = $lib.true
        if ($x = $lib.null) { }

        // 3.x
        $ok = (true)
        if ($x = null) { }

``$lib.vars`` library removed
-----------------------------

What changed
    The ``$lib.vars`` library, with ``get`` / ``set`` / ``del`` / ``list`` / ``type``, is removed.
    In 3.x ``$lib.vars`` is a dict-like object accessed via the standard deref and setitem
    convention, and the type helper has moved to ``$lib.utils.type()``.

Why
    Aligns runtime-variable access with the uniform dict-like deref/setitem convention used across
    Storm objects, and moves the generic value-type helper to a general-purpose utility library.

What you need to do
    Use deref to read, setitem to write, and assign ``$lib.undef`` to remove. Replace
    ``$lib.vars.type()`` with ``$lib.utils.type()``.

    ::

        // 2.x
        $v = $lib.vars.get(foo)
        $lib.vars.set(foo, $bar)
        $t = $lib.vars.type($x)

        // 3.x
        $v = $lib.vars.foo
        $lib.vars.foo = $bar
        $t = $lib.utils.type($x)

``$lib.bytes`` reduced to ``fromints()``
----------------------------------------

What changed
    In 2.x ``$lib.bytes`` exposed ``put()``, ``has()``, ``size()``, ``hashset()``, and ``upload()``
    (all deprecated for v3.0.0) plus ``fromints()``. In 3.x ``$lib.bytes`` is reduced to a single
    method, ``fromints()``, which converts an iterable of integers (0-255) into bytes. The
    Axon-proxy methods are gone.

Why
    Those methods were thin deprecated proxies to ``$lib.axon``; removing them eliminates duplicate
    surface area and steers callers to the canonical Axon and file APIs.

What you need to do
    Replace the removed methods with the corresponding ``$lib.axon`` methods. To create a
    ``file:bytes`` node directly from bytes, use the new ``$lib.file.frombytes()``.
    ``$lib.bytes.fromints()`` is unchanged.

    ::

        // 2.x
        ($size, $sha256) = $lib.bytes.put($buf)
        $ok = $lib.bytes.has($sha256)

        // 3.x
        ($size, $sha256) = $lib.axon.put($buf)
        $ok = $lib.axon.has($sha256)

``$lib.ps`` removed
-------------------

What changed
    The ``$lib.ps`` library (deprecated for v3.0.0) with ``kill(prefix)`` and ``list()`` is removed.
    The equivalent functionality lives on ``$lib.task``.

Why
    ``$lib.ps`` was a deprecated alias; ``$lib.task`` is the canonical task-management surface.

What you need to do
    Move to ``$lib.task``. Note that ``$lib.task.list()`` and ``$lib.task.kill()`` operate across
    the Cortex and its mirrors.

    ::

        // 2.x
        $tasks = $lib.ps.list()
        $lib.ps.kill($iden)

        // 3.x
        $tasks = $lib.task.list()
        $lib.task.kill($iden)

``$lib.infosec.cvss`` node-mutating helpers removed
---------------------------------------------------

What changed
    The ``calculate()``, ``calculateFromProps()``, ``vectToProps()``, and ``saveVectToNode()``
    methods of ``$lib.infosec.cvss`` are removed. The library now exposes a single pure scoring
    helper, ``vectToScore()``. ``vectToProps()`` and ``saveVectToNode()`` were deprecated in
    2.137.0 with an eol of v3.0.0.

Why
    The CVSS properties on ``risk:vuln`` were reworked, so the old helpers that wrote a sprawling
    set of per-component props onto a node no longer fit the model.

What you need to do
    Stop calling ``calculate`` / ``calculateFromProps`` / ``vectToProps`` / ``saveVectToNode``.
    Compute a score with ``$lib.infosec.cvss.vectToScore(vect)`` and set the vector and score props
    directly on the node. The current ``risk:vuln`` CVSS props include ``:cvss:v3`` (the vector) and
    versioned score props such as ``:cvss:v3_1:score``; confirm the exact prop name against the data
    model for your version.

    ::

        // 2.x
        yield $lib.infosec.cvss.saveVectToNode($node, $vect)

        // 3.x
        $score = $lib.infosec.cvss.vectToScore($vect)
        risk:vuln=$node [ :cvss:v3=$vect :cvss:v3_1:score=$score.score ]

``$lib.inet.whois.guid`` removed
--------------------------------

What changed
    The ``$lib.inet.whois`` library and its only method, ``$lib.inet.whois.guid(props, form)``, are
    removed. In 2.x this helper produced standard guids for ``inet:whois`` forms and carried a
    deprecation marker (eol v3.0.0). The whois model itself was also remodeled in 3.x.

Why
    WHOIS node construction now uses standard GUID-constructor (gutor) syntax, so a dedicated guid
    helper is redundant.

What you need to do
    Stop calling ``$lib.inet.whois.guid()`` and build the node directly via GUID-constructor
    syntax that deconflicts on the record's identifying props. Power-up authors should prefer the
    pkgcommon helpers ``genWhoisRec`` / ``genWhoisIpRec`` / ``genWhoisContact``. Confirm the exact
    3.x whois form and prop names against the data model before porting.

    ::

        // 2.x
        $guid = $lib.inet.whois.guid(({"fqdn": $fqdn, "asof": $asof}), inet:whois:rec)
        [ inet:whois:rec=$guid ]

        // 3.x -- construct/deconflict the record directly via a gutor
        // (the form was renamed inet:whois:rec -> inet:whois:record and remodeled;
        //  confirm identifying props against the data model)
        [ inet:whois:record?=({"fqdn": $fqdn}) ]

``$lib.notifications`` and ``$lib.projects`` removed
----------------------------------------------------

What changed
    The ``$lib.notifications`` and ``$lib.projects`` libraries are both removed in 3.x; their source
    modules are deleted.

Why
    The project subsystem was reworked in 3.x (``proj:project`` nodes no longer create authgates),
    and the associated Storm libraries were dropped.

What you need to do
    Remove any use of ``$lib.notifications.*`` and ``$lib.projects.*``. There is no direct
    replacement; migrate project-style workflows to the 3.x ``proj`` model and remaining project
    Storm commands, and flag any reliance on the removed notification API for redesign.

    ::

        // 2.x
        $lib.projects.add(myproj)
        $lib.notifications.list()

        // 3.x -- no direct replacement; redesign against the 3.x proj model and commands

``$lib.gen`` helpers removed and ``gen.*`` commands flattened
-------------------------------------------------------------

What changed
    The ``$lib.gen`` library no longer exposes any public helper methods. The 2.x helpers such as
    ``$lib.gen.orgByName``, ``$lib.gen.vulnByCve``, ``$lib.gen.psContactByEmail``,
    ``$lib.gen.newsByUrl``, ``$lib.gen.riskToolSoftware``, ``$lib.gen.softByName``, and
    ``$lib.gen.langByCode`` are gone; the implementation helpers are now private
    (underscore-prefixed).

    Relatedly, the ``gen.*`` node-generation Storm commands were renamed to drop the
    model-namespace prefix, and several were removed. 3.x defines ten flat commands: ``gen.org``,
    ``gen.campaign``, ``gen.software``, ``gen.threat``, ``gen.vuln``, ``gen.industry``,
    ``gen.country``, ``gen.government``, ``gen.language``, and ``gen.place``.

Why
    The commands track the model reshapes (for example ``ou:campaign`` -> ``entity:campaign``,
    ``ps:contact`` -> ``entity:contact``, ``ou:industry`` -> ``ind:industry``,
    ``risk:tool:software``/``it:prod:soft`` -> ``it:software``), so the namespaced names no longer
    matched the model. Flattening the command names and hiding the helpers keeps the public
    surface aligned with the new model.

What you need to do
    Replace any ``$lib.gen.<helper>()`` call with the corresponding ``gen.*`` command or a direct
    GUID-constructor (gutor). Update Storm and macros to the new command names. The removed
    commands (for example the former ``gen.it.av.scan.result``, ``gen.ou.id.number``/``type``,
    ``gen.ou.org.hq``, ``gen.ps.contact.email``) have no direct replacement -- build the node with
    a GUID-constructor.

    ::

        // 2.x
        gen.ou.org "Acme Inc"
        // or in a module:
        $org = $lib.gen.orgByName("Acme Inc")

        // 3.x
        gen.org "Acme Inc"
        // $lib.gen public helpers are gone; use the command or a gutor:
        [ ou:org?=({"name": "Acme Inc"}) ] $org=$node

    Other renames include ``gen.risk.vuln`` -> ``gen.vuln``, ``gen.ou.campaign`` ->
    ``gen.campaign``, ``gen.risk.threat`` -> ``gen.threat``,
    ``gen.risk.tool.software``/``gen.it.prod.soft`` -> ``gen.software``, ``gen.pol.country`` ->
    ``gen.country``, ``gen.geo.place`` -> ``gen.place``, ``gen.lang.language`` -> ``gen.language``,
    and ``gen.ou.industry`` -> ``gen.industry``.
