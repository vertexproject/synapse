.. _vtx_300_admin-permissions:

Permission Changes
==================

Synapse 3.0.0 simplifies and consolidates several parts of the permission model. Audit any user/role rules that reference the renamed or removed permissions below and update them before moving a 2.x deployment to 3.0.0. Entries are ordered roughly most-impactful first.

Extended model permissions collapsed to ``model.admin``
-------------------------------------------------------

What changed
    The granular extended-data-model permission tree from 2.x is replaced by a single permission, ``model.admin`` (gate ``cortex``). In 2.x the Cortex defined separate permissions for each model operation -- ``model.form.add``/``del``, ``model.type.add``/``del``, ``model.prop.add``/``del``, ``model.tagprop.add``/``del``, ``model.univ.add``/``del``, and ``model.edge.add``/``del`` (with form-scoped variants). In 3.x all extended-model mutation APIs (such as adding or removing forms, props, tag props, and edges) confirm ``model.admin``.

Why
    The fine-grained model permissions were rarely used at that granularity and complicated administration. A single ``model.admin`` permission is simpler to reason about and to grant to the small set of users who should modify the extended data model.

What you need to do
    Audit any user/role rules that grant the old granular permissions (``model.form.add``, ``model.type.del``, ``model.prop.add``, ``model.univ.*``, ``model.edge.*``, ``model.tagprop.*``, and so on). Replace them with a single ``model.admin`` grant for users who need to extend the model.

    ::

        // 2.x: granular grants
        auth.user.addrule visi model.form.add
        auth.user.addrule visi model.prop.add

        // 3.x: single grant
        auth.user.addrule visi model.admin

view.fork no longer granted by default
--------------------------------------

What changed
    The ``view.fork`` permission no longer defaults to allow. In 2.x this permission carried ``'default': True``, so any user with read access to a view could fork it without an explicit grant. In 3.x ``view.fork`` has no default, so it falls through to deny unless explicitly granted. The only Cortex permissions that still default to True are ``storm.graph.add`` and ``storm.macro.add``.

Why
    Forking a view creates a new top layer and view object; letting every user do so implicitly could lead to uncontrolled proliferation of views and layers. Requiring an explicit grant gives admins control over who can fork.

What you need to do
    If your users rely on forking views (for example, analysts creating scratch/work views), explicitly grant ``view.fork`` to the appropriate users or roles -- commonly the ``all`` role to preserve 2.x behavior. Otherwise non-admin fork attempts that previously succeeded will now be denied.

    ::

        // 2.x: any reader could fork; no grant needed
        $lib.view.get().fork()

        // 3.x: grant explicitly to restore prior behavior
        auth.role.addrule all view.fork
        // or per view gate:
        auth.user.addrule analyst view.fork --gate <viewiden>

proj:project nodes no longer create authgates; the project Storm library is removed
-----------------------------------------------------------------------------------

What changed
    In 2.x, project management lived in a dedicated Storm library (``$lib.projects``) and project permissions were enforced against a per-project authgate using ``('project', ...)`` permission strings. In 3.x the entire project Storm library is removed (there is no ``$lib.projects``), ``proj:project`` and ``proj:ticket`` are now ordinary data-model guid nodes, and creating a project no longer creates an authgate. There are no ``('project', ...)`` permissions in the Cortex permission definitions.

Why
    Per-project authgates and a bespoke project permission tree added a parallel authorization surface that did not scale and duplicated normal node-edit permissions. Treating projects as regular nodes means they are governed by the standard ``node``/``view``/``layer`` permission model like any other data.

What you need to do
    Stop using ``$lib.projects.*`` and project-specific Storm methods -- create and edit ``proj:project`` and ``proj:ticket`` as normal nodes with standard Storm node edits. Remove any user/role rules granting ``project.*`` permissions on a project authgate; they no longer apply. Govern who can edit project nodes via the standard ``node.add``/``node.prop.set``/``view`` permissions on the relevant view or layer.

    ::

        // 2.x
        $proj = $lib.projects.get($name)
        $proj.tickets.add(...)
        // auth: user granted ('project', 'ticket', 'add') on the project authgate

        // 3.x: proj:project / proj:ticket are normal guid nodes
        [ proj:ticket=* :name="investigate phishing" :type=task ]
        // auth: standard node.add / node.prop.set / view permissions apply

Storm macro admin/edit permissions moved out of the ``storm.*`` namespace
-------------------------------------------------------------------------

What changed
    The macro management permissions were renamed from ``storm.macro.add``, ``storm.macro.admin``, and ``storm.macro.edit`` to top-level ``macro.add``, ``macro.admin``, and ``macro.edit`` (gate ``cortex``).

Why
    Macro editing and administration is its own concern; promoting it to a top-level ``macro.*`` permission tree separates "add a macro" (a general Storm capability) from "administer/edit existing macros" (a privileged action).

What you need to do
    Update user/role rules: replace grants of ``storm.macro.admin`` with ``macro.admin`` and ``storm.macro.edit`` with ``macro.edit``. Leave ``storm.macro.add`` rules as-is.

    ::

        // 2.x
        auth.user.addrule visi storm.macro.edit

        // 3.x
        auth.user.addrule visi macro.edit

Property permissions drop the full property path
------------------------------------------------

