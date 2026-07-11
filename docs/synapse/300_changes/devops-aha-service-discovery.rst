.. _vtx_300_devops-aha-service-discovery:

AHA Service Discovery, Leadership, and Provisioning
===================================================

Synapse 3.0.0 substantially reworks AHA, the service registry and resolver used by distributed
deployments. The changes are all built on one foundational idea: every service registers with an
AHA deployment under a unique combination of its **service type** and its service **iden**. A
leader and its mirrors are the same logical service, so they share one iden; two genuinely
different services of the same type each have their own iden. Making the ``(type, iden)`` pair the
identity of a service is what makes the rest possible -- resolving a service by type, tracking a
single leader per type, following the leader dynamically, and provisioning a service with nothing
but a shared secret.

This page covers the deployment- and operations-facing consequences of that rework. The
shared-secret provisioning workflow has its own page
(:ref:`vtx_300_devops-service-provisioning`), and the full walkthrough lives in the deployment
guide (:ref:`deploy_provisioning`).

Services register by unique type and identity
---------------------------------------------

What changed
    Every deployable service declares a **service type** (its ``getCellType()`` / ``celltype``),
    and that type is now part of its AHA registration (the AHA service info carries a ``type``
    field). AHA enforces that a given service type is registered by only one service instance: a
    leader and its mirrors share a single iden and re-register freely, but a second instance with a
    *different* iden claiming an already-registered type is rejected. The base ``cell`` type may not
    register at all -- an implementer must override the service type on any deployable service.

Why
    A stable, type-addressable identity per service is the anchor for everything else in this
    page. Because a leader and its mirrors share one iden, AHA can treat them as a single logical
    service while still distinguishing them from an unrelated service of the same type. This
    ``(type, iden)`` uniqueness is the change that enabled type-based resolution, managed
    leadership, and zero-touch provisioning.

What you need to do
    Standard services (Cortex, Axon, JSONStor, and the shipped Advanced Power-Ups) already declare
    a service type, so no action is required. If you run a custom ``synapse.lib.cell.Cell``
    subclass that registered with AHA as a bare ``cell``, give it a real ``celltype``. Uniqueness
    is checked even for an **offline** instance, so when you permanently replace a distinct
    instance of a type, remove the old registration first::

        # from inside the AHA container
        python -m synapse.tools.aha.list                # find the stale service name
        python -m synapse.tools.aha.del 000.cortex...   # remove the old entry from AHA

Resolve a service by its type: ``aha://<type>...``
--------------------------------------------------

What changed
    A bare, single-label AHA name (with no dots, minus the ``.<aha:network>`` suffix) now resolves
    as a **service type**, returning the current leader instance of that type. For example
    ``aha://cortex...``, ``aha://axon...``, and ``aha://jsonstor...`` each resolve to whichever
    instance currently leads that type. The AHA name ``<type>.<aha-network>`` resolves the same
    way. Multi-label names (``foo.bar...``) continue to resolve to a specific named service, not a
    type.

    Two Telepath APIs back this on the AHA service: ``getAhaSvcByType(celltype)`` returns the
    single connectable instance for a type (preferring the online leader; ``filters={'mirror':
    True}`` returns a mirror when one is available), and ``getAhaSvcsByType(celltype)`` yields one
    entry per instance of a type.

What you need to do
    You can point service configuration and tooling at ``aha://<type>...`` instead of a specific
    instance name and let it follow the current leader. This is how a mirror locates its upstream
    and how a Cortex reaches its Axon/JSONStor without pinning a specific instance.

Automatic naming by service type
--------------------------------

What changed
    AHA names each service automatically from its type. The first instance of a type becomes the
    leader ``000.<type>`` (for example ``000.cortex``); additional instances become mirrors
    ``001.<type>``, ``002.<type>``, and so on. The per-type index is tracked in AHA and can be
    reset or overridden by an operator with the ``setAhaSvcTypeIndex(name, valu)`` admin API.

