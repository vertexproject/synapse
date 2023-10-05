.. highlight:: none


.. _storm-ref-cmd:

Storm Reference - Storm Commands
================================

Storm commands are built-in or custom commands that can be used natively within the Synapse Storm
tool / Storm CLI (see :ref:`syn-tools-storm`).

.. NOTE::
  
  The Storm tool / Storm CLI provides a native Storm interpreter and is the preferred tool for
  interacting with a Synapse Cortex from the CLI.


The pipe symbol ( ``|`` ) is used with Storm commands to:

- Return to Storm query syntax after running a Storm command.
- Separate individual Storm commands and their parameters (i.e., if you are "chaining" multiple
  commands together).
 
For example:

::
  
  inet:fqdn=woot.com nettools.whois | nettools.dns --type A AAAA NS | -> inet:dns:a

The query above:

- lifts the FQDN ``woot.com``,
- performs a live "whois" lookup using the Synapse-Nettools :ref:`gloss-power-up`,
- performs a live DNS query for the FQDN's A, AAAA, and NS records, and
- pivots from the FQDN to any associated DNS A records.

The pipe is used to separate the two ``nettools.*`` commands, and to separate the ``nettools.dns``
command and its switches from the subsequent query operation (the pivot).

An additional pipe character can optionally be placed between the initial lift (``inet:fqdn=woot.com``)
and the ``nettools.whois`` command, but is not required.

**Built-in commands** are native to the Storm library and loaded by default within a given Cortex.
Built-in commands comprise a set of helper commands that perform a variety of specialized tasks that
are useful regardless of the types of data stored in Synapse or the types of analysis performed.

**Custom commands** are Storm commands that have been added to a Cortex to invoke the execution of
dynamically loaded modules. Synapse **Power-Ups** (:ref:`gloss-power-up`) are examples of modules that
may install additional Storm commands to implement additional functionality specific to that Power-Up
(such as querying a third-party data source to automatically ingest and model the data in Synapse).

The full list of Storm commands (built-in and custom) available in a given instance of Synapse can
be displayed with the ``help`` command.

Help for a specific Storm command can be displayed with ``<command> --help``.

.. TIP::
  
  This section details the usage and syntax for **built-in** Storm commands. Many of the commands
  below - such as ``count``, ``intersect``, ``limit``, ``max`` / ``min``, ``uniq``, or the various
  ``gen`` (generate) commands - directly support analysis tasks.
  
  Other commands, such as those used to manage daemons, queues, packages, or services, are likely
  of greater interest to Synapse administrators or developers.

- `help`_
- `auth`_
- `background`_
- `batch`_
- `count`_
- `cron`_
- `delnode`_
- `diff`_
- `divert`_
- `dmon`_
- `edges`_
- `feed`_
- `gen`_
- `graph`_
- `iden`_
- `intersect`_
- `layer`_
- `lift`_
- `limit`_
- `macro`_
- `max`_
- `merge`_
- `min`_
- `model`_
- `movetag`_
- `nodes`_
- `note`_
- `once`_
- `parallel`_
- `pkg`_
- `ps`_
- `queue`_
- `reindex`_
- `runas`_
- `scrape`_
- `service`_
- `sleep`_
- `spin`_
- `tag`_
- `tee`_
- `tree`_
- `trigger`_
- `uniq`_
- `uptime`_
- `version`_
- `view`_
- `wget`_

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

The Storm query language is covered in detail starting with the :ref:`storm-ref-intro` section of the
Synapse User Guide.

.. TIP::

  Storm commands, including custom commands, are added to Synapse as **runtime nodes** ("runt nodes"
  - see :ref:`gloss-node-runt`) of the form ``syn:cmd``. With a few restrictions, these runt nodes
  can be lifted, filtered, and operated on similar to the way you work with other nodes.

**Example**

Lift the ``syn:cmd`` node for the Storm ``movetag`` command:

::

    storm> syn:cmd=movetag
    syn:cmd=movetag
            :doc = Rename an entire tag tree and preserve time intervals.
            .created = 2023/10/05 21:46:42.128



.. _storm-help:

help
----

The ``help`` command displays the list of available commands within the current instance of Synapse and
a brief message describing each command. Help for individual commands is available via ``<command> --help``.
The ``help`` command can also be used to inspect information about :ref:`stormtypes-libs-header` and
:ref:`stormtypes-prim-header`.

**Syntax:**

::

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



.. _storm-auth:

auth
----

Storm includes ``auth.*`` commands that allow you create and manage users and roles, and manage their associated
permissions (rules).

- `auth.gate.show`_
- `auth.role.add`_
- `auth.role.addrule`_
- `auth.role.del`_
- `auth.role.delrule`_
- `auth.role.list`_
- `auth.role.mod`_
- `auth.role.show`_
- `auth.user.add`_
- `auth.user.addrule`_
- `auth.user.delrule`_
- `auth.user.grant`_
- `auth.user.list`_
- `auth.user.mod`_
- `auth.user.revoke`_
- `auth.user.show`_
- `auth.user.allowed`_

Help for individual ``auth.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-auth-gate-show:

auth.gate.show
++++++++++++++

The ``auth.gate.show`` command displays the user, roles, and permissions associated with the specified
:ref:`gloss-authgate`.

**Syntax**

::

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



.. _storm-auth-role-add:

auth.role.add
+++++++++++++

The ``auth.role.add`` command creates a role.

**Syntax:**

::

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



.. _storm-auth-role-addrule:

auth.role.addrule
+++++++++++++++++

The ``auth.role.addrule`` command adds a rule (permission) to a role.

**Syntax:**

::

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



.. _storm-auth-role-del:

auth.role.del
+++++++++++++

The ``auth.role.del`` command deletes a role.

**Syntax:**

::

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



.. _storm-auth-role-delrule:

auth.role.delrule
+++++++++++++++++

The ``auth.role.delrule`` command removes a rule (permission) from a role.

**Syntax:**

::

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



.. _storm-auth-role-list:

auth.role.list
++++++++++++++

The ``auth.role.list`` lists all roles in the Cortex.

**Syntax:**

::

    storm> auth.role.list --help
    
    
                List all roles.
    
                Examples:
    
                    // Display the list of all roles
                    auth.role.list
            
    
    Usage: auth.role.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-auth-role-mod:

auth.role.mod
+++++++++++++

The ``auth.role.mod`` modifies an existing role.

**Syntax:**

::

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



.. _storm-auth-role-show:

auth.role.show
++++++++++++++

The ``auth.role.show`` displays the details for a given role.

**Syntax:**

::

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



.. _storm-auth-user-add:

auth.user.add
+++++++++++++

The ``auth.user.add`` command creates a user.

**Syntax:**

::

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



.. _storm-auth-user-addrule:

auth.user.addrule
+++++++++++++++++

The ``auth.user.addrule`` command adds a rule (permission) to a user.

**Syntax:**

::

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



.. _storm-auth-user-delrule:

auth.user.delrule
+++++++++++++++++

The ``auth.user.delrule`` command removes a rule (permission) from a user.

**Syntax:**

::

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



.. _storm-auth-user-grant:

auth.user.grant
+++++++++++++++

The ``auth.user.grant`` command grants a role (and its associated permissions) to a user.

**Syntax:**

::

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



.. _storm-auth-user-list:

auth.user.list
++++++++++++++

The ``auth.user.list`` command displays all users in the Cortex.

**Syntax:**

::

    storm> auth.user.list --help
    
    
                List all users.
    
                Examples:
    
                    // Display the list of all users
                    auth.user.list
            
    
    Usage: auth.user.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-auth-user-mod:

auth.user.mod
+++++++++++++

The ``auth.user.mod`` command modifies a user account.

**Syntax:**

::

    storm> auth.user.mod --help
    
    
                Modify properties of a user.
    
                Examples:
    
                    // Rename the user "foo" to "bar"
                    auth.user.mod foo --name bar
    
                    // Make the user "visi" an admin
                    auth.user.mod visi --admin $lib.true
    
                    // Unlock the user "visi" and set their email to "visi@vertex.link"
                    auth.user.mod visi --locked $lib.false --email visi@vertex.link
            
    
    Usage: auth.user.mod [options] <username>
    
    Options:
    
      --help                      : Display the command usage.
      --name <name>               : The new name for the user.
      --email <email>             : The email address to set for the user.
      --passwd <passwd>           : The new password for the user. This is best passed into the runtime as a variable.
      --admin <admin>             : True to make the user and admin, false to remove their remove their admin status.
      --locked <locked>           : True to lock the user, false to unlock them.
    
    Arguments:
    
      <username>                  : The name of the user.



.. _storm-auth-user-revoke:

auth.user.revoke
+++++++++++++++++

The ``auth.user.revoke`` command revokes a role (and its associated permissions) from a user.

**Syntax:**

::

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



.. _storm-auth-user-show:

auth.user.show
++++++++++++++

The ``auth.user.show`` command displays information for a specific user.

**Syntax:**

::

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



.. _storm-auth-user-allowed:

auth.user.allowed
+++++++++++++++++

The ``auth.user.allowed`` command checks whether a user has a permission for the specified scope
(view or layer; if no scope is specified with the ``--gate`` option, the permission is checked
globally).

The command retuns whether the permission is allowed (true) the source of the permission (e.g.,
if the permission is due to having a particular role).

**Syntax:**

::

    storm> auth.user.allowed --help
    
    
                Show whether the user is allowed the given permission and why.
    
                Examples:
    
                    auth.user.allowed visi foo.bar
            
    
    Usage: auth.user.allowed [options] <username> <permname>
    
    Options:
    
      --help                      : Display the command usage.
      --gate <gate>               : An auth gate to test the perms against.
    
    Arguments:
    
      <username>                  : The name of the user.
      <permname>                  : The permission string.



.. _storm-background:

background
----------

The ``background`` command allows you to execute a Storm query as a background task (e.g., to free up
the CLI / Storm runtime for additional queries).

.. NOTE::
  
  Use of ``background`` is a "fire-and-forget" process - any status messages (warnings or errors) are
  not returned to the console, and if the query is interrupted for any reason, it will not resume.

See also :ref:`storm-parallel`.

**Syntax:**

::

    storm> background --help
    
    
        Execute a query pipeline as a background task.
        NOTE: Variables are passed through but nodes are not
        
    
    Usage: background [options] <query>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <query>                     : The query to execute in the background.



.. _storm-batch:

batch
-----

The ``batch`` command allows you to run a Storm query with batched sets of nodes. 

