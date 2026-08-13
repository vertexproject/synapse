

<a id="adminguide"></a>

# Synapse Admin Guide

This guide is designed for use by Synapse Administrators ("global admins"). Synapse Admins are typically Synapse power-users with `admin=true` privileges on the [Cortex](glossary.md#gloss-cortex) who are responsible for configuration and management of a production instance of Synapse.

The Synapse Admin Guide provides important instructions and background information on topics related to day-to-day Synapse administrative tasks, and focuses on using [Storm](glossary.md#gloss-storm) to carry out those tasks.

Synapse provides a number of additional methods that can be used to perform some or all of the tasks described in this guide; however, these methods are **not** covered here. Additional methods include:

- [stormtypes-libs-header](stormtypes_libs.md#stormtypes-libs-header) that allow you to work with a broad range of objects in Synapse.
- Synapse tools that can be used from the host CLI (as opposed to the Storm CLI). The [Synapse User Guide](userguide.md#userguide) includes documentation on some of these [Tools](userguides/index_tools.md#userguide_tools).
- The [Synapse HTTP/REST API](httpapi.md#http-api).

> [!TIP]
> If you are a commercial Synapse user with the Synapse UI (Optic), see the [UI documentation](/docs/synapse-enterprise-optic/latest/index.md) for information on performing Synapse Admin tasks using Optic. Optic simplifies many of Synapse's administrative tasks. However, we encourage you to review the information in this guide for important background and an overview of the relevant topics.

<a id="admin_enable_powerup"></a>

## Enable Synapse Power-Ups

The Vertex Project provides a number of Power-Ups that extend the functionality of Synapse. For more information on configuring your Cortex to use **Rapid Power-Ups,** see [the blog post on Synapse Power-Ups](https://vertex.link/blogs/synapse-power-ups/).

> [!NOTE]
> **Advanced Power-Ups** are deployed via their own [Docker containers](https://www.docker.com/resources/what-container/) and are typically configured by a DevOps team.

<a id="admin_create_users_roles"></a>

## Create and Manage Users and Roles

A [User](glossary.md#gloss-user) account is required to authenticate to and access Synapse. Having "a Synapse account" effectively means having an account in the Cortex.

In Synapse, a [Role](glossary.md#gloss-role) can be used to "group" users with similar responsibilities (and related permissions requirements). You can **grant** or **revoke** one or more roles from a user.

You grant (or deny) **permissions** to users or roles by assigning **rules** that specify those permissions (see [Assign and Manage Permissions](adminguide.md#admin_perms)).

Synapse includes the following built-in users and roles:

- **Root** user. The **root** account has [Admin](adminguide.md#admin_bkd_admin) privileges in the Cortex. The **admin** status of the root account cannot be revoked, and the account cannot be locked / disabled.
- **All** role. The **all** role has **read** access to the Cortex (specifically, to any view it has been granted `view.read` on, which includes the **default** view). All user accounts are automatically granted the **all** role (are part of the **all** "group"); this role cannot be revoked.

> [!TIP]
> The set of Storm [auth](userguides/storm_ref_cmd.md#storm-auth) commands are collectively used to manage users, roles, and permissions from Storm.
>
> In the commercial Optic UI, users, roles, and permissions can be managed through the **Admin Tool** and through dialogs associated with various objects (such as Views or Stories).

> [!NOTE]
> The descriptions and examples below assume that you have deployed Synapse using native Synapse management and authentication of users, roles, and permissions.
>
> The [Synapse Devops Guide](devopsguide.md#devopsguide) includes information on provisioning **initial** users when Synapse is first deployed (see [Managing Users and Roles](devopsguide.md#devops-task-users)). This guide focuses on ongoing management of users and roles once Synapse admins have access to Storm (i.e., the Storm CLI or Optic UI).

<a id="admin_users"></a>

### Working with Users

<a id="admin_user_add"></a>

#### Add a User

The [auth.user.add](userguides/storm_ref_cmd.md#storm-auth-user-add) command creates a new user. Newly created users do not have any permissions (other than those associated with the built-in **all** role).

**Example:**

Add the user "Ron" with email address `ronthecat@vertex.link`:

```stormdoc
storm> auth.user.add ron --email ronthecat@vertex.link
User (ron) added with iden: 65ef88905c2e29b24739857f60b0759b
```

> [!TIP]
> Users are represented by a unique 128-bit identifier (iden). You can modify information about the user account (such as the username or associated email address) without affecting the underlying identifier or any associated roles or permissions.

<a id="admin_user_show"></a>

#### Display a User

The [auth.user.show](userguides/storm_ref_cmd.md#storm-auth-user-show) command displays information about a user, including any assigned roles or rules (permissions) and their order.

**Example:**

Display information for user "Ron":

```stormdoc
storm> auth.user.show ron
User: ron (65ef88905c2e29b24739857f60b0759b)

  Locked: false
  Admin: false
  Email: ronthecat@vertex.link
  Rules:

  Roles:
    5ff63f33765828350fa00e6c684d79cc - all

  Gates:
```

<a id="admin_user_mod"></a>

#### Modify a User

The [auth.user.mod](userguides/storm_ref_cmd.md#storm-auth-user-mod) command modifies a user account. Use the command to:

- Change the username or email address associated with the user.
- Set or reset the user's password.
- Assign (or remove) **admin** status for the user.
- Lock (or unlock) the account.

**Examples:**

Update the email address for user "Ron":

```stormdoc
storm> auth.user.mod ron --email ron@vertex.link
User (ron) email address set to ron@vertex.link.
```

Assign **admin** status to the user "ron_admin":

```stormdoc
storm> auth.user.mod ron_admin --admin (true)
User (ron_admin) admin status set to true.
```

Remove **admin** status from user "ron_admin":

```stormdoc
storm> auth.user.mod ron_admin --admin (false)
User (ron_admin) admin status set to false.
```

Lock the user account "ron_admin":

```stormdoc
storm> auth.user.mod ron_admin --locked (true)
User (ron_admin) locked status set to true.
```

> [!WARNING]
> We strongly encourage you to **lock** (disable) accounts when necessary instead of deleting them. Changes to data in the Cortex (such as creating nodes, setting properties, or adding tags) are associated with the user account that made those changes. Deleting an account associated with past changes will prohibit you from identifying the user who made those changes.
>
> If necesssary, user accounts can be deleted using the [stormlibs-lib-auth-users-del](stormtypes_libs.md#stormlibs-lib-auth-users-del) library, but there is no equivalent Storm command.

<a id="admin_user_list"></a>

#### List All Users

The [auth.user.list](userguides/storm_ref_cmd.md#storm-auth-user-list) command lists all users in the Cortex.

**Example:**

List all users:

```stormdoc
storm> auth.user.list
Users:
  ron
  root

Locked Users:
  ron_admin
```

<a id="admin_roles"></a>

### Working with Roles

<a id="admin_role_add"></a>

#### Add a Role

The [auth.role.add](userguides/storm_ref_cmd.md#storm-auth-role-add) command creates a new role. Newly created roles do not have any permissions or associated user accounts.

**Example:**

Add the new role "cattribution analyst":

```stormdoc
storm> auth.role.add "cattribution analyst"
Role (cattribution analyst) added with iden: 5519e5ad546c457fe727855b6fe017e3
```

> [!TIP]
> Roles are represented by a unique 128-bit identifier (iden). You can later change information about the role (such as the role name) without affecting the underlying role or any associated permissions or users.

<a id="admin_role_show"></a>

#### Display a Role

The [auth.role.show](userguides/storm_ref_cmd.md#storm-auth-role-show) command displays information about a role, including any assigned rules (permissions) and their associated objects.

**Example:**

Display information for the "all" role:

```stormdoc
storm> auth.role.show all
Role: all (5ff63f33765828350fa00e6c684d79cc)

  Rules:

  Gates:
    79a398abf2e614071e8edee3c0c44943 - (view)
      [0  ] - view.read
```

<a id="admin_role_mod"></a>

#### Modify a Role

The [auth.role.mod](userguides/storm_ref_cmd.md#storm-auth-role-mod) command modifies a role. The command can be used to change the name of the role.

**Example:**

Change the name of the role "cattribution analyst" to "meow-ware analyst":

```stormdoc
storm> auth.role.mod "cattribution analyst" --name "meow-ware analyst"
Role (cattribution analyst) renamed to meow-ware analyst.
```

<a id="admin_role_list"></a>

#### List all Roles

The [auth.role.list](userguides/storm_ref_cmd.md#storm-auth-role-list) command lists all roles in the Cortex.

**Example:**

List all roles:

```stormdoc
storm> auth.role.list
Roles:
  a-cat-emic researcher
  all
  cattribution analyst
  meow-ware analyst
```

<a id="admin_role_del"></a>

#### Delete a Role

The [auth.role.del](userguides/storm_ref_cmd.md#storm-auth-role-del) command deletes a role.

**Example:**

Delete the role "meow-ware analyst":

```stormdoc
storm> auth.role.del "meow-ware analyst"
Role (meow-ware analyst) deleted.
```

> [!NOTE]
> Deleting a role has no impact on any users who have been granted the role (other than losing any permissions provided by that role). The user accounts remain intact and the role is simply removed from each user's list of roles.

<a id="admin_grant_roles"></a>

### Grant or Revoke Roles

**Granting** a role to a user allows the user to inherit the role's permissions. **Revoking** a role removes the associated permissions from the user. It is not possible to grant a role to another role (i.e., roles cannot be nested).

Roles can be granted or revoked using the [auth.user.grant](userguides/storm_ref_cmd.md#storm-auth-user-grant) and [auth.user.revoke](userguides/storm_ref_cmd.md#storm-auth-user-revoke) commands.

**Examples:**

Grant the role "cattribution analyst" to the user "ron":

```stormdoc
storm> auth.user.grant ron "cattribution analyst"
Granting role cattribution analyst to user ron.
```

Revoke the role "a-cat-emic researcher" from user "ron":

```stormdoc
storm> auth.user.revoke ron "a-cat-emic researcher"
Revoking role a-cat-emic researcher from user ron.
```

> [!NOTE]
> The order in which roles are granted to a user matters; when determining whether a user has permission to perform an action, the permissions for each of the user's roles are checked in sequence.
>
> Each role granted to a user is added to the **end** of the set of roles **unless** a location (index) for the role is specified. To "reorder" roles, you must either:
>
> - revoke the roles and grant them in the desired order;
> - use the `--index` option to specify the location to insert the role;
> - use [stormprims-auth-user-setRoles](stormtypes_prims.md#stormprims-auth-user-setRoles) to replace the user's roles with a new list of roles; or
> - use the commercial Synapse UI (Optic) to reorder the roles using drag-and drop.
>
> See [Permissions Background](adminguide.md#admin_perms_background) for additional detail on permissions and [Precedence](adminguide.md#admin_bkd_precedence).

<a id="admin_perms"></a>

## Assign and Manage Permissions

Synapse provides a highly flexible system of role-based access control (RBAC). **Rules** are used to assign permissions to users and / or roles, with a defined order of precedence for how permissions are evaluated.

Permissions can be assigned very broadly, such as allowing a user (or role) to create / modify / delete any node. Permissions can also be very fine-grained, restricting users so that they can **only** create specific nodes, set specific properties, create specific edges, or apply specific tags.

<a id="admin_perms_background"></a>

### Permissions Background

Before describing how to assign and manage permissions in Synapse, it is helpful to define some key components of Synapse and the permissions ecosystem.

<a id="admin_bkd_services"></a>

#### Services

Synapse is designed as a modular set of **services.** A service can be thought of as a container used to run an application. **Synapse services** make up the core Synapse architecture, and include the [Cortex](glossary.md#gloss-cortex) (data store), [Axon](glossary.md#gloss-axon) (file storage), and the commercial [Optic](glossary.md#gloss-optic) UI. Services handle user authentication and authorization.

From a Synapse Admin perspective, you will primarily be concerned with managing user accounts and permissions to (and within) the Synapse **Cortex.**

> [!TIP]
> When we talk about "Synapse users" or "permissions to Synapse" we are generally referring to user accounts and roles in a Cortex, and permissions to a Cortex and its associated objects.
>
> Depending on your Synapse deployment, you may need to grant or manage permissions to additional Synapse services. See the sections on [Optic Permissions](adminguide.md#admin_optic_perms) and [Power-Up Permissions](adminguide.md#admin_power_perms) for details.

<a id="admin_bkd_cortex"></a>

#### Cortex

The **Cortex** is Synapse's primary data store. Users and roles are created and managed in the Cortex, and most things for which users will need permissions apply to the Cortex and to the views, layers, and data (nodes, tags, etc.) that reside there.

<a id="admin_bkd_authgate"></a>

#### Auth Gate

An **Auth Gate** (or "gate", informally) is an object within a service (such as a Cortex) that may have its own set of permissions. A [View](glossary.md#gloss-view) and a [Layer](glossary.md#gloss-layer) are both common examples of Auth Gates.

Auth Gates are represented by a 128-bit identifier (iden) that uniquely identifies the Auth Gate object itself. They also have an associated type to specify the kind of Auth Gate object (e.g., "view"). Some Auth Gates also support the use of "user friendly" names, though this is dependent on the type of Auth Gate and has no impact on the underlying iden or associated permissions.

<a id="admin_bkd_scope"></a>

#### Scope

**Scope** refers to the object to which a particular permission applies. For example, permissions granted on an Auth Gate (such as a view) are scoped to (or **local** to) that Auth Gate. Permissions granted at the Cortex level are **global** with respect to the Cortex.

Scope affects the order (precedence) in which permissions are evaluated.

<a id="admin_bkd_permission"></a>

#### Permission

A **permission** is a string that is used to control access. For example:

`view.add`

> [!TIP]
> A list of most permissions available in a Cortex can be found under [Cortex Permissions](adminguide.md#admin_cortex_perms). You can also display the list in Synapse using the `auth.list.perms` command.

Most permission strings use a dotted (hierarchical) format; specifying a permission higher up in the hierarchy includes all permissions below it. For example, the permission `view` includes all of the following permissions: `view.add`, `view.del`, `view.read`, and `view.set`.

Permissions related to objects such as nodes or tags can optionally extend the permission string to be highly specific, referencing particular forms, properties, tags/tag trees, or light edges. This allows you to set highly granular permissions.

Granular permissions may be useful for organizations with specialized users or teams, where certain individuals are responsible for specific types of analysis (e.g., strategic analysis vs. tactical threat tracking) and should be the only users authorized to create, modify, and tag certain types of data.

Granular permissions can also be used to differentiate between senior and junior roles; for example, only senior analysts may be allowed to apply tags representing certain assessments (such as attribution).

**Examples:**

<table>
<colgroup>
<col style="width: 66%" />
<col style="width: 34%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Description</strong></th>
<th><strong>Permission</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><p>Perform <strong>any</strong> action on <strong>any</strong> kind of node</p>
<p>(including deleting nodes and working with properties, tags,</p>
<p>edges, and node data)</p></td>
<td><code>node</code></td>
</tr>
<tr class="even">
<td><p><strong>Add</strong> any kind of node</p>
<p>(but not delete nodes, or work with properties, tags, edges, or</p>
<p>node data)</p></td>
<td><code>node.add</code></td>
</tr>
<tr class="odd">
<td><p><strong>Only</strong> add <code>inet:ip</code> nodes</p>
<p>(but not set properties, or work with tags or edges)</p></td>
<td><code>node.add.inet:ip</code></td>
</tr>
<tr class="even">
<td><p><strong>Only</strong> add (set) the <code>:asn</code> property of <code>inet:ip</code> nodes</p>
<p>(but not create nodes or work with other properties, tags,</p>
<p>edges, etc.)</p></td>
<td><code>node.prop.set.inet:ip:asn</code></td>
</tr>
<tr class="odd">
<td><p>Add or remove <strong>any</strong> tag</p>
<p>(Note that adding/removing tags may require the ability to</p>
<p>create <code>syn:tag</code> nodes, unless those nodes already exist.)</p></td>
<td><code>node.tag</code></td>
</tr>
<tr class="even">
<td><strong>Only</strong> add and remove tags in the "mytag" tag tree</td>
<td><code>node.tag.add.mytag</code> <code>node.tag.del.mytag</code></td>
</tr>
<tr class="odd">
<td><p>Add or remove <strong>any</strong> edge</p>
<p>(Note that adding or removing edges allows creating edges</p>
<p>between <strong>any</strong> nodes; there are no model constraints on the</p>
<p>kinds of nodes that can be joined. It also allows the creation</p>
<p>of new / arbitrarily named edges.)</p></td>
<td><code>node.edge</code></td>
</tr>
<tr class="even">
<td><strong>Only</strong> add edges</td>
<td><code>node.edge.add</code></td>
</tr>
<tr class="odd">
<td><strong>Only</strong> add <code>refs</code> edges</td>
<td><code>node.edge.add.refs</code></td>
</tr>
</tbody>
</table>

> [!NOTE]
> Permissions strings **do not** support wildcards (`*`). For example, you cannot specify `node.tag.*.mytag` to allow users to both add and delete tags in the `mytag` tree.

<a id="admin_bkd_rule"></a>

#### Rule

A **rule** is used to grant (or prohibit) a specific permission. Rules are evaluated in a defined order of precedence.

When you specify a rule, there is an implicit **allow** directive; a permission string by itself indicates the permission is allowed/true:

`view.add`

To use a rule to **deny** a permission, use the "not" or "bang" symbol ( `!` ) to indicate the permission is denied/false:

`!node.tag.add.mytag`

<a id="admin_bkd_precedence"></a>

#### Precedence

**Rules** in Synapse are evaluated in order of **precedence.** A requested action will be allowed (or denied) based on the **first matching rule** found for the action. If no matching rule is found, the action is **denied.**

Generally speaking, rules are evaluated from "most specific" to "least specific". Rules are evaluated in the following order:

- **User** rules at the **local** (i.e., Auth Gate) level.
- **Role** rules at the **local** level.
- **User** rules at the **global** (i.e., Cortex) level.
- **Role** rules at the **global** level.

> [!NOTE]
> Because global rules are evaluated after local rules, permissions granted at the global level can "override" permissions that are not explicitly denied at the local level. For example, a user may fork a view (making them admin of that view) and grant "read" access to a coworker (`view.read`).
>
> If the coworker has "write" permissions (such as `node.tag`) at the **global** level, they will be able to add tags within the forked view (or any view where they have `view.read` permissions).
>
> If the user forking the view also specified `!node` for the view's layer, the coworker would be prevented from adding any tags in the forked view (or making any edits whatsoever).

**Roles** (granted to a user) and **rules** (assigned to a user or role) are **also ordered:**

- When granting roles to a user, each new role is added to the **end** of the list of roles **unless** a location (index) for the role is specified.
- When assigning rules to a role or user, each new rule is added to the **end** of the list of rules **unless** a location (index) for the rule is specified.

Rules and roles are evaluated in the following order:

- **User rules** are evaluated in order from first to last.
- Each **role** granted to a user is evaluated in order from first to last.
- For each role, the **role's rules** are evaluated in order from first to last.

This means that the same rules, applied and evaluated in a different order, will give different results. As a simple example:

These rules will **allow** the creation of `file:bytes` nodes, but no other nodes:

``` text
node.add.file:bytes
!node.add
```

The same rules in the opposite order will **disallow** the creation of **any** nodes:

``` text
!node.add
node.add.file:bytes
```

<a id="admin_bkd_admin"></a>

#### Admin

Admin status allows a user to **bypass all permissions checks** for the **scope** where the user is admin. For example, a Synapse (Cortex) admin user can bypass all Cortex permissions checks (can "do anything" within the Cortex).

Users are generally **admin** of objects that they create. A user who forks a view is **admin** for the view that they fork, and can bypass all permissions checks ("do anything") within the forked view.

> [!NOTE]
> It is not possible to assign **admin** privileges to a role.

<a id="admin_bkd_easyperms"></a>

#### Easy Permissions

Easy permissions ("easy perms" for short) is a mechanism that simplifies granting common sets of permissions to users or roles for a particular object. Where easy perms are used, you can specify four levels of access: **deny, read, edit,** and **admin.** These access levels have corresponding integer values:

- Deny = 0
- Read = 1
- Edit = 2
- Admin = 3

Easy perms apply to specific objects. Where easy perms are available, the following conventions apply:

- The user who creates the object has **admin** privileges for that object.
- **Admin** privileges include the ability to grant permissions to others (including the ability to explicitly deny access).
- Admin privileges are required to **delete** the object (i.e., **edit** permissions do not include **delete**).

> [!TIP]
> [\$lib.macro.grant()](stormtypes_libs.md#stormlibs-lib-macro-grant) library is an example of where easy permissions can be used to assign permissions.

<a id="admin_bkd_views_layers"></a>

#### Views and Layers

Data in a Cortex is stored in one or more **layers** (see [Layer](glossary.md#gloss-layer)). Layers are composed into **views** (see [View](glossary.md#gloss-view)) containing the data that should be visible to users or roles. (A standard installation of Synapse consists of the default view, which contains one layer.)

**Views** define the data that a user or role can **see** - they act as a **read** boundary. Granting the `view.read` permission on a view allows users to see (read) data in any of the view's layers; you do not need to explicitly grant "read" access to the individual layers themselves.

The ability to read data in a view is "all or nothing" - you cannot allow users to see some nodes in a view but not others. (Sensitive data should be stored in its own layer, and views containing that layer should be limited to users or roles with a need to access that data.)

**Layers** define the changes (if any) that a user or role can make to data in Synapse - they act as a **write** boundary. In normal circumstances, only the top layer in a view is writable. The ability to write data **to** a layer is controlled by the various `node.*` permissions, which specify the forms / properties / tags / light edges a user or role can work with (create / modify / delete). Permissions to modify data must be assigned at the appropriate **layer** (or globally, if the permissions apply to all writable layers in the Cortex).

<a id="admin_assign_perms"></a>

### Assign Permissions

You assign (allow or deny) permissions in Synapse by adding rules to (or removing rules from) roles or users. Recall that **order matters** when adding rules (see [Precedence](adminguide.md#admin_bkd_precedence)).

From a Synapse Admin perspective, managing permissions within Synapse commonly involves:

- Assigning rules to users and roles within the Cortex.
- Assigning rules to users and roles for various Auth Gates (such as layers or views) if necessary.
- Assigning rules to users and roles to allow or deny access to additional services, such as various Power-Ups.

Permissions in Synapse are managed using the Storm [auth](userguides/storm_ref_cmd.md#storm-auth) commands.

In the commercial Optic UI, permissions can also be managed through the **Admin Tool** and through dialogs associated with various objects (such as Views or Stories).

> [!TIP]
> If a user attempts an action that they do not have permissions to perform, Synapse will return an `AuthDeny` error that lists the specific permission that is required.

> [!NOTE]
> The descriptions and examples below assume that you have deployed Synapse using native Synapse management and authentication of users, roles, and permissions.

#### Default Permissions

Synapse includes the following default permissions:

- The built-in **root** user has **admin** access (`admin=true`) to the Cortex.
- The built-in **all** role has **read** access (`view.read`) to the **default** view.

Any additional permissions must be **explicitly granted** to users or roles. In all but a few edge cases, Synapse assumes an implicit default `deny all` as the final rule evaluated when checking permissions.

> [!NOTE]
> There are a few edge cases where a specific permission assumes a **default allow** instead of a **default deny,** but these are uncommon. These cases are highly specific, and usually arise in cases where a **new** permission has been implemented. That is, an action that was not originally subject to a permissions check now has one (usually because of a need to explicitly **deny** that action to particular users or roles).
>
> If a previously unchecked action were added with "default deny", it would potentially break existing Synapse deployments by suddenly blocking an action that had been previously allowed (ungated). In these circumstances the new permission is given a "default allow" that can then be specifically denied if necessary.

#### Available Permissions

The [auth.perms.list](userguides/storm_ref_cmd.md#storm-auth-perms-list) command can be used to display the set of permissions available in your Cortex. This includes native Synapse permissions as well as any permissions associated with other packages and services.

Sample output for this command can be seen under [Cortex Permissions](adminguide.md#admin_cortex_perms). The permissions available on your Cortex may vary depending on the services and packages installed (e.g., such as Power-Ups).

#### Global (Cortex) Permissions

Permissions in Synapse can be assigned at the global (Cortex) level, or to a specific Auth Gate (see [Auth Gate Permissions](adminguide.md#admin_authgate_perms)). To assign permissions to an Auth Gate, you must specify its identifier (iden) (i.e., using the `--gate` option to the appropriate Storm command) when adding the associated rule to a user or role.

If you do not specify an Auth Gate, the permissions are **global** and apply to any / all instances within the Cortex where a user or role has access. For example, the following Storm command:

``` text
auth.role.addrule all node
```

...grants (allows) the `node` permission to the built-in **all** role. This allows **any** user (because all users are granted the **all** role by default) to perform **any** action on **any** node in **any** layer that is the topmost (writeable) layer in **any** view that the user can see.

Specifying rules at the global (Cortex) level may be sufficient for many basic Synapse deployments.

> [!NOTE]
> Recall that **order matters** when adding rules:
>
> - by default, each rule is added to the **end** of the list of rules assigned to a user or role; and
> - rules are evaluated in order of precedence.
>
> To reorder rules, you must:
>
> - use the `--index` option with `auth.user.addrule` or `auth.role.addrule` to specify a location to insert a specific rule;
> - remove and re-add the rules in the desired order;
> - use [stormprims-auth-user-setRules](stormtypes_prims.md#stormprims-auth-user-setRules) or [stormprims-auth-role-setRules](stormtypes_prims.md#stormprims-auth-role-setRules) to replace the rules for a user or role with a new set of rules; or
> - use the commercial Synapse UI (Optic) to reorder rules using drag-and-drop.

##### Assign Permissions

Permissions rules (allow or deny) are assigned using the [auth.user.addrule](userguides/storm_ref_cmd.md#storm-auth-user-addrule) and [auth.role.addrule](userguides/storm_ref_cmd.md#storm-auth-role-addrule) commands.

**Examples:**

Prevent the user "ron" from setting tag descriptions (setting the `syn:tag:desc` property):

```stormdoc
storm> auth.user.addrule ron "!node.prop.set.syn:tag:desc"
Added rule !node.prop.set.syn:tag:desc to user ron.
```

> [!TIP]
> Deny rules specified with Storm must be enclosed in quotes (single or double) because they begin with a symbol ( `!` ).

Allow the role "senior analysts" to add tags in threat attribution (`cno.threat`) tag tree:

```stormdoc
storm> auth.role.addrule "senior analysts" node.tag.add.cno.threat
Added rule node.tag.add.cno.threat to role senior analysts.
```

Prevent the "all" role from deleting nodes:

```stormdoc
storm> auth.role.addrule all "!node.del"
Added rule !node.del to role all.
```

Prevent the "all" role from deleting nodes, and insert this as the first rule for the role:

```stormdoc
storm> auth.role.addrule --index 0 all "!node.del"
Added rule !node.del to role all.
```

> [!TIP]
> Recall that you can [Display a User](adminguide.md#admin_user_show) or [Display a Role](adminguide.md#admin_role_show) with the [auth.user.show](userguides/storm_ref_cmd.md#storm-auth-user-show) and [auth.role.show](userguides/storm_ref_cmd.md#storm-auth-role-show) commands.

##### Revoke Permissions

Permissions rules are revoked using the `auth.user.delrule` and `auth.role.delrule` commands.

**Examples:**

Revoke the rule that prevents user "ron" from setting tag descriptions:

```stormdoc
storm> auth.user.delrule ron "!node.prop.set.syn:tag:desc"
Removed rule !node.prop.set.syn:tag:desc from user ron.
```

Revoke the rule that allows "junior analysts" to apply tags in the `cno.threat` tag tree:

```stormdoc
storm> auth.role.delrule "junior analysts" node.tag.cno.threat
Removed rule node.tag.cno.threat from role junior analysts.
```

##### Check Permissions

The [auth.user.allowed](userguides/storm_ref_cmd.md#storm-auth-user-allowed) command can be used to check whether a user has a particular permission (i.e., is allowed to perform the associated operation) for a specific **scope** (i.e., globally or for an individual Auth Gate). If an appropriate `allow` rule exists, the command will show the source (i.e., the rule, role, and / or associated Auth Gate) where the permission has been assigned.

> [!TIP]
> - A user may have permissions locally (e.g., to a specific Auth Gate) that they do not have globally. In other words a **global** check may (correctly) show that a user does **not** have an expected permission globally, but the permission will show as "allowed" when the appropriate Auth Gate is checked.
> - If no rule matches, the command reports the permission's registered default (see [Default Permissions](#default-permissions)) rather than assuming a deny. This is the same value Synapse uses when enforcing the permission, so the command's answer always agrees with enforcement.
> - When checking whether a user can see (read) data or manipulate (e.g., fork) a view, check the relevant **view.**
> - When checking whether a user can modify (write or delete) data, check the relevant **layer.**

**Examples:**

Check whether user 'ron' is allowed to apply tags in the `cno` tag tree **globally:**

```stormdoc
storm> auth.user.allowed ron node.tag.add.cno
allowed: true - Matched role rule (node.tag.add.cno) for role cattribution analyst.
```

Check whether user 'ron' is allowed to apply tags in the `cno` tag tree in the **current layer:**

```stormdoc
storm> auth.user.allowed --gate $lib.layer.get().iden ron node.tag.add.cno
allowed: true - Matched role rule (node.tag.add.cno) for role cattribution analyst.
```

**Note** that the response for each of the commands above is identical, even though the first example performed a global check (no `--gate` option) while the second example checked the current layer (retrieved with `$lib.layer.get()`). The response in the second example shows that Ron can apply tags in the current layer because he has **global** permissions for this action - indicated by the **absence** of an iden in the response. If Ron's permissions were restricted to the queried gate (in this case, the layer), the associated iden would have been included in the command output.

Check whether user 'ron' is allowed to fork the **current view:**

```stormdoc
storm> auth.user.allowed --gate $lib.view.get().iden ron view.add
allowed: false - No matching rule found. (default: false)
```

<a id="admin_authgate_perms"></a>

#### Auth Gate Permissions

To assign permissions for an Auth Gate, you use the same Storm commands used to assign global permissions, but you must specify the Auth Gate's full identifier (iden) (using the `--gate` option) when adding or removing the rule.

##### Obtain a Gate's Iden

The Storm [view](userguides/storm_ref_cmd.md#storm-view) and [layer](userguides/storm_ref_cmd.md#storm-layer) commands can be used to manage views and layers, respectively. In particular, the following commands are useful for displaying all views or layers (including their idens), or displaying a specific view or layer:

- [view.list](userguides/storm_ref_cmd.md#storm-view-list)
- [view.get](userguides/storm_ref_cmd.md#storm-view-get)
- [layer.list](userguides/storm_ref_cmd.md#storm-layer-list)
- [layer.get](userguides/storm_ref_cmd.md#storm-layer-get)

**Examples:**

Display all views:

```stormdoc
storm> view.list

View: 79a398abf2e614071e8edee3c0c44943 (name: default)
  Creator: 5634a58d79099b36c85d387eb735b705
  Layers:
    542d3436052ecc7626c59135bc9d7e04: default readonly: False

```

Display the current layer:

```stormdoc
storm> layer.get
Layer: 542d3436052ecc7626c59135bc9d7e04 (name: default) readonly: False creator: 5634a58d79099b36c85d387eb735b705
```

##### View a Gate's Permissions

The `auth.gate.show` command is used to display permissions information about a particular Auth Gate (e.g., a view or layer). You can provide the specific iden for an Auth Gate, or use the syntax below to retrieve information for the **current** view or layer. (Viewing information for the "current layer" will return information for the top layer of the current view.)

**Example:**

Display information for the current view:

```stormdoc
storm> auth.gate.show $lib.view.get().iden
Gate Type: view

Auth Gate Users:
  5634a58d79099b36c85d387eb735b705 - root
    Admin: true
    Rules:

Auth Gate Roles:
  5ff63f33765828350fa00e6c684d79cc - all
    Rules:
      [0  ] - view.read
```

Display information for the current layer (i.e., the top layer of the current view):

```stormdoc
storm> auth.gate.show $lib.layer.get().iden
Gate Type: layer

Auth Gate Users:
  5634a58d79099b36c85d387eb735b705 - root
    Admin: true
    Rules:

Auth Gate Roles:
```

<a id="admin_perms_best"></a>

### Permissions Best Practices

- Synapse Admins should use a designated admin account for administrative tasks and a separate account for their user tasks.
- Where possible, assign permissions to roles and grant roles to users vs. assigning permissions to users directly.
- Create a general purpose role (such as `users`, or use the built-in `all` role) and assign the basic permissions that **all** Synapse users should have to this role. This includes "things all users should be able to do" (allow rules) as well as "things all users should be **explicitly** prohibited from doing" (deny rules). Create additional roles as needed to allow (or further restrict) specific operations.
- Segregate data with different access requirements into different **layers.** Grant access to data sets by composing those layers into **views** and granting roles access to the appropriate view(s).
- The ability to **delete nodes** in Synapse should be granted to a limited number of trusted individuals. We recommend creating a dedicated role for this purpose.
- If a role will have **limited permissions,** it is generally easier to **explicitly allow** only those actions; everything else will be denied by default.
- If a role or user will have **broad permissions** with some restrictions, it is generally easier to **explicitly deny** the restricted actions first, and then **grant** broad permissions (for example `!node.del` followed by `node`). Because permissions rules are checked in order, Synapse will encounter any deny rules first (i.e., user is unable to delete nodes), blocking the prohibited action while then allowing anything not specifically denied (i.e., user can do anything else to nodes).

<a id="admin_sample_perms"></a>

### Example Permissions

The examples below illustrate a few common use cases for roles and permissions within Synapse. These rule sets are meant as simple illustrations and do not necessarily illustrate fully-defined, production-ready permission sets.

Recall that:

- Views control **read** access to the data store. Users with read access to a view (`view.read`) can read all data in all layers of the view (i.e., no additional layer-specific permissions are required for read access).
- Layers control **write** access to the data store. Use permissions to manage the data that can be written to a given layer (including the ability to merge data into that layer from a forked view).
- A user who can fork a view is **admin** within their forked view.

A list of available Cortex permissions is available under the [Cortex Permissions](adminguide.md#admin_cortex_perms) section, or can be viewed in Synapse with the `auth.perms.list` command.

<a id="perms_case1"></a>

#### Case 1 - Grant common permissions - basic

These basic permissions can be assigned to a role to allow users to perform common operations in Synapse.

<table>
<colgroup>
<col style="width: 27%" />
<col style="width: 73%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Permission</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><code>view.read</code></td>
<td>See / read any view</td>
</tr>
<tr class="even">
<td><code>view.add</code></td>
<td>Fork any view they can see</td>
</tr>
<tr class="odd">
<td><code>node</code></td>
<td><p>Create, modify, or delete any type of data (nodes, properties, light</p>
<p>edges, tags, and node data) in the top layer of any view they can see</p></td>
</tr>
</tbody>
</table>

**Tips:**

- The `all` role has implicit (and non-revocable) "read" access to Synapse's **default** view. This is not the same as global `view.read` access. To allow the `all` role (or any role) to see other views, you must explicitly assign the `view.read` permission (either globally or to individual views).
- Users can only fork (`view.add`) views they can see (`view.read`). If users should be allowed to fork any view where they have read access, the `view.add` permission can be assigned **globally** even if read access is managed on a **per-view** basis.

<a id="perms_case2"></a>

#### Case 2 - Grant common permissions - intermediate

These permissions expand on Case 1, but only allow the role to see **specific** views (by granting `view.read` locally to individual views).

Any **global** permissions (e.g., `node.add`) will apply to the top (writeable) layer of **any** view the role can see, unless the permissions are overridden locally.

These permissions also prevent the role from **deleting nodes** globally, while allowing them to delete properties or edges and to remove tags.

<table style="width:99%;">
<colgroup>
<col style="width: 19%" />
<col style="width: 13%" />
<col style="width: 65%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Permission</strong></th>
<th><strong>Scope</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><code>view.add</code></td>
<td>global</td>
<td>Fork any view they can see (based on <code>view.read</code>)</td>
</tr>
<tr class="even">
<td><code>!node.del</code></td>
<td>global</td>
<td>Prevent deletion of any nodes</td>
</tr>
<tr class="odd">
<td><code>node.add</code></td>
<td>global</td>
<td>Create nodes in the top layer of any view they can see</td>
</tr>
<tr class="even">
<td><code>node.prop</code></td>
<td>global</td>
<td><p>Set, modify, or delete node properties in the top layer of any</p>
<p>view they can see</p></td>
</tr>
<tr class="odd">
<td><code>node.edge</code></td>
<td>global</td>
<td><p>Add or remove light edges in the top layer of any view they</p>
<p>can see</p></td>
</tr>
<tr class="even">
<td><code>node.tag</code></td>
<td>global</td>
<td><p>Add or remove tags from nodes in the top layer of any view they</p>
<p>can see</p></td>
</tr>
<tr class="odd">
<td><code>view.read</code></td>
<td>local</td>
<td><p>See all the data in all the layers of the specific view(s)</p>
<p>where the rule is assigned</p></td>
</tr>
</tbody>
</table>

<a id="perms_case3"></a>

#### Case 3 - Create a dedicated role that can delete nodes

Deleting nodes indiscriminately or incorrectly can negatively impact your data store (i.e., leaving "holes" in the graph or destroying data). Synapse requires that users run an explicit command ([delnode](userguides/storm_ref_cmd.md#storm-delnode)) to delete nodes, so the action is a deliberate choice (vs. an "accidental click").

We strongly recommend that you create a role whose sole permission is the ability to delete nodes, and grant that role to a limited number of users. To do this:

- **Explicitly deny** permission to delete nodes (`!node.del`) at the **global** level to the general purpose role you use to manage permissions for all users (as shown in Case 2 above).
- Create a dedicated role whose only permission will be the ability to delete nodes.
  - We encourage a name that inspires caution, such as `fire ze missiles` or `agents of destruction`, but you can just use `deleters`.
- Assign the `node.del` rule to the role (globally, or for specific layers).

**Tips:**

- All delete operations (whether deleting nodes, properties, edges, or removing tags) must be performed directly in the layer where the data resides. As admin of any view that they fork, "normal" users can delete data created or modified **within** their forked view.

<a id="perms_case4"></a>

#### Case 4 - Place guardrails around writing (creating or merging) data

Permissions can be used to prevent roles from:

- creating various types of data directly in a layer/view; or
- merging various types of data into an underlying view (technically, to the view's top layer).

These types of permissions can help ensure that data in a "production" layer remains as pristine and error-free as possible. For example:

- Help to limit typos that result in "bad" tags or edges.
- Prevent data from a sensitive or restricted layer from being written to a non-restricted layer.

Example use cases:

- Use permissions around light edges to only allow the creation of specific named edges. This can limit typos in edge names and/or prevent users from creating arbitrarily named edges.
- Use permissions around tags or tag trees to only allow applying certain tags (e.g., to enforce your organization's tag conventions). For example, permissions can ensure that users' "scratch" tags (`#thesilence.mywork`) or tags indicating sensitive data (`#tlp.red`) are not added to "production" data.
- Use permissions around individual properties to prohibit setting specific properties in particular layers. For example, taxonomy properties (such as `risk:threat:type`) may be "under development" in an internal analysis view while users test and agree on appropriate categories. You may want to prevent this property from being set (merged) into production data until the taxonomy is finalized.

> [!TIP]
> The degree to which you enforce data and tag conventions through permissions vs. by consensus (i.e., users agree on "best efforts" to keep the data tidy) will depend on your organization and your use case. Managing permissions adds overhead, but may be worth the effort for data sets that require high fidelity or quality. The overhead may have less benefit for internal data or test data where occasional errors have minimal impact and can be "cleaned up" as needed.

The sample rules below can be applied **globally** (a user with this role can write "approved" data to any writeable layer of any view they can see) or **locally** to specific layers.

The examples below **only** illustrate how certain write actions can be restricted and do not address other permissions that a user/role might need. These permissions could be added to an existing role (such as your general `users` role), or granted via their own role.

**Example 1:**

If a limited set of actions are allowed, simply specify the changes that the role can make. Anything else is implicitly denied by default.

In this example, a role with the following permissions can:

- **only** add and remove tags in the listed tag trees; and
- **only** create and delete the listed edges.

<table>
<colgroup>
<col style="width: 28%" />
<col style="width: 71%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Permission</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><code>node.tag.add.cno</code></td>
<td><p>Add / apply tags in the <code>cno</code> tree (e.g., <code>cno</code>, <code>cno.mal</code>,</p>
<p><code>cno.mal.plugx</code> etc.)</p></td>
</tr>
<tr class="even">
<td><code>node.tag.del.cno</code></td>
<td>Remove any tags in the <code>cno</code> tree</td>
</tr>
<tr class="odd">
<td><code>node.tag.add.rep</code></td>
<td>Add / apply any tags in the <code>rep</code> tree</td>
</tr>
<tr class="even">
<td><code>node.tag.del.rep</code></td>
<td>Remove any tags in the <code>rep</code> tree</td>
</tr>
<tr class="odd">
<td><code>node.edge.add.refs</code></td>
<td>Add <code>refs</code> light edges</td>
</tr>
<tr class="even">
<td><code>node.edge.del.refs</code></td>
<td>Delete <code>refs</code> light edges</td>
</tr>
<tr class="odd">
<td><code>node.edge.add.uses</code></td>
<td>Add <code>uses</code> light edges</td>
</tr>
<tr class="even">
<td><code>node.edge.del.uses</code></td>
<td>Delete <code>uses</code> light edges</td>
</tr>
<tr class="odd">
<td><code>node.edge.add.targets</code></td>
<td>Add <code>targets</code> light edges</td>
</tr>
<tr class="even">
<td><code>node.edge.del.targets</code></td>
<td>Delete <code>targets</code> light edges</td>
</tr>
</tbody>
</table>

**Example 2:**

If specific actions are prohibited, **deny** those changes and then **allow** "everything else".

A role with the following permissions is **prohibited** from:

- Creating `risk:threat:type:taxonomy` nodes (representing "categories" of threats).
- Setting the `:type` property for `risk:threat` nodes (e.g., specifying the taxonomy category for a particular threat).
- Creating tags in the `tlp` tree.

Note that the permissions as listed only prohibit actions. For a role with these permissions to be able to make other changes (e.g., add other nodes or edges), those permissions need to be granted after these "deny" rules, or as part of another role.

<table>
<colgroup>
<col style="width: 42%" />
<col style="width: 57%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Permission</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><code>!node.add.risk:threat:type:taxonomy</code></td>
<td>Prevent creating these nodes</td>
</tr>
<tr class="even">
<td><code>!node.prop.set.risk:threat:type</code></td>
<td><p>Prevent setting this property (i.e., on existing</p>
<p><code>risk:threat</code> nodes)</p></td>
</tr>
<tr class="odd">
<td><code>!node.tag.add.tlp</code></td>
<td>Prevent applying tags in the <code>tlp</code> tree</td>
</tr>
</tbody>
</table>

> [!TIP]
> To prevent users or roles from making **any** changes to a particular view (i.e., users cannot merge any data into the view / write any data directly to the view's topmost layer):
>
> - Do not add `node` permissions to the view's topmost layer (write permissions that are not granted are implicitly denied).
> - If a role has been granted `node` (or similar) permissions **globally,** override this by explicitly denying (`!node`) the permission on the layer you want to protect.

<a id="perms_case5"></a>

#### Case 5 - Senior vs. junior roles

Senior roles (with more permissions) and junior roles (with limited permissions) are used in a variety of situations, such as new trainees vs. experienced users or junior vs. senior analysts.

When using a "fork and merge" workflow, a junior user can "do anything" (as **admin**) in a view that they fork. This allows them to enrich data and annotate their assessments using tags. But permissions can prevent them from merging some (or all) data and tags until a senior user has reviewed the changes. The senior role (with appropriate permissions) can then merge the data on the junior user's behalf.

For example, tags representing key analytical assessments - such as determining if a file or indicator is associated with a malware family, or tags representing threat clustering and attribution - may require careful consideration. The ability to merge these tags may be limited to senior analysts who can verify that the junior analyst has applied them correctly.

These types of permissions are typically **cumulative;** generic users may be prohibited (or simply not allowed) to perform a certain action, with additional permissions granted to increasingly senior or experienced roles. In the example below, all users would have the general `users` role and analysts would be granted **each** additional role as they gained experience.

**Example:**

<table style="width:99%;">
<colgroup>
<col style="width: 21%" />
<col style="width: 29%" />
<col style="width: 48%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Role</strong></th>
<th><strong>Permission(s)</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>users</strong></td>
<td><p><code>!node.tag.cno</code></p>
<p><code>!node.tag.rep</code></p>
<p><code>node.tag</code></p></td>
<td><p>Prevent applying tags in the <code>cno</code> and</p>
<p><code>rep</code> trees (representing specific analytical</p>
<p>assessements) but apply other tags</p></td>
</tr>
<tr class="even">
<td><strong>novice analyst</strong></td>
<td><code>node.tag.add.rep</code></td>
<td><p>Novices can apply tags in the <code>rep</code> tree</p>
<p>(representing third-party reporting)</p></td>
</tr>
<tr class="odd">
<td><strong>junior analyst</strong></td>
<td><code>node.tag.add.cno.infra</code></td>
<td><p>Junior analysts can apply tags in the</p>
<p><code>cno.infra</code> tree (related to network</p>
<p>infrastructure)</p></td>
</tr>
<tr class="even">
<td><strong>senior analyst</strong></td>
<td><p><code>node.tag.add.cno.threat</code></p>
<p><code>node.tag.add.cno.mal</code></p></td>
<td><p>Senior analysts can apply tags in the</p>
<p><code>cno.threat</code> and <code>cno.mal</code> trees</p>
<p>(assessments related to threat clusters and</p>
<p>malware families)</p></td>
</tr>
</tbody>
</table>

> [!NOTE]
> Because of [Precedence](adminguide.md#admin_bkd_precedence), as additional roles are granted, they would need to be added (indexed) **before** the `users` role to prevent that role's explicit deny permissions from overriding the newly allowed tag privileges.

<a id="perms_case6"></a>

#### Case 6 - Specialized roles

For organizations with diverse analysis teams (e.g., where analysts specialize in particular areas) or organizations where multiple teams or departments use Synapse for different purposes, it may be helpful to create highly specialized roles.

**Examples:**

- An organization with a dedicated malware analysis team may **only** allow those specialists to apply tags related to malware/code families and malware ecosystems.
- An organization's strategic analysts may be solely responsible for certain objects and related data. For example, a strategic team may be in charge of researching and creating organizations (`ou:org`) and associated industries (`ind:industry`) in order to track victimology. Strategic analysts can ensure that these objects are created according to the team's standards and that organizations are assigned to the appropriate industries.

**Malware analyst example:**

- We assume the ability to apply the specialized tags listed below is either **not granted** or **explicitly denied** elsewhere/to other roles.
- Malware analysts can also be granted the ability to **remove** the tags listed below with the corresponding `node.tag.del` permissions.

<table>
<colgroup>
<col style="width: 28%" />
<col style="width: 71%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Permission</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><code>node.tag.add.cno.code</code></td>
<td><p>Apply <code>cno.code</code> tags (designating specific samples of code</p>
<p>families - e.g., <code>cno.code.plugx</code>)</p></td>
</tr>
<tr class="even">
<td><code>node.tag.add.cno.mal</code></td>
<td><p>Apply <code>cno.mal</code> tags (designating components of malware / code</p>
<p>family ecosystems, such as related droppers or C2 - e.g.,</p>
<p><code>cno.mal.plugx</code>)</p></td>
</tr>
<tr class="odd">
<td><code>node.tag.add.cno.rel</code></td>
<td><p>Apply <code>cno.rel</code> tags (designating components that may be observed</p>
<p>as part of a malware ecosystem but are not inherently malicious -</p>
<p>e.g., <code>cno.rel.plugx</code>)</p></td>
</tr>
</tbody>
</table>

**Strategic analyst example:**

- We assume the ability to create these nodes / set these properties is either **not granted** or **explicitly denied** elsewhere/to other roles.
- Strategic analysts can optionally be granted the ability to delete relevant nodes/properties with the corresponding `node.del` or `node.prop.del` permissions.
- Depending on how you assign permissions, keep in mind that roles that cannot **create** nodes may still be able to **set or modify properties** on the node as long as the node already exists. This ability can be restricted via additional `node.prop.set` rules if necessary.

| **Permission**                    | **Description**                                |
|-----------------------------------|------------------------------------------------|
| `node.add.ou:org`                 | Create organization nodes                      |
| `node.prop.set.ou:org:industries` | Assign organizations to one or more industries |
| `node.add.ind:industry`           | Create industry nodes                          |

<a id="admin_cortex_perms"></a>

### Cortex Permissions

The following is a list of the Cortex permissions that may be granted to a user or role. If a gate other than `cortex` is specified, the permission will be checked against the specific gate instance and if no match is found, it will be checked against the global rules.

```stormdoc
storm> auth.perms.list
auth
    Controls all auth permissions.
    gate: cortex
    default: false

auth.role
    Controls all auth role permissions.
    gate: cortex
    default: false

auth.role.add
    Controls adding a role.
    gate: cortex
    default: false

auth.role.add
    Controls the ability to add a role to the system. USE WITH CAUTION!
    gate: cortex
    default: false

auth.role.del
    Controls deleting a role.
    gate: cortex
    default: false

auth.role.del
    Controls the ability to remove a role from the system. USE WITH CAUTION!
    gate: cortex
    default: false

auth.role.set
    Controls setting any auth role property.
    gate: cortex
    default: false

auth.role.set.name
    Permits a user to change the name of a role.
    gate: cortex
    default: false

auth.role.set.rules
    Permits a user to modify rules of a role.
    gate: cortex
    default: false

auth.self
    Controls all auth self permissions.
    gate: cortex
    default: false

auth.self.set
    Controls setting any auth self property.
    gate: cortex
    default: false

auth.self.set.apikey
    Permits a user to manage their API keys.
    gate: cortex
    default: true

auth.self.set.email
    Permits a user to change their own email address.
    gate: cortex
    default: true

auth.self.set.name
    Permits a user to change their own username.
    gate: cortex
    default: true

auth.self.set.passwd
    Permits a user to change their own password.
    gate: cortex
    default: true

auth.user
    Controls all auth user permissions.
    gate: cortex
    default: false

auth.user.add
    Controls adding a user.
    gate: cortex
    default: false

auth.user.add
    Controls the ability to add a user to the system. USE WITH CAUTION!
    gate: cortex
    default: false

auth.user.del
    Controls deleting a user.
    gate: cortex
    default: false

auth.user.del
    Controls the ability to remove a user from the system. USE WITH CAUTION!
    gate: cortex
    default: false

auth.user.get
    Controls all auth user get permissions.
    gate: cortex
    default: false

auth.user.grant
    Controls granting roles to a user.
    gate: cortex
    default: false

auth.user.json.del
    Permits a user to remove another user's JSON storage.
    gate: cortex
    default: false
    example: auth.user.json.del

auth.user.json.get
    Permits a user to retrieve another user's JSON storage.
    gate: cortex
    default: false
    example: auth.user.json.get

auth.user.json.set
    Permits a user to set another user's JSON storage.
    gate: cortex
    default: false
    example: auth.user.json.set

auth.user.pop
    Controls all auth user pop permissions.
    gate: cortex
    default: false

auth.user.profile.del.<varname>
    Permits a user to remove profile information.
    gate: cortex
    default: false
    example: auth.user.profile.del.fullname

auth.user.profile.get.<varname>
    Permits a user to retrieve their profile information.
    gate: cortex
    default: false
    example: auth.user.profile.get.fullname

auth.user.profile.set.<varname>
    Permits a user to set profile information.
    gate: cortex
    default: false
    example: auth.user.profile.set.fullname

auth.user.revoke
    Controls revoking roles from a user.
    gate: cortex
    default: false

auth.user.set
    Controls setting any auth user property.
    gate: cortex
    default: false

auth.user.set.admin
    Controls setting/removing a user's admin status.
    gate: cortex
    default: false

auth.user.set.apikey
    Permits a user to manage API keys for other users. USE WITH CAUTION!
    gate: cortex
    default: false

auth.user.set.archived
    Controls archiving/unarchiving a user account.
    gate: cortex
    default: false

auth.user.set.email
    Controls changing a user's email address.
    gate: cortex
    default: false

auth.user.set.locked
    Controls locking/unlocking a user account.
    gate: cortex
    default: false

auth.user.set.passwd
    Controls changing a user password.
    gate: cortex
    default: false

auth.user.set.rules
    Controls adding rules to a user.
    gate: cortex
    default: false

axon
    Controls all Axon permissions.
    gate: cortex
    default: false

axon.del
    Controls the ability to remove a file from the Axon.
    gate: cortex
    default: false

axon.get
    Controls the ability to retrieve a file from the Axon.
    gate: cortex
    default: false

axon.has
    Controls the ability to check if the Axon contains a file.
    gate: cortex
    default: false

axon.upload
    Controls the ability to upload a file to the Axon.
    gate: cortex
    default: false

cron
    Controls all cron permissions.
    gate: cortex
    default: false

cron.add
    Permits a user to create a cron job.
    gate: view
    default: false

cron.del
    Permits a user to remove a cron job.
    gate: cronjob
    default: false

cron.get
    Permits a user to list cron jobs.
    gate: cronjob
    default: false

cron.kill
    Controls the ability to terminate a running cron job.
    gate: cronjob
    default: false

cron.set
    Permits a user to modify/move a cron job.
    gate: cronjob
    default: false

cron.set.user
    Permits a user to modify the user property of a cron job.
    gate: cortex
    default: false

globals
    Used to control all operations for global variables.
    gate: cortex
    default: false

globals.del
    Used to control delete access to all global variables.
    gate: cortex
    default: false

globals.del.<varname>
    Used to control delete access to a specific global variable.
    gate: cortex
    default: false

globals.get
    Used to control read access to all global variables.
    gate: cortex
    default: false

globals.get.<varname>
    Used to control read access to a specific global variable.
    gate: cortex
    default: false

globals.set
    Used to control edit access to all global variables.
    gate: cortex
    default: false

globals.set.<varname>
    Used to control edit access to a specific global variable.
    gate: cortex
    default: false

httpapi.add
    Controls the ability to add a new Extended HTTP API on the Cortex.
    gate: cortex
    default: false

httpapi.del
    Controls the ability to delete an Extended HTTP API on the Cortex.
    gate: cortex
    default: false

httpapi.get
    Controls the ability to get or list Extended HTTP APIs on the Cortex.
    gate: cortex
    default: false

httpapi.set
    Controls the ability to modify an Extended HTTP API on the Cortex.
    gate: cortex
    default: false

inet.http.proxy
    Permits a user to specify the proxy used with `$lib.inet.http` APIs.
    gate: cortex
    default: false

inet.imap.connect
    Controls connecting to external servers via imap.
    gate: cortex
    default: false

inet.smtp.send
    Controls sending SMTP messages to external servers.
    gate: cortex
    default: false

layer
    Controls all layer permissions.
    gate: cortex
    default: false

layer.add
    Controls the ability to add Layers to the cortex.
    gate: cortex
    default: false

layer.del
    Controls the ability to delete a Layer.
    gate: layer
    default: false

layer.set
    Controls setting any layer property.
    gate: layer
    default: false

layer.set.desc
    Controls the ability set a layer description.
    gate: layer
    default: false

layer.set.name
    Controls the ability set a layer name.
    gate: layer
    default: false

layer.set.readonly
    Controls the ability set a layer readonly.
    gate: layer
    default: false

layer.write
    Controls the ability to write to a Layer.
    gate: layer
    default: false

log.debug
    Controls the ability to log a debug level message.
    gate: cortex
    default: false

log.error
    Controls the ability to log a error level message.
    gate: cortex
    default: false

log.info
    Controls the ability to log a info level message.
    gate: cortex
    default: false

log.warning
    Controls the ability to log a warning level message.
    gate: cortex
    default: false

macro
    Controls all Storm macro permissions.
    gate: cortex
    default: false

macro.add
    Controls access to add a storm macro.
    gate: cortex
    default: true

macro.admin
    Controls access to edit/set/delete a storm macro.
    gate: cortex
    default: false

macro.edit
    Controls access to edit a storm macro.
    gate: cortex
    default: false

model.admin
    Controls the ability to modify the extended data model.
    gate: cortex
    default: false

node
    Controls all node edits in a layer.
    gate: layer
    default: false

node.add
    Controls adding any form of node in a layer.
    gate: layer
    default: false

node.add.<form>
    Controls adding a specific form of node in a layer.
    gate: layer
    default: false
    example: node.add.inet:ipv4

node.data
    Controls all node data permissions in a layer.
    gate: layer
    default: false

node.data.del
    Permits a user to remove node data in a given layer.
    gate: layer
    default: false

node.data.del.<varname>
    Permits a user to remove node data in a given layer for a specific key.
    gate: layer
    default: false
    example: node.data.del.hehe

node.data.set
    Permits a user to set node data in a given layer.
    gate: layer
    default: false

node.data.set.<varname>
    Permits a user to set node data in a given layer for a specific key.
    gate: layer
    default: false
    example: node.data.set.hehe

node.del
    Controls removing any form of node in a layer.
    gate: layer
    default: false

node.del.<form>
    Controls removing a specific form of node in a layer.
    gate: layer
    default: false

node.edge
    Controls all node edge permissions in a layer.
    gate: layer
    default: false

node.edge.add
    Controls adding light edges to a node.
    gate: layer
    default: false

node.edge.add.<verb>
    Controls adding a specific light edge to a node.
    gate: layer
    default: false

node.edge.del
    Controls adding light edges to a node.
    gate: layer
    default: false

node.edge.del.<verb>
    Controls adding a specific light edge to a node.
    gate: layer
    default: false

node.prop
    Controls editing any prop on any node in the layer.
    gate: layer
    default: false

node.prop.del
    Controls removing any prop on any node in a layer.
    gate: layer
    default: false

node.prop.del.<form>
    Controls removing any property from a form of node in a layer.
    gate: layer
    default: false
    example: node.prop.del.inet:ipv4

node.prop.del.<form>.<prop>
    Controls removing a specific property from a form of node in a layer.
    gate: layer
    default: false
    example: node.prop.del.inet:ipv4.asn

node.prop.set
    Controls setting any prop on any node in a layer.
    gate: layer
    default: false

node.prop.set.<form>
    Controls setting any property on a form of node in a layer.
    gate: layer
    default: false
    example: node.prop.set.inet:ipv4

node.prop.set.<form>.<prop>
    Controls setting a specific property on a form of node in a layer.
    gate: layer
    default: false
    example: node.prop.set.inet:ipv4.asn

node.tag
    Controls editing any tag on any node in a layer.
    gate: layer
    default: false

node.tag.add
    Controls adding any tag on any node in a layer.
    gate: layer
    default: false

node.tag.add.<tag>
    Controls adding a specific tag on any node in a layer.
    gate: layer
    default: false
    example: node.tag.add.cno.mal.redtree

node.tag.del
    Controls removing any tag on any node in a layer.
    gate: layer
    default: false

node.tag.del.<tag>
    Controls removing a specific tag on any node in a layer.
    gate: layer
    default: false
    example: node.tag.del.cno.mal.redtree

pkg
    Controls all package permissions.
    gate: cortex
    default: false

pkg.add
    Controls access to adding storm packages.
    gate: cortex
    default: false

pkg.del
    Controls access to deleting storm packages.
    gate: cortex
    default: false

power-ups.<power-up>.admin
    Controls the ability to interact with the vars, state, or Queues for a Storm Package by name.
    gate: cortex
    default: false

queue
    Controls all queue permissions.
    gate: cortex
    default: false

queue.add
    Permits a user to create a Queue.
    gate: cortex
    default: false

queue.del
    Permits a user to delete a Queue.
    gate: queue
    default: false

queue.get
    Permits a user to access a Queue. This allows the user to read from the Queue and remove items from it.
    gate: queue
    default: false

queue.put
    Permits a user to put items into a Queue.
    gate: queue
    default: false

service
    Controls all service permissions.
    gate: cortex
    default: false

service.add
    Controls the ability to add a Storm Service to the Cortex.
    gate: cortex
    default: false

service.del
    Controls the ability to delete a Storm Service from the Cortex
    gate: cortex
    default: false

service.get
    Controls the ability to get the Service object for any Storm Service.
    gate: cortex
    default: false

service.list
    Controls the ability to list all available Storm Services and their service definitions.
    gate: cortex
    default: false

storm
    Controls all Storm permissions.
    gate: cortex
    default: false

storm.graph
    Controls all Storm graph permissions.
    gate: cortex
    default: false

storm.graph.add
    Controls access to add a storm graph.
    gate: cortex
    default: true

storm.lib.stix.export.maxsize
    Controls the ability to specify a STIX export bundle maxsize of greater than 10,000.
    gate: cortex
    default: false

storm.sudo
    Allows the user to run Storm as a global admin. This allows the user to bypass all permission checks.
    gate: cortex
    default: false

task
    Controls all task permissions.
    gate: cortex
    default: false

task.del
    Permits a user to kill tasks owned by other users.
    gate: cortex
    default: false

task.get
    Permits a user to view tasks owned by other users.
    gate: cortex
    default: false

telepath.open
    Controls the ability to open a telepath URL. USE WITH CAUTION.
    gate: cortex
    default: false

trigger
    Controls all trigger permissions.
    gate: cortex
    default: false

trigger.add
    Controls adding triggers.
    gate: view
    default: false

trigger.del
    Controls deleting a trigger.
    gate: trigger
    default: false

trigger.get
    Controls listing/retrieving triggers.
    gate: trigger
    default: false

trigger.set
    Controls modifying any user editable property of a trigger.
    gate: trigger
    default: false

trigger.set.async
    Controls modifying the async property of a trigger.
    gate: trigger
    default: false

trigger.set.doc
    Controls modifying the doc property of a trigger.
    gate: trigger
    default: false

trigger.set.enabled
    Controls modifying the enabled property of a trigger.
    gate: trigger
    default: false

trigger.set.name
    Controls modifying the name property of a trigger.
    gate: trigger
    default: false

trigger.set.storm
    Controls modifying the storm property of a trigger.
    gate: trigger
    default: false

trigger.set.user
    Controls modifying the user property of any trigger.
    gate: cortex
    default: false

vertex.packages.install
    Permits a user to install packages from the Vertex Hub.
    gate: cortex
    default: false

vertex.packages.list
    Permits a user to list packages available from the Vertex Hub.
    gate: cortex
    default: false

vertex.register
    Permits a user to register the deployment with the Vertex Hub.
    gate: cortex
    default: false

view
    Controls all view permissions.
    gate: cortex
    default: false

view.add
    Controls access to add a new view including forks.
    gate: cortex
    default: false

view.del
    Controls access to delete a view.
    gate: view
    default: false

view.fork
    Controls access to fork a view.
    gate: view
    default: false

view.read
    Controls read access to view.
    gate: view
    default: false

view.set
    Controls setting any view property.
    gate: view
    default: false

view.set.desc
    Controls access to set a view description.
    gate: view
    default: false

view.set.name
    Controls access to set a view name.
    gate: view
    default: false

view.set.parent
    Controls access to set a view parent view.
    gate: view
    default: false

view.set.protected
    Controls access to set a view protected status.
    gate: view
    default: false

view.set.quorum
    Controls access to set a view quorum status.
    gate: view
    default: false

```

<a id="admin_optic_perms"></a>

### Optic Permissions

Commercial Synapse customers with the Optic UI may need to explicitly grant users or roles permission to some UI tools (such as Spotlight).

- See the [Optic Deployment Guide](/docs/synapse-enterprise-optic/latest/user_interface/deploymentguide.md) for information on Optic deployment.
- See the [Optic DevOps Guide](/docs/synapse-enterprise-optic/latest/user_interface/devopsguide.md) for information on Optic permissions and other features.

> [!TIP]
> You do not need to explicitly grant permissions to Optic itself. If you are creating and managing Synapse ("Cortex") users and roles via Optic, they have permission to access Optic by default.

<a id="admin_power_perms"></a>

### Power-Up Permissions

Synapse **Power-Ups** have their own sets of permissions that must be granted to users or roles to allow them to use the Power-Up and any associated Storm commands. Specific permissions are documented in the **Admin Guide** section of the [Power-Up documentation](power_ups.md) for the individual Power-Up.

> [!TIP]
> While most Vertex-provided Power-Ups are part of the commercial Synapse offering, the following [Rapid Power-Ups](power_ups.md#rapid-powerups) are also available for use with the community (open source) version of Synapse:
>
> - [Synapse-MISP](/docs/synapse-misp/latest/index.md)
> - [Synapse-MITRE-ATT&CK](/docs/synapse-mitre-attack/latest/index.md)
> - [Synapse-PSL](/docs/synapse-psl/latest/index.md) (FQDN public suffix list)
> - [Synapse-TOR](/docs/synapse-tor/latest/index.md)

<a id="admin_runtime_perms"></a>

### Storm Runtime Permissions

When a user runs a Storm query **interactively** (e.g., in the Storm CLI or via the Optic Query Bar), or performs an action in the Optic UI (such as accessing a menu option), the query or action executes **with the permissions of the user,** based on the applicable user and role permissions and the current scope for the query or action.

There are a few cases of Storm runtime execution where different permissions are used that may require additional considerations.

<a id="admin_automation_perms"></a>

#### Automation

Synapse includes the ability to automate Storm-based tasks using triggers, cron jobs, and / or macros. These elements are all impacted by permissions in various ways, including:

- who can create or manage automation (e.g., by default any user can create a macro, but explicit permissions are required to create triggers or cron jobs);
- who a given piece of automation runs as (e.g., macros run as the user who executes them, but triggers and cron jobs run as the user who created them).

Refer to the [Storm Reference - Automation](userguides/storm_ref_automation.md#storm-ref-automation) section of the [Synapse User Guide](userguide.md#userguide) for a detailed discussion of automation in Synapse (including permissions considerations).

#### Power-Ups

Power-Ups implement Storm packages and Storm services to provide additional functionality to Synapse. Power-Ups may be provided by The Vertex Project (as free or commercial offerings). Organizations may also develop their own custom Power-Ups.

Power-Ups commonly install Storm commands to allow users to make use of the additional capabilities of the Power-Up. In some cases, Power-Ups may need to access sensitive data (such as API keys or similar credentials) or perform actions (e.g., in adding nodes or applying tags) that some users would not be allowed to perform on their own.

Power-Ups can use privilege separation ("privsep") so that a limited subset of Power-Up capabilities can run with elevated privileges if necessary, with the remainder of the code running as the user who calls the Power-Up.

See the [Rapid Power-Up Development](devguides/power-ups.md#dev_rapid_power_ups) section of the [Synapse Developer Guide](devguide.md#devguide) for additional details.

> [!NOTE]
> Synapse Admins are typically only responsible for ensuring that the appropriate users and roles can use or run individual Power-Ups (see [Power-Up Permissions](adminguide.md#admin_power_perms)). While Synapse Admins should be aware of privilege separation within a Power-Up as a best practice, implementation of privilege separation is left to Power-Up developers.

<a id="admin_extend_model"></a>

## Add Extended Model Elements

The Synapse data model in a Cortex can be extended with custom [forms](glossary.md#gloss-form-extended) or [properties](glossary.md#gloss-prop-extended) by using the model extension Storm Library ([stormlibs-lib-model-ext](stormtypes_libs.md#stormlibs-lib-model-ext)). Extended model forms and properties must have names beginning with an underscore (`_`) to avoid potential naming conflicts with built-in model elements.

> [!NOTE]
> Extended model elements that are in-use (have nodes using the extended forms or properties) cannot be removed until all instances of that extended model element are removed. In other words, before removing extended forms any nodes created with that extended form must be delete first, and before removing extended properties any nodes with that extended property must have the property value removed.

### Extended Forms

When adding a form, `$lib.model.ext.addForm` takes the following arguments:

`formname`

:   Name of the form, must begin with an underscore (`_`) and contain at least one colon (`:`).

`basetype`

:   The [Synapse data model type](datamodel_types.md) for the form.

`typeopts`

:   A dictionary of type specific options.

`typeinfo`

:   A dictionary of info values for the form.

To add a new form named `_foocorp:name`, which contains string values which will be normalized to lowercase, with whitespace stripped from the beginning/end:

``` text
$typeopts = ({'lower': true, 'strip': true})
$typeinfo = ({'doc': 'Foocorp name.'})

$lib.model.ext.addForm(_foocorp:name, str, $typeopts, $typeinfo)
```

If the form is no longer in use and there are no nodes of this form in the Cortex, it can be removed with:

``` text
$lib.model.ext.delForm(_foocorp:name)
```

### Extended Properties

When adding properties, `$lib.model.ext.addFormProp` takes the following arguments:

`formname`

:   Name of the form to add the property to, may be a built-in or extended model form.

`propname`

:   Relative name of the property, must begin with an underscore (`_`).

`typedef`

:   A tuple of (`type`, `typeopts`) which defines the type for the property

`propinfo`

:   A dictionary of info values for the property.

To add a property named `_score` to the `_foocorp:name` form which contains int values between 0 and 100:

``` text
$typeopts = ({'min': 0, 'max': 100})
$propinfo = ({'doc': 'Score for this name.'})

$lib.model.ext.addFormProp(_foocorp:name, _score, (int, $typeopts), $propinfo)
```

To add a property named `_aliases` to the `_foocorp:name` form which contains a unique array of `base:name` values:

``` text
$typeopts = ({'type': 'base:name', 'uniq': true})
$propinfo = ({'doc': 'Aliases for this name.'})

$lib.model.ext.addFormProp(_foocorp:name, _aliases, (array, $typeopts), $propinfo)
```

Properties may also be added to existing forms, for example, to add a property named `_classification` to `inet:fqdn` which must contain a string from a predefined set of values:

``` text
$typeopts = ({'enums': 'unknown,benign,malicious'})
$propinfo = ({'doc': 'Classification for this FQDN.'})

$lib.model.ext.addFormProp(inet:fqdn, _classification, (str, $typeopts), $propinfo)
```

### Extended Universal Properties

Similar to `$lib.model.ext.addFormProp`, `$lib.model.ext.addUnivProp` takes the same `propname`, `typedef`, and `propinfo` arguments, but applies to all forms.

<a id="admin_manage_deprecations"></a>

## Manage Model Deprecations

As the Synapse Data Model grows and evolves, model elements (types, forms, and properties) may be deprecated and should no longer be used for new data modeling. The Storm `model.deprecated` commands can be used to prepare for the eventual removal of deprecated model elements.

### Lock Deprecated Model Elements

The [model.deprecated.lock](userguides/storm_ref_cmd.md#storm-model-deprecated-lock) command edits the lock status of deprecated model elements. Locked model elements can still be viewed or deleted, but can no longer be added. Attempting to add a locked model element will cause an `IsDeprLocked` error. The [model.deprecated.locks](userguides/storm_ref_cmd.md#storm-model-deprecated-locks) command can be used to show the current lock status of all deprecated model elements.

**Examples:**

Lock the `inet:fqdn:_depr` property:

```stormdoc
storm> model.deprecated.lock inet:fqdn:_depr
Locking: inet:fqdn:_depr
```

Unlock the `inet:fqdn:_depr` property:

```stormdoc
storm> model.deprecated.lock --unlock inet:fqdn:_depr
Unlocking: inet:fqdn:_depr
```

Lock all deprecated model elements:

```stormdoc
storm> model.deprecated.lock *
Locking all deprecated model elements.
```

### Check for Deprecated Model Elements

The [model.deprecated.check](userguides/storm_ref_cmd.md#storm-model-deprecated-check) command checks for lock status and the existence of deprecated model elements in the Cortex. Warnings will be produced for any deprecated model elements which are unlocked or still in use in the Cortex. Once all warnings have been resolved, your Cortex will be ready for future model updates.

<a id="admin_config_mirror"></a>

## Configure a Mirrored Layer

> [!NOTE]
> Mirrored layers are deprecated in 2.x and will be removed in 3.0.0. The [layer.pull.add](userguides/storm_ref_cmd.md#storm-layer-pull-add) and [layer.push.add](userguides/storm_ref_cmd.md#storm-layer-push-add) commands can be used to configure streaming edits to/from layers in a separate Cortex.

Once a mirrored layer is configured, it will need to stream down the entire history of events from the upstream layer. During this process, the layer will be readable but writes will hang due to needing to await the write-back A Cortex may be configured to mirror a layer from a remote Cortex which will synchronize all edits from the remote layer and use write-back support to facilitate edits originating from the downstream layer. The mirrored layer will be an exact copy of the layer on the remote system including all edit history and will only allow changes which are first sent to the upstream layer.

When configuring a mirrored layer, you may choose to mirror from a remote layer *or* from the top layer of a remote view. If you choose to mirror from the top layer of a remote view, that view will have the opportunity to fire triggers and enforce model constraints on the changes being provided by the mirrored layer.

To specify a remote layer as the upstream, use a Telepath URL which includes the shared object `*/layer/<layeriden>` such as:

``` text
aha://cortex.loop.vertex.link/*/layer/8ea600d1732f2c4ef593120b3226dea3
```

To specify a remote view, use the shared object `*/view/<viewiden>` such as:

``` text
aha://cortex.loop.vertex.link/*/view/8ea600d1732f2c4ef593120b3226dea3
```

When you specify a `--mirror` option to the `layer.add` command or within a layer definition provided to the `$lib.layer.add()` Storm API the telepath URL will not be checked. This allows configuration of a remote layer or view which is not yet provisioned or is currently offline.

> [!NOTE]
> To allow write access, the telepath URL must allow admin access to the remote Cortex due to being able to fabricate edit origins. The telepath URL may use aliased names or TLS client side certs to prevent credential disclosure.

Once a mirrored layer is configured, it will need to stream down the entire history of events from the upstream layer. During this process, the layer will be readable but writes will hang due to needing to await the write-back to be fully caught up to guarantee that edits are immediately observable like a normal layer. During that process, you may track progress by calling the `getMirrorStatus()` API on the `layer` object within the Storm runtime.