Why
    Deterministic, type-derived names remove the need to hand-assign a unique ``aha:name`` to every
    instance, which is what makes "just deploy another one" work for mirrors.

What you need to do
    Nothing for the common case -- deploy a service with a provisioning secret and AHA assigns the
    name. If you previously assigned names by hand you may continue to set ``aha:name`` explicitly;
    the automatic naming only applies when a name is not configured.

Managed leadership terms (dynamic mirrors)
------------------------------------------

What changed
    AHA determines a single leader per service type by tracking a **leadership term** -- a record,
    stored in AHA's own slab, naming which service currently leads a type. A service is the leader
    exactly when its name matches the current term for its type. The first service of a type to
    register a term becomes the leader; every other instance of that type follows whichever service
    holds the current term, with no static upstream configuration. A promotion records a new term
    naming the promoted service, and mirrors move to follow it. When the last instance of a type is
    removed, its term is cleared so a future first instance of that type starts cleanly as the
    leader.

    Leadership is never decided by a vote among peers: it is a term recorded by AHA, set by the
    first registrant and changed only by an explicit promotion. A service that has been superseded
    by a forced promotion detects the divergence on startup and must be restored from a backup.

Why
    Static per-mirror upstream configuration and the first-boot leadership race are both gone.
    Mirrors follow the leader dynamically, which is what lets a mirror be added or replaced simply
    by deploying another instance.

What you need to do
    Deploy a mirror by standing up another instance of the same type under the same provisioning
    secret; set ``SYN_PROVISION_FOLLOWER`` on it so it joins as a mirror rather than racing to
    become the first leader (see below). Promote and demote instances with the service tools::

        python -m synapse.tools.service.promote
        python -m synapse.tools.service.demote

    Set the ``aha:promotable`` configuration option to ``false`` on any instance that must never
    hold leadership (for example a read-only or cross-region replica). The
    ``synapse.tools.aha.mirror`` tool reports each instance's ``leader`` / ``follower`` role and
    replication offsets for checking cluster state.

Removed ``mirror`` configuration; new ``parent`` override
---------------------------------------------------------

What changed
    The Cell ``mirror`` configuration option is removed. Mirroring is now expressed by deploying an
    additional instance of a type that follows the AHA-determined leader. A new ``parent`` option
    is available but is **not** a rename of ``mirror``: it is an explicit override that pins a
    service to a fixed upstream Telepath URL, bypassing AHA leadership resolution, and is rarely
    needed. (The separate per-layer ``mirror`` / ``upstream`` options are also removed; see
    :ref:`vtx_300_devops-layer-sync-pushpull`.)

Why
    With leadership managed by AHA, a static upstream URL per mirror is redundant and error-prone.
    The rare cases that still need a fixed upstream have the explicit ``parent`` escape hatch.

What you need to do
    Remove ``mirror`` from any service ``cell.yaml``. Do not translate it to ``parent`` unless you
    specifically need to pin an instance to a fixed upstream; in the normal case a mirror needs no
    upstream configuration at all.

    .. code-block:: yaml

        # 2.x cell.yaml -- mirror pinned to a fixed upstream
        mirror: aha://00.cortex.example.net

    .. code-block:: yaml

        # 3.x cell.yaml -- no upstream config; the mirror follows the AHA-determined leader
        # ( deploy under the same SYN_PROVISION_SECRET and set SYN_PROVISION_FOLLOWER=1 )

AHA registry stored in the cell slab
------------------------------------

What changed
    AHA stores its service registry, leadership terms, and clone/server metadata in its own cell
    LMDB slab rather than in a JSONStor document. The service name is the primary key, with
    dup-sorted indexes by iden and by type (``aha:svcs``, ``aha:svcs:byiden``, ``aha:svcs:bytype``,
    ``aha:lead:term``, and related databases).

Why
    Keeping the registry in AHA's own slab makes lookups fast, keeps updates atomic with the rest
    of AHA's state, and means the registry is captured by an ordinary backup of the AHA service.

