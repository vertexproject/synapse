.. _vtx_300_datamodel-virtual-properties:

Virtual Properties (Model Mechanism)
====================================

Synapse 3.0.0 introduces virtual properties, a model mechanism that lets a type expose parts of
a single stored value -- each with its own type -- so those parts can be lifted, filtered, and
pivoted like real properties. A virtual property may be a computed sub-value derived from the
value (the ``ip`` / ``port`` of a socket address, the ``min`` / ``max`` of an interval) or
additional context bundled with the value rather than computed (for example the ``currency`` of
an ``econ:price``).

.. seealso::

   For the Storm syntax used to read and pivot virtual properties (the leading-dot form),
   see :ref:`vtx_300_storm-virtual-properties-syntax`.

What changed
    Data model types can now declare virtual properties (often called "virts"), each with its
    own type. Some are computed sub-values derived from the stored value; others are extra
    context bundled with the value rather than computed. A virtual property defines how its
    value is read (and, where it makes sense, written), and some virts are indexed, allowing
    them to be used in lift and filter operations as well as read.

    Several built-in types ship virts. The interval type (``ival``, used by ``:seen`` and tag
    timestamps) exposes ``.min``, ``.max``, ``.duration``, and ``.precision``. The ``inet:sockaddr``
    type (and its subtype ``inet:server``) exposes ``ip`` and ``port``, and the ``inet:net``
    range type exposes computed ``mask`` and ``size`` virts. The ``econ:price`` type instead
    carries bundled context as virts -- ``currency`` and ``adjusted`` -- which are stored with
    the value and set directly rather than computed from it.

    In Storm, a virtual property is accessed by appending a leading dot (and no colon) to a
    property, form, or tag reference -- for example ``:seen.max`` (a secondary property of
    interval type), ``inet:server.port`` (a form virt), or ``#(foo).min`` (a tag's interval
    virt; the tag name must be parenthesized so ``min`` is parsed as a virt rather than a tag
    segment). The dot must immediately follow the name it applies to; a dot written after a
    space (or at the start of a query) instead reads a node-level meta property of the current
    node, such as ``.created``.

Why
    Virts let a single stored value carry queryable structure and context -- the IP and port
    inside a socket address, the endpoints of an interval, or the currency bundled with a price
    -- without modeling separate stored properties. Because selected virts are indexed, those
    parts become first-class targets for lift, filter, and pivot.

What you need to do
    Access a virtual property with a leading dot and no colon (this applies to both computed and
    bundled-context virts).

    ::

        // 3.x: filter nodes by the max of their :seen interval property
        inet:dns:a +:seen.max>2025

        // 3.x: set the precision virt of an interval-typed secondary property
        [ :seen.precision=day ]

        // 3.x: filter on the min endpoint of a tag's interval (tag name parenthesized)
        inet:dns:a +#(foo).min>2020

    For the interval type, ``:seen.min`` / ``:seen.max`` give direct access to an interval-typed
    secondary property's endpoints, and ``:seen.duration`` exposes the span.

    ::

        // 2.x: the endpoints and duration of an interval property were not directly queryable virts
        // 3.x: filter on the interval's parts
        inet:dns:a +:seen.duration>(1, days)

    Some interval types have their ``min`` and ``max`` virtual properties overwritten to make more
    sense for the form or property they are associated with. To find those values you can inspect
    the model like this.

    ::

        // 2.x: the endpoints and duration of an interval property were not able to be renamed.
        // 3.x: Inspect the data model to find the renaemd min and max properties in order to assign them
        $prop=$lib.model.prop(entity:campaign:period) for $type in $prop.types { $lib.print(`{$type.opts}`) }
        {'precision': 'microsecond', 'names': {'min': 'began', 'max': 'ended'}}

        // Use that knowledge to create nodes
        [entity:campaign=({"name": "synapse 3.0 beta"}) :period.began='2026-06-30']


    For socket addresses, the ``ip`` and ``port`` parts of an ``inet:sockaddr`` / ``inet:server``
    value -- which in 2.x were encoded in the value (e.g. ``tcp://1.2.3.4:80``) and not separately
    queryable as properties -- are now accessible as virts.

    ::

        // 3.x: lift inet:server nodes by the computed port virt
        inet:server.port=443
