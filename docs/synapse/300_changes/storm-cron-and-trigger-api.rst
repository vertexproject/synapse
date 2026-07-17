.. _vtx_300_storm-cron-and-trigger-api:

Cron and Trigger API Changes
============================

Synapse 3.0.0 consolidates the cron and trigger Storm commands, ``$lib`` APIs, Storm objects, and Cortex
telepath methods around a single dict-based edit path and a new period syntax. The sections below cover the
concrete changes and how to port 2.x usage.

cron.add period syntax
-----------------------

What changed
    In 2.x, ``cron.add`` took the Storm query as its only positional argument plus a swarm of recurrence options
    (``--period`` and the per-unit ``--minute``/``--hour``/``--day``/``--month``/``--year``/``--hourly``/``--daily``/``--monthly``/``--yearly``).
    In 3.x the signature is ``cron.add <period> <query>``: ``period`` is the first positional and the Storm query is
    the second. All per-unit recurrence flags are gone. The period uses a unified
    ``<periodicity>[/<value>...][@<time>]`` format where periodicity is one of hourly/daily/weekly/monthly/yearly
    (for example ``daily``, ``daily@14:30``, ``hourly/2@:00``, ``hourly@:24,45``, ``weekly/mon,wed@10:00``,
    ``monthly/1,15@12:00``, ``monthly/-1``, ``yearly/05-14``, ``yearly/11-14@13:43``). A ``--period`` long-form
    alias for the positional is also accepted.

    The same applies to ``$lib.cron.add()``, which changed from ``add(**kwargs)`` to ``add(period, query, **kwargs)``:
    ``period`` and ``query`` are required positionals and the per-unit recurrence kwargs are gone.

Why
    The old per-unit flags overlapped and were error-prone. A single expressive period format is easier to read,
    validate, and document, and lets 3.x drop the large block of options that were deprecated for v3.0.0.