What changed
    The permissions that gate setting or deleting a node property no longer accept the full property path as a single permission element. In 2.x, a property set/del check matched either the full property path (for example ``node.prop.set.inet:dns:a:fqdn``) or the form name plus the relative property name (``node.prop.set.inet:dns:a.fqdn``). In 3.x only the form name plus relative property name form is checked. The form-level (``node.prop.set.inet:dns:a``) and all-property (``node.prop.set``) permissions are unchanged.

Why
    Maintaining two parallel encodings of the same check was redundant. Keeping only the form-name-plus-relative-name form gives a single, consistent way to scope a property permission that also nests cleanly under the form-level and ``node.prop.set`` / ``node.prop.del`` permissions.

What you need to do
    Migrate any user/role rules granted or denied using the full property path (``node.prop.set.<form>:<prop>`` / ``node.prop.del.<form>:<prop>``) to the form-name-plus-relative-property-name form (``node.prop.set.<form>.<prop>`` / ``node.prop.del.<form>.<prop>``). Rules scoped to a form (``node.prop.set.<form>``) or to all property sets/dels are unaffected.

    ::

        // 2.x: the full property path (colon-joined) was honored
        auth.user.addrule visi node.prop.set.inet:dns:a:fqdn

        // 3.x: use the form name plus the relative property name (dot-joined)
        auth.user.addrule visi node.prop.set.inet:dns:a.fqdn

node.data.pop permission renamed to node.data.del
-------------------------------------------------

What changed
    The node-data deletion permission changed from ``node.data.pop`` to ``node.data.del`` (with a corresponding key-scoped ``node.data.del.<varname>``). The Storm node-data deletion operation now confirms ``node.data.del`` instead of ``node.data.pop``. The ``node.data.set`` permission is unchanged.

Why
    Aligns the permission name with the rest of the permission tree, which uses ``add``/``del`` (for example ``node.add``/``node.del``, ``node.prop.del``) rather than ``pop``.

What you need to do
    Update any user/role rules that grant or deny ``node.data.pop`` (or ``node.data.pop.<key>``) to use ``node.data.del`` (or ``node.data.del.<key>``). The behavior gated is the same: removing node data.

    ::

        // 2.x
        auth.user.addrule visi node.data.pop --gate <layeriden>

        // 3.x
        auth.user.addrule visi node.data.del --gate <layeriden>

Layer read access derived from View read; wildcard layer permissions removed
----------------------------------------------------------------------------

What changed
    The 2.x cortex-gated wildcard layer permissions ``layer.read.<layer>`` and ``layer.write.<layer>`` (gate ``cortex``) have been removed in 3.x. The standalone ``layer.read`` permission has also been removed entirely: layer read access is now derived from View read access. A user who can read any View a layer belongs to -- or who is an admin of the layer's own authgate -- may read that layer. Layer write access is still expressed through the layer-gated ``layer.write`` permission applied against a specific layer's authgate.

    Related, ``$lib.view.list()`` and ``$lib.layer.list()`` now return only the Views and layers the calling user can read, and ``$lib.view.get(<iden>)`` / ``$lib.layer.get(<iden>)`` raise ``NoSuchView`` / ``NoSuchIden`` for an iden the user cannot read rather than returning it, so an unreadable View or layer is indistinguishable from one that does not exist.

Why
    A user who can read a View can switch to it and lift from all of its layers anyway, so a separate layer read permission was redundant. Deriving layer read access from View read access removes the redundant, easily-desynchronized permission and closes a class of information leaks where unreadable Views and layers were still enumerable.

What you need to do
    Replace any ``layer.read`` grants (cortex-gated wildcard ``layer.read.<layeriden>`` or the layer-gated ``layer.read``) with a ``view.read`` grant on a View that uses the layer. Migrate cortex-gated wildcard ``layer.write.<layeriden>`` rules to the layer-gated ``layer.write`` (use ``--gate <layeriden>``).

    ::

        // 2.x
        auth.user.addrule visi layer.read.<layeriden>

        // 3.x  (grant read on a View that uses the layer)
        auth.user.addrule visi view.read --gate <viewiden>

Deprecated storm.asroot.cmd / storm.asroot.mod permission definitions removed
-----------------------------------------------------------------------------

What changed
    The ``storm.asroot.cmd.<cmdname>`` and ``storm.asroot.mod.<modname>`` permission definitions, which were already marked deprecated in 2.x, are no longer present in the Cortex permission definitions in 3.x. The internal asroot execution mechanism (running a command or module with elevated privileges) still exists.

Why
    These were legacy, deprecated permission strings retained for backward compatibility. Storm packages should declare their required privileges via the package ``asroot:perms`` key rather than relying on these per-cmd or per-mod asroot permissions.

What you need to do
    If you still grant ``storm.asroot.cmd.<name>`` or ``storm.asroot.mod.<name>``, migrate the affected packages or modules to declare their needed permissions via ``asroot:perms`` and grant those concrete permissions instead. The asroot permission strings are no longer advertised by the Cortex permission catalog.

    ::

        // 2.x
        auth.user.addrule visi storm.asroot.cmd.mycmd

        // 3.x: declare needed perms via the package's asroot:perms and grant those concrete perms
        auth.user.addrule visi <concrete.perm.from.asroot:perms>
