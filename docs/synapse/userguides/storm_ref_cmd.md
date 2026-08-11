```mdstorm-setup
```

<a id="storm-ref-cmd"></a>


# Storm Reference - Storm Commands

Storm commands are built-in or custom commands that can be used natively within Synapse Storm queries.

**Built-in commands** are native to the Storm library and loaded by default within a given Cortex. Built-in commands comprise a set of helper commands that perform a variety of specialized tasks that are useful regardless of the types of data stored in Synapse or the types of analysis performed.

**Custom commands** are Storm commands that have been added to a Cortex to invoke the execution of dynamically loaded modules. Synapse **Power-Ups** ([Power-Up](../glossary.md#gloss-power-up)) are examples of modules that may install additional Storm commands to implement functionality specific to that Power-Up (such as querying a third-party data source to automatically ingest and model the data in Synapse).

<a id="storm-ref-cmd-pipe"></a>


## Storm Commands and the Pipe Character

The pipe character ( `|` ) is used with Storm commands to:

- Return to Storm query syntax after running a Storm command.
- Separate individual Storm commands and their parameters (i.e., if you are chaining multiple commands together).

For example:

``` text
inet:fqdn=woot.com | nettools.whois | nettools.dns --type A AAAA NS | -> inet:dns:a
```

The query above:

- lifts the FQDN `woot.com`,
- performs a live "whois" lookup using the Synapse-Nettools [Power-Up](../glossary.md#gloss-power-up) (`| nettools.whois`),
- performs a live DNS query for the FQDN's A, AAAA, and NS records (`| nettools.dns --type A AAAA NS`), and
- pivots from the FQDN to any associated DNS A records (`| -> inet:dns:a`).

The pipe is used to:

- separate the initial lift operation (`inet:fqdn=woot.com`) from the `nettools.whois` command;
- separate the `nettools.whois` command from the `nettools.dns` command and its parameters; and
- separate the `nettools.dns` command and its parameters from the subsequent query operation (the pivot).

> [!TIP]
> A pipe character is **not** required between a Storm operation and any **initial** Storm command (e.g., between `inet:fqdn=woot.com` and `nettools.whois` in the example above). A pipe character can **optionally** be placed in this location but is not necessary.
>
> We use the pipe character in our examples to more clearly separate Storm query syntax (operations) from Storm commands.

> [!NOTE]
> A command's argument list is terminated only by a pipe character, a closing brace ( `}` ), or the end of the query. A pipe **is** required between a Storm command and any following Storm operation -- including keyword operations such as `for`, `if`, and `fini`. Without the pipe, the following text is parsed as additional command arguments.

<a id="storm-cmd-ref"></a>


## Storm Command Reference

The full list of Storm commands (built-in and custom) available in a given instance of Synapse can be displayed with the `help` command.

Help for a specific Storm command can be displayed with `<command> --help`.

> [!TIP]
> This section details the usage and syntax for **built-in** Storm commands. Many of the commands below - such as `count`, `intersect`, `limit`, `max` / `min`, `uniq`, or the various `gen` (generate) commands - directly support analysis tasks.
>
> Other commands, such as those used to manage daemons, queues, packages, or services, are likely of greater interest to Synapse administrators or developers.

- [help](storm_ref_cmd.md#storm-help)
- [aha](storm_ref_cmd.md#storm-aha)
- [auth](storm_ref_cmd.md#storm-auth)
- [background](storm_ref_cmd.md#storm-background)
- [batch](storm_ref_cmd.md#storm-batch)
- [copyto](storm_ref_cmd.md#storm-copyto)
- [cortex.httpapi](storm_ref_cmd.md#storm-cortex-httpapi)
- [count](storm_ref_cmd.md#storm-count)
- [cron](storm_ref_cmd.md#storm-cron)
- [delnode](storm_ref_cmd.md#storm-delnode)
- [diff](storm_ref_cmd.md#storm-diff)
- [divert](storm_ref_cmd.md#storm-divert)
- [dmon](storm_ref_cmd.md#storm-dmon)
- [edges](storm_ref_cmd.md#storm-edges)
- [gen](storm_ref_cmd.md#storm-gen)
- [graph](storm_ref_cmd.md#storm-graph)
- [intersect](storm_ref_cmd.md#storm-intersect)
- [layer](storm_ref_cmd.md#storm-layer)
- [lift](storm_ref_cmd.md#storm-lift)
- [limit](storm_ref_cmd.md#storm-limit)
- [macro](storm_ref_cmd.md#storm-macro)
- [max](storm_ref_cmd.md#storm-max)
- [merge](storm_ref_cmd.md#storm-merge)
- [min](storm_ref_cmd.md#storm-min)
- [model](storm_ref_cmd.md#storm-model)
- [movenodes](storm_ref_cmd.md#storm-movenodes)
- [movetag](storm_ref_cmd.md#storm-movetag)
- [nodes](storm_ref_cmd.md#storm-nodes)
- [note](storm_ref_cmd.md#storm-note)
- [once](storm_ref_cmd.md#storm-once)
- [parallel](storm_ref_cmd.md#storm-parallel)
- [pkg](storm_ref_cmd.md#storm-pkg)
- [queue](storm_ref_cmd.md#storm-queue)
- [runas](storm_ref_cmd.md#storm-runas)
- [scrape](storm_ref_cmd.md#storm-scrape)
- [service](storm_ref_cmd.md#storm-service)
- [sleep](storm_ref_cmd.md#storm-sleep)
- [spin](storm_ref_cmd.md#storm-spin)
- [stats](storm_ref_cmd.md#storm-stats)
- [tag](storm_ref_cmd.md#storm-tag)
- [tee](storm_ref_cmd.md#storm-tee)
- [tree](storm_ref_cmd.md#storm-tree)
- [trigger](storm_ref_cmd.md#storm-trigger)
- [uniq](storm_ref_cmd.md#storm-uniq)
- [uptime](storm_ref_cmd.md#storm-uptime)
- [vault](storm_ref_cmd.md#storm-vault)
- [version](storm_ref_cmd.md#storm-version)
- [view](storm_ref_cmd.md#storm-view)
- [wget](storm_ref_cmd.md#storm-wget)

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

The Storm query language is covered in detail starting with the [Storm Reference - Introduction](storm_ref_intro.md#storm-ref-intro) section of the Synapse User Guide.

> [!TIP]
> Storm commands, including custom commands, are added to Synapse as **runtime nodes** ("runt nodes" - see [Node, Runtime](../glossary.md#gloss-node-runtime)) of the form `syn:cmd`. With a few restrictions, these runt nodes can be lifted, filtered, and operated on similar to the way you work with other nodes.

**Example**

Lift the `syn:cmd` node for the Storm `movetag` command:

```mdstorm
syn:cmd=movetag
```

<a id="storm-help"></a>


## help

The `help` command displays the list of available commands within the current instance of Synapse and a brief message describing each command. Help for individual commands is available via `<command> --help`. The `help` command can also be used to inspect information about [stormtypes-libs-header](../stormtypes_libs.md#stormtypes-libs-header) and [stormtypes-prim-header](../stormtypes_prims.md#stormtypes-prim-header).

**Syntax:**

```mdstorm
help --help
```

<a id="storm-aha"></a>


## aha

Storm includes `aha.*` commands that allow you to work with Synapse's [AHA service](../deploymentguide.md#deploy-aha-service).

- [aha.svc.list](storm_ref_cmd.md#storm-aha-svc-list)
- [aha.svc.stat](storm_ref_cmd.md#storm-aha-svc-stat)

Help for individual `aha.*` commands can be displayed using:

> `<command> --help`

<a id="storm-aha-svc-list"></a>


### aha.svc.list

The `aha.svc.list` command lists AHA services.

**Syntax:**

```mdstorm
aha.svc.list --help
```

<a id="storm-aha-svc-stat"></a>


### aha.svc.stat

The `aha.svc.stat` command displays all information for an AHA service.

**Syntax:**

```mdstorm
aha.svc.stat --help
```

<a id="storm-auth"></a>


## auth

Storm includes `auth.*` commands that allow you create and manage users and roles, and manage their associated permissions (rules).

- [auth.gate.show](storm_ref_cmd.md#storm-auth-gate-show)
- [auth.perms.list](storm_ref_cmd.md#storm-auth-perms-list)
- [auth.role.add](storm_ref_cmd.md#storm-auth-role-add)
- [auth.role.addrule](storm_ref_cmd.md#storm-auth-role-addrule)
- [auth.role.del](storm_ref_cmd.md#storm-auth-role-del)
- [auth.role.delrule](storm_ref_cmd.md#storm-auth-role-delrule)
- [auth.role.list](storm_ref_cmd.md#storm-auth-role-list)
- [auth.role.mod](storm_ref_cmd.md#storm-auth-role-mod)
- [auth.role.show](storm_ref_cmd.md#storm-auth-role-show)
- [auth.user.add](storm_ref_cmd.md#storm-auth-user-add)
- [auth.user.addrule](storm_ref_cmd.md#storm-auth-user-addrule)
- [auth.user.allowed](storm_ref_cmd.md#storm-auth-user-allowed)
- [auth.user.delrule](storm_ref_cmd.md#storm-auth-user-delrule)
- [auth.user.grant](storm_ref_cmd.md#storm-auth-user-grant)
- [auth.user.list](storm_ref_cmd.md#storm-auth-user-list)
- [auth.user.mod](storm_ref_cmd.md#storm-auth-user-mod)
- [auth.user.revoke](storm_ref_cmd.md#storm-auth-user-revoke)
- [auth.user.show](storm_ref_cmd.md#storm-auth-user-show)

Help for individual `auth.*` commands can be displayed using:

> `<command> --help`

<a id="storm-auth-gate-show"></a>


### auth.gate.show

The `auth.gate.show` command displays the user, roles, and permissions associated with the specified [Auth Gate](../glossary.md#gloss-authgate).

**Syntax**

```mdstorm
auth.gate.show --help
```

<a id="storm-auth-perms-list"></a>


### auth.perms.list

The `auth.perms.list` command displays the set of permissions currently defined within the Cortex. This includes native Synapse permissions as well as any permissions associated with other packages and services, including Power-Ups. Each permission includes a brief description of the permission, the associated auth gate (e.g., 'cortex', 'layer') and the default state (true/allowed or false/denied).

**Syntax:**

```mdstorm
auth.perms.list --help
```

<a id="storm-auth-role-add"></a>


### auth.role.add

The `auth.role.add` command creates a role.

**Syntax:**

```mdstorm
auth.role.add --help
```

<a id="storm-auth-role-addrule"></a>


### auth.role.addrule

The `auth.role.addrule` command adds a rule (permission) to a role.

**Syntax:**

```mdstorm
auth.role.addrule --help
```

<a id="storm-auth-role-del"></a>


### auth.role.del

The `auth.role.del` command deletes a role.

**Syntax:**

```mdstorm
auth.role.del --help
```

<a id="storm-auth-role-delrule"></a>


### auth.role.delrule

The `auth.role.delrule` command removes a rule (permission) from a role.

**Syntax:**

```mdstorm
auth.role.delrule --help
```

<a id="storm-auth-role-list"></a>


### auth.role.list

The `auth.role.list` lists all roles in the Cortex.

**Syntax:**

```mdstorm
auth.role.list --help
```

<a id="storm-auth-role-mod"></a>


### auth.role.mod

The `auth.role.mod` modifies an existing role.

**Syntax:**

```mdstorm
auth.role.mod --help
```

<a id="storm-auth-role-show"></a>


### auth.role.show

The `auth.role.show` displays the details for a given role.

**Syntax:**

```mdstorm
auth.role.show --help
```

<a id="storm-auth-user-add"></a>


### auth.user.add

The `auth.user.add` command creates a user.

**Syntax:**

```mdstorm
auth.user.add --help
```

<a id="storm-auth-user-addrule"></a>


### auth.user.addrule

The `auth.user.addrule` command adds a rule (permission) to a user.

**Syntax:**

```mdstorm
auth.user.addrule --help
```

<a id="storm-auth-user-allowed"></a>


### auth.user.allowed

The `auth.user.allowed` command checks whether a user has a permission for the specified scope (view or layer; if no scope is specified with the `--gate` option, the permission is checked globally).

The command returns whether the permission is allowed (true or false) and the source of the permission (e.g., if the permission is due to having a particular role).

The permission may be given either as a dotted string (`node.tag.add.cno`) or as a list of permission parts
(`(node, tag, add, cno)`).

If no rule matches, the command reports the permission's registered default, which is the same value used when
the permission is enforced.

**Syntax:**

```mdstorm
auth.user.allowed --help
```

<a id="storm-auth-user-delrule"></a>


### auth.user.delrule

The `auth.user.delrule` command removes a rule (permission) from a user.

**Syntax:**

```mdstorm
auth.user.delrule --help
```

<a id="storm-auth-user-grant"></a>


### auth.user.grant

The `auth.user.grant` command grants a role (and its associated permissions) to a user.

**Syntax:**

```mdstorm
auth.user.grant --help
```

<a id="storm-auth-user-list"></a>


### auth.user.list

The `auth.user.list` command displays all users in the Cortex.

**Syntax:**

```mdstorm
auth.user.list --help
```

<a id="storm-auth-user-mod"></a>


### auth.user.mod

The `auth.user.mod` command modifies a user account.

**Syntax:**

```mdstorm
auth.user.mod --help
```

<a id="storm-auth-user-revoke"></a>


### auth.user.revoke

The `auth.user.revoke` command revokes a role (and its associated permissions) from a user.

**Syntax:**

```mdstorm
auth.user.revoke --help
```

<a id="storm-auth-user-show"></a>


### auth.user.show

The `auth.user.show` command displays information for a specific user.

**Syntax:**

```mdstorm
auth.user.show --help
```

<a id="storm-background"></a>


## background

The `background` command allows you to execute a Storm query as a background task (e.g., to free up the CLI / Storm runtime for additional queries).

> [!NOTE]
> Use of `background` is a "fire-and-forget" process - any status messages (warnings or errors) are not returned to the console, and if the query is interrupted for any reason, it will not resume.

See also [parallel](storm_ref_cmd.md#storm-parallel).

**Syntax:**

```mdstorm
background --help
```

<a id="storm-batch"></a>


## batch

The `batch` command allows you to run a Storm query with batched sets of nodes.

Note that in most cases, Storm queries are meant to operate in a "streaming" manner on individual nodes. This command is intended to be used in cases such as querying external APIs that support aggregate queries (i.e., an API that allows you to query 100 objects in a single API call as part of the API's quota system).

**Syntax:**

```mdstorm
batch --help
```

<a id="storm-copyto"></a>


## copyto

The `copyto` command allows you to copy nodes from the current view to a specified target view. Nodes are copied to the write layer (the topmost layer) in the target view.

When copying nodes, the history of the node (i.e., changes to the node, timestamps, associated user) in the **source** view (the view layer(s)) is preserved; the changes written to the **target** view's write layer are owned by the user executing the `copyto` command.

See the [movenodes](storm_ref_cmd.md#storm-movenodes) command to move nodes between layers in the same layer stack.

> [!NOTE]
> The `copyto` command, like the `movenodes` command, is meant to be used by Synapse **administrators** in specific use cases.

**Syntax:**

```mdstorm
copyto --help
```

<a id="storm-cortex-httpapi"></a>


## cortex.httpapi

> [!NOTE]
> See the [Extended HTTP API](../devopsguide.md#devops-svc-cortex-ext-http) guide for additional background on Extended HTTP API endpoints.

Storm includes `cortex.httpapi.*` commands that allow a user to list and manage Extended HTTP API endpoints.

- [cortex.httpapi.index](storm_ref_cmd.md#storm-cortex-httpapi-index)
- [cortex.httpapi.list](storm_ref_cmd.md#storm-cortex-httpapi-list)
- [cortex.httpapi.stat](storm_ref_cmd.md#storm-cortex-httpapi-stat)

Help for individual `cortex.httpapi.*` commands can be displayed using:

> `<command> --help`

<a id="storm-cortex-httpapi-index"></a>


### cortex.httpapi.index

The `cortex.httpapi.index` command is used to change the resolution order of the Extended HTTP API endpoints.

**Syntax:**

```mdstorm
cortex.httpapi.index --help
```

<a id="storm-cortex-httpapi-list"></a>


### cortex.httpapi.list

The `cortex.httpapi.list` command is used to list the Extended HTTP API endpoints.

**Syntax:**

```mdstorm
cortex.httpapi.list --help
```

<a id="storm-cortex-httpapi-stat"></a>


### cortex.httpapi.stat

The `cortex.httpapi.stat` command is used to show the detailed information for a single Extended HTTP API Endpoint.

**Syntax:**

```mdstorm
cortex.httpapi.stat --help
```

<a id="storm-count"></a>


## count

The `count` command enumerates the number of nodes returned from a given Storm query and displays the final tally. The associated nodes can optionally be displayed with the `--yield` switch.

**Syntax:**

```mdstorm
count --help
```

**Examples:**

Count the number of IP addresses that Trend Micro associates with the threat group Earth Preta (`#rep.trend.earth_preta`):

```mdstorm --hide
[ inet:ip=66.129.222.1 inet:ip=184.82.164.104 inet:ip=209.161.249.125 inet:ip=69.90.65.240 inet:ip=70.62.232.98 +#rep.trend.earth_preta ]
```

```mdstorm
inet:ip#rep.trend.earth_preta | count
```

Count the IP addresses Trend Micro associates with Earth Preta and yield the nodes:

```mdstorm --hide
[ inet:ip=66.129.222.1 inet:ip=184.82.164.104 inet:ip=209.161.249.125 inet:ip=69.90.65.240 inet:ip=70.62.232.98 +#rep.trend.earth_preta ]
```

```mdstorm
inet:ip#rep.trend.earth_preta | count --yield
```

Count the number of DNS A records for the domain `woot.com` where the lift produces no results:

```mdstorm
inet:dns:a:fqdn=woot.com | count
```

<a id="storm-cron"></a>


## cron

> [!NOTE]
> See the [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation) guide for additional background on cron jobs (as well as triggers and macros), including examples.

Storm includes `cron.*` commands that allow you to create and manage scheduled [Cron](../glossary.md#gloss-cron) jobs. Within Synapse, jobs are Storm queries that execute on a recurring or one-time (`cron.at`) basis.

- [cron.add](storm_ref_cmd.md#storm-cron-add)
- [cron.at](storm_ref_cmd.md#storm-cron-at)
- [cron.cleanup](storm_ref_cmd.md#storm-cron-cleanup)
- [cron.list](storm_ref_cmd.md#storm-cron-list)
- [cron.stat](storm_ref_cmd.md#storm-cron-stat)
- [cron.mod](storm_ref_cmd.md#storm-cron-mod)
- [cron.del](storm_ref_cmd.md#storm-cron-del)

Help for individual `cron.*` commands can be displayed using:

> `<command> --help`

<a id="storm-cron-add"></a>


### cron.add

The `cron.add` command creates an individual cron job within a Cortex.

**Syntax:**

```mdstorm
cron.add --help
```

<a id="storm-cron-at"></a>


### cron.at

The `cron.at` command creates a non-recurring (one-time) cron job within a Cortex.

**Syntax:**

```mdstorm
cron.at --help
```

<a id="storm-cron-cleanup"></a>


### cron.cleanup

The `cron.cleanup` command can be used to remove any one-time cron jobs ("at" jobs) that have completed.

**Syntax:**

```mdstorm
cron.cleanup --help
```

<a id="storm-cron-list"></a>


### cron.list

The `cron.list` command displays the set of cron jobs in the Cortex that the current user can view / modify based on their permissions.

Cron jobs are displayed in alphanumeric order by job [Iden](../glossary.md#gloss-iden). Jobs are sorted upon Cortex initialization, so newly-created jobs will be displayed at the bottom of the list until the list is re-sorted the next time the Cortex is restarted.

**Syntax:**

```mdstorm
cron.list --help
```

<a id="storm-cron-stat"></a>


### cron.stat

The `cron.stat` command displays statistics for an individual cron job and provides more detail on an individual job vs. `cron.list`, including any errors and the interval at which the job executes. To view the stats for a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

**Syntax:**

```mdstorm
cron.stat --help
```

<a id="storm-cron-mod"></a>


### cron.mod

The `cron.mod` command modifies properties of an existing cron job. To modify a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

> [!NOTE]
> Some aspects of the cron job, such as its schedule for execution, cannot be modified once the job has been created. To change these aspects you must delete and re-add the job.

**Syntax:**

```mdstorm
cron.mod --help
```

<a id="storm-cron-del"></a>


### cron.del

The `cron.del` command permanently removes a cron job from the Cortex. To delete a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

**Syntax:**

```mdstorm
cron.del --help
```

<a id="storm-delnode"></a>


## delnode

The `delnode` command deletes a node or set of nodes from a Cortex.

> [!WARNING]
> The Storm `delnode` command includes some limited checks (see below) to try and prevent the accidental deletion of nodes that are still connected to other nodes in the knowledge graph. However, these checks are not foolproof, and `delnode` has the potential to be destructive if executed on an incorrect, badly formed, or mistyped query.
>
> Users are **strongly encouraged** to validate their query by first executing it on its own to confirm it returns the expected nodes before piping the query to the `delnode` command.
>
> In addition, use of the `--force` switch with `delnode` will override all safety checks and forcibly delete ALL nodes input to the command.
>
> **This parameter should be used with extreme caution as it may result in broken references (e.g., "holes" in the graph) within Synapse.**

**Syntax:**

```mdstorm
delnode --help
```

**Examples:**

Delete the node for the domain `woowoo.com`:

```mdstorm --hide
[ inet:fqdn=woowoo.com ]
```

```mdstorm
inet:fqdn=woowoo.com | delnode
```

Forcibly delete all nodes with the `#testing` tag:

```mdstorm
#testing | delnode --force
```

**Usage Notes:**

- `delnode` operates on the output of a previous Storm query.

- `delnode` performs some basic sanity-checking to help prevent egregious mistakes, and will generate an error in cases such as:

  - attempting to delete a node (such as `inet:fqdn=woot.com`) that is still referenced by (i.e., is a secondary property of) another node (such as `inet:dns:a=( woot.com, 1.1.1.1 )`.
  - attempting to delete a `syn:tag` node where that tag still exists on other nodes.

  However, it is important to keep in mind that **delnode cannot prevent all mistakes.**

<a id="storm-diff"></a>


## diff

The `diff` command generates a list of nodes with changes (i.e., newly created or modified nodes) present in the top [Layer](../glossary.md#gloss-layer) of the current [View](../glossary.md#gloss-view). The `diff` command may be useful before performing a [merge](storm_ref_cmd.md#storm-merge) operation.

**Syntax:**

```mdstorm
diff --help
```

<a id="storm-divert"></a>


## divert

The `divert` command allows Storm to either consume a generator or yield its results based on a conditional.

**Syntax:**

```mdstorm
divert --help
```

<a id="storm-dmon"></a>


## dmon

Storm includes `dmon.*` commands that allow you to work with daemons (see [Daemon](../glossary.md#gloss-daemon)).

- [dmon.list](storm_ref_cmd.md#storm-dmon-list)

Help for individual `dmon.*` commands can be displayed using:

> `<command> --help`

<a id="storm-dmon-list"></a>


### dmon.list

The `dmon.list` command displays the set of running dmon queries in the Cortex.

**Syntax:**

```mdstorm
dmon.list --help
```

<a id="storm-edges"></a>


## edges

Storm includes `edges.*` commands that allow you to work with lightweight (light) edges. Also see the `lift.byverb` command under [lift](storm_ref_cmd.md#storm-lift) below.

- [edges.del](storm_ref_cmd.md#storm-edges-del)

Help for individual `edge.*` commands can be displayed using:

> `<command> --help`

<a id="storm-edges-del"></a>


### edges.del

The `edges.del` command is designed to delete multiple light edges to (or from) a set of nodes (contrast with using Storm edit syntax - see [Delete Light Edges](storm_ref_data_mod.md#light-edge-del)).

**Syntax:**

```mdstorm
edges.del --help
```

<a id="storm-gen"></a>


## gen

Storm includes various `gen.*` ("generate") commands that allow you to easily query for common guid-based nodes (see [Form, Guid](../glossary.md#gloss-form-guid)) based on one or more "human friendly" secondary properties, and create (generate) the specified node if it does not already exist.

Because guid nodes have a primary property that may be arbitrary, `gen.*` commands simplify the process of **deconflicting on secondary properties** before creating certain guid nodes.

> [!NOTE]
> See the [guid](storm_ref_type_specific.md#type-guid) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for a detailed discussion of guids, guid behavior, and deconfliction considerations for guid forms.

Nodes created using generate commands will have a limited subset of properties set (e.g., an organization node deconflicted and created based on a name will only have its `ou:org:name` property set). Users can set additional property values as they see fit.

- [gen.campaign](storm_ref_cmd.md#storm-gen-campaign)
- [gen.country](storm_ref_cmd.md#storm-gen-country)
- [gen.government](storm_ref_cmd.md#storm-gen-government)
- [gen.industry](storm_ref_cmd.md#storm-gen-industry)
- [gen.language](storm_ref_cmd.md#storm-gen-language)
- [gen.org](storm_ref_cmd.md#storm-gen-org)
- [gen.place](storm_ref_cmd.md#storm-gen-place)
- [gen.software](storm_ref_cmd.md#storm-gen-software)
- [gen.threat](storm_ref_cmd.md#storm-gen-threat)
- [gen.vuln](storm_ref_cmd.md#storm-gen-vuln)

Help for individual `gen.*` commands can be displayed using:

> `<command> --help`

> [!NOTE]
> New `gen.*` commands are added to Synapse on an ongoing basis as we identify new cases where such commands are helpful. Use the `help` command for the current list of `gen.*` commands available in your instance of Synapse.

<a id="storm-gen-campaign"></a>


### gen.campaign

The `gen.campaign` command locates (lifts) or creates an `entity:campaign` node based on the campaign name (`entity:campaign:name` and / or `entity:campaign:names`) and the name of the reporter (`entity:campaign:reporter:name`).

**Syntax:**

```mdstorm
gen.campaign --help
```

<a id="storm-gen-country"></a>


### gen.country

The `gen.country` command locates (lifts) or creates a `pol:country` node based on the two-letter ISO-3166 country code (`pol:country:iso2`).

**Syntax:**

```mdstorm
gen.country --help
```

<a id="storm-gen-government"></a>


### gen.government

The `gen.government` command locates (lifts) the `ou:org` node representing a country's government (i.e., the organization set for the `pol:country:government` property) or creates the node (and sets the `pol:country:government` property) if it does not exist, based on the two-letter ISO-3166 country code (`pol:country:iso2`).

**Syntax:**

```mdstorm
gen.government --help
```

<a id="storm-gen-industry"></a>


### gen.industry

The `gen.industry` command locates (lifts) or creates an `ind:industry` node based on the industry name (`ind:industry:name` and / or `ind:industry:names`) and the name of the reporter (`ind:industry:reporter:name`).

**Syntax:**

```mdstorm
gen.industry --help
```

<a id="storm-gen-language"></a>


### gen.language

The `gen.language` command locates (lifts) or creates a `lang:language` node based on the language name (`lang:language:name` and / or `lang:language:names`).

**Syntax:**

```mdstorm
gen.language --help
```

<a id="storm-gen-org"></a>


### gen.org

The `gen.org` command locates (lifts) or creates an `ou:org` node based on the organization name (`ou:org:name` and / or `ou:org:names`).

**Syntax:**

```mdstorm
gen.org --help
```

<a id="storm-gen-place"></a>


### gen.place

The `gen.place` command locates (lifts) or creates a `geo:place` node based on the place name (`geo:place:name` and / or `geo:place:names` properties).

**Syntax:**

```mdstorm
gen.place --help
```

<a id="storm-gen-software"></a>


### gen.software

The `gen.software` command locates (lifts) or creates an `it:software` node based on the software name (`it:software:name` and / or `it:software:names`) and the name of the reporter (`it:software:reporter:name`).

**Syntax:**

```mdstorm
gen.software --help
```

<a id="storm-gen-threat"></a>


### gen.threat

The `gen.threat` command locates (lifts) or creates a `risk:threat` node using the name of the threat group (`risk:threat:name` and / or `risk:threat:names`) and the name of the reporter (`risk:threat:reporter:name`).

**Syntax:**

```mdstorm
gen.threat --help
```

<a id="storm-gen-vuln"></a>


### gen.vuln

The `gen.vuln` command locates (lifts) or creates a `risk:vuln` node using the Common Vulnerabilities and Exposures (CVE) number associated with the vulnerability (`risk:vuln:id`) and the name of the reporter (`risk:vuln:reporter:name`).

**Syntax:**

```mdstorm
gen.vuln --help
```

<a id="storm-graph"></a>


## graph

The `graph` command generates a subgraph based on a specified set of nodes and parameters.

**Syntax:**

```mdstorm
graph --help
```

<a id="storm-intersect"></a>


## intersect

The `intersect` command returns the intersection of the results from performing a pivot and/or traversal operation on multiple inbound nodes. In other words, `intersect` will return the subset of results that are **common** to each of the inbound nodes.

**Syntax:**

```mdstorm
intersect --help
```

<a id="storm-layer"></a>


## layer

Storm includes `layer.*` commands that allow you to work with layers (see [Layer](../glossary.md#gloss-layer)).

- [layer.add](storm_ref_cmd.md#storm-layer-add)
- [layer.set](storm_ref_cmd.md#storm-layer-set)
- [layer.get](storm_ref_cmd.md#storm-layer-get)
- [layer.list](storm_ref_cmd.md#storm-layer-list)
- [layer.del](storm_ref_cmd.md#storm-layer-del)
- [layer.pull.add](storm_ref_cmd.md#storm-layer-pull-add)
- [layer.pull.list](storm_ref_cmd.md#storm-layer-pull-list)
- [layer.pull.del](storm_ref_cmd.md#storm-layer-pull-del)
- [layer.push.add](storm_ref_cmd.md#storm-layer-push-add)
- [layer.push.list](storm_ref_cmd.md#storm-layer-push-list)
- [layer.push.del](storm_ref_cmd.md#storm-layer-push-del)

Help for individual `layer.*` commands can be displayed using:

> `<command> --help`

<a id="storm-layer-add"></a>


### layer.add

The `layer.add` command adds a layer to the Cortex.

**Syntax**

```mdstorm
layer.add --help
```

<a id="storm-layer-set"></a>


### layer.set

The `layer.set` command sets an option for the specified layer.

**Syntax**

```mdstorm
layer.set --help
```

<a id="storm-layer-get"></a>


### layer.get

The `layer.get` command retrieves the specified layer from a Cortex.

**Syntax**

```mdstorm
layer.get --help
```

<a id="storm-layer-list"></a>


### layer.list

The `layer.list` command lists the available layers in a Cortex.

**Syntax**

```mdstorm
layer.list --help
```

<a id="storm-layer-del"></a>


### layer.del

The `layer.del` command deletes a layer from a Cortex.

**Syntax**

```mdstorm
layer.del --help
```

<a id="storm-layer-pull-add"></a>


### layer.pull.add

The `layer.pull.add` command adds a pull configuration to a layer.

**Syntax**

```mdstorm
layer.pull.add --help
```

<a id="storm-layer-pull-list"></a>


### layer.pull.list

The `layer.pull.list` command lists the pull configurations for a layer.

**Syntax**

```mdstorm
layer.pull.list --help
```

<a id="storm-layer-pull-del"></a>


### layer.pull.del

The `layer.pull.del` command deletes a pull configuration from a layer.

**Syntax**

```mdstorm
layer.pull.del --help
```

<a id="storm-layer-push-add"></a>


### layer.push.add

The `layer.push.add` command adds a push configuration to a layer.

**Syntax**

```mdstorm
layer.push.add --help
```

<a id="storm-layer-push-list"></a>


### layer.push.list

The `layer.push.list` command lists the push configurations for a layer.

**Syntax**

```mdstorm
layer.push.list --help
```

<a id="storm-layer-push-del"></a>


### layer.push.del

The `layer.push.del` command deletes a push configuration from a layer.

**Syntax**

```mdstorm
layer.push.del --help
```

<a id="storm-lift"></a>


## lift

Storm includes `lift.*` commands that allow you to perform specialized lift operations.

- [lift.byverb](storm_ref_cmd.md#storm-lift-byverb)

Help for individual `lift.*` commands can be displayed using:

> `<command> --help`

<a id="storm-lift-byverb"></a>


### lift.byverb

The `lift.byverb` command lifts nodes that are connected by the specified lightweight (light) edge. By default, the command lifts the N1 nodes (i.e., the nodes on the left side of the directional light edge relationship: `n1 -(<verb>)> n2`)

> [!NOTE]
> For other commands associated with light edges, see `edges.del` under [edges](storm_ref_cmd.md#storm-edges).

**Syntax:**

```mdstorm
lift.byverb --help
```

<a id="storm-limit"></a>


## limit

The `limit` command restricts the number of nodes returned from a given Storm query to the specified number of nodes.

**Syntax:**

```mdstorm
limit --help
```

**Example:**

Lift a single IP address that Palo Alto associates with the threat group Stately Taurus (`#rep.paloalto.stately_taurus`):

```mdstorm --hide
[ inet:ip=67.53.148.77 inet:ip=43.254.132.242 +#rep.paloalto.stately_taurus ]
```

```mdstorm
inet:ip#rep.paloalto.stately_taurus | limit 1
```

**Usage Notes:**

- If the limit number specified (i.e., `limit 100`) is greater than the total number of nodes returned from the Storm query, no limit will be applied to the resultant nodes (i.e., all nodes will be returned).
- By design, `limit` imposes an artificial limit on the nodes returned by a query, which may impair effective analysis of data by restricting results. As such, `limit` is most useful for viewing a subset of a large result set or an exemplar node for a given form.
- While `limit` returns a sampling of nodes, it is not statistically random for the purposes of population sampling for algorithmic use.

<a id="storm-macro"></a>


## macro

> [!NOTE]
> See the [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation) guide for additional background on macros (as well as triggers and cron jobs), including examples.

Storm includes `macro.*` commands that allow you to work with macros (see [Macro](../glossary.md#gloss-macro)).

- [macro.list](storm_ref_cmd.md#storm-macro-list)
- [macro.set](storm_ref_cmd.md#storm-macro-set)
- [macro.get](storm_ref_cmd.md#storm-macro-get)
- [macro.exec](storm_ref_cmd.md#storm-macro-exec)
- [macro.del](storm_ref_cmd.md#storm-macro-del)

Help for individual `macro.*` commands can be displayed using:

> `<command> --help`

<a id="storm-macro-list"></a>


### macro.list

The `macro.list` command lists the macros in a Cortex.

**Syntax:**

```mdstorm
macro.list --help
```

<a id="storm-macro-set"></a>


### macro.set

The `macro.set` command creates (or modifies) a macro in a Cortex.

**Syntax:**

```mdstorm
macro.set --help
```

<a id="storm-macro-get"></a>


### macro.get

The `macro.get` command retrieves and displays the specified macro.

**Syntax:**

```mdstorm
macro.get --help
```

<a id="storm-macro-exec"></a>


### macro.exec

The `macro.exec` command executes the specified macro.

**Syntax:**

```mdstorm
macro.exec --help
```

<a id="storm-macro-del"></a>


### macro.del

The `macro.del` command deletes the specified macro from a Cortex.

**Syntax:**

```mdstorm
macro.del --help
```

<a id="storm-max"></a>


## max

The `max` command returns the node(s) from a given set that contain the highest value(s) for a specified secondary property, tag interval, or variable. By default a single node is returned. Use `--size` to return more than one node; results are yielded in **descending** order.

If `max` is used on a property whose type is an interval (`ival`) and you only specify the property name (e.g., `max :seen`), `max` will return the highest value of the interval's `.max` virtual property (`:seen.max`) by default.

**Syntax:**

```mdstorm
max --help
```

**Examples:**

Return the DNS A record for `woot.com` with the most recent `:seen` value:

```mdstorm --hide
[ ( inet:dns:a=( woot.com, 107.21.53.159 ) :seen=( 2014/08/13, 2014/08/14 ) ) ( inet:dns:a=( woot.com, 75.101.146.4 ) :seen=( 2013/09/21, 2013/09/22 ) ) ( inet:dns:a=( woot.com, 246.21.93.214 ) :seen=( '2014/01/05 02:34:56', '2014/10/19 06:15:04' ) ) ( inet:dns:a=( woot.com, 53.25.18.25 ) :seen=( '2014/08/13 12:44:55', '2014/08/13 18:09:22' ) ) ]
```

```mdstorm
inet:dns:a:fqdn=woot.com | max :seen
```

Return the two most recent DNS A records for `woot.com`, in descending order by `:seen`

```mdstorm
inet:dns:a:fqdn=woot.com | max :seen --size 2
```

Return the DNS A record for `woot.com` with the longest duration:

```mdstorm
inet:dns:a:fqdn=woot.com | max :seen.duration
```

Return a WHOIS record for the most recently registered (`:created`) FQDN associated with the threat cluster Sparkling Unicorn (`#cno.threat.sparkling_unicorn`):

```mdstorm --hide
$fqdn1={ [ inet:fqdn=hurr.com +#cno.threat.sparkling_unicorn ] } $fqdn2={ [ inet:fqdn=derp.net +#cno.threat.sparkling_unicorn ] } [ inet:whois:record=( { "fqdn": $fqdn1, "created": "2025/10/23 09:00:00" } ) inet:whois:record=( { "fqdn": $fqdn2, "created": "2026/03/26 13:00:00" } ) ]
```

```mdstorm
inet:fqdn#cno.threat.sparkling_unicorn -> inet:whois:record | max :created
```

<a id="storm-merge"></a>


## merge

The `merge` command takes a subset of nodes from a forked view and merges them down to the next layer. The nodes can optionally be reviewed without actually merging them.

Contrast with [view.merge](storm_ref_cmd.md#storm-view-merge) for merging the entire contents of a forked view.

See the [view](storm_ref_cmd.md#storm-view) and [layer](storm_ref_cmd.md#storm-layer) commands for working with views and layers.

**Syntax:**

```mdstorm
merge --help
```

<a id="storm-min"></a>


## min

The `min` command returns the node(s) from a given set that contain the lowest value(s) for a specified secondary property, tag interval, or variable. By default a single node is returned. Use `--size` to return more than one node; results are yielded in **ascending** order.

If `min` is used on a property whose type is an interval (`ival`) and you only specify the property name (e.g., `min :seen`), `min` will return the lowest value of the interval's `.min` virtual property (`:seen.min`) by default.

**Syntax:**

```mdstorm
min --help
```

**Examples:**

Return the DNS A record for `woot.com` with the oldest `:seen` value:

```mdstorm
inet:dns:a:fqdn=woot.com min :seen
```

Return the two oldest DNS A records for `woot.com`, in ascending order by `:seen`:

```mdstorm
inet:dns:a:fqdn=woot.com | min :seen --size 2
```

Return the DNS A record for `woot.com` with the shortest duration:

```mdstorm
inet:dns:a:fqdn=woot.com | min :seen.duration
```

Return a WHOIS record for the earliest registered (`:created`) FQDN associated with the threat cluster Sparkling Unicorn (`#cno.threat.sparkling_unicorn`):

```mdstorm --hide
$fqdn1={ [ inet:fqdn=hurr.com +#cno.threat.sparkling_unicorn ] } $fqdn2={ [ inet:fqdn=derp.net +#cno.threat.sparkling_unicorn ] } [ inet:whois:record=( { "fqdn": $fqdn1, "created": "2025/10/23 09:00:00" } ) inet:whois:record=( { "fqdn": $fqdn2, "created": "2026/03/26 13:00:00" } ) ]
```

```mdstorm
inet:fqdn#cno.threat.sparkling_unicorn -> inet:whois:record | min :created
```

<a id="storm-model"></a>


## model

Storm includes `model.*` commands that allow you to work with model elements.

`model.deprecated.*` commands allow you to view model elements (forms or properties) that have been marked as "deprecated", determine whether your Cortex contains deprecated nodes / nodes with deprecated properties, and optionally lock / unlock those properties to prevent (or allow) continued creation of deprecated model elements.

- [model.deprecated.check](storm_ref_cmd.md#storm-model-deprecated-check)
- [model.deprecated.lock](storm_ref_cmd.md#storm-model-deprecated-lock)
- [model.deprecated.locks](storm_ref_cmd.md#storm-model-deprecated-locks)

Help for individual `model.*` commands can be displayed using:

> `<command> --help`

<a id="storm-model-deprecated-check"></a>


### model.deprecated.check

The `model.deprecated.check` command lists deprecated elements, their lock status, and whether deprecated elements exist in the Cortex.

**Syntax:**

```mdstorm
model.deprecated.check --help
```

<a id="storm-model-deprecated-lock"></a>


### model.deprecated.lock

The `model.deprecated.lock` command allows you to lock or unlock (e.g., disallow or allow the use of) deprecated model elements in a Cortex.

**Syntax:**

```mdstorm
model.deprecated.lock --help
```

<a id="storm-model-deprecated-locks"></a>


### model.deprecated.locks

The `model.deprecated.locks` command displays the lock status of all deprecated model elements.

**Syntax:**

```mdstorm
model.deprecated.locks --help
```

<a id="storm-movenodes"></a>


## movenodes

The `movenodes` command allows you to move nodes between layers ([Layer](../glossary.md#gloss-layer)) in a Cortex.

The command will move the specified storage nodes (see [Node, Storage](../glossary.md#gloss-node-storage)) - "sodes" for short - to the target layer. If a sode is the "left hand" (`n1`) of two nodes joined by a light edge (`n1 -(*)> n2`), then the edge is also moved.

Sodes are fully removed from the source layer(s) and added to (or merged with existing nodes in) the target layer. The history of the node (i.e., changes to the node, timestamps, associated user) in the **source** layer is preserved; the changes written to the **target** layer are owned by the user executing the `movenodes` command.

By default (i.e., if you do not specify a source and / or target layer), `movenodes` will migrate sodes from the bottom layer in the view, through each intervening layer (if any), and finally into the top layer. If you explicitly specify a source and target layer, `movenodes` migrates the sodes **directly** from the source to the target, skipping any intervening layers (if any).

Similarly, by default as the node is moved "up", any data for that node (property values, tags) in the higher layer will take precedence over (overwrite) data from a lower layer. This precedence behavior can be modified with the appropriate command switch.

The `movenodes` command is intended for use in the same layer stack. See the [copyto](storm_ref_cmd.md#storm-copyto) command to copy nodes from a view to the write layer in a specified target view.

> [!NOTE]
> The [merge](storm_ref_cmd.md#storm-merge) command specifically moves (merges) nodes from the top layer in a [View](../glossary.md#gloss-view) to the underlying layer. Merging is a common **user action** performed in a standard "fork and merge" workflow. The `merge` command should be used to move/merge nodes **down** from a higher layer/view to a lower/underlying one.
>
> The `movenodes` command allows you to move nodes between arbitrary layers and is meant to be used by Synapse **administrators** in very specific use cases (e.g., data that was accidentally merged into a lower layer that should not be there). It can be used to move nodes "up" from a lower layer to a higher one.

**Syntax:**

```mdstorm
movenodes --help
```

<a id="storm-movetag"></a>


## movetag

The `movetag` command moves a Synapse tag and its associated tag tree from one location in a tag hierarchy to another location. It is equivalent to "renaming" a given tag and all of its subtags. Moving a tag consists of:

- Creating the new `syn:tag` node(s).
- Copying the definitions (`:title` and `:doc` properties) from the old `syn:tag` node to the new `syn:tag` node.
- Applying the new tag(s) to the nodes with the old tag(s).
  - If the old tag(s) have associated timestamps / time intervals, they will be applied to the new tag(s).
- Deleting the old tag(s) from the nodes.
- Setting the `:isnow` property of the old `syn:tag` node(s) to reference the new `syn:tag` node.
  - The old `syn:tag` nodes are **not** deleted.
  - Once the `:isnow` property is set, attempts to apply the old tag will automatically result in the new tag being applied.

See also the [tag](storm_ref_cmd.md#storm-tag) command.

**Syntax:**

```mdstorm
movetag --help
```

**Examples:**

Move the tag named `#research` to `#internal.research`:

```mdstorm --hide
[ inet:asn=1138 +#research ]
```

```mdstorm
movetag research internal.research
```

Move the tag tree `#aka.fireeye.malware` to `#rep.feye.mal`:

```mdstorm --hide
[ inet:fqdn=blackcake.net +#aka.fireeye.malware]
```

```mdstorm
movetag aka.fireeye.malware rep.feye.mal
```

**Usage Notes:**

> [!WARNING]
> `movetag` should be used with caution as when used incorrectly it can result in "deleted" (inadvertently moved / removed) or orphaned (inadvertently retained) tags. For example, in the second example query above, all `aka.fireeye.malware` tags are renamed `rep.feye.mal`, but the tag `aka.fireeye` still exists and is still applied to all of the original nodes. In other words, the result of the above command will be that nodes previously tagged `aka.fireeye.malware` will now be tagged both `rep.feye.mal` **and** `aka.fireeye`. Users may wish to test the command on sample data first to understand its effects before applying it in a production Cortex.

<a id="storm-nodes"></a>


## nodes

Storm includes `nodes.*` commands that allow you to work with nodes and `.nodes` files.

- [nodes.import](storm_ref_cmd.md#storm-nodes-import)

Help for individual `nodes.*` commands can be displayed using:

> `<command> --help`

<a id="storm-nodes-import"></a>


### nodes.import

The `nodes.import` command will import a Synapse `.nodes` file (i.e., a file containing a set / subgraph of nodes, light edges, and / or tags exported from a Cortex) from a specified URL.

**Syntax:**

```mdstorm
nodes.import --help
```

<a id="storm-note"></a>


## note

Storm includes `note.*` commands that allow you to work with free form text notes (`meta:note` nodes).

- [note.add](storm_ref_cmd.md#storm-note-add)

Help for individual `note.*` commands can be displayed using:

> `<command> --help`

<a id="storm-note-add"></a>


### note.add

The `note.add` command will create a `meta:note` node containing the specified text and link it to the inbound node(s) via an `-(about)>` light edge (i.e., `meta:note=<guid> -(about)> <node(s)>`).

**Syntax:**

```mdstorm
note.add --help
```

**Usage Notes:**

> [!NOTE]
> Synapse's data and analytical models are meant to represent a broad range of data and information in a structured (and therefore **queryable**) way. As free form notes are counter to this structured approach, we recommend using `meta:note` nodes as an exception rather than a regular practice.

<a id="storm-once"></a>


## once

The `once` command is used to ensure a given node is processed by the associated Storm command only once, even if the same command is executed in a different, independent Storm query. The `once` command uses [Node Data](../glossary.md#gloss-node-data) to keep track of the associated Storm command's execution, so `once` is specific to the [View](../glossary.md#gloss-view) in which it is executed. You can override the single-execution feature of `once` with the `--asof` parameter.

**Syntax:**

```mdstorm
once --help
```

<a id="storm-parallel"></a>


## parallel

The Storm `parallel` command allows you to execute a Storm query using a specified number of query pipelines. This can improve performance for some queries.

See also [background](storm_ref_cmd.md#storm-background).

**Syntax:**

```mdstorm
parallel --help
```

<a id="storm-pkg"></a>


## pkg

Storm includes `pkg.*` commands that allow you to work with Storm packages (see [Package](../glossary.md#gloss-package)).

- [pkg.list](storm_ref_cmd.md#storm-pkg-list)
- [pkg.load](storm_ref_cmd.md#storm-pkg-load)
- [pkg.del](storm_ref_cmd.md#storm-pkg-del)
- [pkg.docs](storm_ref_cmd.md#storm-pkg-docs)
- [pkg.perms.list](storm_ref_cmd.md#storm-pkg-perms-list)

Help for individual `pkg.*` commands can be displayed using:

> `<command> --help`

Packages typically contain Storm commands and Storm library code used to implement a Storm [Service](../glossary.md#gloss-service).

<a id="storm-pkg-list"></a>


### pkg.list

The `pkg.list` command lists each Storm package loaded in the Cortex. Output is displayed in tabular form and includes the package name and version information.

**Syntax:**

```mdstorm
pkg.list --help
```

<a id="storm-pkg-load"></a>


### pkg.load

The `pgk.load` command loads the specified package into the Cortex.

**Syntax:**

```mdstorm
pkg.load --help
```

<a id="storm-pkg-del"></a>


### pkg.del

The `pkg.del` command removes a Storm package from the Cortex.

**Syntax:**

```mdstorm
pkg.del --help
```

<a id="storm-pkg-docs"></a>


### pkg.docs

The `pkg.docs` command displays the documentation for a Storm package.

**Syntax:**

```mdstorm
pkg.docs --help
```

<a id="storm-pkg-perms-list"></a>


### pkg.perms.list

The `pkg.perms.list` command lists the permissions declared by a Storm package.

**Syntax:**

```mdstorm
pkg.perms.list --help
```

<a id="storm-queue"></a>


## queue

Storm includes `queue.*` commands that allow you to work with queues (see [Queue](../glossary.md#gloss-queue)).

- [queue.add](storm_ref_cmd.md#storm-queue-add)
- [queue.list](storm_ref_cmd.md#storm-queue-list)
- [queue.del](storm_ref_cmd.md#storm-queue-del)

Help for individual `queue.*` commands can be displayed using:

> `<command> --help`

<a id="storm-queue-add"></a>


### queue.add

The `queue.add` command adds a queue to the Cortex.

**Syntax:**

```mdstorm
queue.add --help
```

<a id="storm-queue-list"></a>


### queue.list

The `queue.list` command lists each queue in the Cortex.

**Syntax:**

```mdstorm
queue.list --help
```

<a id="storm-queue-del"></a>


### queue.del

The `queue.del` command removes a queue from the Cortex.

**Syntax:**

```mdstorm
queue.del --help
```

<a id="storm-runas"></a>


## runas

The `runas` command allows you to execute a Storm query as a specified user.

> [!NOTE]
> The `runas` command requires **admin** permissions.

**Syntax:**

```mdstorm
runas --help
```

<a id="storm-scrape"></a>


## scrape

The `scrape` command parses one or more secondary properties of the inbound node(s) and attempts to identify ("scrape") common forms from the content, creating the nodes if they do not already exist. This is useful (for example) for extracting forms such as email addresses, domains, URLs, hashes, etc. from unstructured text.

The `--refs` switch can be used to optionally link the source nodes(s) to the scraped forms via `-(refs)>` light edges.

By default, the `scrape` command will return the nodes that it received as input. The `--yield` option can be used to return the scraped nodes rather than the input nodes.

**Syntax:**

```mdstorm
scrape --help
```

**Example:**

Scrape the text of a social media post (`inet:service:message`) and create nodes for common forms found in the text:

```mdstorm --hide
$platform={ [ inet:service:platform=( { "name": "bluesky", "zone": "bsky.app", "url": "https://bsky.app" } ) ]  } [ inet:service:message=( { "platform": $platform, "text": "IP address 8.8.8.8 and FQDN woot.com seen doing bad things" } ) ]
```

```mdstorm
inet:service:message | scrape :text
```

Scrape the text of a social media post for FQDNs and IP addresses, link the nodes to the original post, and return (yield) the created nodes:

```mdstorm
inet:service:message | scrape :text --forms (inet:fqdn, inet:ip) --refs --yield
```

**Usage Notes:**

- If no properties to scrape are specified, `scrape` will attempt to scrape **all** properties of the inbound nodes by default.
- `scrape` will only scrape node **properties**; it will not scrape files (this includes files that may be referenced by properties, such as `doc:report:file`). In other words, `scrape` cannot be used to parse indicators from a file such as a PDF.
- `scrape` extracts the following forms / indicators (note that this list may change as the command is updated):
  - FQDNs
  - IPs
  - Servers (IP / port combinations)
  - Hashes (MD5, SHA1, SHA256)
  - URLs
  - Email addresses
  - Cryptocurrency addresses
- `scrape` is able to recognize and account for common defanging techniques (such as `evildomain[.]com`, `myemail[@]somedomain.net`, or `hxxp://badwebsite.org/`), and will scrape defanged indicators by default. Use the `--skiprefang` switch to ignore defanged indicators.

<a id="storm-service"></a>


## service

Storm includes `service.*` commands that allow you to work with Storm services (see [Service](../glossary.md#gloss-service)).

- [service.add](storm_ref_cmd.md#storm-service-add)
- [service.list](storm_ref_cmd.md#storm-service-list)
- [service.del](storm_ref_cmd.md#storm-service-del)

Help for individual `service.*` commands can be displayed using:

> `<command> --help`

<a id="storm-service-add"></a>


### service.add

The `service.add` command adds a Storm service to the Cortex.

**Syntax:**

```mdstorm
service.add --help
```

<a id="storm-service-list"></a>


### service.list

The `service.list` command lists each Storm service in the Cortex.

**Syntax:**

```mdstorm
service.list --help
```

<a id="storm-service-del"></a>


### service.del

The `service.del` command removes a Storm service from the Cortex.

**Syntax:**

```mdstorm
service.del --help
```

<a id="storm-sleep"></a>


## sleep

The `sleep` command adds a delay in returning each result for a given Storm query. By default, query results are streamed back and displayed as soon as they arrive for optimal performance. A `sleep` delay effectively slows the display of results.

> `sleep` may be useful in cases such as querying rate-limited APIs.

**Syntax:**

```mdstorm
sleep --help
```

**Example:**

- Retrieve email nodes from a Cortex every second:

```mdstorm --hide
[ inet:email=foo@gmail.com inet:email=bar@gmail.com inet:email=baz@gmail.com ]
```

```mdstorm
inet:email sleep 1.0
```

<a id="storm-spin"></a>


## spin

The `spin` command is used to suppress the output of a Storm query. `Spin` simply consumes all nodes sent to the command, so no nodes are output to the CLI. This allows you to execute a Storm query and view messages and results without displaying the associated nodes.

**Syntax:**

```mdstorm
spin --help
```

**Example:**

Add the tag `#int.research` to any FQDN containing the string `firefox` but do not display the nodes.

```mdstorm --hide
[ inet:fqdn=firefoxupdata.com inet:fqdn=fakefirefox.net ]
```

```mdstorm
inet:fqdn~=firefox [ +#int.research ] | spin
```

<a id="storm-stats"></a>


## stats

Storm includes `stats.*` commands that allow you to query and work with statistics.

- [stats.countby](storm_ref_cmd.md#storm-stats-countby)

Help for individual `stats.*` commands can be displayed using:

> `<command> --help`

<a id="storm-stats-countby"></a>


### stats.countby

The `stats.countby` command allows you to query and display a bar chart of tallied data in the Storm CLI.

**Syntax:**

```mdstorm
stats.countby --help
```

<a id="storm-tag"></a>


## tag

Storm includes `tag.*` commands that allow you to work with tags (see [Tag](../glossary.md#gloss-tag)).

- [tag.prune](storm_ref_cmd.md#storm-tag-prune)

Help for individual `tag.*` commands can be displayed using:

> `<command> --help`

See also the related [movetag](storm_ref_cmd.md#storm-movetag) command.

<a id="storm-tag-prune"></a>


### tag.prune

The `tag.prune` command will delete the tags from incoming nodes, as well as all of their parent tags that don't have other tags as children.

**Syntax:**

```mdstorm
tag.prune --help
```

## task

Storm includes `task.*` commands that allow you to work with Storm tasks.

- [task.list](storm_ref_cmd.md#storm-task-list)
- [task.kill](storm_ref_cmd.md#storm-task-kill)

Help for individual `task.*` commands can be displayed using:

> `<command> --help`

<a id="storm-task-list"></a>


### task.list

The `task.list` command lists the currently executing tasks on a Cortex and any mirrors. By default, the command displays the first 120 characters of the executing query. The `--verbose` option can be used to display the full query regardless of length.

**Syntax:**

```mdstorm
task.list --help
```

<a id="storm-task-kill"></a>


### task.kill

The `task.kill` command can be used to terminate an executing task. The command requires the [Iden](../glossary.md#gloss-iden) of the task to be terminated, which can be obtained with [task.list](storm_ref_cmd.md#storm-task-list).

**Syntax:**

```mdstorm
task.kill --help
```

<a id="storm-tee"></a>


## tee

The `tee` command executes multiple Storm queries on the inbound nodes and returns the combined result set.

**Syntax:**

```mdstorm
tee --help
```

**Examples:**

Return the set of FQDNs and IP addresses associated with a set of DNS A records:

```mdstorm --hide
[ inet:dns:a=( foo.mydomain.com, 8.8.8.8 ) inet:dns:a=( bar.mydomain.com, 34.56.78.90 ) inet:dns:a=( baz.mydomain.com, 127.0.0.2 ) ]
```

```mdstorm
inet:fqdn:zone=mydomain.com -> inet:dns:a | tee { -> inet:fqdn } { -> inet:ip }
```

Return the set of FQDNs and IP addresses associated with a set of DNS A records along with the original DNS A records:

```mdstorm
inet:fqdn:zone=mydomain.com -> inet:dns:a | tee --join { -> inet:fqdn } { -> inet:ip }
```

**Usage Notes:**

- `tee` can take an arbitrary number of Storm queries (i.e., 1 to n queries) as arguments.

<a id="storm-tree"></a>


## tree

The `tree` command recursively performs the specified pivot until no additional nodes are returned.

**Syntax:**

```mdstorm
tree --help
```

**Example:**

List the full set of tags in the `cno` tag tree.

```mdstorm --hide
[ syn:tag=cno.ttp.phish syn:tag=cno.threat.sparkling_unicorn syn:tag=cno.mal.redtree ]
```

```mdstorm
syn:tag=cno | tree { $node.value -> syn:tag:up }
```

**Usage Notes:**

- `tree` is useful for "walking" a set of properties with a single command vs. performing an arbitrary number of pivots until the end of the data is reached.

<a id="storm-trigger"></a>


## trigger

> [!NOTE]
> See the [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation) guide for additional background on triggers (as well as cron jobs and macros), including examples.

Storm includes `trigger.*` commands that allow you to create automated event-driven triggers (see [Trigger](../glossary.md#gloss-trigger)) using the Storm query syntax.

- [trigger.add](storm_ref_cmd.md#storm-trigger-add)
- [trigger.list](storm_ref_cmd.md#storm-trigger-list)
- [trigger.mod](storm_ref_cmd.md#storm-trigger-mod)
- [trigger.del](storm_ref_cmd.md#storm-trigger-del)

Help for individual `trigger.*` commands can be displayed using:

> `<command> --help`

<a id="storm-trigger-add"></a>


### trigger.add

The `trigger.add` command adds a trigger to a Cortex.

**Syntax:**

```mdstorm
trigger.add --help
```

<a id="storm-trigger-list"></a>


### trigger.list

The `trigger-list` command displays the set of triggers in the Cortex that the current user can view / modify based on their permissions. Triggers are displayed at the Storm CLI in tabular format, with columns including the user who created the trigger, the [Iden](../glossary.md#gloss-iden) of the trigger, the condition that fires the trigger (i.e., `node:add`), and the Storm query associated with the trigger.

Triggers are displayed in alphanumeric order by iden. Triggers are sorted upon Cortex initialization, so newly-created triggers will be displayed at the bottom of the list until the list is re-sorted the next time the Cortex is restarted.

**Syntax:**

```mdstorm
trigger.list --help
```

<a id="storm-trigger-mod"></a>


### trigger.mod

The `trigger.mod` command modifies the Storm query associated with a specific trigger. To modify a trigger, you must provide the first portion of the trigger's iden (i.e., enough of the iden that the trigger can be uniquely identified), which can be obtained using `trigger.list`.

> [!NOTE]
> Other aspects of the trigger, such as the condition used to fire the trigger or the tag or property associated with the trigger, cannot be modified once the trigger has been created. To change these aspects, you must delete and re-add the trigger.

**Syntax:**

```mdstorm
trigger.mod --help
```

<a id="storm-trigger-del"></a>


### trigger.del

The `trigger.del` command permanently removes a trigger from the Cortex. To delete a trigger, you must provide the first portion of the trigger's iden (i.e., enough of the iden that the trigger can be uniquely identified), which can be obtained using `trigger.list`.

**Syntax:**

```mdstorm
trigger.del --help
```

<a id="storm-uniq"></a>


## uniq

The `uniq` command removes duplicate results from a Storm query. By default, results are uniqued based on each node's node identifier (node ID / iden) so that only the first node with a given node ID is returned. (You can think of this as effectively deconflicting on a node's primary property.)

You can optionally specify a property, set of properties, or a variable as a parameter to unique the results based on that value / set of values instead of the node ID. Synapse will return the first node with the specified value or combination of values.

**Syntax:**

```mdstorm
uniq --help
```

**Examples:**

Lift all of the unique IP addresses that domains associated with the Fancy Bear threat group have resolved to:

```mdstorm --hide
[ inet:dns:a=( gdforum.info, 111.90.148.124 ) inet:dns:a=( live-settings.com, 209.99.40.222 ) inet:dns:a=( misdepatrment.com, 209.99.40.222 ) inet:dns:a=( drive-google.ga, 141.8.224.221 ) ] -> inet:fqdn [ +#rep.threatconnect.fancybear ]
```

```mdstorm --hide
inet:fqdn#rep.threatconnect.fancybear -> inet:dns:a -> inet:ip | uniq
```

``` text
inet:fqdn#rep.threatconnect.fancybear -> inet:dns:a -> inet:ip | uniq
```

Lift a set of network flow (`inet:flow`) nodes and unique (de-duplicate) them based on the source IP address:

```mdstorm --hide
[ inet:flow=( { "client": "tcp://1.1.1.1", "server": "tcp://2.2.2.2" } ) inet:flow=( { "client": "tcp://11.11.11.11", "server": "tcp://3.3.3.3" } ) inet:flow=( { "client": "tcp://1.1.1.1", "server": "tcp://4.4.4.4" } ) inet:flow=( { "client": "tcp://1.1.1.1", "server": "tcp://4.4.4.4" } ) inet:flow=( { "client": "tcp://121.121.121.121", "server": "tcp://2.2.2.2" } ) ]
```

```mdstorm --hide
inet:flow | uniq :client.ip
```

``` text
inet:flow | uniq :client.ip
```

Lift a set of network flow nodes and de-duplicate them based on each unique combination of source and destination IP addresses:

```mdstorm --hide
inet:flow | uniq ( :client, :server )
```

``` text
inet:flow | uniq ( :client, :server )
```

Nodes can be uniqued based on variables. Alert (`risk:alert`) nodes can be categorized in various ways. This includes `:priority` and `:severity` properties, both of which use a set of fixed text values (e.g., "low" vs. "highest") that correspond to integers (e.g., 20 vs. 50). These integer values could be joined together in a variable to provide a sample of alerts which have unique combinations of those values:

```mdstorm --hide
[ ( risk:alert=( { "name": "Cat sitting in front of monitor", "created": "2026/05/28 08:15:23" } ) :priority=20 :severity=20 ) ( risk:alert=( { "name": "Out of coffee", "created": "2026/03/16 16:20:44" } ) :priority=10 :severity=50 ) ( risk:alert=( { "name": "Laptop BIOS update bricked system", "created": "2025/12/19 13:22:47" } ) :priority=50 :severity=50 ) ( risk:alert=( { "name": "New version of favorite Power-Up released", "created": "2026/05/08 11:03:52" } ) :priority=50 :severity=50 ) ]
```

```mdstorm --hide
risk:alert:priority +:severity $pri=:priority $sev=:severity $value=( $pri, $sev ) | uniq $value
```

``` text
risk:alert:priority +:severity $pri=:priority $sev=:severity $value=( $pri, $sev ) | uniq $value
```

<a id="storm-uptime"></a>


## uptime

The `uptime` command displays the uptime for the Cortex or specified service.

**Syntax:**

```mdstorm
uptime --help
```

<a id="storm-vault"></a>


## vault

Storm includes `vault.*` commands that allow you to create and manage vaults (see [Vault](../glossary.md#gloss-vault)).

- [vault.add](storm_ref_cmd.md#storm-vault-add)
- [vault.list](storm_ref_cmd.md#storm-vault-list)
- [vault.set.configs](storm_ref_cmd.md#storm-vault-set-configs)
- [vault.set.perm](storm_ref_cmd.md#storm-vault-set-perm)
- [vault.set.secrets](storm_ref_cmd.md#storm-vault-set-secrets)
- [vault.del](storm_ref_cmd.md#storm-vault-del)

Help for individual `vault.*` commands can be displayed using:

> `<command> --help`

<a id="storm-vault-add"></a>


### vault.add

The `vault.add` command creates a new vault.

**Syntax:**

```mdstorm
vault.add --help
```

<a id="storm-vault-list"></a>


### vault.list

The `vault.list` command displays the available vaults.

**Syntax:**

```mdstorm
vault.list --help
```

<a id="storm-vault-set-configs"></a>


### vault.set.configs

The `vault.set.configs` sets configuration options for the specified vault.

**Syntax:**

```mdstorm
vault.set.configs --help
```

<a id="storm-vault-set-perm"></a>


### vault.set.perm

The `vault.set.perm` command grants or revokes permissions to a vault.

**Syntax:**

```mdstorm
vault.set.perm --help
```

<a id="storm-vault-set-secrets"></a>


### vault.set.secrets

The `vault.set.secrets` command sets the specified secret for the vault.

**Syntax:**

```mdstorm
vault.set.secrets --help
```

<a id="storm-vault-del"></a>


### vault.del

The `vault.del` command deletes a vault.

**Syntax:**

```mdstorm
vault.del --help
```

<a id="storm-version"></a>


## version

The `version` command displays the current version of Synapse and associated metadata.

**Syntax:**

```mdstorm
version --help
```

<a id="storm-view"></a>


## view

Storm includes `view.*` commands that allow you to work with views (see [View](../glossary.md#gloss-view)).

- [view.add](storm_ref_cmd.md#storm-view-add)
- [view.fork](storm_ref_cmd.md#storm-view-fork)
- [view.set](storm_ref_cmd.md#storm-view-set)
- [view.get](storm_ref_cmd.md#storm-view-get)
- [view.list](storm_ref_cmd.md#storm-view-list)
- [view.exec](storm_ref_cmd.md#storm-view-exec)
- [view.merge](storm_ref_cmd.md#storm-view-merge)
- [view.del](storm_ref_cmd.md#storm-view-del)

Help for individual `view.*` commands can be displayed using:

> `<command> --help`

<a id="storm-view-add"></a>


### view.add

The `view.add` command adds a view to the Cortex.

**Syntax:**

```mdstorm
view.add --help
```

<a id="storm-view-fork"></a>


### view.fork

The `view.fork` command forks an existing view from the Cortex. Forking a view creates a new view with a new writable layer on top of the set of layers from the previous (forked) view.

**Syntax:**

```mdstorm
view.fork --help
```

<a id="storm-view-set"></a>


### view.set

The `view.set` command sets a property on the specified view.

**Syntax:**

```mdstorm
view.set --help
```

<a id="storm-view-get"></a>


### view.get

The `view.get` command retrieves an existing view from the Cortex.

**Syntax:**

```mdstorm
view.get --help
```

<a id="storm-view-list"></a>


### view.list

The `view.list` command lists the views in the Cortex.

**Syntax:**

```mdstorm
view.list --help
```

<a id="storm-view-exec"></a>


### view.exec

The `view.exec` command executes a Storm query in the specified view.

**Behavior and Limitations**

The `view.exec` command creates its own execution environment (sub-runtime) to execute a Storm query in a different view. This results in a firm separation boundary between the source view and the destination view where nodes do not pass in or out across the `view.exec` boundary. Pipelines, events, messages, etc will NOT pass from the destination view to the source view or vice-versa. This includes `$lib.print(...)`, `$lib.warn(...)`, and other functions that may print to the CLI.

Variables declared before the `view.exec` are accessible in the destination view (including assignment). The interactive help example demonstrates this behavior:

``` text
// Move some tagged nodes to another view
inet:fqdn#foo.bar $fqdn=$node.value | view.exec 95d5f31f0fb414d2b00069d3b1ee64c6 { [ inet:fqdn=$fqdn ] }
```

Here we have `inet:fqdn` nodes with the tag `#foo.bar` being lifted and their value (not the node) is saved into the `$fqdn` variable. This variable is later accessible in the `view.exec` sub-query and used to create an `inet:fqdn` node in the destination view. If more than one `inet:fqdn` node with the tag `#foo.bar` exists, the `view.exec` command would be executed once for each node in the pipeline as expected. Again, the actual nodes will not be accessible in the `view.exec` query. Also note the sub-query executed in the `view.exec` may assign a different value back to `$fqdn` to be accessed by the source view (that doesn't happen in this example though).

Inline functions are bound to the scope they are declared in, and heavy objects (for example `View` or `Layer` objects) are bound to the scope they are instantiated in. For `view.exec`, this means that a function declared outside the `view.exec` command will still run in the original scope/view, not the view specified to `view.exec`.

**Syntax:**

```mdstorm
view.exec --help
```

<a id="storm-view-merge"></a>


### view.merge

The `view.merge` command merges **all** data from a forked view into its parent view.

Contrast with [merge](storm_ref_cmd.md#storm-merge) which can merge a subset of nodes.

**Syntax:**

```mdstorm
view.merge --help
```

<a id="storm-view-del"></a>


### view.del

The `view.del` command permanently deletes a view from the Cortex.

**Syntax:**

```mdstorm
view.del --help
```

<a id="storm-wget"></a>


## wget

The `wget` command retrieves content from one or more specified URLs. The command creates and yields `inet:urlfile` nodes and the retrieved content (`file:bytes`) is stored in the [Axon](../glossary.md#gloss-axon).

**Syntax:**

```mdstorm
wget --help
```
