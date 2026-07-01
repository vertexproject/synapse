.. _vtx_300_datamodel-removed-forms:

Removed Forms
=============

The 3.0 model cleanup removes several 2.x forms (and a taxonomy or two) in favor of
more general or more explicit modeling. The most common removals are summarized below,
with migration guidance for each.

inet:ssl:cert removed in favor of the inet:tls:* family
-------------------------------------------------------

What changed
    The 2.x ``inet:ssl:cert`` comp form (``(server, file)``) is removed. 3.x models
    a certificate-to-endpoint binding with ``inet:tls:servercert`` (a comp of
    ``inet:server`` + ``crypto:x509:cert``) and ``inet:tls:clientcert`` (a comp of
    ``inet:client`` + ``crypto:x509:cert``), alongside a richer ``inet:tls:*`` family
    including ``inet:tls:handshake`` (with JA3/JA4/JARM properties),
    ``inet:tls:ja4``/``inet:tls:ja4s``, and ``inet:tls:jarmhash``.

Why
    The 2.x form conflated a transport binding with a raw file and could not express
    client versus server certs, JA3/JA4/JARM fingerprints, or full handshakes. The
    TLS family models the certificate and the negotiation explicitly.

What you need to do
    Stop using ``inet:ssl:cert``. For a server cert observed at an endpoint use
    ``inet:tls:servercert=(server, cert)``; for a client cert use
    ``inet:tls:clientcert=(client, cert)``. For full handshake context create an
    ``inet:tls:handshake``. The certificate itself is a ``crypto:x509:cert``.

    ::

        // 2.x
        [ inet:ssl:cert=(1.2.3.4:443, $filesha256) ]

        // 3.x
        [ inet:tls:servercert=((tcp://1.2.3.4:443), {crypto:x509:cert:sha256=$certsha}) ]

it:av:filehit / it:av:sig removed; it:av:scan:result :target collapsed
----------------------------------------------------------------------

What changed
    The 2.x ``it:av:filehit`` and ``it:av:sig`` forms are removed. Both were
    deprecated for some time in 2.x in favor of the existing
    ``it:av:scan:result`` guid form, so most callers have already moved off them.

    The more impactful change is on ``it:av:scan:result`` itself: the separate
    per-type target properties from 2.x (``:target:file``, ``:target:proc``,
    ``:target:host``, ``:target:fqdn``, ``:target:url``, ``:target:ipv4``,
    ``:target:ipv6``) collapse into a single, multi-typed ``:target`` property --
    a union of ``file:bytes``, ``it:exec:proc``, ``it:host``, ``inet:fqdn``,
    ``inet:url``, and ``inet:ip``. The result still carries ``:scanner`` /
    ``:scanner:name``, ``:signame`` (an ``it:av:signame``), ``:verdict`` (an
    ``it:av:verdict`` enum), ``:categories``, and ``:multi:*`` aggregation fields.

Why
    The narrow ``it:av:filehit`` and ``it:av:sig`` forms were long deprecated. On
    ``it:av:scan:result``, a separate property per target type was redundant -- a
    single multi-typed ``:target`` represents the scanned thing uniformly whatever
    its type.

What you need to do
    Set the scanned thing on the single ``:target`` property instead of a
    per-type ``:target:file`` / ``:target:fqdn`` / ... property. Replace any
    remaining ``it:av:filehit`` / ``it:av:sig`` usage with ``it:av:scan:result``.
    ``:verdict`` is an ``it:av:verdict`` enum, not a free string -- use one of
    ``benign`` / ``unknown`` / ``suspicious`` / ``malicious``.

    ::

        // 2.x: the scanned file lived on the per-type :target:file prop
        [ it:av:scan:result=* :target:file={ file:bytes:sha256=$filesha256 } :signame="Win.Trojan" ]

        // 3.x: a single multi-typed :target holds the scanned node
        [ it:av:scan:result=({"target": {file:bytes:sha256=$filesha256}, "scanner:name": "clamav", "signame": "Win.Trojan", "verdict": "malicious"}) ]

inet:whois contact forms removed; records carry a :contacts array
-----------------------------------------------------------------

What changed
    ``inet:whois:rec`` is renamed ``inet:whois:record`` and ``inet:whois:iprec`` is
    renamed ``inet:whois:iprecord`` (existing nodes are reconciled when a
    Cortex is migrated to 3.x). The separate WHOIS
    contact forms ``inet:whois:contact``, ``inet:whois:email``, and
    ``inet:whois:ipcontact`` are all removed. WHOIS contacts are now modeled as
    ``entity:contact`` nodes carried in the record's ``:contacts`` array (an array
    of ``entity:contact`` on both ``inet:whois:record`` and ``inet:whois:iprecord``).

Why
    WHOIS contacts are just contacts. Reusing ``entity:contact`` and attaching them to
    the record via a ``:contacts`` array removes the duplicate contact forms and
    unifies contact modeling.

What you need to do
    Use ``inet:whois:record`` / ``inet:whois:iprecord``. Model WHOIS contacts as
    ``entity:contact`` added to the record's ``:contacts`` array, and stop creating
    ``inet:whois:contact`` / ``inet:whois:email`` / ``inet:whois:ipcontact``.

    ::

        // 2.x
        [ inet:whois:rec=(woot.com, 2021) :registrar="NIC" ]
        [ inet:whois:contact=((woot.com, 2021), registrant) ]

        // 3.x
        [ inet:whois:record=({"fqdn": "woot.com"}) :contacts+={[ entity:contact=({"name": "bob smith"}) ]} ]

risk:availability taxonomy removed
----------------------------------

What changed
    The 2.x ``risk:availability`` taxonomy (and the ``risk:tool:software:availability``
    property that used it) is removed in the 3.0 model cleanup. When a Cortex is
    migrated to 3.x, existing ``risk:availability`` values are dropped rather than
    carried forward.

Why
    The availability-status concept is better captured by general scoring or priority
    properties (``meta:score``) on the relevant risk forms rather than a dedicated
    taxonomy.

What you need to do
    Stop using the ``risk:availability`` taxonomy and the
    ``risk:tool:software:availability`` property. Express the concept with a
    ``meta:score`` valued property such as a ``:priority`` on the relevant risk form.

    ::

        // 2.x
        [ risk:tool:software=* :availability=public ]

        // 3.x -- model via a meta:score property (e.g. :priority) on the relevant risk form
