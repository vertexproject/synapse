.. _vtx_300_datamodel-ip-unification:

Merged inet:ipv4 / inet:ipv6 into inet:ip
=========================================

The separate ``inet:ipv4`` and ``inet:ipv6`` forms have been replaced by a single ``inet:ip``
form that auto-detects the address version.

What changed
    The ``inet:ipv4`` and ``inet:ipv6`` forms are gone. There is now a single ``inet:ip`` form
    that auto-detects the address version. Its normalized system value is a 2-tuple of
    ``(version, int)`` -- for example ``(4, 16909060)`` or ``(6, <bigint>)`` -- rather than a
    bare integer. The ``inet:ip`` form has secondary props ``version`` (``inet:ipversion``),
    ``scope`` (``inet:ipscope``), and ``type`` (``str:lower``), populated automatically when a
    value is set.

    ``inet:ipv4`` and ``inet:ipv6`` survive only as version-restricting types,
    ``('inet:ip', {'version': 4})`` and ``('inet:ip', {'version': 6})``. The IP range forms
    merged the same way: ``inet:cidr4`` / ``inet:cidr6`` become ``inet:net``, and ``inet:cidr``
    is a CIDR-aligned subtype of ``inet:net``.

Why
    A single form simplifies modeling and pivoting when both IPv4 and IPv6 are present, removes
    the constant IPv4-or-IPv6 branching, and reduces complexity in queries that previously had
    to handle two parallel forms and props.

What you need to do
    Replace ``inet:ipv4`` and ``inet:ipv6`` lifts and props with ``inet:ip``. To constrain to a
    single version, lift on the ``version`` prop or use the version-restricted ``inet:ipv4`` /
    ``inet:ipv6`` type on a typed prop.

    ::

        // 2.x
        inet:ipv4=1.2.3.4
        inet:dns:a:ipv4=1.2.3.4
        inet:server:ipv6="::1"

        // 3.x
        inet:ip=1.2.3.4
        inet:dns:a:ip=1.2.3.4
        // constrain to a single version via the version prop
        inet:ip:version=6