What you need to do
    Put the period first in ``cron.add`` and translate old usage to the new format. Note that hourly periods
    REQUIRE an explicit minute (for example ``hourly@:00``) or a ``BadTime`` is raised. For ``$lib.cron.add()``,
    pass the period string and query positionally and drop the per-unit recurrence kwargs.

    ::

        // 2.x
        cron.add --hourly 30 { inet:ipv4#stale | delnode }
        cron.add --day +1 --hour 14 --minute 30 { $lib.print(daily) }

        // 3.x
        cron.add hourly@:30 { inet:ip#stale | delnode }
        cron.add daily@14:30 { $lib.print(daily) }

    ::

        // 2.x
        $cron = $lib.cron.add(query=${ #stale | delnode }, hourly=30)

        // 3.x
        $cron = $lib.cron.add("hourly@:30", ${ #stale | delnode })

    ``$lib.cron.at()`` likewise now takes ``query`` as a required leading positional, but at-jobs are not
    period-based, so it still accepts the relative-time kwargs ``minute``/``hour``/``day``/``dt``/``now``.

    ::

        // 2.x
        $cron = $lib.cron.at(query=${ [inet:ipv4=1.2.3.4] }, minute='+5')

        // 3.x
        $cron = $lib.cron.at(${ [inet:ip=1.2.3.4] }, minute='+5')

cron.mod consolidation and removed cron commands
------------------------------------------------

What changed
    In 2.x ``cron.mod <iden> [<query>] [--period ...]`` could only change the query and/or period, and the
    standalone commands ``cron.move``, ``cron.enable``, and ``cron.disable`` handled the rest. In 3.x ``cron.move``,
    ``cron.enable``, and ``cron.disable`` are removed; their behavior folds into ``cron.mod``, which now takes
    ``<iden>`` plus the flags ``--view``, ``--storm``, ``--user``, ``--doc``, ``--name``,
    ``--enabled``, ``--loglevel``, and ``--period``. The 3.x cron command set is add/at/del/mod/cleanup/list/stat.

    ``$lib.cron`` lost the ``move()``, ``enable()``, and ``disable()`` methods and now exposes only ``at``, ``add``,
    ``del``, ``get``, ``mod``, and ``list``. ``$lib.cron.mod(prefix, edits)`` now takes a single ``edits`` dict
    instead of a positional query. Allowed edit keys are ``storm``, ``reqs``, ``incunit``, ``incvals``, ``name``,
    ``enabled``, ``affinity``, ``doc``, ``loglevel``, ``user``, and ``view`` (a ``period`` key is parsed
    into ``reqs``/``incunit``/``incvals``); any other key raises ``BadOptValu``.

Why
    Consolidating all cron mutation through one dict-based edit path lets a user change view/user/enabled/
    loglevel/doc/name/storm/period in one command and removes the need for separate move/enable/disable commands
    and methods.

What you need to do
    Use the new ``cron.mod`` flags, and replace the removed commands and ``$lib.cron`` methods with edits.

    ::

        // 2.x
        cron.mod <iden> { $lib.print(newq) }
        cron.disable 7a1b...
        cron.move 7a1b... 2c3d...

        // 3.x
        cron.mod <iden> --storm { $lib.print(newq) } --enabled true
        cron.mod 7a1b... --enabled false
        cron.mod 7a1b... --view 2c3d...

    ::

        // 2.x
        $lib.cron.mod($iden, ${ $lib.print(newq) })
        $lib.cron.disable($iden)
        $lib.cron.move($iden, $viewiden)

        // 3.x
        $lib.cron.mod($iden, ({"storm": "$lib.print(newq)", "enabled": true}))
        $lib.cron.mod($iden, ({"enabled": false}))
        $lib.cron.mod($iden, ({"view": $viewiden}))

CronJob Storm object
--------------------

What changed
    The 2.x ``cronjob`` primitive exposed ``set(name, valu)``, ``kill()``, ``pack()``, and ``pprint()``. In 3.x
    ``set`` and ``pack`` are removed (the object exposes only ``kill`` and ``pprint`` as methods). Instead the
    cronjob exposes readable named properties -- ``completed``, ``creator``, ``created``, ``doc``, ``enabled``,
    ``iden``, ``name``, ``pool``, ``storm``, ``view``, ``user`` -- and supports direct attribute assignment (for
    example ``$cron.name = 'foo'``), which internally calls ``editCronJob``. The new ``completed`` property returns
    true when a non-recurring (at) job has finished.

Why
    First-class typed properties and Pythonic attribute assignment replace the generic ``set``/``pack`` accessors,
    and a direct ``completed`` flag supports at-job cleanup.

What you need to do
    Replace ``$cron.set(name, $valu)`` with direct assignment (or ``$lib.cron.mod``), replace ``$cron.pack()`` with
    the named properties or ``$cron.pprint()``, and use ``$cron.completed`` to detect finished at-jobs.

    ::

        // 2.x
        $cron.set(name, 'nightly cleanup')
        $job = $cron.pack()
        if (not $job.recs) { $lib.cron.del($job.iden) }

        // 3.x
        $cron.name = 'nightly cleanup'
        if $cron.completed { $lib.cron.del($cron.iden) }

trigger.add and trigger.mod
---------------------------

What changed
    In 2.x ``trigger.add`` required the query via ``--query`` (with ``condition`` the only positional). In 3.x
    ``trigger.add`` takes two positionals -- ``condition`` and ``storm`` (the query) -- and ``--query`` is gone.
    ``trigger.mod`` changed from ``trigger.mod <iden> <query>`` (only the query could change) to ``trigger.mod
    <iden>`` with the flags ``--view``, ``--storm``, ``--user``, ``--async``, ``--enabled``, and ``--name``,
    backed by ``$lib.trigger.mod(prefix, edits)`` taking an edits dict.

    The standalone ``trigger.enable`` and ``trigger.disable`` commands and the ``$lib.trigger.enable``/
    ``$lib.trigger.disable`` methods are removed; enabling and disabling is now done through ``--enabled true|false``
    (or the ``enabled`` edit key). The 3.x trigger command set is add/del/mod/list and ``$lib.trigger`` exposes
    add/del/list/get/mod.

    A trigger's condition (``form``/``tag``/``prop``/``verb``/``n2form``/``cond``) is set at creation time and is
    not one of the editable keys; passing any of these to ``trigger.mod`` or ``$lib.trigger.mod`` raises
    ``BadArg``. To change what a trigger fires on, delete it and add a new one with the desired condition.

Why
    Making the query a required positional matches ``cron.add``, and a single ``trigger.mod`` edit path lets any
    editable trigger property (view/storm/user/async/enabled/name) change in one command, replacing the removed
    enable/disable commands. A trigger's condition isn't included because changing it isn't really "editing" the
    trigger -- it would fire on different data entirely -- so that case is handled by replacing the trigger.

What you need to do
    Drop ``--query`` from ``trigger.add`` and pass the query positionally. Use ``trigger.mod --storm`` to change
    the query and ``--enabled true|false`` instead of the removed enable/disable commands. For ``$lib.trigger.mod``,
    pass an edits dict instead of a query string.

    ::

        // 2.x
        trigger.add node:add --form inet:ipv4 --query { $lib.print(hi) }
        trigger.mod <iden> { $lib.print(new) }
        trigger.disable 7a1b...
        $lib.trigger.enable($iden)

        // 3.x
        trigger.add node:add --form inet:ip { $lib.print(hi) }
        trigger.mod <iden> --storm { $lib.print(new) } --enabled true
        trigger.mod 7a1b... --enabled false
        $lib.trigger.mod($iden, ({"enabled": true}))

Trigger Storm object
--------------------

What changed
    The Trigger Storm object (returned by ``$lib.trigger.*`` and ``view.triggers``) was restructured to mirror the
    CronJob change. The 2.x ``set()``, ``move()``, ``pack()``, and ``valu()`` methods and the ``viewiden`` member
    are removed. In 3.x the trigger exposes named properties -- ``async``, ``cond``, ``created``, ``creator``,
    ``doc``, ``enabled``, ``form``, ``n2form``, ``prop``, ``storm``, ``tag``, ``verb``, ``view`` (plus ``iden``,
    ``name``, ``user``) -- and supports direct attribute assignment.

Why
    Consistency with the CronJob redesign: discrete named, individually-settable properties replace the
    ``set()``/``move()``/``pack()`` method surface.

What you need to do
    Replace ``$trig.set(prop, valu)`` with direct assignment, replace ``$trig.pack()`` with reads of the named
    properties, and set the ``view`` property in place of the removed ``$trig.move()``.

    ::

        // 2.x
        $trig = $lib.trigger.get($iden)
        $trig.set("storm", "[ +#reviewed ]")
        $info = $trig.pack()

        // 3.x
        $trig = $lib.trigger.get($iden)
        $trig.storm = "[ +#reviewed ]"
        $query = $trig.storm

Cortex telepath cron API and cron definition
--------------------------------------------

What changed
    2.x Cortex exposed ``moveCronJob(useriden, croniden, viewiden)``, ``updateCronJob(iden, query=None, reqs=None,
    incunit=None, incvals=None)``, ``enableCronJob(iden)``, ``disableCronJob(iden)``, and a single-property
    ``editCronJob(iden, name, valu)``. 3.x removes move/update/enable/disable and exposes a single
    ``editCronJob(iden, edits)`` that accepts a dict of properties (allowed keys: ``storm``, ``reqs``, ``incunit``,
    ``incvals``, ``name``, ``enabled``, ``pool``, ``affinity``, ``doc``, ``loglevel``, ``user``, ``view``) and
    returns the packed cdef. ``addCronJob(cdef)``, ``delCronJob(iden)``, ``killCronTask(iden)``, and
    ``listCronJobs()`` remain. Edits replicate via a single ``cron:edit`` nexus event.

    The cron definition dict (cdef) also changed: the query key is renamed from ``query`` (2.x) to ``storm`` (3.x),
    and the job now tracks ``creator`` (who created the job) separately from ``user`` (who the job runs as). The
    cdef also carries a ``created`` timestamp.

Why
    One dict-based edit entry point replaces four narrow mutators, simplifying replication and the client surface.
    Separating creator from run-as user enables clearer auditing, and renaming query to storm aligns cron defs with
    trigger and other definitions that use ``storm``.

What you need to do
    Telepath clients calling ``updateCronJob``, ``moveCronJob``, ``enableCronJob``, or ``disableCronJob`` must
    switch to ``editCronJob(iden, edits)`` with the relevant keys. Single-property ``editCronJob(iden, name, valu)``
    calls become ``editCronJob(iden, {name: valu})``. Integrators constructing a cdef should use the ``storm`` key
    (not ``query``) and may set ``creator``, ``user``, and ``created``; code reading packed cron defs should read
    ``storm`` instead of ``query``.

    .. code-block:: python

        # 2.x
        await core.disableCronJob(iden)
        await core.moveCronJob(useriden, iden, viewiden)
        await core.editCronJob(iden, 'name', 'nightly')

        # 3.x
        await core.editCronJob(iden, {'enabled': False})
        await core.editCronJob(iden, {'view': viewiden})
        await core.editCronJob(iden, {'name': 'nightly'})

    .. code-block:: python

        # 2.x
        cdef = {'query': '$lib.print(hi)', 'creator': useriden, 'reqs': {...}, 'incunit': 'day', 'incvals': 1}
        await core.addCronJob(cdef)

        # 3.x
        cdef = {'storm': '$lib.print(hi)', 'creator': useriden, 'user': runasiden, 'reqs': {...}, 'incunit': 'day', 'incvals': 1}
        await core.addCronJob(cdef)
