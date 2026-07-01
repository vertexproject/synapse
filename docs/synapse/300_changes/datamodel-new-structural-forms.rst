.. _vtx_300_datamodel-new-structural-forms:

New Structural Forms
====================

Synapse 3.0.0 introduces new structural forms that replace text-stuffed
properties and single-key abstractions from 2.x with dedicated, queryable
forms. The most impactful changes are in the network protocol model.

Protocol handshake and banner forms
-----------------------------------

What changed
    3.x adds dedicated guid forms for protocol negotiation that 2.x recorded
    in opaque ``inet:flow`` text properties:

    - ``inet:tls:handshake`` with ``:server:cert`` / ``:client:cert``
      (``crypto:x509:cert``), ``:server:ja3s`` / ``:client:ja3``
      (``crypto:hash:md5``), ``:server:ja4s`` (``inet:tls:ja4s``),
      ``:client:ja4`` (``inet:tls:ja4``), and ``:server:jarmhash``
      (``inet:tls:jarmhash``).
    - ``inet:ssh:handshake`` with ``:server:key`` / ``:client:key``
      (``crypto:key``).
    - ``inet:rdp:handshake`` with ``:client:hostname`` (``it:hostname``) and
      ``:client:keyboard:layout`` (``base:name``).
    - ``inet:banner``, a guid form with ``:server`` (``inet:server``) and
      ``:text`` (``it:dev:str``), implementing ``meta:observable``.

    All three handshake forms implement the ``inet:proto:request`` interface,
    which supplies a ``:flow`` prop (``inet:flow``) linking each handshake back
    to its network flow.

Why
    Handshake and banner data -- fingerprints, certificates, keys -- deserve
    structured, queryable modeling instead of being buried in flow text props.
    Linking each record to its ``inet:flow`` via the interface ``:flow`` prop
    keeps the relationship explicit and pivotable.

What you need to do
    Move handshake and banner data off ``inet:flow`` text properties onto the
    dedicated forms, linking each to its flow with ``:flow``. Note that
    ``inet:banner`` is a guid form keyed on its props, not a comp.

    ::

        // 2.x -- handshake details stuffed into flow text
        [ inet:flow=$flowguid :raw=({"tls": "..."}) ]

        // 3.x -- dedicated handshake form linked to the flow
        [ inet:tls:handshake=({
            "flow": $flow,
            "server:cert": {crypto:x509:cert:sha256=$cert}
        }) ]