Note that in most cases, Storm queries are meant to operate in a "streaming" manner on individual nodes.
This command is intended to be used in cases such as querying external APIs that support aggregate queries
(i.e., an API that allows you to query 100 objects in a single API call as part of the API's quota system).

**Syntax:**

::

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
            batch $lib.false --size 5 { $lib.print($nodes) }
        
    
    Usage: batch [options] <cond> <query>
    
    Options:
    
      --help                      : Display the command usage.
      --size <size>               : The number of nodes to collect before running the batched query (max 10000). (default: 10)
    
    Arguments:
    
      <cond>                      : The conditional value for the yield option.
      <query>                     : The query to execute with batched nodes.



.. _storm-count:

count
-----

The ``count`` command enumerates the number of nodes returned from a given Storm query and displays
the final tally. The associated nodes can optionally be displayed with the ``--yield`` switch.

**Syntax:**

::

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

    

**Examples:**

- Count the number of IP address nodes that Trend Micro reports are associated with the threat group
  Earth Preta:


::

    storm> inet:ipv4#rep.trend.earthpreta | count
    Counted 5 nodes.


- Count nodes from a lift and yield the output:

::

    storm> inet:ipv4#rep.trend.earthpreta | count --yield
    inet:ipv4=66.129.222.1
            :type = unicast
            .created = 2023/10/05 21:46:42.397
            #rep.trend.earthpreta
    inet:ipv4=184.82.164.104
            :type = unicast
            .created = 2023/10/05 21:46:42.401
            #rep.trend.earthpreta
    inet:ipv4=209.161.249.125
            :type = unicast
            .created = 2023/10/05 21:46:42.403
            #rep.trend.earthpreta
    inet:ipv4=69.90.65.240
            :type = unicast
            .created = 2023/10/05 21:46:42.406
            #rep.trend.earthpreta
    inet:ipv4=70.62.232.98
            :type = unicast
            .created = 2023/10/05 21:46:42.409
            #rep.trend.earthpreta
    Counted 5 nodes.


- Count the number of DNS A records for the domain woot.com where the lift produces no results:

::

    storm> inet:dns:a:fqdn=woot.com | count
    Counted 0 nodes.



.. _storm-cron:

cron
----

.. NOTE::
  
  See the :ref:`storm-ref-automation` guide for additional background on cron jobs (as well as triggers
  and macros), including examples.

Storm includes ``cron.*`` commands that allow you to create and manage scheduled :ref:`gloss-cron` jobs.
Within Synapse, jobs are Storm queries that execute on a recurring or one-time (``cron.at``) basis.

- `cron.add`_
- `cron.at`_
- `cron.cleanup`_
- `cron.list`_
- `cron.stat`_
- `cron.mod`_
- `cron.move`_
- `cron.disable`_
- `cron.enable`_
- `cron.del`_

Help for individual ``cron.*`` commands can be displayed using:

  ``<command> --help``

.. TIP::
  
  Cron jobs (including jobs created with ``cron.at``) are added to Synapse as **runtime nodes** ("runt
  nodes" - see :ref:`gloss-node-runt`) of the form ``syn:cron``. With a few restrictions, these runt nodes
  can be lifted, filtered, and operated on similar to the way you work with other nodes.


.. _storm-cron-add:

cron.add
++++++++

The ``cron.add`` command creates an individual cron job within a Cortex.

**Syntax:**

::

    storm> cron.add --help
    
    
    Add a recurring cron job to a cortex.
    
    Notes:
        All times are interpreted as UTC.
    
        All arguments are interpreted as the job period, unless the value ends in
        an equals sign, in which case the argument is interpreted as the recurrence
        period.  Only one recurrence period parameter may be specified.
    
        Currently, a fixed unit must not be larger than a specified recurrence
        period.  i.e. '--hour 7 --minute +15' (every 15 minutes from 7-8am?) is not
        supported.
    
        Value values for fixed hours are 0-23 on a 24-hour clock where midnight is 0.
    
        If the --day parameter value does not start with a '+' and is an integer, it is
        interpreted as a fixed day of the month.  A negative integer may be
        specified to count from the end of the month with -1 meaning the last day
        of the month.  All fixed day values are clamped to valid days, so for
        example '-d 31' will run on February 28.
        If the fixed day parameter is a value in ([Mon, Tue, Wed, Thu, Fri, Sat,
        Sun] if locale is set to English) it is interpreted as a fixed day of the
        week.
    
        Otherwise, if the parameter value starts with a '+', then it is interpreted
        as a recurrence interval of that many days.
    
        If no plus-sign-starting parameter is specified, the recurrence period
        defaults to the unit larger than all the fixed parameters.   e.g. '--minute 5'
        means every hour at 5 minutes past, and --hour 3, --minute 1 means 3:01 every day.
    
        At least one optional parameter must be provided.
    
        All parameters accept multiple comma-separated values.  If multiple
        parameters have multiple values, all combinations of those values are used.
    
        All fixed units not specified lower than the recurrence period default to
        the lowest valid value, e.g. --month +2 will be scheduled at 12:00am the first of
        every other month.  One exception is if the largest fixed value is day of the
        week, then the default period is set to be a week.
    
        A month period with a day of week fixed value is not currently supported.
    
        Fixed-value year (i.e. --year 2019) is not supported.  See the 'at'
        command for one-time cron jobs.
    
        As an alternative to the above options, one may use exactly one of
        --hourly, --daily, --monthly, --yearly with a colon-separated list of
        fixed parameters for the value.  It is an error to use both the individual
        options and these aliases at the same time.
    
    Examples:
        Run a query every last day of the month at 3 am
        cron.add --hour 3 --day -1 {#foo}
    
        Run a query every 8 hours
        cron.add --hour +8 {#foo}
    
        Run a query every Wednesday and Sunday at midnight and noon
        cron.add --hour 0,12 --day Wed,Sun {#foo}
    
        Run a query every other day at 3:57pm
        cron.add --day +2 --minute 57 --hour 15 {#foo}
    
    
    Usage: cron.add [options] <query>
    
    Options:
    
      --help                      : Display the command usage.
      --minute <minute>           : Minute value for job or recurrence period.
      --name <name>               : An optional name for the cron job.
      --doc <doc>                 : An optional doc string for the cron job.
      --hour <hour>               : Hour value for job or recurrence period.
      --day <day>                 : Day value for job or recurrence period.
      --month <month>             : Month value for job or recurrence period.
      --year <year>               : Year value for recurrence period.
      --hourly <hourly>           : Fixed parameters for an hourly job.
      --daily <daily>             : Fixed parameters for a daily job.
      --monthly <monthly>         : Fixed parameters for a monthly job.
      --yearly <yearly>           : Fixed parameters for a yearly job.
      --iden <iden>               : Fixed iden to assign to the cron job
      --view <view>               : View to run the cron job against
    
    Arguments:
    
      <query>                     : Query for the cron job to execute.



.. _storm-cron-at:

cron.at
+++++++

The ``cron.at`` command creates a non-recurring (one-time) cron job within a Cortex. Just like standard
(recurring) cron jobs, jobs created with ``cron.at`` will persist (remain in the list of cron jobs and
as ``syn:cron`` runt nodes) until they are explicitly removed using ``cron.del``.

**Syntax:**

::

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
    
    Arguments:
    
      <query>                     : Query for the cron job to execute.



.. _storm-cron-cleanup:

cron.cleanup
++++++++++++

The ``cron.cleanup`` command can be used to remove any one-time cron jobs ("at" jobs) that have completed.

**Syntax:**

::

    storm> cron.cleanup --help
    
    Delete all completed at jobs
    
    Usage: cron.cleanup [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-cron-list:

cron.list
+++++++++

The ``cron.list`` command displays the set of cron jobs in the Cortex that the current user can view /
modify based on their permissions.

Cron jobs are displayed in alphanumeric order by job :ref:`gloss-iden`. Jobs are sorted upon Cortex
initialization, so newly-created jobs will be displayed at the bottom of the list until the list is
re-sorted the next time the Cortex is restarted.

**Syntax:**

::

    storm> cron.list --help
    
    List existing cron jobs in the cortex.
    
    Usage: cron.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-cron-stat:

cron.stat
+++++++++

The ``cron.stat`` command displays statistics for an individual cron job and provides more detail on
an individual job vs. ``cron.list``, including any errors and the interval at which the job executes.
To view the stats for a job, you must provide the first portion of the job's iden (i.e., enough of the
iden that the job can be uniquely identified), which can be obtained using ``cron.list`` or by lifting
the appropriate ``syn:cron`` node.

**Syntax:**

::

    storm> cron.stat --help
    
    Gives detailed information about a cron job.
    
    Usage: cron.stat [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.



.. _storm-cron-mod:

cron.mod
++++++++

The ``cron.mod`` command modifies the Storm query associated with a specific cron job. To modify a job,
you must provide the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely
identified), which can be obtained using ``cron.list`` or by lifting the appropriate ``syn:cron`` node.

.. NOTE::
  
  Other aspects of the cron job, such as its schedule for execution, cannot be modified once the job has
  been created. To change these aspects you must delete and re-add the job.

**Syntax:**

::

    storm> cron.mod --help
    
    Modify an existing cron job's query.
    
    Usage: cron.mod [options] <iden> <query>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.
      <query>                     : New storm query for the cron job.



.. _storm-cron-move:

cron.move
+++++++++

The ``cron.move`` command moves a cron job from one :ref:`gloss-view` to another.

**Syntax:**

::

    storm> cron.move --help
    
    Move a cron job from one view to another
    
    Usage: cron.move [options] <iden> <view>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.
      <view>                      : View to move the cron job to.



.. _storm-cron-disable:

cron.disable
++++++++++++

The ``cron.disable`` command disables a job and prevents it from executing without removing it from the
Cortex. To disable a job, you must provide the first portion of the job's iden (i.e., enough of the iden
that the job can be uniquely identified), which can be obtained using ``cron.list`` or by lifting the
appropriate ``syn:cron`` node.

**Syntax:**

::

    storm> cron.disable --help
    
    Disable a cron job in the cortex.
    
    Usage: cron.disable [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.



.. _storm-cron-enable:

cron.enable
+++++++++++

The ``cron.enable`` command enables a disabled cron job. To enable a job, you must provide the first portion
of the job's iden (i.e., enough of the iden that the job can be uniquely identified), which can be obtained
using ``cron.list`` or by lifting the appropriate ``syn:cron`` node.

.. NOTE::

  Cron jobs, including non-recurring jobs added with ``cron.at``, are enabled by default upon creation.

**Syntax:**

::

    storm> cron.enable --help
    
    Enable a cron job in the cortex.
    
    Usage: cron.enable [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.



.. _storm-cron-del:

cron.del
++++++++

The ``cron.del`` command permanently removes a cron job from the Cortex. To delete a job, you must provide
the first portion of the job's iden (i.e., enough of the iden that the job can be uniquely identified),
which can be obtained using ``cron.list`` or by lifting the appropriate ``syn:cron`` node.

**Syntax:**

::

    storm> cron.del --help
    
    Delete a cron job from the cortex.
    
    Usage: cron.del [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid cron job iden is accepted.



.. _storm-delnode:

delnode
-------

The ``delnode`` command deletes a node or set of nodes from a Cortex.

.. WARNING::
  
  The Storm ``delnode`` command includes some limited checks (see below) to try and prevent the
  accidental deletion of nodes that are still connected to other nodes in the knowledge graph.
  However, these checks are not foolproof, and ``delnode`` has the potential to be destructive
  if executed on an incorrect, badly formed, or mistyped query.
  
  Users are **strongly encouraged** to validate their query by first executing it on its own to
  confirm it returns the expected nodes before piping the query to the ``delnode`` command.
  
  In addition, use of the ``--force`` switch with ``delnode`` will override all safety checks and
  forcibly delete ALL nodes input to the command.
  
  **This parameter should be used with extreme caution as it may result in broken references
  (e.g., "holes" in the graph) within Synapse.**

**Syntax:**

::

    storm> delnode --help
    
    
        Delete nodes produced by the previous query logic.
    
        (no nodes are returned)
    
        Example
    
            inet:fqdn=vertex.link | delnode
        
    
    Usage: delnode [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --force                     : Force delete even if it causes broken references (requires admin).
      --delbytes                  : For file:bytes nodes, remove the bytes associated with the sha256 property from the axon as well if present.



**Examples:**

- Delete the node for the domain woowoo.com:

::

    storm> inet:fqdn=woowoo.com | delnode



- Forcibly delete all nodes with the #testing tag:

::

    storm> #testing | delnode --force



**Usage Notes:**

- ``delnode`` operates on the output of a previous Storm query.
- ``delnode`` performs some basic sanity-checking to help prevent egregious mistakes, and will
  generate an error in cases such as:
  
  - attempting to delete a node (such as ``inet:fqdn=woot.com``) that is still referenced by
    (i.e., is a secondary property of) another node (such as ``inet:dns:a=(woot.com, 1.1.1.1)``.
  - attmpting to delete a ``syn:tag`` node where that tag still exists on other nodes.
  
  However, it is important to keep in mind that **delnode cannot prevent all mistakes.**


.. _storm-diff:

diff
----

The ``diff`` command generates a list of nodes with changes (i.e., newly created or modified nodes)
present in the top :ref:`gloss-layer` of the current :ref:`gloss-view`. The ``diff`` command may be
useful before performing a :ref:`storm-merge` operation.

**Syntax:**

::

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
        
    
    Usage: diff [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --tag <tag>                 : Lift only nodes with the given tag in the top layer. (default: None)
      --prop <prop>               : Lift nodes with changes to the given property the top layer. (default: None)



.. _storm-divert:

divert
------

The ``divert`` command allows Storm to either consume a generator or yield its results based on a
conditional.

**Syntax:**

::

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



.. _storm-dmon:

dmon
----

Storm includes ``dmon.*`` commands that allow you to work with daemons (see :ref:`gloss-daemon`).

- `dmon.list`_

Help for individual ``dmon.*`` commands can be displayed using:

  ``<command> --help``


.. _storm-dmon-list:

dmon.list
+++++++++

The ``dmon.list`` command displays the set of running dmon queries in the Cortex.

**Syntax:**

::

    storm> dmon.list --help
    
    List the storm daemon queries running in the cortex.
    
    Usage: dmon.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-edges:

edges
-----

Storm includes ``edges.*`` commands that allow you to work with lightweight (light) edges. Also
see the ``lift.byverb`` and ``model.edge.*`` commands under :ref:`storm-lift` and :ref:`storm-model`
below.

- `edges.del`_

Help for individual ``edge.*`` commands can be displayed using:

  ``<command> --help``


.. _storm-edges-del:

edges.del
+++++++++

The ``edges.del`` command is designed to delete multiple light edges to (or from) a set of nodes
(contrast with using Storm edit syntax - see :ref:`light-edge-del`).

**Syntax:**

::

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



.. _storm-feed:

feed
----

Storm includes ``feed.*`` commands that allow you to work with feeds (see :ref:`gloss-feed`).

- `feed.list`_

Help for individual ``feed.*`` commands can be displayed using:

  ``<command> --help``


.. _storm-feed-list:

feed.list
+++++++++

The ``feed.list`` command displays available feed functions in the Cortex.

**Syntax:**

::

    storm> feed.list --help
    
    List the feed functions available in the Cortex
    
    Usage: feed.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-gen:

gen
---

Storm includes various ``gen.*`` ("generate") commands that allow you to easily query
for common guid-based nodes (see :ref:`gloss-form-guid`) based on one or more "human
friendly" secondary properties, and create (generate) the specified node if it does
not already exist.

Because guid nodes have a primary property that may be arbitrary, ``gen.*`` commands simplify
the process of **deconflicting on secondary properties** before creating certain guid nodes.

.. NOTE::
  
  See the :ref:`type-guid` section of the :ref:`storm-ref-type-specific` for a detailed
  discussion of guids, guid behavior, and deconfliction considerations for guid forms.

Nodes created using generate commands will have a limited subset of properties set (e.g.,
an organization node deconflicted and created based on a name will only have its ``ou:org:name``
property set). Users can set additional property values as they see fit.

Help for individual ``gen.*`` commands can be displayed using:

  ``<command> --help``

.. NOTE::
  
  New ``gen.*`` commands are added to Synapse on an ongoing basis as we identify new cases
  where such commands are helpful. Use the ``help`` command for the current list of ``gen.*``
  commands available in your instance of Synapse.


.. _storm-gen-prodsoft:

gen.it.prod.soft
++++++++++++++++

The ``gen.it.prod.soft`` command locates (lifts) or creates an ``it:prod:soft`` node based on
the software name (``it:prod:soft:name`` and / or ``it:prod:soft:names``).

::

    storm> gen.it.prod.soft --help
    
    Lift (or create) an it:prod:soft node based on the software name.
    
    Usage: gen.it.prod.soft [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the software.



.. _storm-gen-lang:

gen.lang.language
+++++++++++++++++

The ``gen.lang.language`` command locates (lifts) or creates a ``lang:language`` node based on
the language name (``lang:language:name`` and / or ``lang:language:names``).

::

    storm> gen.lang.language --help
    
    Lift (or create) a lang:language node based on the name.
    
    Usage: gen.lang.language [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the language.


.. _storm-gen-ou-id

gen.ou.id.number
++++++++++++++++

The ``gen.ou.id.number`` command locates (lifts) or creates an ``ou:id:number`` node based on
the organization ID type (``ou:id:type``) and organization ID value (``str``).

::

    storm> gen.ou.id.number --help
    
    Lift (or create) an ou:id:number node based on the organization ID type and value.
    
    Usage: gen.ou.id.number [options] <type> <value>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <type>                      : The type of the organization ID.
      <value>                     : The value of the organization ID.


gen.ou.id.type
++++++++++++++

The ``gen.ou.id.type`` command locates (lifts) or creates an ``ou:id:type`` node based on
the friendly name of the organization ID type (``str``).

::

    storm> gen.ou.id.type --help
    
    Lift (or create) an ou:id:type node based on the name of the type.
    
    Usage: gen.ou.id.type [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The friendly name of the organization ID type.


.. _storm-gen-industry:

gen.ou.industry
+++++++++++++++

The ``gen.ou.industry`` commands locates (lifts) or creates an ``ou:industry`` node based on
the industry name (``ou:industry:name`` and / or ``ou:industry:names``).

::

    storm> gen.ou.industry --help
    
    
                Lift (or create) an ou:industry node based on the industry name.
            
    
    Usage: gen.ou.industry [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The industry name.



.. _storm-gen-org:

gen.ou.org
++++++++++

The ``gen.ou.org`` command locates (lifts) or creates an ``ou:org`` node based on the organization
name (``ou:org:name`` and / or ``ou:org:names``).

::

    storm> gen.ou.org --help
    
    Lift (or create) an ou:org node based on the organization name.
    
    Usage: gen.ou.org [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the organization.



.. _storm-gen-orghq:

gen.ou.org.hq
+++++++++++++

The ``gen.ou.org.hq`` command locates (lifts) the primary ``ps:contact`` node for an organization
(i.e., the contact set for the ``ou:org:hq`` property) or creates the contact node (and sets the
``ou:org:hq`` property) if it does not exist, based on the organization name (``ou:org:name`` and / or
``ou:org:names``).

::

    storm> gen.ou.org.hq --help
    
    Lift (or create) the primary ps:contact node for the ou:org based on the organization name.
    
    Usage: gen.ou.org.hq [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the organization.



.. _storm-gen-country:

gen.pol.country
+++++++++++++++

The ``gen.pol.country`` command locates (lifts) or creates a ``pol:country`` node based on the
two-letter ISO-3166 country code (``pol:country:iso2``) .

::

    storm> gen.pol.country --help
    
    
                Lift (or create) a pol:country node based on the 2 letter ISO-3166 country code.
    
                Examples:
    
                    // Yield the pol:country node which represents the country of Ukraine.
                    gen.pol.country ua
            
    
    Usage: gen.pol.country [options] <iso2>
    
    Options:
    
      --help                      : Display the command usage.
      --try                       : Type normalization will fail silently instead of raising an exception.
    
    Arguments:
    
      <iso2>                      : The 2 letter ISO-3166 country code.



.. _storm-gen-country-gov:

gen.pol.country.government
+++++++++++++++++++++++++++

The ``gen.pol.country.government`` command locates (lifts) the ``ou:org`` node representing a
country's government (i.e., the organization set for the ``pol:country:government`` property) or
creates the node (and sets the ``pol:country:government`` property) if it does not exist, based
on the two-letter ISO-3166 country code (``pol:country:iso2``).

::

    storm> gen.pol.country.government --help
    
    
                Lift (or create) the ou:org node representing a country's
                government based on the 2 letter ISO-3166 country code.
    
                Examples:
    
                    // Yield the ou:org node which represents the Government of Ukraine.
                    gen.pol.country.government ua
            
    
    Usage: gen.pol.country.government [options] <iso2>
    
    Options:
    
      --help                      : Display the command usage.
      --try                       : Type normalization will fail silently instead of raising an exception.
    
    Arguments:
    
      <iso2>                      : The 2 letter ISO-3166 country code.



.. _storm-gen-contact-email:

gen.ps.contact.email
++++++++++++++++++++

The ``gen.ps.contact.email`` command locates (lifts) or creates a ``ps:contact`` node using
the contact's primary email address (``ps:contact:email``) and type (``ps:contact:type``).

::

    storm> gen.ps.contact.email --help
    
    
                Lift (or create) the ps:contact node by deconflicting the email and type.
    
                Examples:
    
                    // Yield the ps:contact node for the type and email
                    gen.ps.contact.email vertex.employee visi@vertex.link
            
    
    Usage: gen.ps.contact.email [options] <type> <email>
    
    Options:
    
      --help                      : Display the command usage.
      --try                       : Type normalization will fail silently instead of raising an exception.
    
    Arguments:
    
      <type>                      : The contact type.
      <email>                     : The contact email address.



.. _storm-gen-risk-threat:

gen.risk.threat
+++++++++++++++

The ``gen.risk.threat`` command locates (lifts) or creates a ``risk:threat`` node using the
name of the threat group (``risk:threat:org:name``) and the name of the entity reporting on
the threat (``risk:threat:reporter:name``).

::

    storm> gen.risk.threat --help
    
    
                Lift (or create) a risk:threat node based on the threat name and reporter name.
    
                Examples:
    
                    // Yield a risk:threat node for the threat cluster "APT1" reported by "Mandiant".
                    gen.risk.threat apt1 mandiant
            
    
    Usage: gen.risk.threat [options] <name> <reporter>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the threat cluster. For example: APT1
      <reporter>                  : The name of the reporting organization. For example: Mandiant



.. _storm-gen-risk-toolsoft:

gen.risk.tool.software
++++++++++++++++++++++

The ``gen.risk.tool.software`` command locates (lifts) or creates a ``risk:tool:software``
node using the name of the software / malware (``risk:tool:software:soft:name``) and the
name of the entity reporting on the software / malware (``risk:tool:software:reporter:name``).

::

    storm> gen.risk.tool.software --help
    
    
                Lift (or create) a risk:tool:software node based on the tool name and reporter name.
    
                Examples:
    
                    // Yield a risk:tool:software node for the "redtree" tool reported by "vertex".
                    gen.risk.tool.software redtree vertex
            
    
    Usage: gen.risk.tool.software [options] <name> <reporter>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The tool name.
      <reporter>                  : The name of the reporting organization. For example: "recorded future"



.. _storm-gen-risk-vuln:

gen.risk.vuln
+++++++++++++

The ``gen.risk.vuln`` command locates (lifts) or creates a ``risk:tool:vuln`` node using the
Common Vulnerabilities and Exposures (CVE) number associated with the vulnerability
(``risk:vuln:cve``).

::

    storm> gen.risk.vuln --help
    
    
                Lift (or create) a risk:vuln node based on the CVE.
            
    
    Usage: gen.risk.vuln [options] <cve>
    
    Options:
    
      --help                      : Display the command usage.
      --try                       : Type normalization will fail silently instead of raising an exception.
    
    Arguments:
    
      <cve>                       : The CVE identifier.



.. _storm-graph:

graph
-----

The ``graph`` command generates a subgraph based on a specified set of nodes and parameters.

**Syntax:**


::

    storm> graph --help
    
    
        Generate a subgraph from the given input nodes and command line options.
    
        Example:
    
            Using the graph command::
    
                inet:fqdn | graph
                            --degrees 2
                            --filter { -#nope }
                            --pivot { <- meta:seen <- meta:source }
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
      --refs                      : Deprecated. This is now enabled by default.
      --no-refs                   : Disable automatic in-model pivoting with node.getNodeRefs().
      --yield-filtered            : Yield nodes which would be filtered. This still performs pivots to collect edge data,but does not yield pivoted nodes.
      --no-filter-input           : Do not drop input nodes if they would match a filter.



.. _storm-iden:

iden
----

The ``iden`` command lifts one or more nodes by their node identifier (node ID / iden).

**Syntax:**


::

    storm> iden --help
    
    
        Lift nodes by iden.
    
        Example:
    
            iden b25bc9eec7e159dce879f9ec85fb791f83b505ac55b346fcb64c3c51e98d1175 | count
        
    
    Usage: iden [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      [<iden> ...]                : Iden to lift nodes by. May be specified multiple times.



**Example:**

- Lift the node with node ID 20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f:

::

    storm> iden 20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f
    inet:ipv4=1.2.3.4
            :type = unicast
            .created = 2023/10/05 21:46:42.848


.. _storm-intersect:

intersect
---------

The ``intersect`` command returns the intersection of the results from performing a pivot operation
on multiple inbound nodes. In other words, ``intersect`` will return the subset of pivot results
that are **common** to each of the inbound nodes.

**Syntax:**


::

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


.. _storm-layer:

layer
-----

Storm includes ``layer.*`` commands that allow you to work with layers (see :ref:`gloss-layer`).

- `layer.add`_
- `layer.set`_
- `layer.get`_
- `layer.list`_
- `layer.del`_
- `layer.pull.add`_
- `layer.pull.list`_
- `layer.pull.del`_
- `layer.push.add`_
- `layer.push.list`_
- `layer.push.del`_

Help for individual ``layer.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-layer-add:

layer.add
+++++++++

The ``layer.add`` command adds a layer to the Cortex.

**Syntax**


::

    storm> layer.add --help
    
    Add a layer to the cortex.
    
    Usage: layer.add [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --lockmemory                : Should the layer lock memory for performance.
      --readonly                  : Should the layer be readonly.
      --mirror <mirror>           : A telepath URL of an upstream layer/view to mirror.
      --growsize <growsize>       : Amount to grow the map size when necessary.
      --upstream <upstream>       : One or more telepath urls to receive updates from.
      --name <name>               : The name of the layer.



.. _storm-layer-set:

layer.set
+++++++++

The ``layer.set`` command sets an option for the specified layer.

**Syntax**


::

    storm> layer.set --help
    
    Set a layer option.
    
    Usage: layer.set [options] <iden> <name> <valu>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Iden of the layer to modify.
      <name>                      : The name of the layer property to set.
      <valu>                      : The value to set the layer property to.


.. _storm-layer-get:

layer.get
+++++++++

The ``layer.get`` command retrieves the specified layer from a Cortex.

**Syntax**


::

    storm> layer.get --help
    
    Get a layer from the cortex.
    
    Usage: layer.get [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      [iden]                      : Iden of the layer to get. If no iden is provided, the main layer will be returned.



.. _storm-layer-list:

layer.list
++++++++++

The ``layer.list`` command lists the available layers in a Cortex.

**Syntax**


::

    storm> layer.list --help
    
    List the layers in the cortex.
    
    Usage: layer.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-layer-del:

layer.del
+++++++++

The ``layer.del`` command deletes a layer from a Cortex.

**Syntax**

::

    storm> layer.del --help
    
    Delete a layer from the cortex.
    
    Usage: layer.del [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Iden of the layer to delete.



.. _storm-layer-pull-add:

layer.pull.add
++++++++++++++

The ``layer.pull.add`` command adds a pull configuration to a layer.

**Syntax**

::

    storm> layer.pull.add --help
    
    Add a pull configuration to a layer.
    
    Usage: layer.pull.add [options] <layr> <src>
    
    Options:
    
      --help                      : Display the command usage.
      --offset <offset>           : Layer offset to begin pulling from (default: 0)
    
    Arguments:
    
      <layr>                      : Iden of the layer to pull to.
      <src>                       : Telepath url of the source layer to pull from.



.. _storm-layer-pull-list:

layer.pull.list
+++++++++++++++

The ``layer.pull.list`` command lists the pull configurations for a layer.

**Syntax**

::

    storm> layer.pull.list --help
    
    Get a list of the pull configurations for a layer.
    
    Usage: layer.pull.list [options] <layr>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <layr>                      : Iden of the layer to retrieve pull configurations for.



.. _storm-layer-pull-del:

layer.pull.del
++++++++++++++

The ``layer.pull.del`` command deletes a pull configuration from a layer.

**Syntax**

::

    storm> layer.pull.del --help
    
    Delete a pull configuration from a layer.
    
    Usage: layer.pull.del [options] <layr> <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <layr>                      : Iden of the layer to modify.
      <iden>                      : Iden of the pull configuration to delete.



.. _storm-layer-push-add:

layer.push.add
++++++++++++++

The ``layer.push.add`` command adds a push configuration to a layer.

**Syntax**

::

    storm> layer.push.add --help
    
    Add a push configuration to a layer.
    
    Usage: layer.push.add [options] <layr> <dest>
    
    Options:
    
      --help                      : Display the command usage.
      --offset <offset>           : Layer offset to begin pushing from. (default: 0)
    
    Arguments:
    
      <layr>                      : Iden of the layer to push from.
      <dest>                      : Telepath url of the layer to push to.



.. _storm-layer-push-list:

layer.push.list
+++++++++++++++

The ``layer.push.list`` command lists the push configurations for a layer.

**Syntax**

::

    storm> layer.push.list --help
    
    Get a list of the push configurations for a layer.
    
    Usage: layer.push.list [options] <layr>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <layr>                      : Iden of the layer to retrieve push configurations for.



.. _storm-layer-push-del:

layer.push.del
++++++++++++++

The ``layer.push.del`` command deletes a push configuration from a layer.

**Syntax**

::

    storm> layer.push.del --help
    
    Delete a push configuration from a layer.
    
    Usage: layer.push.del [options] <layr> <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <layr>                      : Iden of the layer to modify.
      <iden>                      : Iden of the push configuration to delete.



.. _storm-lift:

lift
----

Storm includes ``lift.*`` commands that allow you to perform specialized lift operations.

- `lift.byverb`_

Help for individual ``lift.*`` commands can be displayed using:

  ``<command> --help``


.. _storm-lift-byverb:

lift.byverb
+++++++++++

The ``lift.byverb`` command lifts nodes that are connected by the specified lightweight (light) edge.
By default, the command lifts the N1 nodes (i.e., the nodes on the left side of the directional light
edge relationship: ``n1 -(<verb>)> n2``)

.. NOTE::
  For other commands associated with light edges, see ``edges.del`` and ``model.edge.*`` under
  :ref:`storm-edges` and :ref:`storm-model` respectively.

**Syntax:**

::

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



.. _storm-limit:

limit
-----

The ``limit`` command restricts the number of nodes returned from a given Storm query to the specified
number of nodes.

**Syntax:**

::

    storm> limit --help
    
    
        Limit the number of nodes generated by the query in the given position.
    
        Example:
    
            inet:ipv4 | limit 10
        
    
    Usage: limit [options] <count>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <count>                     : The maximum number of nodes to yield.

    

**Example:**

- Lift a single IP address that FireEye associates with the threat group APT1:

::

    storm> inet:ipv4#aka.feye.thr.apt1 | limit 1



**Usage Notes:**

- If the limit number specified (i.e., ``limit 100``) is greater than the total number of nodes returned
  from the Storm query, no limit will be applied to the resultant nodes (i.e., all nodes will be returned).
- By design, ``limit`` imposes an artificial limit on the nodes returned by a query, which may impair
  effective analysis of data by restricting results. As such, ``limit`` is most useful for viewing a subset
  of a large result set or an exemplar node for a given form.
- While ``limit`` returns a sampling of nodes, it is not statistically random for the purposes of population
  sampling for algorithmic use.

.. _storm-macro:

macro
-----

.. NOTE::
  See the :ref:`storm-ref-automation` guide for additional background on macros (as well as triggers and
  cron jobs), including examples.

Storm includes ``macro.*`` commands that allow you to work with macros (see :ref:`gloss-macro`).

- `macro.list`_
- `macro.set`_
- `macro.get`_
- `macro.exec`_
- `macro.del`_

Help for individual ``macro.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-macro-list:

macro.list
++++++++++

The ``macro.list`` command lists the macros in a Cortex.

**Syntax:**

::

    storm> macro.list --help
    
    
    List the macros set on the cortex.
    
    
    Usage: macro.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-macro-set:

macro.set
+++++++++

The ``macro.set`` command creates (or modifies) a macro in a Cortex.

**Syntax:**

::

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



.. _storm-macro-get:

macro.get
+++++++++

The ``macro.get`` command retrieves and displays the specified macro.

**Syntax:**

::

    storm> macro.get --help
    
    
    Display the storm query for a macro in the cortex.
    
    
    Usage: macro.get [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the macro to display.



.. _storm-macro-exec:

macro.exec
++++++++++

The ``macro.exec`` command executes the specified macro.

**Syntax:**

::

    storm> macro.exec --help
    
    
        Execute a named macro.
    
        Example:
    
            inet:ipv4#cno.threat.t80 | macro.exec enrich_foo
    
        
    
    Usage: macro.exec [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the macro to execute


.. _storm-macro-del:

macro.del
+++++++++

The ``macro.del`` command deletes the specified macro from a Cortex.

**Syntax:**

::

    storm> macro.del --help
    
    
    Remove a macro definition from the cortex.
    
    
    Usage: macro.del [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the macro to delete.



.. _storm-max:

max
---

The ``max`` command returns the node from a given set that contains the highest value for a specified
secondary property, tag interval, or variable.

**Syntax:**

::

    storm> max --help
    
    
        Consume nodes and yield only the one node with the highest value for an expression.
    
        Examples:
    
            // Yield the file:bytes node with the highest :size property
            file:bytes#foo.bar | max :size
    
            // Yield the file:bytes node with the highest value for $tick
            file:bytes#foo.bar +.seen ($tick, $tock) = .seen | max $tick
    
            // Yield the it:dev:str node with the longest length
            it:dev:str | max $lib.len($node.value())
    
        
    
    Usage: max [options] <valu>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <valu>                      : The property or variable to use for comparison.

    

**Examples:**

- Return the DNS A record for woot.com with the most recent ``.seen`` value:

::

    storm> inet:dns:a:fqdn=woot.com | max .seen
    inet:dns:a=('woot.com', '107.21.53.159')
            :fqdn = woot.com
            :ipv4 = 107.21.53.159
            .created = 2023/10/05 21:46:43.152
            .seen = ('2014/08/13 00:00:00.000', '2014/08/14 00:00:00.000')



- Return the most recent WHOIS record for domain woot.com:

::

    storm> inet:whois:rec:fqdn=woot.com | max :asof
    inet:whois:rec=('woot.com', '2018/05/22 00:00:00.000')
            :asof = 2018/05/22 00:00:00.000
            :fqdn = woot.com
            :text = domain name: woot.com
            .created = 2023/10/05 21:46:43.192



.. _storm-merge:

merge
-----

The ``merge`` command takes a subset of nodes from a forked view and merges them down to the next layer.
The nodes can optionally be reviewed without actually merging them.

Contrast with :ref:`storm-view-merge` for merging the entire contents of a forked view.

See the :ref:`storm-view` and :ref:`storm-layer` commands for working with views and layers.

**Syntax:**

::

    storm> merge --help
    
    
        Merge edits from the incoming nodes down to the next layer.
    
        NOTE: This command requires the current view to be a fork.
    
        NOTE: The arguments for including/excluding tags can accept tag glob
              expressions for specifying tags. For more information on tag glob
              expressions, check the Synapse documentation for $node.globtags().
    
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
      --no-tags                   : Do not merge tags/tagprops or syn:tag nodes.
      --only-tags                 : Only merge tags/tagprops or syn:tag nodes.
      --include-tags [<include_tags> ...]: Include specific tags/tagprops or syn:tag nodes when merging, others are ignored. Tag glob expressions may be used to specify the tags. (default: [])
      --exclude-tags [<exclude_tags> ...]: Exclude specific tags/tagprops or syn:tag nodes from merge.Tag glob expressions may be used to specify the tags. (default: [])
      --include-props [<include_props> ...]: Include specific props when merging, others are ignored. (default: [])
      --exclude-props [<exclude_props> ...]: Exclude specific props from merge. (default: [])
      --diff                      : Enumerate all changes in the current layer.



.. _storm-min:

min
---

The ``min`` command returns the node from a given set that contains the lowest value for a specified
secondary property, tag interval, or variable.

**Syntax:**

::

    storm> min --help
    
    
        Consume nodes and yield only the one node with the lowest value for an expression.
    
        Examples:
    
            // Yield the file:bytes node with the lowest :size property
            file:bytes#foo.bar | min :size
    
            // Yield the file:bytes node with the lowest value for $tick
            file:bytes#foo.bar +.seen ($tick, $tock) = .seen | min $tick
    
            // Yield the it:dev:str node with the shortest length
            it:dev:str | min $lib.len($node.value())
    
        
    
    Usage: min [options] <valu>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <valu>                      : The property or variable to use for comparison.



**Examples:**

- Return the DNS A record for woot.com with the oldest ``.seen`` value:

::

    storm> inet:dns:a:fqdn=woot.com | min .seen
    inet:dns:a=('woot.com', '75.101.146.4')
            :fqdn = woot.com
            :ipv4 = 75.101.146.4
            .created = 2023/10/05 21:46:43.157
            .seen = ('2013/09/21 00:00:00.000', '2013/09/22 00:00:00.000')



- Return the oldest WHOIS record for domain woot.com:

::

    storm> inet:whois:rec:fqdn=woot.com | min :asof
    inet:whois:rec=('woot.com', '2018/05/22 00:00:00.000')
            :asof = 2018/05/22 00:00:00.000
            :fqdn = woot.com
            :text = domain name: woot.com
            .created = 2023/10/05 21:46:43.192



.. _storm-model:

model
-----

Storm includes ``model.*`` commands that allow you to work with model elements.

``model.deprecated.*`` commands allow you to view model elements (forms or properties) that have been
marked as "deprecated", determine whether your Cortex contains deprecated nodes / nodes with deprecated
properties, and optionally lock / unlock those properties to prevent (or allow) continued creation of
deprecated model elements.

``model.edge.*`` commands allow you to work with lightweight (light) edges. (See also the ``edges.del``
and ``lift.byverb`` commands under :ref:`storm-edges` and :ref:`storm-lift`, respectively.)

- `model.deprecated.check`_
- `model.deprecated.lock`_
- `model.deprecated.locks`_
- `model.edge.list`_
- `model.edge.set`_
- `model.edge.get`_
- `model.edge.del`_

Help for individual ``model.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-model-deprecated-check:

model.deprecated.check
++++++++++++++++++++++

The ``model.deprecated.check`` command lists deprecated elements, their lock status, and whether deprecated
elements exist in the Cortex.

**Syntax:**

::

    storm> model.deprecated.check --help
    
    Check for lock status and the existence of deprecated model elements
    
    Usage: model.deprecated.check [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-model-deprecated-lock:

model.deprecated.lock
+++++++++++++++++++++

The ``model.deprecated.lock`` command allows you to lock or unlock (e.g., disallow or allow the use of)
deprecated model elements in a Cortex.

**Syntax:**

::

    storm> model.deprecated.lock --help
    
    Edit lock status of deprecated model elements.
    
    Usage: model.deprecated.lock [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
      --unlock                    : Unlock rather than lock the deprecated property.
    
    Arguments:
    
      <name>                      : The deprecated form or property name to lock or * to lock all.



.. _storm-model-deprecated-locks:

model.deprecated.locks
++++++++++++++++++++++

The ``model.deprecated.locks`` command displays the lock status of all deprecated model elements.

**Syntax:**

::

    storm> model.deprecated.locks --help
    
    Display lock status of deprecated model elements.
    
    Usage: model.deprecated.locks [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-model-edge-list:

model.edge.list
+++++++++++++++

The ``model.edge.list`` command displays the set of light edges currently defined in the Cortex and any
``doc`` values set on them.

**Syntax:**

::

    storm> model.edge.list --help
    
    List all edge verbs in the current view and their doc key (if set).
    
    Usage: model.edge.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-model-edge-set:

model.edge.set
++++++++++++++

The ``model.edge.set`` command allows you to set the value of a given key on a light edge (such as a
``doc``  value to specify a definition for the light edge). The current list of valid keys include the
following:

- ``doc``

**Syntax:**

::

    storm> model.edge.set --help
    
    Set a key-value for an edge verb that exists in the current view.
    
    Usage: model.edge.set [options] <verb> <key> <valu>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <verb>                      : The edge verb to add a key to.
      <key>                       : The key name (e.g. doc).
      <valu>                      : The string value to set.



.. _storm-model-edge-get:

model.edge.get
++++++++++++++

The ``model.edge.get`` command allows you to retrieve all of the keys that have been set on a light edge.

**Syntax:**

::

    storm> model.edge.get --help
    
    Retrieve key-value pairs for an edge verb in the current view.
    
    Usage: model.edge.get [options] <verb>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <verb>                      : The edge verb to retrieve.



.. _storm-model-edge-del:

model.edge.del
++++++++++++++

The ``model.edge.del`` command allows you to delete the key from a light edge (such as a ``doc`` property
to specify a definition for the light edge). Deleting a key from a specific light edge does not delete
the key from Synapse (e.g., the property can be re-added to the light edge or to other light edges).

**Syntax:**

::

    storm> model.edge.del --help
    
    Delete a global key-value pair for an edge verb in the current view.
    
    Usage: model.edge.del [options] <verb> <key>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <verb>                      : The edge verb to delete documentation for.
      <key>                       : The key name (e.g. doc).



.. _storm-movenodes:

movenodes
---------

The ``movenodes`` command allows you to move nodes between layers (:ref:`gloss-layer`) in a Cortex.

The command will move the specified storage nodes (see :ref:`gloss-node-storage`) - "sodes" for
short - to the target layer. If a sode is the "left hand" (``n1``) of two nodes joined by a light
edge (``n1 -(*)> n2``), then the edge is also moved.

Sodes are fully removed from the source layer(s) and added to (or merged with existing nodes in)
the target layer.

By default (i.e., if you do not specify a source and / or target layer), ``movenodes`` will migrate
sodes from the bottom layer in the view, through each intervening layer (if any), and finally into
the top layer. If you explicitly specify a source and target layer, ``movenodes`` migrates the sodes
**directly** from the source to the target, skipping any intervening layers (if any).

Similarly, by default as the node is moved "up", any data for that node (property values, tags)
in the higher layer will take precedence over (overwrite) data from a lower layer. This precedence
behavior can be modified with the appropriate command switch.

.. NOTE::
  
  The :ref:`storm-merge` command specifically moves (merges) nodes from the top layer in a
  :ref:`gloss-view` to the underlying layer. Merging is a common **user action** performed
  in a standard "fork and merge" workflow. The ``merge`` command should be used to move/merge
  nodes **down** from a higher layer/view to a lower/underlying one.
  
  The ``movenodes`` command allows you to move nodes between arbitrary layers and is meant to
  be used by Synapse **administrators** in very specific use cases (e.g., data that was accidentally
  merged into a lower layer that should not be there). It can be used to move nodes "up" from
  a lower layer to a higher one.

**Syntax:**

::

    storm> movenodes --help
    
    
        Move storage nodes between layers.
    
        Storage nodes will be removed from the source layers and the resulting
        storage node in the destination layer will contain the merged values (merged
        in bottom up layer order by default).
    
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
      --srclayers [<srclayers> ...]: Specify layers to move storage nodes from (defaults to all below the top layer) (default: None)
      --destlayer <destlayer>     : Layer to move storage nodes to (defaults to the top layer) (default: None)
      --precedence [<precedence> ...]: Layer precedence for resolving conflicts (defaults to bottom up) (default: None)



.. _storm-movetag:

movetag
-------

The ``movetag`` command moves a Synapse tag and its associated tag tree from one location in a tag
hierarchy to another location. It is equivalent to "renaming" a given tag and all of its subtags.
Moving a tag consists of:

- Creating the new ``syn:tag`` node(s).
- Copying the definitions (``:title`` and ``:doc`` properties) from the old ``syn:tag`` node to the
  new ``syn:tag`` node.
- Applying the new tag(s) to the nodes with the old tag(s).

  - If the old tag(s) have associated timestamps / time intervals, they will be applied to the new tag(s).

- Deleting the old tag(s) from the nodes.
- Setting the ``:isnow`` property of the old ``syn:tag`` node(s) to reference the new ``syn:tag`` node.

  - The old ``syn:tag`` nodes are **not** deleted.
  - Once the ``:isnow`` property is set, attempts to apply the old tag will automatically result in the
    new tag being applied.

See also the :ref:`storm-tag` command.

**Syntax:**

::

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



**Examples:**

- Move the tag named #research to #internal.research:

::

    storm> movetag research internal.research
    moved tags on 1 nodes.



- Move the tag tree #aka.fireeye.malware to #rep.feye.mal:

::

    storm> movetag aka.fireeye.malware rep.feye.mal
    moved tags on 1 nodes.



**Usage Notes:**

.. WARNING::
  
  ``movetag`` should be used with caution as when used incorrectly it can result in "deleted"
  (inadvertently moved / removed) or orphaned (inadvertently retained) tags. For example, in the
  second example query above, all ``aka.fireeye.malware`` tags are renamed ``rep.feye.mal``, but the
  tag ``aka.fireeye`` still exists and is still applied to all of the original nodes. In other words,
  the result of the above command will be that nodes previously tagged ``aka.fireeye.malware`` will now
  be tagged both ``rep.feye.mal`` **and** ``aka.fireeye``. Users may wish to test the command on sample
  data first to understand its effects before applying it in a production Cortex.


.. _storm-nodes:

nodes
-----

Storm includes ``nodes.*`` commands that allow you to work with nodes and ``.nodes`` files.

- `nodes.import`_

Help for individual ``nodes.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-nodes-import:

nodes.import
++++++++++++

The ``nodes.import`` command will import a Synapse ``.nodes`` file (i.e., a file containing a set /
subgraph of nodes, light edges, and / or tags exported from a Cortex) from a specified URL.

**Syntax:**

::

    storm> nodes.import --help
    
    Import a nodes file hosted at a URL into the cortex. Yields created nodes.
    
    Usage: nodes.import [options] <urls>
    
    Options:
    
      --help                      : Display the command usage.
      --no-ssl-verify             : Ignore SSL certificate validation errors.
    
    Arguments:
    
      [<urls> ...]                : URL(s) to fetch nodes file from



.. _storm-note:

note
----

Storm includes ``note.*`` commands that allow you to work with free form text notes (``meta:note`` nodes).

- `note.add`_

Help for individual ``note.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-note-add:

note.add
++++++++

The ``note.add`` command will create a ``meta:note`` node containing the specified text and link it
to the inbound node(s) via an ``-(about)>`` light edge (i.e., ``meta:note=<guid> -(about)> <node(s)>``).

**Syntax:**

::

    storm> note.add --help
    
    Add a new meta:note node and link it to the inbound nodes using an -(about)> edge.
    
    Usage: note.add [options] <text>
    
    Options:
    
      --help                      : Display the command usage.
      --type <type>               : The note type.
      --yield                     : Yield the newly created meta:note node.
    
    Arguments:
    
      <text>                      : The note text to add to the nodes.



**Usage Notes:**

.. NOTE::
  
  Synapse's data and analytical models are meant to represent a broad range of data and information
  in a structured (and therefore **queryable**) way. As free form notes are counter to this structured
  approach, we recommend using ``meta:note`` nodes as an exception rather than a regular practice.


.. _storm-once:

once
----

The ``once`` command is used to ensure a given node is processed by the associated Storm command only
once, even if the same command is executed in a different, independent Storm query. The ``once`` command
uses :ref:`gloss-node-data` to keep track of the associated Storm command's execution, so ``once`` is
specific to the :ref:`gloss-view` in which it is executed. You can override the single-execution feature
of ``once`` with the ``--asof`` parameter.

**Syntax:**

::

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



.. _storm-parallel:

parallel
--------

The Storm ``parallel`` command allows you to execute a Storm query using a specified number of query
pipelines. This can improve performance for some queries.

See also :ref:`storm-background`.

**Syntax:**

::

    storm> parallel --help
    
    
        Execute part of a query pipeline in parallel.
        This can be useful to minimize round-trip delay during enrichments.
    
        Examples:
            inet:ipv4#foo | parallel { $place = $lib.import(foobar).lookup(:latlong) [ :place=$place ] }
    
        NOTE: Storm variables set within the parallel query pipelines do not interact.
        
    
    Usage: parallel [options] <query>
    
    Options:
    
      --help                      : Display the command usage.
      --size <size>               : The number of parallel Storm pipelines to execute. (default: 8)
    
    Arguments:
    
      <query>                     : The query to execute in parallel.



.. _storm-pkg:

pkg
---

Storm includes ``pkg.*`` commands that allow you to work with Storm packages (see :ref:`gloss-package`).

- `pkg.list`_
- `pkg.load`_
- `pkg.del`_
- `pkg.docs`_
- `pkg.perms.list`_

Help for individual ``pkg.*`` commands can be displayed using:

  ``<command> --help``

Packages typically contain Storm commands and Storm library code used to implement a Storm :ref:`gloss-service`.

.. _storm-pkg-list:

pkg.list
++++++++

The ``pkg.list`` command lists each Storm package loaded in the Cortex. Output is displayed in tabular
form and includes the package name and version information.

**Syntax:**

::

    storm> pkg.list --help
    
    List the storm packages loaded in the cortex.
    
    Usage: pkg.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-pkg-load:

pkg.load
++++++++

The ``pgk.load`` command loads the specified package into the Cortex.

**Syntax:**

::

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



.. _storm-pkg-del:

pkg.del
+++++++

The ``pkg.del`` command removes a Storm package from the Cortex.

**Syntax:**

::

    storm> pkg.del --help
    
    Remove a storm package from the cortex.
    
    Usage: pkg.del [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name (or name prefix) of the package to remove.



.. _storm-pkg-docs:

pkg.docs
++++++++

The ``pkg.docs`` command displays the documentation for a Storm package.

**Syntax:**

::

    storm> pkg.docs --help
    
    Display documentation included in a storm package.
    
    Usage: pkg.docs [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name (or name prefix) of the package.



.. _storm-pkg-perms-list:

pkg.perms.list
++++++++++++++

The ``pkg.perms.list`` command lists the permissions declared by a Storm package.

**Syntax:**

::

    storm> pkg.perms.list --help
    
    List any permissions declared by the package.
    
    Usage: pkg.perms.list [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name (or name prefix) of the package.



.. _storm-ps:

ps
--

Storm includes ``ps.*`` commands that allow you to work with Storm tasks/queries.

- `ps.list`_
- `ps.kill`_

Help for individual ``ps.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-ps-list:

ps.list
+++++++

The ``ps.list`` command lists the currently executing tasks/queries. By default, the command displays
the first 120 characters of the executing query. The ``--verbose`` option can be used to display the
full query regardless of length.

**Syntax:**

::

    storm> ps.list --help
    
    List running tasks in the cortex.
    
    Usage: ps.list [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --verbose                   : Enable verbose output.



.. _storm-ps-kill:

ps.kill
+++++++

The ``ps.kill`` command can be used to terminate an executing task/query. The command requires the
:ref:`gloss-iden` of the task to be terminated, which can be obtained with :ref:`storm-ps-list`.

**Syntax:**

::

    storm> ps.kill --help
    
    Kill a running task/query within the cortex.
    
    Usage: ps.kill [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid process iden is accepted.



.. _storm-queue:

queue
-----

Storm includes ``queue.*`` commands that allow you to work with queues (see :ref:`gloss-queue`).

- `queue.add`_
- `queue.list`_
- `queue.del`_

Help for individual ``queue.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-queue-add:

queue.add
+++++++++

The ``queue.add`` command adds a queue to the Cortex.

**Syntax:**

::

    storm> queue.add --help
    
    Add a queue to the cortex.
    
    Usage: queue.add [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the new queue.



.. _storm-queue-list:

queue.list
++++++++++

The ``queue.list`` command lists each queue in the Cortex.

**Syntax:**

::

    storm> queue.list --help
    
    List the queues in the cortex.
    
    Usage: queue.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-queue-del:

queue.del
+++++++++

The ``queue.del`` command removes a queue from the Cortex.

**Syntax:**

::

    storm> queue.del --help
    
    Remove a queue from the cortex.
    
    Usage: queue.del [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the queue to remove.



.. _storm-reindex:

reindex
-------

The ``reindex`` command is currently reserved for future use.

The intended purpose of this administrative command is to reindex a given node property. This may
be necessary as part of a manual data migration.

.. NOTE::
  
  Any changes to the Synapse data model are noted in the changelog_ for the relevant Synapse
  release. Changes that require data migration are specifically noted and the data migration is
  typically performed automatically when deploying the new version. See the :ref:`datamigration`
  section of the :ref:`devopsguide` for additional detail.

**Syntax:**

::

    storm> reindex --help
    
    
        Use admin privileges to re index/normalize node properties.
    
        NOTE: Currently does nothing but is reserved for future use.
        
    
    Usage: reindex [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-runas:

runas
-----

The ``runas`` command allows you to execute a Storm query as a specified user.

.. NOTE::
  
  The ``runas`` commmand requires **admin** permisisons.

**Syntax:**

::

    storm> runas --help
    
    
        Execute a storm query as a specified user.
    
        NOTE: This command requires admin privileges.
    
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



.. _storm-scrape:

scrape
------

The ``scrape`` command parses one or more secondary properties of the inbound node(s) and attempts
to identify ("scrape") common forms from the content, creating the nodes if they do not already exist.
This is useful (for example) for extracting forms such as email addresses, domains, URLs, hashes, etc.
from unstructured text.

The ``--refs`` switch can be used to optionally link the source nodes(s) to the scraped forms via ``refs``
light edges.

By default, the ``scrape`` command will return the nodes that it received as input. The ``--yield`` option
can be used to return the scraped nodes rather than the input nodes.

**Syntax:**

::

    storm> scrape --help
    
    
        Use textual properties of existing nodes to find other easily recognizable nodes.
    
        Examples:
    
            # Scrape properties from inbound nodes and create standalone nodes.
            inet:search:query | scrape
    
            # Scrape properties from inbound nodes and make refs light edges to the scraped nodes.
            inet:search:query | scrape --refs
    
            # Scrape only the :engine and :text props from the inbound nodes.
            inet:search:query | scrape :text :engine
    
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



**Example:**

- Scrape the text of WHOIS records for the domain ``woot.com`` and create nodes for common forms found
  in the text:

::

    storm> inet:whois:rec:fqdn=woot.com | scrape :text
    inet:whois:rec=('woot.com', '2018/05/22 00:00:00.000')
            :asof = 2018/05/22 00:00:00.000
            :fqdn = woot.com
            :text = domain name: woot.com
            .created = 2023/10/05 21:46:43.192



**Usage Notes:**

- If no properties to scrape are specified, ``scrape`` will attempt to scrape **all** properties of the
  inbound nodes by default.
- ``scrape`` will only scrape node **properties**; it will not scrape files (this includes files that may
  be referenced by properties, such as ``media:news:file``). In other words, ``scrape`` cannot be used to
  parse indicators from a file such as a PDF.
- ``scrape`` extracts the following forms / indicators (note that this list may change as the command is
  updated):

  - FQDNs
  - IPv4s
  - Servers (IPv4 / port combinations)
  - Hashes (MD5, SHA1, SHA256)
  - URLs
  - Email addresses
  - Cryptocurrency addresses
  
- ``scrape`` is able to recognize and account for common "defanging" techniques (such as ``evildomain[.]com``,
  ``myemail[@]somedomain.net``, or ``hxxp://badwebsite.org/``), and will scrape "defanged" indicators by
  default. Use the ``--skiprefang`` switch to ignore defanged indicators.


.. _storm-service:

service
-------

Storm includes ``service.*`` commands that allow you to work with Storm services (see :ref:`gloss-service`).

- `service.add`_
- `service.list`_
- `service.del`_

Help for individual ``service.*`` commands can be displayed using:

  ``<command> --help``

.. _storm-service-add:

service.add
+++++++++++

The ``service.add`` command adds a Storm service to the Cortex.

**Syntax:**

::

    storm> service.add --help
    
    Add a storm service to the cortex.
    
    Usage: service.add [options] <name> <url>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <name>                      : The name of the service.
      <url>                       : The telepath URL for the remote service.



.. _storm-service-list:

service.list
++++++++++++

The ``service.list`` command lists each Storm service in the Cortex.

**Syntax:**

::

    storm> service.list --help
    
    List the storm services configured in the cortex.
    
    Usage: service.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-service-del:

service.del
+++++++++++

The ``service.del`` command removes a Storm service from the Cortex.

**Syntax:**

::

    storm> service.del --help
    
    Remove a storm service from the cortex.
    
    Usage: service.del [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : The service identifier or prefix.



.. _storm-sleep:

sleep
-----

The ``sleep`` command adds a delay in returning each result for a given Storm query. By default,
query results are streamed back and displayed as soon as they arrive for optimal performance.
A ``sleep`` delay effectively slows the display of results.

.. TIP:

  ``sleep`` may be useful in cases such as querying rate-limited APIs.

**Syntax:**

::

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



**Example:**

- Retrieve email nodes from a Cortex every second:

::

    storm> inet:email | sleep 1.0
    inet:email=bar@gmail.com
            :fqdn = gmail.com
            :user = bar
            .created = 2023/10/05 21:46:43.676
    inet:email=baz@gmail.com
            :fqdn = gmail.com
            :user = baz
            .created = 2023/10/05 21:46:43.679
    inet:email=foo@gmail.com
            :fqdn = gmail.com
            :user = foo
            .created = 2023/10/05 21:46:43.672



.. _storm-spin:

spin
----

The ``spin`` command is used to suppress the output of a Storm query. ``Spin`` simply consumes all
nodes sent to the command, so no nodes are output to the CLI. This allows you to execute a Storm
query and view messages and results without displaying the associated nodes.

**Syntax:**

::

    storm> spin --help
    
    
        Iterate through all query results, but do not yield any.
        This can be used to operate on many nodes without returning any.
    
        Example:
    
            foo:bar:size=20 [ +#hehe ] | spin
    
        
    
    Usage: spin [options] 
    
    Options:
    
      --help                      : Display the command usage.



**Example:**

- Add the tag #int.research to any domain containing the string "firefox" but do not display the nodes.


::

    storm> inet:fqdn~=firefox [+#int.research] | spin



.. _storm-tag:

tag
---

Storm includes ``tag.*`` commands that allow you to work with tags (see :ref:`gloss-tag`).

- `tag.prune`_

Help for individual ``tag.*`` commands can be displayed using:

  ``<command> --help``
  
See also the related :ref:`storm-movetag` command.

.. _storm-tag-prune:

tag.prune
+++++++++

The ``tag.prune`` command will delete the tags from incoming nodes, as well as all of their parent
tags that don't have other tags as children.

**Syntax:**

::

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



.. _storm-tee:

tee
---

The ``tee`` command executes multiple Storm queries on the inbound nodes and returns the combined
result set.

**Syntax:**

::

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
      --parallel                  : Run the storm queries in parallel instead of sequence. The node output order is not guaranteed.
    
    Arguments:
    
      [<query> ...]               : Specify a query to execute on the input nodes.



**Examples:**

- Return the set of domains and IP addresses associated with a set of DNS A records.

::

    storm> inet:fqdn:zone=mydomain.com -> inet:dns:a | tee { -> inet:fqdn } { -> inet:ipv4 }
    inet:fqdn=foo.mydomain.com
            :domain = mydomain.com
            :host = foo
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.775
    inet:ipv4=8.8.8.8
            :type = unicast
            .created = 2023/10/05 21:46:46.775
    inet:fqdn=bar.mydomain.com
            :domain = mydomain.com
            :host = bar
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.780
    inet:ipv4=34.56.78.90
            :type = unicast
            .created = 2023/10/05 21:46:46.780
    inet:fqdn=baz.mydomain.com
            :domain = mydomain.com
            :host = baz
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.784
    inet:ipv4=127.0.0.2
            :type = loopback
            .created = 2023/10/05 21:46:46.784



- Return the set of domains and IP addresses associated with a set of DNS A records along with the
  original DNS A records.

::

    storm> inet:fqdn:zone=mydomain.com -> inet:dns:a | tee --join { -> inet:fqdn } { -> inet:ipv4 }
    inet:fqdn=foo.mydomain.com
            :domain = mydomain.com
            :host = foo
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.775
    inet:ipv4=8.8.8.8
            :type = unicast
            .created = 2023/10/05 21:46:46.775
    inet:dns:a=('foo.mydomain.com', '8.8.8.8')
            :fqdn = foo.mydomain.com
            :ipv4 = 8.8.8.8
            .created = 2023/10/05 21:46:46.775
    inet:fqdn=bar.mydomain.com
            :domain = mydomain.com
            :host = bar
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.780
    inet:ipv4=34.56.78.90
            :type = unicast
            .created = 2023/10/05 21:46:46.780
    inet:dns:a=('bar.mydomain.com', '34.56.78.90')
            :fqdn = bar.mydomain.com
            :ipv4 = 34.56.78.90
            .created = 2023/10/05 21:46:46.780
    inet:fqdn=baz.mydomain.com
            :domain = mydomain.com
            :host = baz
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2023/10/05 21:46:46.784
    inet:ipv4=127.0.0.2
            :type = loopback
            .created = 2023/10/05 21:46:46.784
    inet:dns:a=('baz.mydomain.com', '127.0.0.2')
            :fqdn = baz.mydomain.com
            :ipv4 = 127.0.0.2
            .created = 2023/10/05 21:46:46.784



**Usage Notes:**

- ``tee`` can take an arbitrary number of Storm queries (i.e., 1 to n queries) as arguments.


.. _storm-tree:

tree
----

The ``tree`` command recursively performs the specified pivot until no additional nodes are returned.

**Syntax:**

::

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



**Example:**

- List the full set of tags in the "TTP" tag hierarchy.

::

    storm> syn:tag=ttp | tree { $node.value() -> syn:tag:up }
    syn:tag=ttp
            :base = ttp
            :depth = 0
            .created = 2023/10/05 21:46:46.853
    syn:tag=ttp.opsec
            :base = opsec
            :depth = 1
            :up = ttp
            .created = 2023/10/05 21:46:46.853
    syn:tag=ttp.opsec.anon
            :base = anon
            :depth = 2
            :up = ttp.opsec
            .created = 2023/10/05 21:46:46.853
    syn:tag=ttp.se
            :base = se
            :depth = 1
            :up = ttp
            .created = 2023/10/05 21:46:46.857
    syn:tag=ttp.se.masq
            :base = masq
            :depth = 2
            :up = ttp.se
            .created = 2023/10/05 21:46:46.857
    syn:tag=ttp.phish
            :base = phish
            :depth = 1
            :up = ttp
            .created = 2023/10/05 21:46:46.860
    syn:tag=ttp.phish.payload
            :base = payload
            :depth = 2
            :up = ttp.phish
            .created = 2023/10/05 21:46:46.860



**Usage Notes:**

- ``tree`` is useful for "walking" a set of properties with a single command vs. performing an
  arbitrary number of pivots until the end of the data is reached.

.. _storm-trigger:

trigger
-------

.. NOTE::
  
  See the :ref:`storm-ref-automation` guide for additional background on triggers (as well as cron
  jobs and macros), including examples.

Storm includes ``trigger.*`` commands that allow you to create automated event-driven triggers
(see :ref:`gloss-trigger`) using the Storm query syntax.

- `trigger.add`_
- `trigger.list`_
- `trigger.mod`_
- `trigger.disable`_
- `trigger.enable`_
- `trigger.del`_

Help for individual ``trigger.*`` commands can be displayed using:

  ``<command> --help``

Triggers are added to the Cortex as **runtime nodes** ("runt nodes" - see :ref:`gloss-node-runt`)
of the form ``syn:trigger``. These runt nodes can be lifted and filtered just like standard nodes
in Synapse.

.. _storm-trigger-add:

trigger.add
+++++++++++

The ``trigger.add`` command adds a trigger to a Cortex.

**Syntax:**

::

    storm> trigger.add --help
    
    
    Add a trigger to the cortex.
    
    Notes:
        Valid values for condition are:
            * tag:add
            * tag:del
            * node:add
            * node:del
            * prop:set
    
    When condition is tag:add or tag:del, you may optionally provide a form name
    to restrict the trigger to fire only on tags added or deleted from nodes of
    those forms.
    
    The added tag is provided to the query as an embedded variable '$tag'.
    
    Simple one level tag globbing is supported, only at the end after a period,
    that is aka.* matches aka.foo and aka.bar but not aka.foo.bar. aka* is not
    supported.
    
    Examples:
        # Adds a tag to every inet:ipv4 added
        trigger.add node:add --form inet:ipv4 --query {[ +#mytag ]}
    
        # Adds a tag #todo to every node as it is tagged #aka
        trigger.add tag:add --tag aka --query {[ +#todo ]}
    
        # Adds a tag #todo to every inet:ipv4 as it is tagged #aka
        trigger.add tag:add --form inet:ipv4 --tag aka --query {[ +#todo ]}
    
    
    Usage: trigger.add [options] <condition>
    
    Options:
    
      --help                      : Display the command usage.
      --form <form>               : Form to fire on.
      --tag <tag>                 : Tag to fire on.
      --prop <prop>               : Property to fire on.
      --query <storm>             : Query for the trigger to execute.
      --async                     : Make the trigger run in the background.
      --disabled                  : Create the trigger in disabled state.
      --name <name>               : Human friendly name of the trigger.
      --view <view>               : The view to add the trigger to.
    
    Arguments:
    
      <condition>                 : Condition for the trigger.



.. _storm-trigger-list:

trigger.list
++++++++++++

The ``trigger-list`` command displays the set of triggers in the Cortex that the current user can
view / modify based on their permissions. Triggers are displayed at the Storm CLI in tabular format,
with columns including the user who created the trigger, the :ref:`gloss-iden` of the trigger, the
condition that fires the trigger (i.e., ``node:add``), and the Storm query associated with the trigger.

Triggers are displayed in alphanumeric order by iden. Triggers are sorted upon Cortex initialization,
so newly-created triggers will be displayed at the bottom of the list until the list is re-sorted the
next time the Cortex is restarted.

.. NOTE::

  Triggers can also be viewed in runt node form as ``syn:trigger`` nodes.

**Syntax:**

::

    storm> trigger.list --help
    
    List existing triggers in the cortex.
    
    Usage: trigger.list [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --all                       : List every trigger in every readable view, rather than just the current view.



.. _storm-trigger-mod:

trigger.mod
+++++++++++

The ``trigger.mod`` command modifies the Storm query associated with a specific trigger. To modify
a trigger, you must provide the first portion of the trigger's iden (i.e., enough of the iden that
the trigger can be uniquely identified), which can be obtained using ``trigger.list`` or by lifting
the appropriate ``syn:trigger`` node.

.. NOTE::

  Other aspects of the trigger, such as the condition used to fire the trigger or the tag or property
  associated with the trigger, cannot be modified once the trigger has been created. To change these
  aspects, you must delete and re-add the trigger.

**Syntax:**

::

    storm> trigger.mod --help
    
    Modify an existing trigger's query.
    
    Usage: trigger.mod [options] <iden> <query>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.
      <query>                     : New storm query for the trigger.



.. _storm-trigger-disable:

trigger.disable
+++++++++++++++

The ``trigger.disable`` command disables a trigger and prevents it from firing without removing it from
the Cortex. To disable a trigger, you must provide the first portion of the trigger's iden (i.e., enough
of the iden that the trigger can be uniquely identified), which can be obtained using ``trigger.list``
or by lifting the appropriate ``syn:trigger`` node.

**Syntax:**

::

    storm> trigger.disable --help
    
    Disable a trigger in the cortex.
    
    Usage: trigger.disable [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.



.. _storm-trigger-enable:

trigger.enable
++++++++++++++

The ``trigger-enable`` command enables a disabled trigger. To enable a trigger, you must provide the
first portion of the trigger's iden (i.e., enough of the iden that the trigger can be uniquely identified),
which can be obtained using ``trigger.list`` or by lifting the appropriate ``syn:trigger`` node.

.. NOTE::

  Triggers are enabled by default upon creation.

**Syntax:**

::

    storm> trigger.enable --help
    
    Enable a trigger in the cortex.
    
    Usage: trigger.enable [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.



.. _storm-trigger-del:

trigger.del
+++++++++++

The ``trigger.del`` command permanently removes a trigger from the Cortex. To delete a trigger, you
must provide the first portion of the trigger's iden (i.e., enough of the iden that the trigger can
be uniquely identified), which can be obtained using ``trigger.list`` or by lifting the appropriate
``syn:trigger`` node.

**Syntax:**

::

    storm> trigger.del --help
    
    Delete a trigger from the cortex.
    
    Usage: trigger.del [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Any prefix that matches exactly one valid trigger iden is accepted.



.. _storm-uniq:

uniq
----

The ``uniq`` command removes duplicate results from a Storm query. Results are uniqued based on each
node's node identifier (node ID / iden) so that only the first node with a given node ID is returned.

**Syntax:**

::

    storm> uniq --help
    
    
        Filter nodes by their uniq iden values.
        When this is used a Storm pipeline, only the first instance of a
        given node is allowed through the pipeline.
    
        A relative property or variable may also be specified, which will cause
        this command to only allow through the first node with a given value for
        that property or value rather than checking the node iden.
    
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



**Examples:**

- Lift all of the unique IP addresses that domains associated with the Fancy Bear threat group have
  resolved to:

::

    storm> inet:fqdn#rep.threatconnect.fancybear -> inet:dns:a -> inet:ipv4 | uniq
    inet:ipv4=111.90.148.124
            :type = unicast
            .created = 2023/10/05 21:46:46.992
    inet:ipv4=209.99.40.222
            :type = unicast
            .created = 2023/10/05 21:46:46.997
    inet:ipv4=141.8.224.221
            :type = unicast
            .created = 2023/10/05 21:46:47.001



.. _storm-uptime:

uptime
------

The ``uptime`` command displays the uptime for the Cortex or specified service.

**Syntax:**

::

    storm> uptime --help
    
    Print the uptime for the Cortex or a connected service.
    
    Usage: uptime [options] <name>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      [name]                      : The name, or iden, of the service (if not provided defaults to the Cortex).



.. _storm-version:

version
-------

The ``version`` command displays the current version of Synapse and associated metadata.

**Syntax:**

::

    storm> version --help
    
    Show version metadata relating to Synapse.
    
    Usage: version [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-view:

view
----

Storm includes ``view.*`` commands that allow you to work with views (see :ref:`gloss-view`).

- `view.add`_
- `view.fork`_
- `view.set`_
- `view.get`_
- `view.list`_
- `view.exec`_
- `view.merge`_
- `view.del`_

Help for individual ``view.*`` commands can be displayed using:

  ``<command> --help``


.. _storm-view-add:

view.add
++++++++

The ``view.add`` command adds a view to the Cortex.

**Syntax:**

::

    storm> view.add --help
    
    Add a view to the cortex.
    
    Usage: view.add [options] 
    
    Options:
    
      --help                      : Display the command usage.
      --name <name>               : The name of the new view. (default: None)
      --worldreadable <worldreadable>: Grant read access to the `all` role. (default: False)
      --layers [<layers> ...]     : Layers for the view. (default: [])



.. _storm-view-fork:

view.fork
+++++++++

The ``view.fork`` command forks an existing view from the Cortex. Forking a view creates a new
view with a new writeable layer on top of the set of layers from the previous (forked) view.

**Syntax:**

::

    storm> view.fork --help
    
    Fork a view in the cortex.
    
    Usage: view.fork [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
      --name <name>               : Name for the newly forked view. (default: None)
    
    Arguments:
    
      <iden>                      : Iden of the view to fork.



.. _storm-view-set:

view.set
++++++++

The ``view.set`` command sets a property on the specified view.

**Syntax:**

::

    storm> view.set --help
    
    Set a view option.
    
    Usage: view.set [options] <iden> <name> <valu>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Iden of the view to modify.
      <name>                      : The name of the view property to set.
      <valu>                      : The value to set the view property to.



.. _storm-view-get:

view.get
++++++++

The ``view.get`` command retrieves an existing view from the Cortex.

**Syntax:**

::

    storm> view.get --help
    
    Get a view from the cortex.
    
    Usage: view.get [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      [iden]                      : Iden of the view to get. If no iden is provided, the main view will be returned.



.. _storm-view-list:

view.list
+++++++++

The ``view.list`` command lists the views in the Cortex.

**Syntax:**

::

    storm> view.list --help
    
    List the views in the cortex.
    
    Usage: view.list [options] 
    
    Options:
    
      --help                      : Display the command usage.



.. _storm-view-exec:

view.exec
+++++++++

The ``view.exec`` command executes a Storm query in the specified view.

**Syntax:**

::

    storm> view.exec --help
    
    
        Execute a storm query in a different view.
    
        NOTE: Variables are passed through but nodes are not
    
        Examples:
    
            // Move some tagged nodes to another view
            inet:fqdn#foo.bar $fqdn=$node.value() | view.exec 95d5f31f0fb414d2b00069d3b1ee64c6 { [ inet:fqdn=$fqdn ] }
        
    
    Usage: view.exec [options] <view> <storm>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <view>                      : The GUID of the view in which the query will execute.
      <storm>                     : The storm query to execute on the view.



.. _storm-view-merge:

view.merge
++++++++++

The ``view.merge`` command merges **all** data from a forked view into its parent view.

Contrast with :ref:`storm-merge` which can merge a subset of nodes.

**Syntax:**

::

    storm> view.merge --help
    
    Merge a forked view into its parent view.
    
    Usage: view.merge [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
      --delete                    : Once the merge is complete, delete the layer and view.
    
    Arguments:
    
      <iden>                      : Iden of the view to merge.



.. _storm-view-del:

view.del
++++++++

The ``view.del`` command permanently deletes a view from the Cortex.

**Syntax:**

::

    storm> view.del --help
    
    Delete a view from the cortex.
    
    Usage: view.del [options] <iden>
    
    Options:
    
      --help                      : Display the command usage.
    
    Arguments:
    
      <iden>                      : Iden of the view to delete.



.. _storm-wget:

wget
----

The ``wget`` command retrieves content from one or more specified URLs. The command creates
and yields ``inet:urlfile`` nodes and the retrieved content (``file:bytes``) is stored in the
:ref:`gloss-axon`.

**Syntax:**

::

    storm> wget --help
    
    Retrieve bytes from a URL and store them in the axon. Yields inet:urlfile nodes.
    
    Examples:
    
        # Specify custom headers and parameters
        inet:url=https://vertex.link/foo.bar.txt | wget --headers $lib.dict("User-Agent"="Foo/Bar") --params $lib.dict("clientid"="42")
    
        # Download multiple URL targets without inbound nodes
        wget https://vertex.link https://vtx.lk
    
    
    Usage: wget [options] <urls>
    
    Options:
    
      --help                      : Display the command usage.
      --no-ssl-verify             : Ignore SSL certificate validation errors.
      --timeout <timeout>         : Configure the timeout for the download operation. (default: 300)
      --params <params>           : Provide a dict containing url parameters. (default: None)
      --headers <headers>         : Provide a Storm dict containing custom request headers. (default: 
    {                                 'Accept': '*/*',
                                      'Accept-Encoding': 'gzip, deflate',
                                      'Accept-Language': 'en-US,en;q=0.9',
                                      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                    'Chrome/92.0.4515.131 Safari/537.36'})
      --no-headers                : Do NOT use any default headers.
    
    Arguments:
    
      [<urls> ...]                : URLs to download.


.. _changelog: https://synapse.docs.vertex.link/en/latest/synapse/changelog.html
