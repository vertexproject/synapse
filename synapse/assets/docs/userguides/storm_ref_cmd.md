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

```stormdoc
storm> syn:cmd=movetag
syn:cmd=movetag
        :doc = Rename an entire tag tree and preserve time intervals.
```

<a id="storm-help"></a>

## help

The `help` command displays the list of available commands within the current instance of Synapse and a brief message describing each command. Help for individual commands is available via `<command> --help`. The `help` command can also be used to inspect information about [stormtypes-libs-header](../stormtypes_libs.md#stormtypes-libs-header) and [stormtypes-prim-header](../stormtypes_prims.md#stormtypes-prim-header).

**Syntax:**

```stormdoc
storm> help --help


List available information about Storm and brief descriptions of different items.

Notes:

    If an item is provided, this can be a string or a function.

Examples:

    // Get all available commands, libraries, types, and their brief descriptions.

    help

    // Only get commands which have "model" in the name.

    help model

    // Get help about the base Storm library

    help $lib

    // Get detailed help about a specific library or library function

    help --verbose $lib.print

    // Get detailed help about a named Storm type

    help --verbose str

    // Get help about a method from a $node object

    <inbound $node> help $node.tags



Usage: help [options] <item>

Options:

  --help                      : Display the command usage.
  -v                          : Display detailed help when available.

Arguments:

  [item]                      : List information about a subset of commands or a specific item.
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

```stormdoc
storm> aha.svc.list --help

List AHA services.

If the --nexus argument is given, the Cortex will attempt to connect to each service and report the Nexus offset of the service.

The ready column indicates that a service has entered into the realtime change window for synchronizing changes from its leader.

Usage: aha.svc.list [options] 

Options:

  --help                      : Display the command usage.
  --nexus                     : Try to connect to online services and report their nexus offset.
```

<a id="storm-aha-svc-stat"></a>

### aha.svc.stat

The `aha.svc.stat` command displays all information for an AHA service.

**Syntax:**

```stormdoc
storm> aha.svc.stat --help

Show all information for a specific AHA service.

If the --nexus argument is given, the Cortex will attempt to connect the service and report the Nexus offset of the service.

The ready value indicates that a service has entered into the realtime change window for synchronizing changes from its leader.
        

Usage: aha.svc.stat [options] <svc>

Options:

  --help                      : Display the command usage.
  --nexus                     : Try to connect to online services and report their nexus offset.

Arguments:

  <svc>                       : The service to inspect.
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

```stormdoc
storm> auth.gate.show --help



            Display users, roles, and permissions for an auth gate.

            Examples:
                // Display the users and roles with permissions to the top layer of the current view.
                auth.gate.show $lib.layer.get().iden

                // Display the users and roles with permissions to the current view.
                auth.gate.show $lib.view.get().iden
        

Usage: auth.gate.show [options] <gateiden>

Options:

  --help                      : Display the command usage.

Arguments:

  <gateiden>                  : The GUID of the auth gate.
```

<a id="storm-auth-perms-list"></a>

### auth.perms.list

The `auth.perms.list` command displays the set of permissions currently defined within the Cortex. This includes native Synapse permissions as well as any permissions associated with other packages and services, including Power-Ups. Each permission includes a brief description of the permission, the associated auth gate (e.g., 'cortex', 'layer') and the default state (true/allowed or false/denied).

**Syntax:**

```stormdoc
storm> auth.perms.list --help

Display a list of the current permissions defined within the Cortex.

Usage: auth.perms.list [options] 

Options:

  --help                      : Display the command usage.
  --find <find>               : A search string for permissions.
```

<a id="storm-auth-role-add"></a>

### auth.role.add

The `auth.role.add` command creates a role.

**Syntax:**

```stormdoc
storm> auth.role.add --help


            Add a role.

            Examples:

                // Add a role named "ninjas"
                auth.role.add ninjas
        

Usage: auth.role.add [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the role.
```

<a id="storm-auth-role-addrule"></a>

### auth.role.addrule

The `auth.role.addrule` command adds a rule (permission) to a role.

**Syntax:**

```stormdoc
storm> auth.role.addrule --help


            Add a rule to a role.

            Examples:

                // add an allow rule to the role "ninjas" for permission "foo.bar.baz"
                auth.role.addrule ninjas foo.bar.baz

                // add a deny rule to the role "ninjas" for permission "foo.bar.baz"
                auth.role.addrule ninjas "!foo.bar.baz"

                // add an allow rule to the role "ninjas" for permission "baz" at the first index.
                auth.role.addrule ninjas baz --index 0
        

Usage: auth.role.addrule [options] <name> <rule>

Options:

  --help                      : Display the command usage.
  --gate <gate>               : The auth gate id to add the rule to. (default: None)
  --index <index>             : Specify the rule location as a 0 based index. (default: None)

Arguments:

  <name>                      : The name of the role.
  <rule>                      : The rule string.
```

<a id="storm-auth-role-del"></a>

### auth.role.del

The `auth.role.del` command deletes a role.

**Syntax:**

```stormdoc
storm> auth.role.del --help


            Delete a role.

            Examples:

                // Delete a role named "ninjas"
                auth.role.del ninjas
        

Usage: auth.role.del [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the role.
```

<a id="storm-auth-role-delrule"></a>

### auth.role.delrule

The `auth.role.delrule` command removes a rule (permission) from a role.

**Syntax:**

```stormdoc
storm> auth.role.delrule --help


            Remove a rule from a role.

            Examples:

                // Delete the allow rule from the role "ninjas" for permission "foo.bar.baz"
                auth.role.delrule ninjas foo.bar.baz

                // Delete the deny rule from the role "ninjas" for permission "foo.bar.baz"
                auth.role.delrule ninjas "!foo.bar.baz"

                // Delete the rule at index 5 from the role "ninjas"
                auth.role.delrule ninjas --index  5
        

Usage: auth.role.delrule [options] <name> <rule>

Options:

  --help                      : Display the command usage.
  --gate <gate>               : The auth gate id to remove the rule from. (default: None)
  --index                     : Specify the rule as a 0 based index into the list of rules.

Arguments:

  <name>                      : The name of the role.
  <rule>                      : The rule string.
```

<a id="storm-auth-role-list"></a>

### auth.role.list

The `auth.role.list` lists all roles in the Cortex.

**Syntax:**

```stormdoc
storm> auth.role.list --help


            List all roles.

            Examples:

                // Display the list of all roles
                auth.role.list
        

Usage: auth.role.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-auth-role-mod"></a>

### auth.role.mod

The `auth.role.mod` modifies an existing role.

**Syntax:**

```stormdoc
storm> auth.role.mod --help


            Modify properties of a role.

            Examples:

                // Rename the "ninjas" role to "admins"
                auth.role.mod ninjas --name admins
        

Usage: auth.role.mod [options] <rolename>

Options:

  --help                      : Display the command usage.
  --name <name>               : The new name for the role.

Arguments:

  <rolename>                  : The name of the role.
```

<a id="storm-auth-role-show"></a>

### auth.role.show

The `auth.role.show` displays the details for a given role.

**Syntax:**

```stormdoc
storm> auth.role.show --help



            Display details for a given role by name.

            Examples:

                // Display details about the role "ninjas"
                auth.role.show ninjas
        

Usage: auth.role.show [options] <rolename>

Options:

  --help                      : Display the command usage.

Arguments:

  <rolename>                  : The name of the role.
```

<a id="storm-auth-user-add"></a>

### auth.user.add

The `auth.user.add` command creates a user.

**Syntax:**

```stormdoc
storm> auth.user.add --help


            Add a user.

            Examples:

                // Add a user named "visi" with the email address "visi@vertex.link"
                auth.user.add visi --email visi@vertex.link
        

Usage: auth.user.add [options] <name>

Options:

  --help                      : Display the command usage.
  --email <email>             : The user's email address. (default: None)

Arguments:

  <name>                      : The name of the user.
```

<a id="storm-auth-user-addrule"></a>

### auth.user.addrule

The `auth.user.addrule` command adds a rule (permission) to a user.

**Syntax:**

```stormdoc
storm> auth.user.addrule --help


            Add a rule to a user.

            Examples:

                // add an allow rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi foo.bar.baz

                // add a deny rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi "!foo.bar.baz"

                // add an allow rule to the user "visi" for permission "baz" at the first index.
                auth.user.addrule visi baz --index 0
        

Usage: auth.user.addrule [options] <name> <rule>

Options:

  --help                      : Display the command usage.
  --gate <gate>               : The auth gate id to grant permission on. (default: None)
  --index <index>             : Specify the rule location as a 0 based index. (default: None)

Arguments:

  <name>                      : The name of the user.
  <rule>                      : The rule string.
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

```stormdoc
storm> auth.user.allowed --help


            Show whether the user is allowed the given permission and why.

            The permission may be specified as either a dotted string or a list of permission parts.

            Examples:

                auth.user.allowed visi foo.bar

                auth.user.allowed visi (foo, bar)
        

Usage: auth.user.allowed [options] <username> <permname>

Options:

  --help                      : Display the command usage.
  --gate <gate>               : An auth gate to test the perms against.

Arguments:

  <username>                  : The name of the user.
  <permname>                  : The permission, as a dotted string or a list of permission parts.
```

<a id="storm-auth-user-delrule"></a>

### auth.user.delrule

The `auth.user.delrule` command removes a rule (permission) from a user.

**Syntax:**

```stormdoc
storm> auth.user.delrule --help


            Remove a rule from a user.

            Examples:

                // Delete the allow rule from the user "visi" for permission "foo.bar.baz"
                auth.user.delrule visi foo.bar.baz

                // Delete the deny rule from the user "visi" for permission "foo.bar.baz"
                auth.user.delrule visi "!foo.bar.baz"

                // Delete the rule at index 5 from the user "visi"
                auth.user.delrule visi --index  5
        

Usage: auth.user.delrule [options] <name> <rule>

Options:

  --help                      : Display the command usage.
  --gate <gate>               : The auth gate id to grant permission on. (default: None)
  --index                     : Specify the rule as a 0 based index into the list of rules.

Arguments:

  <name>                      : The name of the user.
  <rule>                      : The rule string.
```

<a id="storm-auth-user-grant"></a>

### auth.user.grant

The `auth.user.grant` command grants a role (and its associated permissions) to a user.

**Syntax:**

```stormdoc
storm> auth.user.grant --help


            Grant a role to a user.

            Examples:

                // Grant the role "ninjas" to the user "visi"
                auth.user.grant visi ninjas

                // Grant the role "ninjas" to the user "visi" at the first index.
                auth.user.grant visi ninjas --index 0

        

Usage: auth.user.grant [options] <username> <rolename>

Options:

  --help                      : Display the command usage.
  --index <index>             : Specify the role location as a 0 based index. (default: None)

Arguments:

  <username>                  : The name of the user.
  <rolename>                  : The name of the role.
```

<a id="storm-auth-user-list"></a>

### auth.user.list

The `auth.user.list` command displays all users in the Cortex.

**Syntax:**

```stormdoc
storm> auth.user.list --help


            List all users.

            Examples:

                // Display the list of all users
                auth.user.list
        

Usage: auth.user.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-auth-user-mod"></a>

### auth.user.mod

The `auth.user.mod` command modifies a user account.

**Syntax:**

```stormdoc
storm> auth.user.mod --help


            Modify properties of a user.

            Examples:

                // Rename the user "foo" to "bar"
                auth.user.mod foo --name bar

                // Make the user "visi" an admin
                auth.user.mod visi --admin (true)

                // Unlock the user "visi" and set their email to "visi@vertex.link"
                auth.user.mod visi --locked (false) --email visi@vertex.link

                // Grant admin access to user visi for the current view
                auth.user.mod visi --admin (true) --gate $lib.view.get().iden

                // Revoke admin access to user visi for the current view
                auth.user.mod visi --admin (false) --gate $lib.view.get().iden
        

Usage: auth.user.mod [options] <username>

Options:

  --help                      : Display the command usage.
  --name <name>               : The new name for the user.
  --email <email>             : The email address to set for the user.
  --passwd <passwd>           : The new password for the user. This is best passed into the runtime as a variable.
  --admin <admin>             : True to make the user and admin, false to remove their remove their admin status.
  --gate <gate>               : The auth gate iden to grant or revoke admin status on. Use in conjunction with `--admin
                                <boolean>`.
  --locked <locked>           : True to lock the user, false to unlock them.

Arguments:

  <username>                  : The name of the user.
```

<a id="storm-auth-user-revoke"></a>

### auth.user.revoke

The `auth.user.revoke` command revokes a role (and its associated permissions) from a user.

**Syntax:**

```stormdoc
storm> auth.user.revoke --help


            Revoke a role from a user.

            Examples:

                // Revoke the role "ninjas" from the user "visi"
                auth.user.revoke visi ninjas

        

Usage: auth.user.revoke [options] <username> <rolename>

Options:

  --help                      : Display the command usage.

Arguments:

  <username>                  : The name of the user.
  <rolename>                  : The name of the role.
```

<a id="storm-auth-user-show"></a>

### auth.user.show

The `auth.user.show` command displays information for a specific user.

**Syntax:**

```stormdoc
storm> auth.user.show --help


            Display details for a given user by name.

            Examples:

                // Display details about the user "visi"
                auth.user.show visi
        

Usage: auth.user.show [options] <username>

Options:

  --help                      : Display the command usage.

Arguments:

  <username>                  : The name of the user.
```

<a id="storm-background"></a>

## background

The `background` command allows you to execute a Storm query as a background task (e.g., to free up the CLI / Storm runtime for additional queries).

> [!NOTE]
> Use of `background` is a "fire-and-forget" process - any status messages (warnings or errors) are not returned to the console, and if the query is interrupted for any reason, it will not resume.

See also [parallel](storm_ref_cmd.md#storm-parallel).

**Syntax:**

```stormdoc
storm> background --help


Execute a query pipeline as a background task.
NOTE: Variables are passed through but nodes are not


Usage: background [options] <query>

Options:

  --help                      : Display the command usage.

Arguments:

  <query>                     : The query to execute in the background.
```

<a id="storm-batch"></a>

## batch

The `batch` command allows you to run a Storm query with batched sets of nodes.

Note that in most cases, Storm queries are meant to operate in a "streaming" manner on individual nodes. This command is intended to be used in cases such as querying external APIs that support aggregate queries (i.e., an API that allows you to query 100 objects in a single API call as part of the API's quota system).

**Syntax:**

```stormdoc
storm> batch --help


Run a query with batched sets of nodes.

The batched query will have the set of inbound nodes available in the
variable $nodes.

This command also takes a conditional as an argument. If the conditional
evaluates to true, the nodes returned by the batched query will be yielded,
if it evaluates to false, the inbound nodes will be yielded after executing the
batched query.

NOTE: This command is intended to facilitate use cases such as queries to external
      APIs with aggregate node values to reduce quota consumption. As this command
      interrupts the node stream, it should be used carefully to avoid unintended
      slowdowns in the pipeline.

Example:

    // Execute a query with batches of 5 nodes, then yield the inbound nodes
    batch (false) --size 5 { $lib.print($nodes) }


Usage: batch [options] <cond> <query>

Options:

  --help                      : Display the command usage.
  --size <size>               : The number of nodes to collect before running the batched query (max 10000). (default:
                                10)

Arguments:

  <cond>                      : The conditional value for the yield option.
  <query>                     : The query to execute with batched nodes.
```

<a id="storm-copyto"></a>

## copyto

The `copyto` command allows you to copy nodes from the current view to a specified target view. Nodes are copied to the write layer (the topmost layer) in the target view.

When copying nodes, the history of the node (i.e., changes to the node, timestamps, associated user) in the **source** view (the view layer(s)) is preserved; the changes written to the **target** view's write layer are owned by the user executing the `copyto` command.

See the [movenodes](storm_ref_cmd.md#storm-movenodes) command to move nodes between layers in the same layer stack.

> [!NOTE]
> The `copyto` command, like the `movenodes` command, is meant to be used by Synapse **administrators** in specific use cases.

**Syntax:**

```stormdoc
storm> copyto --help


Copy nodes from the current view into another view.

Examples:

    // Copy all nodes tagged with #cno.mal.redtree to the target view.

    #cno.mal.redtree | copyto 33c971ac77943da91392dadd0eec0571


Usage: copyto [options] <view>

Options:

  --help                      : Display the command usage.
  --no-data                   : Do not copy node data to the destination view.

Arguments:

  <view>                      : The destination view ID to copy the nodes to.
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

```stormdoc
storm> cortex.httpapi.index --help

Set the index of an Extended HTTP API endpoint.

Examples:

    // Move an endpoint to the first index.
    cortex.httpapi.index 60e5ba38e90958fd8e2ddd9e4730f16b 0

    // Move an endpoint to the third index.
    cortex.httpapi.index dd9e4730f16b60e5ba58fd8e2d38e909 2


Usage: cortex.httpapi.index [options] <iden> <index>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : The iden of the endpoint to move. This will also match iden prefixes or name prefixes.
  <index>                     : Specify the endpoint location as a 0 based index.
```

<a id="storm-cortex-httpapi-list"></a>

### cortex.httpapi.list

The `cortex.httpapi.list` command is used to list the Extended HTTP API endpoints.

**Syntax:**

```stormdoc
storm> cortex.httpapi.list --help

List Extended HTTP API endpoints

Usage: cortex.httpapi.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-cortex-httpapi-stat"></a>

### cortex.httpapi.stat

The `cortex.httpapi.stat` command is used to show the detailed information for a single Extended HTTP API Endpoint.

**Syntax:**

```stormdoc
storm> cortex.httpapi.stat --help

Get details for an Extended HTTP API endpoint.

Usage: cortex.httpapi.stat [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : The iden of the endpoint to inspect. This will also match iden prefixes or name prefixes.
```

<a id="storm-count"></a>

## count

The `count` command enumerates the number of nodes returned from a given Storm query and displays the final tally. The associated nodes can optionally be displayed with the `--yield` switch.

**Syntax:**

```stormdoc
storm> count --help


Iterate through query results, and print the resulting number of nodes
which were lifted. This does not yield the nodes counted, unless the
--yield switch is provided.

Example:

    # Count the number of IPV4 nodes with a given ASN.
    inet:ipv4:asn=20 | count

    # Count the number of IPV4 nodes with a given ASN and yield them.
    inet:ipv4:asn=20 | count --yield



Usage: count [options] 

Options:

  --help                      : Display the command usage.
  --yield                     : Yield inbound nodes.
```

**Examples:**

Count the number of IP addresses that Trend Micro associates with the threat group Earth Preta (`#rep.trend.earth_preta`):

```stormdoc
storm> inet:ip#rep.trend.earth_preta | count
Counted 5 nodes.
```

Count the IP addresses Trend Micro associates with Earth Preta and yield the nodes:

```stormdoc
storm> inet:ip#rep.trend.earth_preta | count --yield
inet:ip=66.129.222.1
        :type = unicast
        :version = 4
        #rep.trend.earth_preta
inet:ip=184.82.164.104
        :type = unicast
        :version = 4
        #rep.trend.earth_preta
inet:ip=209.161.249.125
        :type = unicast
        :version = 4
        #rep.trend.earth_preta
inet:ip=69.90.65.240
        :type = unicast
        :version = 4
        #rep.trend.earth_preta
inet:ip=70.62.232.98
        :type = unicast
        :version = 4
        #rep.trend.earth_preta
Counted 5 nodes.
```

Count the number of DNS A records for the domain `woot.com` where the lift produces no results:

```stormdoc
storm> inet:dns:a:fqdn=woot.com | count
Counted 0 nodes.
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

```stormdoc
storm> cron.add --help


Add a recurring cron job to a cortex.

Notes:
    All times are interpreted as UTC.

    The period argument uses a simplified syntax:
        <periodicity>[/<value>...][@<time>]

    Periodicity:
        - minutely: Every minute
        - hourly: Every hour (defaults to minute 0)
        - daily: Every day (defaults to 00:00 UTC)
        - weekly: Every week (defaults to Monday at 00:00 UTC)
        - monthly: Every month (defaults to day 1 at 00:00 UTC)
        - yearly: Every year (defaults to January 1 at 00:00 UTC)

    Value:
        - minutely/N: Every N minutes
        - hourly/N: Every N hours
        - daily/N: Every N days
        - weekly/day1,day2: Specific weekdays (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
        - monthly/day1,day2: Specific days of month (1-31, negative counts from end)

    Time:
        - HH:MM (24-hour format, e.g., 14:30 for 2:30 PM)
        - HH (hour only, minute defaults to 0)
        - :MM (minute only, for hourly periods)
        - :MM,MM,... (comma-separated minutes, e.g., :15,45 runs at minute 15 and 45)

Examples:
    # Run every minute
    cron.add minutely { $lib.print(minutely) }

    # Run every 5 minutes
    cron.add minutely/5 { $lib.print(minutely) }

    # Run every day at midnight UTC
    cron.add daily { $lib.print(daily) }

    # Run every day at 14:30 UTC
    cron.add daily@14:30 { $lib.print(daily) }

    # Run every 2 hours at minute 0
    cron.add hourly/2@:00 { $lib.print(hourly) }

    # Run every hour at minute 25
    cron.add hourly@:25 { $lib.print(hourly) }

    # Run every hour at minute 24 and minute 45
    cron.add hourly@:24,45 { $lib.print(hourly) }

    # Run every Monday and Wednesday at 10:00 UTC
    cron.add weekly/mon,wed@10:00 { $lib.print(weekly) }

    # Run on the 1st and 15th of every month at noon UTC
    cron.add monthly/1,15@12:00 { $lib.print(monthly) }

    # Run on the last day of every month at 00:00 UTC
    cron.add monthly/-1 { $lib.print(monthly) }

    # Run every year on January 1st at midnight UTC
    cron.add yearly { $lib.print(yearly) }

    # Run every year on January 1st at 07:00 UTC
    cron.add yearly@07 { $lib.print(yearly) }

    # Run every year on January 1st at 12:21 UTC
    cron.add yearly@12:21 { $lib.print(yearly) }

    # Run every year on May 14th at midnight UTC
    cron.add yearly/05-14 { $lib.print(yearly) }

    # Run every year on November 12th at 13:43 UTC
    cron.add yearly/11-14@13:43 { $lib.print(yearly) }

    # Run every year on July 1st at 04:44 UTC, November 12th at 15:00 UTC, and January 4th at midnight UTC
    cron.add yearly/07-01@04:44,11-12@15,01-04 { $lib.print(yearly) }


Usage: cron.add [options] <period> <query>

Options:

  --help                      : Display the command usage.
  --affinity <affinity>       : AHA service name to preferentially run the cron job on. (default: None)
  --name <name>               : An optional name for the cron job.
  --iden <iden>               : Fixed iden to assign to the cron job
  --doc <doc>                 : An optional doc string for the cron job.
  --view <view>               : View to run the cron job against.

Arguments:

  <period>                    : The recurrence period for the cron job.
  <query>                     : Query for the cron job to execute.
```

<a id="storm-cron-at"></a>

### cron.at

The `cron.at` command creates a non-recurring (one-time) cron job within a Cortex.

**Syntax:**

```stormdoc
storm> cron.at --help


Adds a non-recurring cron job.

Notes:
    This command accepts one or more time specifications followed by exactly
    one storm query in curly braces.  Each time specification may be in synapse
    time delta format (e.g --day +1) or synapse time format (e.g.
    20501217030432101).  Seconds will be ignored, as cron jobs' granularity is
    limited to minutes.

    All times are interpreted as UTC.

    The other option for time specification is a relative time from now.  This
    consists of a plus sign, a positive integer, then one of 'minutes, hours,
    days'.

    Note that the record for a cron job is stored until explicitly deleted via
    "cron.del".

Examples:
    # Run a storm query in 5 minutes
    cron.at --minute +5 {[inet:ipv4=1]}

    # Run a storm query tomorrow and in a week
    cron.at --day +1,+7 {[inet:ipv4=1]}

    # Run a query at the end of the year Zulu
    cron.at --dt 20181231Z2359 {[inet:ipv4=1]}


Usage: cron.at [options] <query>

Options:

  --help                      : Display the command usage.
  --minute <minute>           : Minute(s) to execute at.
  --hour <hour>               : Hour(s) to execute at.
  --day <day>                 : Day(s) to execute at.
  --dt <dt>                   : Datetime(s) to execute at.
  --now                       : Execute immediately.
  --iden <iden>               : A set iden to assign to the new cron job
  --view <view>               : View to run the cron job against
  --affinity <affinity>       : AHA service name to preferentially run the cron job on. (default: None)

Arguments:

  <query>                     : Query for the cron job to execute.
```

<a id="storm-cron-cleanup"></a>

### cron.cleanup

The `cron.cleanup` command can be used to remove any one-time cron jobs ("at" jobs) that have completed.

**Syntax:**

```stormdoc
storm> cron.cleanup --help

Delete all completed at jobs

Usage: cron.cleanup [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-cron-list"></a>

### cron.list

The `cron.list` command displays the set of cron jobs in the Cortex that the current user can view / modify based on their permissions.

Cron jobs are displayed in alphanumeric order by job [Iden](../glossary.md#gloss-iden). Jobs are sorted upon Cortex initialization, so newly-created jobs will be displayed at the bottom of the list until the list is re-sorted the next time the Cortex is restarted.

**Syntax:**

```stormdoc
storm> cron.list --help

List existing cron jobs in the cortex.

Usage: cron.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-cron-stat"></a>

### cron.stat

The `cron.stat` command displays statistics for an individual cron job and provides more detail on an individual job vs. `cron.list`, including any errors and the interval at which the job executes. To view the stats for a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

**Syntax:**

```stormdoc
storm> cron.stat --help

Gives detailed information about a cron job.

Usage: cron.stat [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.
```

<a id="storm-cron-mod"></a>

### cron.mod

The `cron.mod` command modifies properties of an existing cron job. To modify a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

> [!NOTE]
> Some aspects of the cron job, such as its schedule for execution, cannot be modified once the job has been created. To change these aspects you must delete and re-add the job.

**Syntax:**

```stormdoc
storm> cron.mod --help


Modify an existing cron job's properties.

Notes:
    All times are interpreted as UTC.

    The --period argument uses the same syntax as cron.add:
        <periodicity>[/<value>...][@<time>]

    Any combination of properties may be modified at the same time.

Examples:
    # Modify only the query
    cron.mod <iden> --storm { $lib.print(new_query) }

    # Modify only the period (change to daily at 14:30 UTC)
    cron.mod <iden> --period daily@14:30

    # Modify both query and period
    cron.mod <iden> --period weekly/mon,wed@10:00 --storm { $lib.print(updated) }

    # Change to hourly period at minute 25 and enable the cron job
    cron.mod <iden> --period hourly@:25 --enabled true

    # Change to run every 5 minutes
    cron.mod <iden> --period minutely/5


Usage: cron.mod [options] <iden>

Options:

  --help                      : Display the command usage.
  --view <view>               : View to move the cron job to.
  --storm <storm>             : New Storm query for the cron job.
  --user <user>               : New user for the cron job to run as.
  --doc <doc>                 : New doc string for the cron job.
  --name <name>               : New name for the cron job.
  --enabled <enabled>         : True to enable the cron job, False to disable.
  --loglevel <loglevel>       : New logging level for the cron job. (choices: DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --period <period>           : The new recurrence period for the cron job.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.
```

<a id="storm-cron-del"></a>

### cron.del

The `cron.del` command permanently removes a cron job from the Cortex. To delete a job, you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained using `cron.list`.

**Syntax:**

```stormdoc
storm> cron.del --help

Delete a cron job from the cortex.

Usage: cron.del [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.
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

```stormdoc
storm> delnode --help


Delete nodes produced by the previous query logic.

(no nodes are returned)

Example

    inet:fqdn=vertex.link | delnode


Usage: delnode [options] 

Options:

  --help                      : Display the command usage.
  --force                     : Force delete even if it causes broken references (requires admin).
  --delbytes                  : For file:bytes nodes, remove the bytes associated with the sha256 property from the
                                axon as well if present.
  --deledges                  : Delete N2 light edges before deleting the node.
```

**Examples:**

Delete the node for the domain `woowoo.com`:

```stormdoc
storm> inet:fqdn=woowoo.com | delnode
```

Forcibly delete all nodes with the `#testing` tag:

```stormdoc
storm> #testing | delnode --force
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

```stormdoc
storm> diff --help


Generate a list of nodes with changes in the top layer of the current view.

Examples:

    // Lift all nodes with any changes

    diff

    // Lift ou:org nodes that were added in the top layer.

    diff --prop ou:org

    // Lift inet:ipv4 nodes with the :asn property modified in the top layer.

    diff --prop inet:ipv4:asn

    // Lift the nodes with the tag #cno.mal.redtree added in the top layer.

    diff --tag cno.mal.redtree

    // Lift nodes by multiple tags (results are uniqued)

    diff --tag cno.mal.redtree rep.vt

    // Lift nodes by tags specified in a list variable

    $tags=(cno.mal.redtree, rep.vt) diff --tag $tags


Usage: diff [options] 

Options:

  --help                      : Display the command usage.
  --tag [<tag> ...]           : Lift only nodes with the given tag (or tags) in the top layer. (default: None)
  --prop <prop>               : Lift nodes with changes to the given property the top layer. (default: None)
```

<a id="storm-divert"></a>

## divert

The `divert` command allows Storm to either consume a generator or yield its results based on a conditional.

**Syntax:**

```stormdoc
storm> divert --help


Either consume a generator or yield it's results based on a conditional.

NOTE: This command is purpose built to facilitate the --yield convention
      common to storm commands.

NOTE: The genr argument must not be a function that returns, else it will
      be invoked for each inbound node.

Example:
    divert $cmdopts.yield $fooBarBaz()


Usage: divert [options] <cond> <genr>

Options:

  --help                      : Display the command usage.
  --size <size>               : The max number of times to iterate the generator. (default: None)

Arguments:

  <cond>                      : The conditional value for the yield option.
  <genr>                      : The generator function value that yields nodes.
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

```stormdoc
storm> dmon.list --help

List the storm daemon queries running in the cortex.

Usage: dmon.list [options] 

Options:

  --help                      : Display the command usage.
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

```stormdoc
storm> edges.del --help


Bulk delete light edges from input nodes.

Examples:

    # Delete all "foo" light edges from an inet:ipv4
    inet:ipv4=1.2.3.4 | edges.del foo

    # Delete light edges with any verb from a node
    inet:ipv4=1.2.3.4 | edges.del *

    # Delete all "foo" light edges to an inet:ipv4
    inet:ipv4=1.2.3.4 | edges.del foo --n2


Usage: edges.del [options] <verb>

Options:

  --help                      : Display the command usage.
  --n2                        : Delete light edges where input node is N2 instead of N1.

Arguments:

  <verb>                      : The verb of light edges to delete.
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

```stormdoc
storm> gen.campaign --help

Lift (or create) an entity:campaign based on the name and reporter.

Usage: gen.campaign [options] <name> <reporter>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the campaign.
  <reporter>                  : The name of the reporting entity.
```

<a id="storm-gen-country"></a>

### gen.country

The `gen.country` command locates (lifts) or creates a `pol:country` node based on the two-letter ISO-3166 country code (`pol:country:iso2`).

**Syntax:**

```stormdoc
storm> gen.country --help


            Lift (or create) a pol:country node based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the pol:country node which represents the country of Ukraine.
                gen.country ua
        

Usage: gen.country [options] <code>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <code>                      : The 2 letter ISO-3166 country code.
```

<a id="storm-gen-government"></a>

### gen.government

The `gen.government` command locates (lifts) the `ou:org` node representing a country's government (i.e., the organization set for the `pol:country:government` property) or creates the node (and sets the `pol:country:government` property) if it does not exist, based on the two-letter ISO-3166 country code (`pol:country:iso2`).

**Syntax:**

```stormdoc
storm> gen.government --help


            Lift (or create) the ou:org node representing a country's government based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the ou:org node which represents the Government of Ukraine.
                gen.government ua
        

Usage: gen.government [options] <code>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <code>                      : The 2 letter ISO-3166 country code.
```

<a id="storm-gen-industry"></a>

### gen.industry

The `gen.industry` command locates (lifts) or creates an `ind:industry` node based on the industry name (`ind:industry:name` and / or `ind:industry:names`) and the name of the reporter (`ind:industry:reporter:name`).

**Syntax:**

```stormdoc
storm> gen.industry --help


            Lift (or create) an ind:industry node based on the industry name and reporter name.
        

Usage: gen.industry [options] <name> <reporter>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The industry name.
  <reporter>                  : The name of the reporting entity.
```

<a id="storm-gen-language"></a>

### gen.language

The `gen.language` command locates (lifts) or creates a `lang:language` node based on the language name (`lang:language:name` and / or `lang:language:names`).

**Syntax:**

```stormdoc
storm> gen.language --help

Lift (or create) a lang:language node based on the name.

Usage: gen.language [options] <name>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the language.
```

<a id="storm-gen-org"></a>

### gen.org

The `gen.org` command locates (lifts) or creates an `ou:org` node based on the organization name (`ou:org:name` and / or `ou:org:names`).

**Syntax:**

```stormdoc
storm> gen.org --help

Lift (or create) an ou:org node based on the organization name.

Usage: gen.org [options] <name>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the organization.
```

<a id="storm-gen-place"></a>

### gen.place

The `gen.place` command locates (lifts) or creates a `geo:place` node based on the place name (`geo:place:name` and / or `geo:place:names` properties).

**Syntax:**

```stormdoc
storm> gen.place --help


            Lift (or create) a geo:place node based on the name.
        

Usage: gen.place [options] <name>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the place.
```

<a id="storm-gen-software"></a>

### gen.software

The `gen.software` command locates (lifts) or creates an `it:software` node based on the software name (`it:software:name` and / or `it:software:names`) and the name of the reporter (`it:software:reporter:name`).

**Syntax:**

```stormdoc
storm> gen.software --help

Lift (or create) an it:software node based on the software name and reporter.

Usage: gen.software [options] <name> <reporter>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the software.
  <reporter>                  : The name of the reporting entity.
```

<a id="storm-gen-threat"></a>

### gen.threat

The `gen.threat` command locates (lifts) or creates a `risk:threat` node using the name of the threat group (`risk:threat:name` and / or `risk:threat:names`) and the name of the reporter (`risk:threat:reporter:name`).

**Syntax:**

```stormdoc
storm> gen.threat --help


            Lift (or create) a risk:threat node based on the threat name and reporter name.

            Examples:

                // Yield a risk:threat node for the threat cluster "APT1" reported by "Mandiant".
                gen.threat apt1 mandiant
        

Usage: gen.threat [options] <name> <reporter>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <name>                      : The name of the threat cluster. For example: APT1
  <reporter>                  : The name of the reporting entity. For example: Mandiant
```

<a id="storm-gen-vuln"></a>

### gen.vuln

The `gen.vuln` command locates (lifts) or creates a `risk:vuln` node using the Common Vulnerabilities and Exposures (CVE) number associated with the vulnerability (`risk:vuln:id`) and the name of the reporter (`risk:vuln:reporter:name`).

**Syntax:**

```stormdoc
storm> gen.vuln --help


            Lift (or create) a risk:vuln node based on the CVE and reporter name.

            Examples:

                // Yield a risk:vuln node for CVE-2012-0157 reported by Mandiant.
                gen.vuln CVE-2012-0157 Mandiant
        

Usage: gen.vuln [options] <cve> <reporter>

Options:

  --help                      : Display the command usage.
  --try                       : Type normalization will fail silently instead of raising an exception.

Arguments:

  <cve>                       : The CVE identifier.
  <reporter>                  : The name of the reporting entity.
```

<a id="storm-graph"></a>

## graph

The `graph` command generates a subgraph based on a specified set of nodes and parameters.

**Syntax:**

```stormdoc
storm> graph --help


Generate a subgraph from the given input nodes and command line options.

Example:

    Using the graph command::

        inet:fqdn | graph
                    --degrees 2
                    --filter { -#nope }
                    --pivot { <(seen)- meta:source }
                    --form-pivot inet:fqdn {<- * | limit 20}
                    --form-pivot inet:fqdn {-> * | limit 20}
                    --form-filter inet:fqdn {-inet:fqdn:issuffix=1}
                    --form-pivot syn:tag {-> *}
                    --form-pivot * {-> #}



Usage: graph [options] 

Options:

  --help                      : Display the command usage.
  --degrees <degrees>         : How many degrees to graph out. (default: 1)
  --pivot <pivot>             : Specify a storm pivot for all nodes. (must quote) (default: [])
  --filter <filter>           : Specify a storm filter for all nodes. (must quote) (default: [])
  --no-edges                  : Do not include light weight edges in the per-node output.
  --form-pivot <form_pivot>   : Specify a <form> <pivot> form specific pivot. (default: [])
  --form-filter <form_filter> : Specify a <form> <filter> form specific filter. (default: [])
  --no-refs                   : Disable automatic in-model pivoting with node.getNodeRefs().
  --yield-filtered            : Yield nodes which would be filtered. This still performs pivots to collect edge
                                data,but does not yield pivoted nodes.
  --no-filter-input           : Do not drop input nodes if they would match a filter.
```

<a id="storm-intersect"></a>

## intersect

The `intersect` command returns the intersection of the results from performing a pivot and/or traversal operation on multiple inbound nodes. In other words, `intersect` will return the subset of results that are **common** to each of the inbound nodes.

**Syntax:**

```stormdoc
storm> intersect --help


Yield an intersection of the results of running inbound nodes through a pivot.

NOTE:
    This command must consume the entire inbound stream to produce the intersection.
    This type of stream consuming before yielding results can cause the query to appear
    laggy in comparison with normal incremental stream operations.

Examples:

    // Show the it:mitre:attack:technique nodes common to several groups

    it:mitre:attack:group*in=(G0006, G0007) | intersect { -> it:mitre:attack:technique }


Usage: intersect [options] <query>

Options:

  --help                      : Display the command usage.

Arguments:

  <query>                     : The pivot query to run each inbound node through.
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

```stormdoc
storm> layer.add --help

Add a layer to the cortex.

Usage: layer.add [options] 

Options:

  --help                      : Display the command usage.
  --readonly                  : Should the layer be readonly.
  --growsize <growsize>       : Amount to grow the map size when necessary.
  --cache-size <cache:size>   : Number of storage nodes to cache.
  --name <name>               : The name of the layer.
```

<a id="storm-layer-set"></a>

### layer.set

The `layer.set` command sets an option for the specified layer.

**Syntax**

```stormdoc
storm> layer.set --help

Set a layer option.

Usage: layer.set [options] <iden> <name> <valu>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Iden of the layer to modify.
  <name>                      : The name of the layer property to set.
  <valu>                      : The value to set the layer property to.
```

<a id="storm-layer-get"></a>

### layer.get

The `layer.get` command retrieves the specified layer from a Cortex.

**Syntax**

```stormdoc
storm> layer.get --help

Get a layer from the cortex.

Usage: layer.get [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  [iden]                      : Iden of the layer to get. If no iden is provided, the main layer will be returned.
```

<a id="storm-layer-list"></a>

### layer.list

The `layer.list` command lists the available layers in a Cortex.

**Syntax**

```stormdoc
storm> layer.list --help

List the layers in the cortex.

Usage: layer.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-layer-del"></a>

### layer.del

The `layer.del` command deletes a layer from a Cortex.

**Syntax**

```stormdoc
storm> layer.del --help

Delete a layer from the cortex.

Usage: layer.del [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Iden of the layer to delete.
```

<a id="storm-layer-pull-add"></a>

### layer.pull.add

The `layer.pull.add` command adds a pull configuration to a layer.

**Syntax**

```stormdoc
storm> layer.pull.add --help

Add a pull configuration to a layer.

Usage: layer.pull.add [options] <layr> <src>

Options:

  --help                      : Display the command usage.
  --offset <offset>           : Layer offset to begin pulling from (default: 0)

Arguments:

  <layr>                      : Iden of the layer to pull to.
  <src>                       : Telepath url of the source layer to pull from.
```

<a id="storm-layer-pull-list"></a>

### layer.pull.list

The `layer.pull.list` command lists the pull configurations for a layer.

**Syntax**

```stormdoc
storm> layer.pull.list --help

Get a list of the pull configurations for a layer.

Usage: layer.pull.list [options] <layr>

Options:

  --help                      : Display the command usage.

Arguments:

  <layr>                      : Iden of the layer to retrieve pull configurations for.
```

<a id="storm-layer-pull-del"></a>

### layer.pull.del

The `layer.pull.del` command deletes a pull configuration from a layer.

**Syntax**

```stormdoc
storm> layer.pull.del --help

Delete a pull configuration from a layer.

Usage: layer.pull.del [options] <layr> <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <layr>                      : Iden of the layer to modify.
  <iden>                      : Iden of the pull configuration to delete.
```

<a id="storm-layer-push-add"></a>

### layer.push.add

The `layer.push.add` command adds a push configuration to a layer.

**Syntax**

```stormdoc
storm> layer.push.add --help

Add a push configuration to a layer.

Usage: layer.push.add [options] <layr> <dest>

Options:

  --help                      : Display the command usage.
  --offset <offset>           : Layer offset to begin pushing from. (default: 0)

Arguments:

  <layr>                      : Iden of the layer to push from.
  <dest>                      : Telepath url of the layer to push to.
```

<a id="storm-layer-push-list"></a>

### layer.push.list

The `layer.push.list` command lists the push configurations for a layer.

**Syntax**

```stormdoc
storm> layer.push.list --help

Get a list of the push configurations for a layer.

Usage: layer.push.list [options] <layr>

Options:

  --help                      : Display the command usage.

Arguments:

  <layr>                      : Iden of the layer to retrieve push configurations for.
```

<a id="storm-layer-push-del"></a>

### layer.push.del

The `layer.push.del` command deletes a push configuration from a layer.

**Syntax**

```stormdoc
storm> layer.push.del --help

Delete a push configuration from a layer.

Usage: layer.push.del [options] <layr> <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <layr>                      : Iden of the layer to modify.
  <iden>                      : Iden of the push configuration to delete.
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

```stormdoc
storm> lift.byverb --help


Lift nodes from the current view by an light edge verb.

Examples:

    # Lift all the n1 nodes for the light edge "foo"
    lift.byverb "foo"

    # Lift all the n2 nodes for the light edge "foo"
    lift.byverb --n2 "foo"

Notes:

    Only a single instance of a node will be yielded from this command
    when that node is lifted via the light edge membership.


Usage: lift.byverb [options] <verb>

Options:

  --help                      : Display the command usage.
  --n2                        : Lift by the N2 value instead of N1 value.

Arguments:

  <verb>                      : The edge verb to lift nodes by.
```

<a id="storm-limit"></a>

## limit

The `limit` command restricts the number of nodes returned from a given Storm query to the specified number of nodes.

**Syntax:**

```stormdoc
storm> limit --help


Limit the number of nodes generated by the query in the given position.

Example:

    inet:ipv4 | limit 10


Usage: limit [options] <count>

Options:

  --help                      : Display the command usage.

Arguments:

  <count>                     : The maximum number of nodes to yield.
```

**Example:**

Lift a single IP address that Palo Alto associates with the threat group Stately Taurus (`#rep.paloalto.stately_taurus`):

```stormdoc
storm> inet:ip#rep.paloalto.stately_taurus | limit 1
inet:ip=67.53.148.77
        :type = unicast
        :version = 4
        #rep.paloalto.stately_taurus
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

```stormdoc
storm> macro.list --help


List the macros set on the cortex.


Usage: macro.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-macro-set"></a>

### macro.set

The `macro.set` command creates (or modifies) a macro in a Cortex.

**Syntax:**

```stormdoc
storm> macro.set --help


Set a macro definition in the cortex.

Variables can also be used that are defined outside the definition.

Examples:
    macro.set foobar ${ [+#foo] }

    # Use variable from parent scope
    macro.set bam ${ [ inet:ipv4=$val ] }
    $val=1.2.3.4 macro.exec bam


Usage: macro.set [options] <name> <storm>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the macro to set.
  <storm>                     : The storm command string or embedded query to set.
```

<a id="storm-macro-get"></a>

### macro.get

The `macro.get` command retrieves and displays the specified macro.

**Syntax:**

```stormdoc
storm> macro.get --help


Display the storm query for a macro in the cortex.


Usage: macro.get [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the macro to display.
```

<a id="storm-macro-exec"></a>

### macro.exec

The `macro.exec` command executes the specified macro.

**Syntax:**

```stormdoc
storm> macro.exec --help


Execute a named macro.

Example:

    inet:ipv4#cno.threat.t80 | macro.exec enrich_foo



Usage: macro.exec [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the macro to execute
```

<a id="storm-macro-del"></a>

### macro.del

The `macro.del` command deletes the specified macro from a Cortex.

**Syntax:**

```stormdoc
storm> macro.del --help


Remove a macro definition from the cortex.


Usage: macro.del [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the macro to delete.
```

<a id="storm-max"></a>

## max

The `max` command returns the node(s) from a given set that contain the highest value(s) for a specified secondary property, tag interval, or variable. By default a single node is returned. Use `--size` to return more than one node; results are yielded in **descending** order.

If `max` is used on a property whose type is an interval (`ival`) and you only specify the property name (e.g., `max :seen`), `max` will return the highest value of the interval's `.max` virtual property (`:seen.max`) by default.

**Syntax:**

```stormdoc
storm> max --help


Consume nodes and yield the nodes with the highest values for an expression.

Notes:

    Values are ordered using the ordering defined by their type. Strings order
    lexically and case insensitively. Intervals order by the end being sought.
    it:version values order by epoch, major, minor, patch, and pre-release tier
    only, so versions which differ only within a pre-release tier (such as
    1.0.0-alpha.1 and 1.0.0-alpha.2) or only by build metadata compare equal.
    Values which their type cannot order are skipped.

Examples:

    // Yield the file:bytes node with the highest :size property
    file:bytes#foo.bar | max :size

    // Yield the file:bytes node with the highest value for $tick
    file:bytes#foo.bar +:seen ($tick, $tock) = :seen | max $tick

    // Yield the it:dev:str node with the longest length
    it:dev:str | max $lib.len($node.value)

    // Yield the two most recent inet:dns:ns records (descending order)
    inet:fqdn=vertex.link -> inet:dns:ns | max .seen --size 2

    // Yield the doc:report node with the highest :version
    doc:report | max :version



Usage: max [options] <valu>

Options:

  --help                      : Display the command usage.
  --size <size>               : The number of nodes to yield (max 100). Nodes are yielded in descending order.
                                (default: 1)

Arguments:

  <valu>                      : The property or variable to use for comparison.
```

**Examples:**

Return the DNS A record for `woot.com` with the most recent `:seen` value:

```stormdoc
storm> inet:dns:a:fqdn=woot.com | max :seen
inet:dns:a=('woot.com', '246.21.93.214')
        :fqdn = woot.com
        :ip = 246.21.93.214
        :seen = 2014-01-05T02:34:56Z - 2014-10-19T06:15:04Z
```

Return the two most recent DNS A records for `woot.com`, in descending order by `:seen`

```stormdoc
storm> inet:dns:a:fqdn=woot.com | max :seen --size 2
inet:dns:a=('woot.com', '246.21.93.214')
        :fqdn = woot.com
        :ip = 246.21.93.214
        :seen = 2014-01-05T02:34:56Z - 2014-10-19T06:15:04Z
inet:dns:a=('woot.com', '107.21.53.159')
        :fqdn = woot.com
        :ip = 107.21.53.159
        :seen = 2014-08-13T00:00:00Z - 2014-08-14T00:00:00Z
```

Return the DNS A record for `woot.com` with the longest duration:

```stormdoc
storm> inet:dns:a:fqdn=woot.com | max :seen.duration
inet:dns:a=('woot.com', '246.21.93.214')
        :fqdn = woot.com
        :ip = 246.21.93.214
        :seen = 2014-01-05T02:34:56Z - 2014-10-19T06:15:04Z
```

Return a WHOIS record for the most recently registered (`:created`) FQDN associated with the threat cluster Sparkling Unicorn (`#cno.threat.sparkling_unicorn`):

```stormdoc
storm> inet:fqdn#cno.threat.sparkling_unicorn -> inet:whois:record | max :created
inet:whois:record=5200d9b0914e2bfe8bac590aa3f517fc
        :created = 2026-03-26T13:00:00Z
        :fqdn = derp.net
```

<a id="storm-merge"></a>

## merge

The `merge` command takes a subset of nodes from a forked view and merges them down to the next layer. The nodes can optionally be reviewed without actually merging them.

Contrast with [view.merge](storm_ref_cmd.md#storm-view-merge) for merging the entire contents of a forked view.

See the [view](storm_ref_cmd.md#storm-view) and [layer](storm_ref_cmd.md#storm-layer) commands for working with views and layers.

**Syntax:**

```stormdoc
storm> merge --help


Merge edits from the incoming nodes down to the next layer.

NOTE: This command requires the current view to be a fork.

NOTE: The arguments for including/excluding tags can accept tag glob
      expressions for specifying tags. For more information on tag glob
      expressions, check the Synapse documentation for $node.globtags().

NOTE: If --wipe is specified, and there are nodes that cannot be merged,
      they will be skipped (with a warning printed) and removed when
      the top layer is replaced. This should occur infrequently, for example,
      when a form is locked due to deprecation, a form no longer exists,
      or the data at rest fails normalization.

Examples:

    // Having tagged a new #cno.mal.redtree subgraph in a forked view...

    #cno.mal.redtree | merge --apply

    // Print out what the merge command *would* do but dont.

    #cno.mal.redtree | merge

    // Merge any org nodes with changes in the top layer.

    diff | +ou:org | merge --apply

    // Merge all tags other than cno.* from ou:org nodes with edits in the
    // top layer.

    diff | +ou:org | merge --only-tags --exclude-tags cno.** --apply

    // Merge only tags rep.vt.* and rep.whoxy.* from ou:org nodes with edits
    // in the top layer.

    diff | +ou:org | merge --include-tags rep.vt.* rep.whoxy.* --apply

    // Lift only inet:ipv4 nodes with a changed :asn property in top layer
    // and merge all changes.

    diff --prop inet:ipv4:asn | merge --apply

    // Lift only nodes with an added #cno.mal.redtree tag in the top layer and merge them.

    diff --tag cno.mal.redtree | merge --apply


Usage: merge [options] 

Options:

  --help                      : Display the command usage.
  --apply                     : Execute the merge changes.
  --wipe                      : Replace the top layer in the view with a fresh layer.
  --no-tags                   : Do not merge tags/tagprops or syn:tag nodes.
  --only-tags                 : Only merge tags/tagprops or syn:tag nodes.
  --include-tags [<include_tags> ...]: Include specific tags/tagprops or syn:tag nodes when merging, others are ignored. Tag
                                glob expressions may be used to specify the tags. (default: [])
  --exclude-tags [<exclude_tags> ...]: Exclude specific tags/tagprops or syn:tag nodes from merge.Tag glob expressions may be
                                used to specify the tags. (default: [])
  --include-props [<include_props> ...]: Include specific props when merging, others are ignored. (default: [])
  --exclude-props [<exclude_props> ...]: Exclude specific props from merge. (default: [])
  --diff                      : Enumerate all changes in the current layer.
```

<a id="storm-min"></a>

## min

The `min` command returns the node(s) from a given set that contain the lowest value(s) for a specified secondary property, tag interval, or variable. By default a single node is returned. Use `--size` to return more than one node; results are yielded in **ascending** order.

If `min` is used on a property whose type is an interval (`ival`) and you only specify the property name (e.g., `min :seen`), `min` will return the lowest value of the interval's `.min` virtual property (`:seen.min`) by default.

**Syntax:**

```stormdoc
storm> min --help


Consume nodes and yield the nodes with the lowest values for an expression.

Notes:

    Values are ordered using the ordering defined by their type. Strings order
    lexically and case insensitively. Intervals order by the end being sought.
    it:version values order by epoch, major, minor, patch, and pre-release tier
    only, so versions which differ only within a pre-release tier (such as
    1.0.0-alpha.1 and 1.0.0-alpha.2) or only by build metadata compare equal.
    Values which their type cannot order are skipped.

Examples:

    // Yield the file:bytes node with the lowest :size property
    file:bytes#foo.bar | min :size

    // Yield the file:bytes node with the lowest value for $tick
    file:bytes#foo.bar +:seen ($tick, $tock) = :seen | min $tick

    // Yield the it:dev:str node with the shortest length
    it:dev:str | min $lib.len($node.value)

    // Yield the two oldest inet:dns:ns records (ascending order)
    inet:fqdn=vertex.link -> inet:dns:ns | min .seen --size 2

    // Yield the doc:report node with the lowest :version
    doc:report | min :version



Usage: min [options] <valu>

Options:

  --help                      : Display the command usage.
  --size <size>               : The number of nodes to yield (max 100). Nodes are yielded in ascending order. (default:
                                1)

Arguments:

  <valu>                      : The property or variable to use for comparison.
```

**Examples:**

Return the DNS A record for `woot.com` with the oldest `:seen` value:

```stormdoc
storm> inet:dns:a:fqdn=woot.com min :seen
inet:dns:a=('woot.com', '75.101.146.4')
        :fqdn = woot.com
        :ip = 75.101.146.4
        :seen = 2013-09-21T00:00:00Z - 2013-09-22T00:00:00Z
```

Return the two oldest DNS A records for `woot.com`, in ascending order by `:seen`:

```stormdoc
storm> inet:dns:a:fqdn=woot.com | min :seen --size 2
inet:dns:a=('woot.com', '75.101.146.4')
        :fqdn = woot.com
        :ip = 75.101.146.4
        :seen = 2013-09-21T00:00:00Z - 2013-09-22T00:00:00Z
inet:dns:a=('woot.com', '246.21.93.214')
        :fqdn = woot.com
        :ip = 246.21.93.214
        :seen = 2014-01-05T02:34:56Z - 2014-10-19T06:15:04Z
```

Return the DNS A record for `woot.com` with the shortest duration:

```stormdoc
storm> inet:dns:a:fqdn=woot.com | min :seen.duration
inet:dns:a=('woot.com', '53.25.18.25')
        :fqdn = woot.com
        :ip = 53.25.18.25
        :seen = 2014-08-13T12:44:55Z - 2014-08-13T18:09:22Z
```

Return a WHOIS record for the earliest registered (`:created`) FQDN associated with the threat cluster Sparkling Unicorn (`#cno.threat.sparkling_unicorn`):

```stormdoc
storm> inet:fqdn#cno.threat.sparkling_unicorn -> inet:whois:record | min :created
inet:whois:record=b3f03e02c398aeeafe40b80c9fbed15c
        :created = 2025-10-23T09:00:00Z
        :fqdn = hurr.com
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

```stormdoc
storm> model.deprecated.check --help

Check for lock status and the existence of deprecated model elements

Usage: model.deprecated.check [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-model-deprecated-lock"></a>

### model.deprecated.lock

The `model.deprecated.lock` command allows you to lock or unlock (e.g., disallow or allow the use of) deprecated model elements in a Cortex.

**Syntax:**

```stormdoc
storm> model.deprecated.lock --help

Edit lock status of deprecated model elements.

Usage: model.deprecated.lock [options] <name>

Options:

  --help                      : Display the command usage.
  --unlock                    : Unlock rather than lock the deprecated property.

Arguments:

  <name>                      : The deprecated form or property name to lock or * to lock all.
```

<a id="storm-model-deprecated-locks"></a>

### model.deprecated.locks

The `model.deprecated.locks` command displays the lock status of all deprecated model elements.

**Syntax:**

```stormdoc
storm> model.deprecated.locks --help

Display lock status of deprecated model elements.

Usage: model.deprecated.locks [options] 

Options:

  --help                      : Display the command usage.
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

```stormdoc
storm> movenodes --help


Move storage nodes between layers.

Storage nodes will be removed from the source layers and the resulting
storage node in the destination layer will contain the merged values (merged
in bottom up layer order by default).

By default, when the resulting merged value is a tombstone, any current value
in the destination layer will be deleted and the tombstone will be removed. The
--preserve-tombstones option may be used to add the tombstone to the destination
layer in addition to deleting any current value.

Examples:

    // Move storage nodes for ou:org nodes to the top layer

    ou:org | movenodes --apply

    // Print out what the movenodes command *would* do but dont.

    ou:org | movenodes

    // In a view with many layers, only move storage nodes from the bottom layer
    // to the top layer.

    $layers = $lib.view.get().layers
    $top = $layers.0.iden
    $bot = $layers."-1".iden

    ou:org | movenodes --srclayers $bot --destlayer $top

    // In a view with many layers, move storage nodes to the top layer and
    // prioritize values from the bottom layer over the other layers.

    $layers = $lib.view.get().layers
    $top = $layers.0.iden
    $mid = $layers.1.iden
    $bot = $layers.2.iden

    ou:org | movenodes --precedence $bot $top $mid


Usage: movenodes [options] 

Options:

  --help                      : Display the command usage.
  --apply                     : Execute the move changes.
  --srclayers [<srclayers> ...]: Specify layers to move storage nodes from (defaults to all below the top layer)
                                (default: None)
  --destlayer <destlayer>     : Layer to move storage nodes to (defaults to the top layer) (default: None)
  --precedence [<precedence> ...]: Layer precedence for resolving conflicts (defaults to bottom up) (default: None)
  --preserve-tombstones       : Add tombstones to the destination layer in addition to deleting the current value.
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

```stormdoc
storm> movetag --help


Rename an entire tag tree and preserve time intervals.

Example:

    movetag foo.bar baz.faz.bar


Usage: movetag [options] <oldtag> <newtag>

Options:

  --help                      : Display the command usage.

Arguments:

  <oldtag>                    : The tag tree to rename.
  <newtag>                    : The new tag tree name.
```

**Examples:**

Move the tag named `#research` to `#internal.research`:

```stormdoc
storm> movetag research internal.research
moved tags on 1 nodes.
```

Move the tag tree `#aka.fireeye.malware` to `#rep.feye.mal`:

```stormdoc
storm> movetag aka.fireeye.malware rep.feye.mal
moved tags on 1 nodes.
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

```stormdoc
storm> nodes.import --help

Import a nodes file hosted at a URL into the cortex. Yields created nodes.

Usage: nodes.import [options] <urls>

Options:

  --help                      : Display the command usage.
  --no-ssl-verify             : Ignore SSL certificate validation errors.

Arguments:

  [<urls> ...]                : URL(s) to fetch nodes file from
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

```stormdoc
storm> note.add --help

Add a new meta:note node and link it to the inbound nodes using an -(about)> edge.

Usage: note.add [options] <text>

Options:

  --help                      : Display the command usage.
  --type <type>               : The note type.
  --yield                     : Yield the newly created meta:note node.

Arguments:

  <text>                      : The note text to add to the nodes.
```

**Usage Notes:**

> [!NOTE]
> Synapse's data and analytical models are meant to represent a broad range of data and information in a structured (and therefore **queryable**) way. As free form notes are counter to this structured approach, we recommend using `meta:note` nodes as an exception rather than a regular practice.

<a id="storm-once"></a>

## once

The `once` command is used to ensure a given node is processed by the associated Storm command only once, even if the same command is executed in a different, independent Storm query. The `once` command uses [Node Data](../glossary.md#gloss-node-data) to keep track of the associated Storm command's execution, so `once` is specific to the [View](../glossary.md#gloss-view) in which it is executed. You can override the single-execution feature of `once` with the `--asof` parameter.

**Syntax:**

```stormdoc
storm> once --help


The once command is used to filter out nodes which have already been processed
via the use of a named key. It includes an optional parameter to allow the node
to pass the filter again after a given amount of time.

For example, to run an enrichment command on a set of nodes just once:

    file:bytes#my.files | once enrich:foo | enrich.foo

The once command filters out any nodes which have previously been through any other
use of the "once" command using the same <name> (in this case "enrich:foo").

You may also specify the --asof option to allow nodes to pass the filter after a given
amount of time. For example, the following command will allow any given node through
every 2 days:

    file:bytes#my.files | once enrich:foo --asof "-2 days" | enrich.foo

Use of "--asof now" or any future date or positive relative time offset will always
allow the node to pass the filter.

State tracking data for the once command is stored as nodedata which is stored in your
view's write layer, making it view-specific. So if you have two views, A and B, and they
do not share any layers between them, and you execute this query in view A:

    inet:ipv4=8.8.8.8 | once enrich:address | enrich.baz

And then you run it in view B, the node will still pass through the once command to the
enrich.baz portion of the query because the tracking data for the once command does not
yet exist in view B.


Usage: once [options] <name>

Options:

  --help                      : Display the command usage.
  --asof <asof>               : The associated time the name was updated/performed. (default: None)

Arguments:

  <name>                      : Name of the action to only perform once.
```

<a id="storm-parallel"></a>

## parallel

The Storm `parallel` command allows you to execute a Storm query using a specified number of query pipelines. This can improve performance for some queries.

See also [background](storm_ref_cmd.md#storm-background).

**Syntax:**

```stormdoc
storm> parallel --help


Execute part of a query pipeline in parallel.
This can be useful to minimize round-trip delay during enrichments.

Examples:
    inet:ipv4#foo | parallel { $place = $lib.import(foobar).lookup(:latlong) [ :place=$place ] }

NOTE: Storm variables set within the parallel query pipelines do not interact.

NOTE: If there are inbound nodes to the parallel command, parallel pipelines will be created as each node
      is processed, up to the number specified by --size. If the number of nodes in the pipeline is less
      than the value specified by --size, additional pipelines with no inbound node will not be created.
      If there are no inbound nodes to the parallel command, the number of pipelines specified by --size
      will always be created.


Usage: parallel [options] <query>

Options:

  --help                      : Display the command usage.
  --size <size>               : The number of parallel Storm pipelines to execute. (default: 8)

Arguments:

  <query>                     : The query to execute in parallel.
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

```stormdoc
storm> pkg.list --help

List the storm packages loaded in the cortex.

Usage: pkg.list [options] 

Options:

  --help                      : Display the command usage.
  --verbose                   : Display build time for each package.
```

<a id="storm-pkg-load"></a>

### pkg.load

The `pgk.load` command loads the specified package into the Cortex.

**Syntax:**

```stormdoc
storm> pkg.load --help

Load a storm package from an HTTP URL.

Usage: pkg.load [options] <url>

Options:

  --help                      : Display the command usage.
  --raw                       : Response JSON is a raw package definition without an envelope.
  --verify                    : Enforce code signature verification on the storm package.
  --ssl-noverify              : Specify to disable SSL verification of the server.

Arguments:

  <url>                       : The HTTP URL to load the package from.
```

<a id="storm-pkg-del"></a>

### pkg.del

The `pkg.del` command removes a Storm package from the Cortex.

**Syntax:**

```stormdoc
storm> pkg.del --help

Remove a storm package from the cortex.

Usage: pkg.del [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name (or name prefix) of the package to remove.
```

<a id="storm-pkg-docs"></a>

### pkg.docs

The `pkg.docs` command displays the documentation for a Storm package.

**Syntax:**

```stormdoc
storm> pkg.docs --help

Display documentation included in a storm package.

Usage: pkg.docs [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name (or name prefix) of the package.
```

<a id="storm-pkg-perms-list"></a>

### pkg.perms.list

The `pkg.perms.list` command lists the permissions declared by a Storm package.

**Syntax:**

```stormdoc
storm> pkg.perms.list --help

List any permissions declared by the package.

Usage: pkg.perms.list [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name (or name prefix) of the package.
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

```stormdoc
storm> queue.add --help

Add a queue to the cortex.

Usage: queue.add [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The name of the new queue.
```

<a id="storm-queue-list"></a>

### queue.list

The `queue.list` command lists each queue in the Cortex.

**Syntax:**

```stormdoc
storm> queue.list --help

List the queues in the cortex.

Usage: queue.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-queue-del"></a>

### queue.del

The `queue.del` command removes a queue from the Cortex.

**Syntax:**

```stormdoc
storm> queue.del --help

Remove a queue from the cortex.

Usage: queue.del [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : The iden of the queue to remove.
```

<a id="storm-runas"></a>

## runas

The `runas` command allows you to execute a Storm query as a specified user.

> [!NOTE]
> The `runas` command requires **admin** permissions.

**Syntax:**

```stormdoc
storm> runas --help


Execute a storm query as a specified user.

NOTE: This command requires admin privileges.

NOTE: Heavy objects (for example a View or Layer) are bound to the context which they
      are instantiated in and methods on them will be run using the user in that
      context. This means that executing a method on a variable containing a heavy
      object which was instantiated outside of the runas command and then used
      within the runas command will check the permissions of the outer user, not
      the one specified by the runas command.

Examples:

    // Create a node as another user.
    runas someuser { [ inet:fqdn=foo.com ] }


Usage: runas [options] <user> <storm>

Options:

  --help                      : Display the command usage.
  --asroot                    : Propagate asroot to query subruntime.

Arguments:

  <user>                      : The user name or iden to execute the storm query as.
  <storm>                     : The storm query to execute.
```

<a id="storm-scrape"></a>

## scrape

The `scrape` command parses one or more secondary properties of the inbound node(s) and attempts to identify ("scrape") common forms from the content, creating the nodes if they do not already exist. This is useful (for example) for extracting forms such as email addresses, domains, URLs, hashes, etc. from unstructured text.

The `--refs` switch can be used to optionally link the source nodes(s) to the scraped forms via `-(refs)>` light edges.

By default, the `scrape` command will return the nodes that it received as input. The `--yield` option can be used to return the scraped nodes rather than the input nodes.

**Syntax:**

```stormdoc
storm> scrape --help


Use textual properties of existing nodes to find other easily recognizable nodes.

Examples:

    # Scrape properties from inbound nodes and create standalone nodes.
    inet:search:query | scrape

    # Scrape properties from inbound nodes and make refs light edges to the scraped nodes.
    inet:search:query | scrape --refs

    # Scrape only the :engine and :text props from the inbound nodes.
    inet:search:query | scrape :text :engine

    # Scrape the primary property from the inbound nodes.
    it:dev:str | scrape $node.repr()

    # Scrape properties inbound nodes and yield newly scraped nodes.
    inet:search:query | scrape --yield

    # Skip re-fanging text before scraping.
    inet:search:query | scrape --skiprefang

    # Limit scrape to specific forms.
    inet:search:query | scrape --forms (inet:fqdn, inet:ipv4)


Usage: scrape [options] <values>

Options:

  --help                      : Display the command usage.
  --refs                      : Create refs light edges to any scraped nodes from the input node
  --yield                     : Include newly scraped nodes in the output
  --skiprefang                : Do not remove de-fanging from text before scraping
  --forms <forms>             : Only scrape values which match specific forms. (default: [])

Arguments:

  [<values> ...]              : Specific relative properties or variables to scrape
```

**Example:**

Scrape the text of a social media post (`inet:service:message`) and create nodes for common forms found in the text:

```stormdoc
storm> inet:service:message | scrape :text
inet:service:message=c7b00606bd374d4cd9d925d0696e325e
        :platform = 723636292813abbc9884384d3c0caa9f
        :text = IP address 8.8.8.8 and FQDN woot.com seen doing bad things
```

Scrape the text of a social media post for FQDNs and IP addresses, link the nodes to the original post, and return (yield) the created nodes:

```stormdoc
storm> inet:service:message | scrape :text --forms (inet:fqdn, inet:ip) --refs --yield
inet:ip=8.8.8.8
        :type = unicast
        :version = 4
inet:fqdn=woot.com
        :domain = com
        :host = woot
        :issuffix = false
        :iszone = true
        :zone = woot.com
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

```stormdoc
storm> service.add --help

Add a storm service to the cortex.

Usage: service.add [options] <name> <url>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The cell type name of the service.
  <url>                       : The telepath URL for the remote service.
```

<a id="storm-service-list"></a>

### service.list

The `service.list` command lists each Storm service in the Cortex.

**Syntax:**

```stormdoc
storm> service.list --help

List the storm services configured in the cortex.

Usage: service.list [options] 

Options:

  --help                      : Display the command usage.
```

<a id="storm-service-del"></a>

### service.del

The `service.del` command removes a Storm service from the Cortex.

**Syntax:**

```stormdoc
storm> service.del --help

Remove a storm service from the cortex.

Usage: service.del [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The cell type name of the service.
```

<a id="storm-sleep"></a>

## sleep

The `sleep` command adds a delay in returning each result for a given Storm query. By default, query results are streamed back and displayed as soon as they arrive for optimal performance. A `sleep` delay effectively slows the display of results.

> `sleep` may be useful in cases such as querying rate-limited APIs.

**Syntax:**

```stormdoc
storm> sleep --help


Introduce a delay between returning each result for the storm query.

NOTE: This is mostly used for testing / debugging.

Example:

    #foo.bar | sleep 0.5



Usage: sleep [options] <delay>

Options:

  --help                      : Display the command usage.

Arguments:

  <delay>                     : Delay in floating point seconds.
```

**Example:**

- Retrieve email nodes from a Cortex every second:

```stormdoc
storm> inet:email sleep 1.0
inet:email=bar@gmail.com
        :fqdn = gmail.com
        :username = bar
inet:email=baz@gmail.com
        :fqdn = gmail.com
        :username = baz
inet:email=foo@gmail.com
        :fqdn = gmail.com
        :username = foo
```

<a id="storm-spin"></a>

## spin

The `spin` command is used to suppress the output of a Storm query. `Spin` simply consumes all nodes sent to the command, so no nodes are output to the CLI. This allows you to execute a Storm query and view messages and results without displaying the associated nodes.

**Syntax:**

```stormdoc
storm> spin --help


Iterate through all query results, but do not yield any.
This can be used to operate on many nodes without returning any.

Example:

    foo:bar:size=20 [ +#hehe ] | spin



Usage: spin [options] 

Options:

  --help                      : Display the command usage.
```

**Example:**

Add the tag `#int.research` to any FQDN containing the string `firefox` but do not display the nodes.

```stormdoc
storm> inet:fqdn~=firefox [ +#int.research ] | spin
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

```stormdoc
storm> stats.countby --help


Tally occurrences of values and display a bar chart of the results.

Examples:

    // Show counts of entity:name values referenced by media:news nodes.
    doc:report -(refs)> entity:name | stats.countby

    // Show counts of ASN values in a set of IPs.
    inet:ip#myips | stats.countby :asn

    // Show counts of attacker names for risk:compromise nodes.
    risk:compromise | stats.countby :attacker::name


Usage: stats.countby [options] <valu>

Options:

  --help                      : Display the command usage.
  --reverse                   : Display results in ascending instead of descending order.
  --size <size>               : Maximum number of bars to display. (default: None)
  --char <char>               : Character to use for bars. (default: #)
  --bar-width <bar_width>     : Width of the bars to display. (default: 50)
  --label-max-width <label_max_width>: Maximum width of the labels to display. (default: None)
  --yield                     : Yield inbound nodes.
  --by-name                   : Print stats sorted by name instead of count.

Arguments:

  [valu]                      : A relative property or variable to tally.
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

```stormdoc
storm> tag.prune --help


Prune a tag (or tags) from nodes.

This command will delete the tags specified as parameters from incoming nodes,
as well as all of their parent tags that don't have other tags as children.

For example, given a node with the tags:

    #parent
    #parent.child
    #parent.child.grandchild

Pruning the parent.child.grandchild tag would remove all tags. If the node had
the tags:

    #parent
    #parent.child
    #parent.child.step
    #parent.child.grandchild

Pruning the parent.child.grandchild tag will only remove the parent.child.grandchild
tag as the parent tags still have other children.

Examples:

    # Prune the parent.child.grandchild tag
    inet:ipv4=1.2.3.4 | tag.prune parent.child.grandchild


Usage: tag.prune [options] <tags>

Options:

  --help                      : Display the command usage.

Arguments:

  [<tags> ...]                : Names of tags to prune.
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

```stormdoc
storm> task.list --help

List running tasks on the Cortex and any mirrors.

Usage: task.list [options] 

Options:

  --help                      : Display the command usage.
  --verbose                   : Enable verbose output.
```

<a id="storm-task-kill"></a>

### task.kill

The `task.kill` command can be used to terminate an executing task. The command requires the [Iden](../glossary.md#gloss-iden) of the task to be terminated, which can be obtained with [task.list](storm_ref_cmd.md#storm-task-list).

**Syntax:**

```stormdoc
storm> task.kill --help

Kill a running task on the Cortex or a mirror.

Usage: task.kill [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid task iden is accepted.
```

<a id="storm-tee"></a>

## tee

The `tee` command executes multiple Storm queries on the inbound nodes and returns the combined result set.

**Syntax:**

```stormdoc
storm> tee --help


Execute multiple Storm queries on each node in the input stream, joining output streams together.

Commands are executed in order they are given; unless the ``--parallel`` switch is provided.

Examples:

    # Perform a pivot out and pivot in on a inet:ivp4 node
    inet:ipv4=1.2.3.4 | tee { -> * } { <- * }

    # Also emit the inbound node
    inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }

    # Execute multiple enrichment queries in parallel.
    inet:ipv4=1.2.3.4 | tee -p { enrich.foo } { enrich.bar } { enrich.baz }



Usage: tee [options] <query>

Options:

  --help                      : Display the command usage.
  --join                      : Emit inbound nodes after processing storm queries.
  --parallel                  : Run the storm queries in parallel instead of sequence. The node output order is not
                                guaranteed.

Arguments:

  [<query> ...]               : Specify a query to execute on the input nodes.
```

**Examples:**

Return the set of FQDNs and IP addresses associated with a set of DNS A records:

```stormdoc
storm> inet:fqdn:zone=mydomain.com -> inet:dns:a | tee { -> inet:fqdn } { -> inet:ip }
inet:fqdn=foo.mydomain.com
        :domain = mydomain.com
        :host = foo
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=8.8.8.8
        :type = unicast
        :version = 4
inet:fqdn=bar.mydomain.com
        :domain = mydomain.com
        :host = bar
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=34.56.78.90
        :type = unicast
        :version = 4
inet:fqdn=baz.mydomain.com
        :domain = mydomain.com
        :host = baz
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=127.0.0.2
        :type = loopback
        :version = 4
```

Return the set of FQDNs and IP addresses associated with a set of DNS A records along with the original DNS A records:

```stormdoc
storm> inet:fqdn:zone=mydomain.com -> inet:dns:a | tee --join { -> inet:fqdn } { -> inet:ip }
inet:fqdn=foo.mydomain.com
        :domain = mydomain.com
        :host = foo
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=8.8.8.8
        :type = unicast
        :version = 4
inet:dns:a=('foo.mydomain.com', '8.8.8.8')
        :fqdn = foo.mydomain.com
        :ip = 8.8.8.8
inet:fqdn=bar.mydomain.com
        :domain = mydomain.com
        :host = bar
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=34.56.78.90
        :type = unicast
        :version = 4
inet:dns:a=('bar.mydomain.com', '34.56.78.90')
        :fqdn = bar.mydomain.com
        :ip = 34.56.78.90
inet:fqdn=baz.mydomain.com
        :domain = mydomain.com
        :host = baz
        :issuffix = false
        :iszone = false
        :zone = mydomain.com
inet:ip=127.0.0.2
        :type = loopback
        :version = 4
inet:dns:a=('baz.mydomain.com', '127.0.0.2')
        :fqdn = baz.mydomain.com
        :ip = 127.0.0.2
```

**Usage Notes:**

- `tee` can take an arbitrary number of Storm queries (i.e., 1 to n queries) as arguments.

<a id="storm-tree"></a>

## tree

The `tree` command recursively performs the specified pivot until no additional nodes are returned.

**Syntax:**

```stormdoc
storm> tree --help


Walk elements of a tree using a recursive pivot.

Examples:

    # pivot upward yielding each FQDN
    inet:fqdn=www.vertex.link | tree { :domain -> inet:fqdn }


Usage: tree [options] <query>

Options:

  --help                      : Display the command usage.

Arguments:

  <query>                     : The pivot query
```

**Example:**

List the full set of tags in the `cno` tag tree.

```stormdoc
storm> syn:tag=cno | tree { $node.value -> syn:tag:up }
syn:tag=cno
        :base = cno
        :depth = 0
syn:tag=cno.threat
        :base = threat
        :depth = 1
        :up = cno
syn:tag=cno.threat.sparkling_unicorn
        :base = sparkling_unicorn
        :depth = 2
        :up = cno.threat
syn:tag=cno.ttp
        :base = ttp
        :depth = 1
        :up = cno
syn:tag=cno.ttp.phish
        :base = phish
        :depth = 2
        :up = cno.ttp
syn:tag=cno.mal
        :base = mal
        :depth = 1
        :up = cno
syn:tag=cno.mal.redtree
        :base = redtree
        :depth = 2
        :up = cno.mal
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

```stormdoc
storm> trigger.add --help


Add a trigger to the cortex.

Notes:
    Valid values for condition are:
        * tag:add
        * tag:del
        * node:add
        * node:del
        * prop:set
        * edge:add
        * edge:del

When condition is tag:add or tag:del, you may optionally provide a form name
to restrict the trigger to fire only on tags added or deleted from nodes of
those forms.

The added tag is provided to the query in the ``$auto`` dictionary variable under
``$auto.opts.tag``.

Simple one level tag globbing is supported, only at the end after a period,
that is aka.* matches aka.foo and aka.bar but not aka.foo.bar. aka* is not
supported.

When the condition is edge:add or edge:del, you may optionally provide a
form name or a destination form name to only fire on edges added or deleted
from nodes of those forms.

Examples:
    # Adds a tag to every inet:ipv4 added
    trigger.add node:add --form inet:ipv4 {[ +#mytag ]}

    # Adds a tag #todo to every node as it is tagged #aka
    trigger.add tag:add --tag aka {[ +#todo ]}

    # Adds a tag #todo to every inet:ipv4 as it is tagged #aka
    trigger.add tag:add --form inet:ipv4 --tag aka {[ +#todo ]}

    # Adds a tag #todo to the N1 node of every refs edge add
    trigger.add edge:add --verb refs {[ +#todo ]}

    # Adds a tag #todo to the N1 node of every seen edge delete, provided that
    # both nodes are of form file:bytes
    trigger.add edge:del --verb seen --form file:bytes --n2form file:bytes {[ +#todo ]}


Usage: trigger.add [options] <condition> <storm>

Options:

  --help                      : Display the command usage.
  --form <form>               : Form to fire on.
  --tag <tag>                 : Tag to fire on.
  --prop <prop>               : Property to fire on.
  --verb <verb>               : Edge verb to fire on.
  --n2form <n2form>           : The form of the n2 node to fire on.
  --async                     : Make the trigger run in the background.
  --disabled                  : Create the trigger in disabled state.
  --name <name>               : Human friendly name of the trigger.
  --view <view>               : The view to add the trigger to.

Arguments:

  <condition>                 : Condition for the trigger.
  <storm>                     : Storm query for the trigger to execute.
```

<a id="storm-trigger-list"></a>

### trigger.list

The `trigger-list` command displays the set of triggers in the Cortex that the current user can view / modify based on their permissions. Triggers are displayed at the Storm CLI in tabular format, with columns including the user who created the trigger, the [Iden](../glossary.md#gloss-iden) of the trigger, the condition that fires the trigger (i.e., `node:add`), and the Storm query associated with the trigger.

Triggers are displayed in alphanumeric order by iden. Triggers are sorted upon Cortex initialization, so newly-created triggers will be displayed at the bottom of the list until the list is re-sorted the next time the Cortex is restarted.

**Syntax:**

```stormdoc
storm> trigger.list --help

List existing triggers in the cortex.

Usage: trigger.list [options] 

Options:

  --help                      : Display the command usage.
  --all                       : List every trigger in every readable view, rather than just the current view.
```

<a id="storm-trigger-mod"></a>

### trigger.mod

The `trigger.mod` command modifies the Storm query associated with a specific trigger. To modify a trigger, you must provide the first portion of the trigger's iden (i.e., enough of the iden that the trigger can be uniquely identified), which can be obtained using `trigger.list`.

> [!NOTE]
> Other aspects of the trigger, such as the condition used to fire the trigger or the tag or property associated with the trigger, cannot be modified once the trigger has been created. To change these aspects, you must delete and re-add the trigger.

**Syntax:**

```stormdoc
storm> trigger.mod --help

Modify an existing trigger.

Usage: trigger.mod [options] <iden>

Options:

  --help                      : Display the command usage.
  --view <view>               : View to move the trigger to.
  --storm <storm>             : New Storm query for the trigger.
  --user <user>               : User to run the trigger as.
  --async <async>             : Make the trigger run in the background.
  --enabled <enabled>         : Enable the trigger.
  --name <name>               : Human friendly name of the trigger.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.
```

<a id="storm-trigger-del"></a>

### trigger.del

The `trigger.del` command permanently removes a trigger from the Cortex. To delete a trigger, you must provide the first portion of the trigger's iden (i.e., enough of the iden that the trigger can be uniquely identified), which can be obtained using `trigger.list`.

**Syntax:**

```stormdoc
storm> trigger.del --help

Delete a trigger from the cortex.

Usage: trigger.del [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.
```

<a id="storm-uniq"></a>

## uniq

The `uniq` command removes duplicate results from a Storm query. By default, results are uniqued based on each node's node identifier (node ID / iden) so that only the first node with a given node ID is returned. (You can think of this as effectively deconflicting on a node's primary property.)

You can optionally specify a property, set of properties, or a variable as a parameter to unique the results based on that value / set of values instead of the node ID. Synapse will return the first node with the specified value or combination of values.

**Syntax:**

```stormdoc
storm> uniq --help


Filter nodes by their uniq iden values.
When this is used a Storm pipeline, only the first instance of a
given node is allowed through the pipeline.

A relative property or variable may also be specified, which will cause
this command to only allow through the first node with a given value for
that property or value rather than checking the node id.

Examples:

    # Filter duplicate nodes after pivoting from inet:ipv4 nodes tagged with #badstuff
    #badstuff +inet:ipv4 ->* | uniq

    # Unique inet:ipv4 nodes by their :asn property
    #badstuff +inet:ipv4 | uniq :asn


Usage: uniq [options] <value>

Options:

  --help                      : Display the command usage.

Arguments:

  [value]                     : A relative property or variable to uniq by.
```

**Examples:**

Lift all of the unique IP addresses that domains associated with the Fancy Bear threat group have resolved to:

``` text
inet:fqdn#rep.threatconnect.fancybear -> inet:dns:a -> inet:ip | uniq
```

Lift a set of network flow (`inet:flow`) nodes and unique (de-duplicate) them based on the source IP address:

``` text
inet:flow | uniq :client.ip
```

Lift a set of network flow nodes and de-duplicate them based on each unique combination of source and destination IP addresses:

``` text
inet:flow | uniq ( :client, :server )
```

Nodes can be uniqued based on variables. Alert (`risk:alert`) nodes can be categorized in various ways. This includes `:priority` and `:severity` properties, both of which use a set of fixed text values (e.g., "low" vs. "highest") that correspond to integers (e.g., 20 vs. 50). These integer values could be joined together in a variable to provide a sample of alerts which have unique combinations of those values:

``` text
risk:alert:priority +:severity $pri=:priority $sev=:severity $value=( $pri, $sev ) | uniq $value
```

<a id="storm-uptime"></a>

## uptime

The `uptime` command displays the uptime for the Cortex or specified service.

**Syntax:**

```stormdoc
storm> uptime --help

Print the uptime for the Cortex or a connected service.

Usage: uptime [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  [name]                      : The name, or iden, of the service (if not provided defaults to the Cortex).
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

```stormdoc
storm> vault.add --help


            Add a vault.

            Examples:

                // Add a global vault with type `synapse-test`
                vault.add "shared-global-vault" synapse-test ({'apikey': 'foobar'}) ({}) --global

                // Add a user vault with type `synapse-test`
                vault.add "visi-user-vault" synapse-test ({'apikey': 'barbaz'}) ({}) --user visi

                // Add a role vault with type `synapse-test`
                vault.add "contributor-role-vault" synapse-test ({'apikey': 'bazquux'}) ({}) --role contributor

                // Add an unscoped vault with type `synapse-test`
                vault.add "unscoped-vault" synapse-test ({'apikey': 'quuxquo'}) ({'server': 'api.foobar.com'}) --unscoped visi
        

Usage: vault.add [options] <name> <type> <secrets> <configs>

Options:

  --help                      : Display the command usage.
  --user <user>               : This vault is a user-scoped vault, for the specified user name.
  --role <role>               : This vault is a role-scoped vault, for the specified role name.
  --unscoped <unscoped>       : This vault is an unscoped vault, for the specified user name.
  --global                    : This vault is a global-scoped vault.

Arguments:

  <name>                      : The vault name.
  <type>                      : The vault type.
  <secrets>                   : The secrets to store in the new vault.
  <configs>                   : The configs to store in the new vault.
```

<a id="storm-vault-list"></a>

### vault.list

The `vault.list` command displays the available vaults.

**Syntax:**

```stormdoc
storm> vault.list --help


            List available vaults.
        

Usage: vault.list [options] 

Options:

  --help                      : Display the command usage.
  --name <name>               : Only list vaults with the specified name or iden.
  --type <type>               : Only list vaults with the specified type.
  --showsecrets               : Print vault secrets.
```

<a id="storm-vault-set-configs"></a>

### vault.set.configs

The `vault.set.configs` sets configuration options for the specified vault.

**Syntax:**

```stormdoc
storm> vault.set.configs --help


            Set vault config data.

            Examples:

                // Set data to visi's user vault configs
                vault.set.configs "visi-user-vault" color --value orange

                // Set data to contributor's role vault configs
                vault.set.configs "contributor-role-vault" color --value blue

                // Remove apikey from a global vault configs
                vault.set.configs "some-global-vault" color --delete
        

Usage: vault.set.configs [options] <name> <key>

Options:

  --help                      : Display the command usage.
  --value <value>             : The config value to store in the vault.
  --delete                    : Specify this flag to remove the config from the vault.

Arguments:

  <name>                      : The vault name or iden.
  <key>                       : The key for the config value.
```

<a id="storm-vault-set-perm"></a>

### vault.set.perm

The `vault.set.perm` command grants or revokes permissions to a vault.

**Syntax:**

```stormdoc
storm> vault.set.perm --help


            Set permissions on a vault.

            Examples:

                // Give blackout read permissions to visi's user vault
                vault.set.perm "my-user-vault" blackout --level read

                // Give the contributor role read permissions to visi's user vault
                vault.set.perm "my-user-vault" --role contributor --level read

                // Revoke blackout's permissions from visi's user vault
                vault.set.perm "my-user-vault" blackout --revoke

                // Give visi read permissions to the contributor role vault. (Assume
                // visi is not a member of the contributor role).
                vault.set.perm "contributor-role-vault" visi read
        

Usage: vault.set.perm [options] <name>

Options:

  --help                      : Display the command usage.
  --user <user>               : The user name or role name to update in the vault.
  --role <role>               : Specified when `user` is a role name.
  --level <level>             : The permission level to grant.
  --revoke                    : Specify this flag when revoking an existing permission.

Arguments:

  <name>                      : The vault name or iden to set permissions on.
```

<a id="storm-vault-set-secrets"></a>

### vault.set.secrets

The `vault.set.secrets` command sets the specified secret for the vault.

**Syntax:**

```stormdoc
storm> vault.set.secrets --help


            Set vault secret data.

            Examples:

                // Set data to visi's user vault secrets
                vault.set.secrets "visi-user-vault" apikey --value foobar

                // Set data to contributor's role vault secrets
                vault.set.secrets "contributor-role-vault" apikey --value barbaz

                // Remove apikey from a global vault secrets
                vault.set.secrets "some-global-vault" apikey --delete
        

Usage: vault.set.secrets [options] <name> <key>

Options:

  --help                      : Display the command usage.
  --value <value>             : The secret value to store in the vault.
  --delete                    : Specify this flag to remove the secret from the vault.

Arguments:

  <name>                      : The vault name or iden.
  <key>                       : The key for the secret value.
```

<a id="storm-vault-del"></a>

### vault.del

The `vault.del` command deletes a vault.

**Syntax:**

```stormdoc
storm> vault.del --help


            Delete a vault.

            Examples:

                // Delete visi's user vault
                vault.del "visi-user-vault"

                // Delete contributor's role vault
                vault.del "contributor-role-vault"
        

Usage: vault.del [options] <name>

Options:

  --help                      : Display the command usage.

Arguments:

  <name>                      : The vault name or iden.
```

<a id="storm-version"></a>

## version

The `version` command displays the current version of Synapse and associated metadata.

**Syntax:**

```stormdoc
storm> version --help

Show version metadata relating to Synapse.

Usage: version [options] 

Options:

  --help                      : Display the command usage.
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

```stormdoc
storm> view.add --help

Add a view to the cortex.

Usage: view.add [options] 

Options:

  --help                      : Display the command usage.
  --name <name>               : The name of the new view. (default: None)
  --worldreadable <worldreadable>: Grant read access to the `all` role. (default: False)
  --layers [<layers> ...]     : Layers for the view. (default: [])
```

<a id="storm-view-fork"></a>

### view.fork

The `view.fork` command forks an existing view from the Cortex. Forking a view creates a new view with a new writable layer on top of the set of layers from the previous (forked) view.

**Syntax:**

```stormdoc
storm> view.fork --help

Fork a view in the cortex.

Usage: view.fork [options] <iden>

Options:

  --help                      : Display the command usage.
  --name <name>               : Name for the newly forked view. (default: None)

Arguments:

  <iden>                      : Iden of the view to fork.
```

<a id="storm-view-set"></a>

### view.set

The `view.set` command sets a property on the specified view.

**Syntax:**

```stormdoc
storm> view.set --help

Set a view option.

Usage: view.set [options] <iden> <name> <valu>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Iden of the view to modify.
  <name>                      : The name of the view property to set.
  <valu>                      : The value to set the view property to.
```

<a id="storm-view-get"></a>

### view.get

The `view.get` command retrieves an existing view from the Cortex.

**Syntax:**

```stormdoc
storm> view.get --help

Get a view from the cortex.

Usage: view.get [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  [iden]                      : Iden of the view to get. If no iden is provided, the main view will be returned.
```

<a id="storm-view-list"></a>

### view.list

The `view.list` command lists the views in the Cortex.

**Syntax:**

```stormdoc
storm> view.list --help

List the views in the cortex.

Usage: view.list [options] 

Options:

  --help                      : Display the command usage.
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

```stormdoc
storm> view.exec --help


Execute a storm query in a different view.

NOTE: Variables are passed through but nodes are not. The behavior of this command may be
non-intuitive in relation to the way storm normally operates. For further information on
behavior and limitations when using `view.exec`, reference the `view.exec` section of the
Synapse User Guide: https://v.vtx.lk/view-exec.

Examples:

    // Move some tagged nodes to another view
    inet:fqdn#foo.bar $fqdn=$node.value | view.exec 95d5f31f0fb414d2b00069d3b1ee64c6 { [ inet:fqdn=$fqdn ] }


Usage: view.exec [options] <view> <storm>

Options:

  --help                      : Display the command usage.

Arguments:

  <view>                      : The GUID of the view in which the query will execute.
  <storm>                     : The storm query to execute on the view.
```

<a id="storm-view-merge"></a>

### view.merge

The `view.merge` command merges **all** data from a forked view into its parent view.

Contrast with [merge](storm_ref_cmd.md#storm-merge) which can merge a subset of nodes.

**Syntax:**

```stormdoc
storm> view.merge --help


            Merge a forked view into its parent view.

            The merge runs as a background task that ends by removing the
            forked view and its top layer.
        

Usage: view.merge [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Iden of the view to merge.
```

<a id="storm-view-del"></a>

### view.del

The `view.del` command permanently deletes a view from the Cortex.

**Syntax:**

```stormdoc
storm> view.del --help


Delete a view from the cortex.

Notes:
    Deleting a view with the `view.del` command does not delete any of the layers in the view.
    To delete layers, you must use the `layer.del` command separately.


Usage: view.del [options] <iden>

Options:

  --help                      : Display the command usage.

Arguments:

  <iden>                      : Iden of the view to delete.
```

<a id="storm-wget"></a>

## wget

The `wget` command retrieves content from one or more specified URLs. The command creates and yields `inet:urlfile` nodes and the retrieved content (`file:bytes`) is stored in the [Axon](../glossary.md#gloss-axon).

**Syntax:**

```stormdoc
storm> wget --help

Retrieve bytes from a URL and store them in the axon. Yields inet:urlfile nodes.

Examples:

    # Specify custom headers and parameters
    inet:url=https://vertex.link/foo.bar.txt | wget --headers ({"User-Agent": "Foo/Bar"}) --params ({"clientid": "42"})

    # Download multiple URL targets without inbound nodes
    wget https://vertex.link https://vtx.lk


Usage: wget [options] <urls>

Options:

  --help                      : Display the command usage.
  --no-ssl-verify             : Ignore SSL certificate validation errors.
  --timeout <timeout>         : Configure the timeout for the download operation. (default: 300)
  --params <params>           : Provide a dict containing url parameters. (default: None)
  --headers <headers>         : Provide a Storm dict containing custom request headers. (default:
                                {'Accept': '*/*',
                                'Accept-Encoding': 'gzip, deflate',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)
                                Chrome/92.0.4515.131 '
                                'Safari/537.36'})
  --no-headers                : Do NOT use any default headers.

Arguments:

  [<urls> ...]                : URLs to download.
```
