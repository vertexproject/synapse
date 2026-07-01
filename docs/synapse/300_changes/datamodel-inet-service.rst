.. _vtx_300_datamodel-inet-service:

inet:service:* Model Updates
============================

The ``inet:service:*`` platform model -- accounts, messages, channels, and related activity
across any SaaS or social platform -- has been available since 2.x. Synapse 3.0.0 updates it to
the 3.x data model: it adds new forms and marker interfaces, removes several interim forms, and
supplies more properties through shared interfaces.

.. note::

    The long-superseded flat ``inet:web:*`` model is fully removed in 3.0.0; use the
    ``inet:service:*`` forms instead (see :ref:`vtx_300_breakingchanges`).

What changed
    New forms and interfaces:

    - ``inet:service:role`` models a platform role, and ``inet:service:member`` records an
      account's membership. The 2.x per-container ``inet:service:channel:member`` /
      ``inet:service:group:member`` forms are removed in favor of ``inet:service:member``.
    - ``inet:service:comment``, ``inet:service:label``, and ``inet:service:labeled`` provide
      reusable commenting and labeling, declared on a form via the new marker interfaces
      ``inet:service:commentable`` and ``inet:service:labelable``. ``inet:service:joinable``
      marks a form an account can be a member of.
    - ``inet:service:error`` models a platform-defined error code, and
      ``inet:service:action:authorized`` records an authorized action.

    Removed interim forms: ``inet:service:group``, ``inet:service:thread``,
    ``inet:service:instance``, ``inet:service:channel:member``, ``inet:service:group:member``,
    ``inet:service:message:attachment``, ``inet:service:message:link``, and
    ``inet:service:object:status``. The interim ``inet:service:app`` form is renamed
    ``inet:service:agent``.

    Shared interfaces supply common properties rather than each form declaring its own:
    ``:id`` / ``:platform`` (``inet:service:base``); ``:username`` / ``:name`` / ``:email`` /
    ``:profile`` (``inet:service:subscriber``); and observability such as ``:seen``
    (``inet:service:object`` / ``meta:observable``).

Why
    The 3.x pass aligns ``inet:service:*`` with the 3.x data model: it consolidates the interim
    2.x forms onto shared interfaces, generalizes commenting and labeling into reusable forms,
    and unifies membership, so the same structure models any platform consistently.

What you need to do
    Review your ``inet:service:*`` usage against the generated data model docs. The form set
    changed (new ``inet:service:role`` / ``:member`` / ``:comment`` / ``:label`` / ``:error``;
    removed ``inet:service:group`` / ``:thread`` / ``:instance`` and the per-container
    ``*:member`` and ``message:*`` forms), ``inet:service:app`` is now ``inet:service:agent``,
    and several properties are now interface-supplied. Move membership onto
    ``inet:service:member`` and use the comment/label forms where you previously modeled those
    inline.