What you need to do
    There is no in-place migration of a 2.x AHA registry. Stand up the 3.x AHA and let services
    register and provision against it; the registry is rebuilt as they do. A backup of the 3.x AHA
    now includes the registry.

Shared-secret provisioning
--------------------------

What changed
    A service can provision itself with nothing but a shared secret. Setting the same
    ``SYN_PROVISION_SECRET`` on the AHA server and on a service lets the service discover AHA over
    the network on its first boot -- via encrypted, authenticated multicast (or unicast to a
    specific host with ``SYN_PROVISION_HOST``) -- and provision itself with no per-service one-time
    URL. URL-based provisioning via the ``aha:provision`` config option still works exactly as
    before and short-circuits discovery when set.

What you need to do
    See :ref:`vtx_300_devops-service-provisioning` for the full workflow, the multicast group and
    port, firewall considerations, and the unicast fallback. In short: set
    ``SYN_PROVISION_SECRET`` on AHA and on each service and omit the per-service provisioning URL.

Followers and AHA clones: ``SYN_PROVISION_FOLLOWER``
----------------------------------------------------

What changed
    By default a fresh service of a type that has no registered leader boots as the first leader.
    Setting the ``SYN_PROVISION_FOLLOWER`` environment variable instead declares that a leader of
    the service's type already exists: the service assumes it must follow that leader and waits
    (indefinitely, logging a warning roughly once a minute) for the leader to register rather than
    ever starting empty. This removes the ambiguity of the first-boot leadership race when a
    follower may start before the leader has registered.

    The same mechanism lets an AHA server enroll itself as a clone. An AHA cannot resolve its own
    leader through ``aha://`` (it *is* the registry), so with ``SYN_PROVISION_FOLLOWER`` and
    ``dns:name`` set, a new AHA discovers the current leader AHA over the network and enrolls as a
    clone of it, again waiting for the leader to become reachable.

    Relatedly, when ``SYN_PROVISION_SECRET`` is set on an inaugural boot, provisioning discovery
    itself now retries until AHA responds rather than giving up and booting un-provisioned -- the
    secret is treated as a declaration that AHA must provision the service.

What you need to do
    Set ``SYN_PROVISION_FOLLOWER`` on any additional instance you intend to be a mirror, and on a
    new AHA clone (together with ``dns:name``). Ensure the leader is deployed so the follower can
    complete its bootstrap.

    .. code-block:: yaml

        # 3.x mirror / clone -- deploy as a follower of the current leader
        environment:
            - SYN_PROVISION_SECRET=<shared-secret>
            - SYN_PROVISION_FOLLOWER=1

``aha:network`` defaults to ``syn`` on the AHA service
------------------------------------------------------

What changed
    The ``aha:network`` configuration option now defaults to ``syn`` on the AHA service when it is
    not configured, and AHA bootstraps its network CA from that value. The default applies to the
    AHA service only; other services continue to receive their ``aha:network`` from provisioning
    and have no default.

Why
    A default network lets a quick-start or single-network AHA boot without hand-configuring a
    network name.

What you need to do
    For a real deployment, set ``aha:network`` explicitly to a name that reflects the deployment
    (for example ``dev.syn`` vs ``prod.syn``) so service names and certificates are namespaced to
    that environment. The AHA network is an internal AHA namespace only -- it is not a DNS name and
    is unrelated to DNS. The ``syn`` default is a convenience, not a recommendation for production.

Automatic Storm service discovery
---------------------------------

What changed
    A Storm service advertises a ``stormservice`` feature when it registers with AHA. An active
    Cortex watches the AHA registry and, for each discovered Storm service, adds it automatically
    using an ``aha://<type>...`` URL -- no manual ``service.add`` step. Auto-add is idempotent (the
    discovered service uses a deterministic iden) and does not override a service you added by hand
    under the same name.

Why
    Type-addressable services plus a live view of the registry make it possible for a Cortex to
    wire up Storm services on its own.

What you need to do
    Nothing. Storm services deployed into the AHA network are added to an active Cortex
    automatically.
