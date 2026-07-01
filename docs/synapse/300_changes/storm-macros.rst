.. _vtx_300_storm-macros:

Storm Macro Definition Changes
==============================

The Storm macro definition lost its ``user`` field and moved to the easy-permission model.

What changed
    A Storm macro definition (the ``mdef`` dict returned by ``$lib.macro.get()`` and
    ``$lib.macro.list()``) no longer has a ``user`` field. In 2.x the definition carried
    both a ``user`` field (the owning / run-as user iden) and a ``creator`` field; in 3.x
    the ``user`` field is removed and only ``creator`` (the iden of the user who created
    the macro) remains. The 3.x definition now always includes ``iden``, ``created`` and
    ``updated``, and an easy-permissions ``permissions`` block, and who may use, edit, or
    administer a macro is expressed through those graded permissions rather than a single
    owning ``user``. The legacy ``enabled`` / ``stormopts`` macro fields are gone as well.

Why
    Macros adopted the same easy-permission model used elsewhere in the Cortex, so a single
    owning ``user`` field became redundant: ``creator`` records provenance, and read / edit /
    admin access is now graded per user and role.

What you need to do
    Replace any read of a macro's ``user`` field with ``creator``. Manage who can use or edit
    a macro with the ``macro.grant`` command (or ``$lib.macro.grant()``) instead of relying on
    an owning user. See :ref:`vtx_300_admin-permissions` for the related change moving the macro
    admin / edit permissions out of the ``storm.*`` namespace.

    ::

        // 2.x -- read the owning user iden from the macro definition
        $mdef = $lib.macro.get(mymacro)
        $owner = $mdef.user

        // 3.x -- the "user" field is gone; use creator
        $mdef = $lib.macro.get(mymacro)
        $owner = $mdef.creator
