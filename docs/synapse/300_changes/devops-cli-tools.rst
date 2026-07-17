.. _vtx_300_devops-cli-tools:

CLI Tool Changes (cmdr, cellauth, reorg)
========================================

Synapse 3.0.0 reorganizes the command line tools under ``synapse.tools`` into
service-oriented subpackages and removes the legacy ``cmdr`` and ``cellauth`` tools
along with several retired subsystems. The entries below are ordered by how likely
they are to affect an existing 2.x deployment.

Tools relocated into namespaced subpackages
--------------------------------------------

What changed
    The top-level tool modules under ``synapse.tools.<name>`` -- which in 2.x
    were deprecation shims (warning since ``v2.225.0``) re-exporting from a
    subpackage -- are deleted in 3.0.0. Only the dotted subpackage paths work
    now. The 3.x layout is: ``synapse.tools.service.*`` holds ``apikey``,
    ``backup``, ``demote``, ``healthcheck``, ``modrole``,
    ``moduser``, ``promote``, ``reload``, ``shutdown``, and ``snapshot``;
    ``synapse.tools.cortex.*`` holds ``csv`` (the renamed ``csvtool``),
    ``docmodel``, ``feed``, and a ``layer`` subpackage;
    ``synapse.tools.axon.*`` holds ``copy``, ``dump``, ``get``, ``load``, and
    ``put``; ``synapse.tools.utils.*`` holds ``autodoc``, ``easycert``,
    ``guid``, ``json2mpk``, and ``rstorm``; and ``synapse.tools.aha.*`` holds
    ``clone``, ``del``, ``easycert``, ``enroll``, ``list``, ``mirror``, and a
    ``provision`` subpackage.

Why
    Grouping tools by the service they operate on clarifies usage and
    ownership, and 3.0.0 completes a migration that began with the
    ``v2.225.0`` deprecation warnings.

What you need to do
    Update scripts, cron jobs, systemd units, container entrypoints, and
    Dockerfiles that call the old top-level module paths. The CLI arguments
    are otherwise unchanged. Common mappings: ``csvtool`` -> ``cortex.csv``,
    ``feed`` -> ``cortex.feed``, ``genpkg`` -> ``storm.pkg.gen``, ``rstorm``
    -> ``utils.rstorm``, ``autodoc`` -> ``utils.autodoc``, ``easycert`` ->
    ``utils.easycert``, ``guid`` -> ``utils.guid``, ``json2mpk`` ->
    ``utils.json2mpk``, ``apikey`` -> ``service.apikey``, ``backup`` ->
    ``service.backup``, ``snapshot`` -> ``service.snapshot``, ``reload`` -> ``service.reload``,
    ``shutdown`` -> ``service.shutdown``, ``demote`` -> ``service.demote``,
    ``promote`` -> ``service.promote``, ``healthcheck`` ->
    ``service.healthcheck``, ``moduser`` -> ``service.moduser``, ``modrole``
    -> ``service.modrole``, ``pushfile`` -> ``axon.put``, ``pullfile`` ->
    ``axon.get``, and ``axon2axon`` -> ``axon.copy``.

    .. code-block:: bash

        # 2.x
        python -m synapse.tools.pushfile cell://axon ./report.pdf
        python -m synapse.tools.csvtool ./load.storm ./data.csv --cortex cell://core
        python -m synapse.tools.backup /srv/core /backups/core

        # 3.x
        python -m synapse.tools.axon.put cell://axon ./report.pdf
        python -m synapse.tools.cortex.csv ./load.storm ./data.csv --cortex cell://core
        python -m synapse.tools.service.backup /srv/core /backups/core

cmdr removed -- use the Storm CLI
---------------------------------

What changed
    The interactive command shell ``synapse.tools.cmdr`` is removed. The replacement
    is the Storm CLI, ``synapse.tools.storm``.

Why
    ``cmdr`` layered a bespoke command interpreter on top of Storm. The Storm
    CLI is the single, supported way to run interactive queries against a
    Cortex and exposes interpreter commands via the ``!`` convention.

What you need to do
    Replace any invocation of ``python -m synapse.tools.cmdr <url>`` with
    ``python -m synapse.tools.storm <url>``. In the Storm CLI, lines
    beginning with ``!`` are routed to the local interpreter (e.g.
    ``!help``); everything else is executed as Storm. Remove any code that
    imports ``synapse.lib.cmdr``; it no longer exists.

    .. code-block:: bash

        # 2.x
        python -m synapse.tools.cmdr cell://vertex/storage

        # 3.x
        python -m synapse.tools.storm cell://vertex/storage

cellauth removed -- manage auth with moduser/modrole
----------------------------------------------------

What changed
    The auth-management CLI ``synapse.tools.cellauth`` is removed. Its
    capabilities are now covered by ``synapse.tools.service.moduser`` and
    ``synapse.tools.service.modrole`` (plus the Storm ``$lib.auth.*`` APIs
    for in-Storm management).

Why
    Auth management is consolidated into the per-object service tools and
    Storm auth APIs, removing the parallel ``cellauth`` tool with its own
    rule-string handling.

What you need to do
    Replace ``cellauth`` invocations with ``moduser``/``modrole``.
    ``moduser`` takes the username as a positional argument and supports
    ``--url``, ``--add``/``--del``, ``--list``, ``--admin {true,false}``,
    ``--passwd``, ``--email``, ``--locked {true,false}``,
    ``--grant``/``--revoke`` (roles), ``--allow``/``--deny`` (permission
    rules, repeatable), and ``--gate`` (target an auth gate iden).
    ``modrole`` offers the equivalent for roles. See :ref:`vtx_300_admin-permissions`
    for the renamed and removed permission strings to use with ``--allow``/``--deny``.

    .. code-block:: bash

        # 2.x
        python -m synapse.tools.cellauth cell://core modify visi --addrule node.add
        python -m synapse.tools.cellauth cell://core modify visi --admin true

        # 3.x
        python -m synapse.tools.service.moduser --url cell://core --allow node.add visi
        python -m synapse.tools.service.moduser --url cell://core --admin true visi

Cryotank and Hive tooling removed
---------------------------------

What changed
    The Cryotank service and its CLI tools (``synapse.tools.cryo.cat``,
    ``synapse.tools.cryo.list``) are removed, along with ``synapse.cryotank``
    and ``synapse.servers.cryotank``. The Hive tools
    (``synapse.tools.hive.load``, ``synapse.tools.hive.save``) and the
    ``synapse.lib.hive`` library are removed.

Why
    Cryotank and Hive are legacy subsystems retired in 3.0.0; cell
    configuration and state no longer live in a Hive tree, and Cryotank is no
    longer a shipped service.

What you need to do
    Stop using ``cryo.cat``/``cryo.list`` and ``hive.load``/``hive.save``. If
    you ran a Cryotank service, plan a migration off it before upgrading. Any
    code importing ``synapse.lib.hive``, ``synapse.cryotank``, or
    ``synapse.servers.cryotank`` must be removed -- they no longer exist.

    .. code-block:: bash

        # 2.x
        python -m synapse.tools.cryo.list cell://cryo

        # 3.x -- cryotank service removed; no replacement
