.. _vtx_300_datamodel-form-inheritance:

Form Inheritance (Subforms)
===========================

Synapse 3.0.0 lets a form declare another form as its base type. A subform inherits
the base form's properties, may add or override props (an override may change the
prop's type), and IS-A the base everywhere lifts, props, and interfaces are typed to
the base form.

What changed
    A form may now be declared with another form as its base type, for example
    ``it:host:windows:account`` whose type is ``it:host:account``. The subform
    inherits the base form's props and can add new props or override inherited ones
    (an override may change the prop type). The subform also is an instance of the base,
    so a subform matches the base form in lifts and anywhere a prop or interface is typed
    to the base.

    An example of form inheritance is the host account/group hierarchy in the ``it:`` model.
    ``it:host:account`` (base props ``:id`` (``base:id``), ``:username``, ``:period``,
    ``:profile``, ``:host``, ``:service:account``, ``:home``) has subforms
    ``it:host:posix:account`` (overrides ``:id`` to ``it:os:posix:id``, adds ``:gid``,
    ``:gecos``, ``:shell``) and ``it:host:windows:account`` (overrides ``:id`` to
    ``it:os:windows:sid``). Likewise ``it:host:group`` has subforms
    ``it:host:posix:group`` and ``it:host:windows:group``, each overriding ``:id``.

Why
    Creating base forms and more specific extended forms addresses model limitations
    in 2.x, where forms either needed to be overly generic (to account for a lowest common
    denominator set of properties) or overly detailed (with multiple, often conflicting
    properties to account for different use cases).

    In the ``it:host:account`` example, the inherited forms are ``it:host:windows:account``
    and ``it:host:posix:account``. Each OS variant gets its own form with correctly typed
    identifiers, while a common base preserves shared props and lets a single lift of the
    base match all variants.

What you need to do
    When ingesting, create the most specific subform you have evidence for (for example
    ``it:host:windows:account`` when you have a Windows SID); it inherits the base form's
    props, so set shared values on the inherited names (the identifier on ``:id``) rather than
    on a separate per-variant property. Lifting, pivoting, or filtering on the base form --
    and ``$node.is(<base>)`` -- matches every subform, so code that targets ``it:host:account``
    also sees its Windows and POSIX subforms.

    For model introspection, a subform's ``syn:form`` node carries a ``:parent`` of its base
    form, so you can discover the hierarchy -- for example ``syn:form=it:host:windows:account``
    has ``:parent=it:host:account``.

    ::

        // create the most specific subform; it inherits the base form's props
        [ it:host:windows:account=* :id="S-1-5-21-..." ]

        // a lift of the base form matches every subform
        it:host:account

        // introspect the hierarchy: a subform's syn:form has a :parent of its base
        syn:form=it:host:windows:account
