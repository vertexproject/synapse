.. _vtx_300_datamodel-typed-values:

Typed Property Values
=====================

In Synapse 3.0.0 a property value carries its type alongside the value. This lets a single
property hold values of more than one form or type, and changes how you set properties whose
type is a form or interface.

What changed
    A stored property value now records the ``syn:type`` name of the value alongside the value
    itself, so the stored type is self-describing. Setting a scalar-typed property still
    accepts a raw value -- normalization records the type for you.

Why
    Recording the type with the value lets a single property hold values of more than one form
    or type (for example a ``:reporter`` that may resolve to more than one entity form) and
    makes the stored type self-describing, which supports type-based lift and filter.

What you need to do
    When setting a property whose type points to a form or interface, assign a node (via
    subquery or variable) rather than a bare string. A scalar-typed property still normalizes a
    bare value, but a property backed by a guid form does not auto-default: you must name the
    form explicitly even when only one form is allowed -- use a dictionary guid constructor
    with the ``$as`` key (which names the guid form to build), or an ``as <type>`` cast. The
    ``$as`` key is also how you build a property whose type can resolve to more than one form,
    such as an interface-typed ``:creator``.

    ::

        // $as names the guid form to build for a property whose type can resolve to more than one form
        [ meta:note=* :creator=({"$as": "ps:person", "name": "bob smith"}) ]
