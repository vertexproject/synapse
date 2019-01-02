



.. _syn-ref-cmd:

Synapse Reference - Synapse Commands
====================================

The Synapse CLI contains a set of built-in commands that can be used to interact with a Synapse Cortex. This section details the usage for each built-in Synapse command.

See :ref:`syn-tools-cmdr` for background on using ``cmdr`` and interacting with the Synapse CLI.

The following Synapse commands are currently supported:

- `help`_
- `at`_
- `cron`_
- `kill`_
- `locs`_
- `log`_
- `ps`_
- `quit`_
- `storm`_
- `trigger`_

.. _syn_help:

help
----

The ``help`` command displays the list of available built-in commands and a brief message describing each command. Help on individual commands is available via ``help <command>``.

**Syntax:**



.. _syn-at:

at
--

The ``at`` command allows you to schedule a `storm`_ query to execute within a Cortex at one or more specified times. Once created, tasks / queries scheduled with ``at`` are managed using the `cron`_ command. At jobs, like cron jobs, remain in a Cortex until explicitly removed.

**Syntax:**



**Example:**

<stuff>



.. _syn-cron:

cron
----

The ``cron`` command allows you to schedule a `storm`_ query to execute within a Cortex on a recurring basis. ``cron`` has multiple subcommands, including:

- `cron help`_
- `cron list`_
- `cron del`_
- `cron add`_
- `cron stat`_
- `cron mod`_

**Syntax:**



cron help
+++++++++

``cron`` includes detailed help describing its individual subcommands.

**Syntax:**



cron list
+++++++++

``cron list`` lists existing cron jobs in a Cortex that the current user can view / modify based on their permissions.

**Syntax:**



**Example:**

<stuff>



cron del
++++++++

``cron del`` deletes the specified cron job. Cron jobs remain in a Cortex until explicitly removed. ``cron del`` requires the iden (ID, identifier) prefix of the cron job to be removed, which can be obtained with the `cron list`_ command.

**Syntax:**



**Example:**

<stuff>



cron add
++++++++

``cron add`` adds a cron job to a Cortex.

**Syntax:**



**Example:**

<stuff>



cron stat
+++++++++

``cron stat`` displays statistics about a cron job. ``cron stat`` requires the iden (ID, identifier) prefix of the cron job to be displayed, which can be obtained with the `cron list`_ command.

**Syntax:**



**Example:**

<stuff>



cron mod
++++++++

``cron mod`` allows you to modify the `storm`_ query executed by a cron job. ``cron mod`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `cron list`_ command.

Once created, a cron job’s schedule (including jobs created with `at`_ ) cannot be modified. A new job must be added and the old job removed.

**Syntax:**



**Example:**

<stuff>



.. _syn-kill:

kill
----

The ``kill`` command terminates a task/query executing within a Cortex. ``kill`` requires the iden (ID, identifier) or iden prefix of the task to be terminated, which can be obtained with the `ps`_ command.

**Syntax:**



**Example:**

<stuff>



.. _syn-locs:

locs
----

The ``locs`` command prints a json-compatible dictionary of local CLI variables where the value is a repr of the object.

**Syntax:**



**Example:**

<stuff>



.. _syn-log:

log
---

The ``log`` command creates a local log of `storm`_ commands executed during your current session.

**Syntax:**



**Example:**

<stuff>



.. _syn-ps:

ps
--

The ``ps`` command displays the tasks/queries currently running in a Cortex.

**Syntax:**



**Example:**

<stuff>



.. _syn-quit:

quit
----

The ``quit`` command terminates the current Synapse session and exits from the command line interpreter.

**Syntax:**



.. _syn-storm:

storm
-----

The ``storm`` command executes a Synapse Storm query. Storm is the native Synapse query language used to lift, modify, model and analyze data in a Cortex and execute any loaded Synapse modules. The Storm query language is covered in detail starting with the :ref:`storm-ref-intro` section of the Synapse User Guide.

**Syntax:**



.. _syn-trigger:

trigger
-------

The ``trigger`` command manipulates triggers in a Cortex. A trigger is a rule stored in a Cortex that enables the automatic execution of a Storm query when a particular event occurs (e.g., an IP address node being added to the Cortex). For a detailed discussion of triggers and their use, see :ref:`synapse-triggers`.

``trigger`` has multiple subcommands, including:

- `trigger help`_
- `trigger list`_
- `trigger add`_
- `trigger del`_
- `trigger mod`_

**Syntax:**



trigger help
++++++++++++

``trigger`` includes detailed help describing its individual subcommands.

**Syntax:**



trigger list
++++++++++++

``trigger list`` lists the current triggers in a Cortex.

**Syntax:**



**Example:**

<stuff>



trigger add
+++++++++++

``trigger add`` adds a new trigger to a Cortex.

**Syntax:**



**Example:**

<stuff>



trigger del
+++++++++++

``trigger del`` removes the specified trigger from a Cortex. ``trigger del`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `trigger list`_ command.

**Syntax:**



**Example:**

<stuff>



trigger mod
+++++++++++

``trigger mod`` allows you to modify the `storm`_ query associated with a given trigger. ``trigger mod`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `trigger list`_ command.

Once created, a trigger’s condition, object, and tag parameters cannot be modified. To change these parameters, a new trigger must be added and the old trigger removed.

**Syntax:**



**Example:**

<stuff>


