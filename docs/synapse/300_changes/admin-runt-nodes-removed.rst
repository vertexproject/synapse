.. _vtx_300_admin-runt-nodes-removed:

syn:cron and syn:trigger Runt Nodes Removed
===========================================

The ``syn:cron`` and ``syn:trigger`` runtime-only (runt) node forms have been removed in 3.0.0.

.. seealso::

   The full replacement command / library / object surface for cron and triggers is
   described in :ref:`vtx_300_storm-cron-and-trigger-api`. The new ``syn:deleted`` runt node
   (also listed below) is described in :ref:`vtx_300_admin-tombstones`.

What changed
    In 2.x, cron jobs and triggers were exposed as runtime-only (runt) nodes via the
    ``syn:cron`` and ``syn:trigger`` forms, which could be lifted and filtered in Storm
    like any other node. In 3.x those forms and their lift handlers no longer exist in the
    data model; the runt forms defined by the ``syn`` model are now ``syn:type``,
    ``syn:form``, ``syn:interface``, ``syn:prop``, ``syn:tagprop``, ``syn:cmd``, and
    ``syn:deleted``.

    Cron and trigger inspection now goes through the dedicated Storm commands
    (``cron.list``, ``cron.stat``, ``trigger.list``) and the ``$lib.cron`` and
    ``$lib.trigger`` libraries, all of which remain. The objects returned by
    ``$lib.cron.list()`` and ``$lib.trigger.list()`` expose properties such as
    ``iden``, ``enabled``, ``view``, ``doc`` (and ``cond`` for triggers) for filtering.

Why
    Cron and trigger configuration is operational scheduler state, not graph data.
    Representing it as liftable runt nodes invited filtering and pivoting patterns that
    did not compose well and were view-scoped. The command and library surface is the
    supported, consistent way to manage these objects.

What you need to do
    Replace any Storm that lifts ``syn:cron`` or ``syn:trigger`` nodes. To enumerate
    cron jobs use ``cron.list`` or ``cron.stat``; to enumerate triggers use
    ``trigger.list`` (add ``--all`` to list every trigger in every readable view rather
    than just the current view). For programmatic access, iterate ``$lib.cron.list()`` or
    ``$lib.trigger.list()`` and filter on the returned object properties. There is no
    data to migrate -- these were runtime-only nodes with no stored data.

    ::

        // 2.x: enumerate via runt nodes
        syn:cron
        syn:trigger:doc~=ingest

        // 3.x: use the commands
        cron.list
        trigger.list --all

    ::

        // 2.x: filter crons by a node prop (the runt form exposed :doc, :name, :storm)
        syn:cron:doc~=ingest

        // 3.x: iterate the library and filter on object properties
        // (e.g. find disabled crons -- the cronjob object exposes .enabled)
        for $cron in $lib.cron.list() {
            if (not $cron.enabled) { $lib.print($cron.iden) }
        }

        // 3.x: iterate triggers
        for $trig in $lib.trigger.list() { $lib.print($trig.iden) }
