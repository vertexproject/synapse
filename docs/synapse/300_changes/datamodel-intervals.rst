.. _vtx_300_datamodel-intervals:

Intervals and Timestamps
========================

Synapse 3.0.0 reworks how time intervals (``ival``) are modeled and where
observation and node-metadata timestamps live. Interval endpoints gain explicit
"ongoing" and "unknown" sentinels, and the 2.x universal ``.seen`` / ``.created``
properties are replaced by a per-form ``:seen`` and by node ``created`` /
``updated`` metadata.

Intervals gain ongoing/unknown sentinels
----------------------------------------

What changed
    The ``ival`` and ``time`` types now support two sentinel endpoints: ``*``
    (an ongoing/now-relative end) and ``?`` (an unknown time). The ``time``
    type norms ``now`` to the current micros, ``?`` to the unknown sentinel,
    and ``*`` to the ongoing sentinel. Interval values expose ``min``, ``max``,
    ``duration``, and ``precision`` virtual properties (accessed via the dot
    path, e.g. ``.min`` / ``.max`` / ``.duration``) and default to
    ``microsecond`` precision.

Why
    Explicit ongoing and unknown endpoints let an interval model "started at
    X, still ongoing" and "ended at an unknown time" precisely, rather than
    relying on out-of-band conventions for open-ended or uncertain times.

What you need to do
    When setting an interval, use ``?`` for an unknown endpoint and ``*``
    for an ongoing one (use ``*`` only when the source actually states the
    span is still ongoing). Set or read endpoints via the ``.min`` and
    ``.max`` virtual properties.

    ::

        // 3.x: an interval endpoint can be ? (unknown) or * (ongoing)
        [ inet:dns:a=(vertex.link, 1.2.3.4) :seen=(2023, ?) ]

        // read or filter endpoints via the .min / .max virtual properties
        inet:dns:a +:seen.max>2020

Universal .seen / .created replaced by :seen and node metadata
--------------------------------------------------------------

What changed
    Synapse 2.x defined ``.seen`` and ``.created`` as universal properties
    present on every node. In 3.0.0 there are no universal properties. Instead,
    ``:seen`` (an ``ival``) is a per-form property contributed by the
    ``meta:observable`` interface, so it appears only on forms that where the
    first observed and last observed times are analytically relevant.
    Separately, ``.created`` and ``.updated`` are now node meta
    properties (``time`` typed; ``.created`` is a min) read through the
    leading-dot names ``.created`` and ``.updated``.

Why
    There are many forms where the idea of an analytically relevant observation
    window (:seen interval) is irrelevant or nonsensical
    (e.g., syn:tag, ind:industry). Implementing the meta:observable interface on
    a per-form basis adds a :seen property only where it makes sense.

    The .created and .updated times are metadata about individual nodes, so are
    now meta properties applicable to all forms.

What you need to do
    Move 2.x ``.seen`` data onto ``:seen``, but only on forms that implement
    ``meta:observable``. If the destination form has no ``:seen``, do not
    relocate that data onto another interval (for example ``:period``). Read
    node creation and modification times through the ``.created`` and
    ``.updated`` meta properties.

    ::

        // 2.x: universal .seen and .created
        [ inet:fqdn=vertex.link .seen=2023 ]
        inet:fqdn.created>2023

    ::

        // 3.x: :seen via meta:observable; created/updated are node metadata
        [ inet:fqdn=vertex.link :seen=2023 ]
        inet:fqdn.created>2023
