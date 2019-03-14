



.. highlight:: none

.. _syn-ref-cmd:

Synapse Reference - cmdr Commands
====================================

The Synapse CLI (cmdr) contains a set of built-in commands that can be used to interact with a Synapse Cortex. This section details the usage for each built-in Synapse command.

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



.. parsed-literal::

    cli> help
    at      - Adds a non-recurring cron job.
    cron    - Manages cron jobs in a cortex.
    help    - List commands and display help output.
    hive    - Manipulates values in a cell's Hive.
    kill    - Kill a running task/query within the cortex.
    locs    - List the current locals for a given CLI object.
    log     - Add a storm log to the local command session.
    ps      - List running tasks in the cortex.
    quit    - Quit the current command line interpreter.
    storm   - Execute a storm query.
    trigger - Manipulate triggers in a cortex.


.. _syn-at:

at
--

The ``at`` command allows you to schedule a `storm`_ query to execute within a Cortex at one or more specified times. Once created, tasks / queries scheduled with ``at`` are managed using the `cron`_ command. At jobs, like cron jobs, remain in a Cortex until explicitly removed.

**Syntax:**



.. parsed-literal::

    cli> help at
    === at
    
    Adds a non-recurring cron job.
    
    It will execute a Storm query at one or more specified times.
    
    List/details/deleting cron jobs created with 'at' use the same commands as
    other cron jobs:  cron list/stat/del respectively.
    
    Syntax:
        at (time|+time delta)+ {query}
    
    Notes:
        This command accepts one or more time specifications followed by exactly
        one storm query in curly braces.  Each time specification may be in synapse
        time delta format (e.g + 1 day) or synapse time format (e.g.
        20501217030432101).  Seconds will be ignored, as cron jobs' granularity is
        limited to minutes.
    
        All times are interpreted as UTC.
    
        The other option for time specification is a relative time from now.  This
        consists of a plus sign, a positive integer, then one of 'minutes, hours,
        days'.
    
        Note that the record for a cron job is stored until explicitly deleted via
        "cron del".
    
    Examples:
        # Run a storm query in 5 minutes
        at +5 minutes {[inet:ipv4=1]}
    
        # Run a storm query tomorrow and in a week
        at +1 day +7 days {[inet:ipv4=1]}
    
        # Run a query at the end of the year Zulu
        at 20181231Z2359 {[inet:ipv4=1]}
    


**Example:**

TBD



.. _syn-cron:

cron
----

The ``cron`` command allows you to schedule a `storm`_ query to execute within a Cortex on a recurring basis. ``cron`` has multiple subcommands, including:

- `cron help`_
- `cron add`_
- `cron list`_
- `cron stat`_
- `cron mod`_
- `cron del`_

**Syntax:**



.. parsed-literal::

    cli> help cron
    === cron
    
    Manages cron jobs in a cortex.
    
    Cron jobs are rules persistently stored in a cortex such that storm queries
    automatically run on a time schedule.
    
    Cron jobs may be be recurring or one-time.  Use the 'at' command to add
    one-time jobs.
    
    A subcommand is required.  Use 'cron -h' for more detailed help.  


cron help
+++++++++

``cron`` includes detailed help describing its individual subcommands.

**Syntax:**



.. parsed-literal::

    cli> cron -h
    usage: cron [-h] {list,add,del,stat,mod} ...
    
    Manages cron jobs in a cortex.
    
    Cron jobs are rules persistently stored in a cortex such that storm queries
    automatically run on a time schedule.
    
    Cron jobs may be be recurring or one-time.  Use the 'at' command to add
    one-time jobs.
    
    A subcommand is required.  Use 'cron -h' for more detailed help.  
    
    optional arguments:
      -h, --help            show this help message and exit
    
    subcommands:
      {list,add,del,stat,mod}
        list                List cron jobs you're allowed to manipulate
        add                 add a cron job
        del                 delete a cron job
        stat                details a cron job
        mod                 change an existing cron jobquery
    


cron add
++++++++

``cron add`` adds a cron job to a Cortex.

**Syntax:**



.. parsed-literal::

    cli> cron add -h
    usage: 
    Add a recurring cron job to a cortex.
    
    Syntax:
        cron add [optional arguments] {query}
    
        --minute, -M int[,int...][=]
        --hour, -H
        --day, -d
        --month, -m
        --year, -y
    
           *or:*
    
        [--hourly <min> |
         --daily <hour>:<min> |
         --monthly <day>:<hour>:<min> |
         --yearly <month>:<day>:<hour>:<min>]
    
    Notes:
        All times are interpreted as UTC.
    
        All arguments are interpreted as the job period, unless the value ends in
        an equals sign, in which case the argument is interpreted as the recurrence
        period.  Only one recurrence period parameter may be specified.
    
        Currently, a fixed unit must not be larger than a specified recurrence
        period.  i.e. '--hour 7 --minute +15' (every 15 minutes from 7-8am?) is not
        supported.
    
        Value values for fixed hours are 0-23 on a 24-hour clock where midnight is 0.
    
        If the --day parameter value does not start with in '+' and is an integer, it is
        interpreted as a fixed day of the month.  A negative integer may be
        specified to count from the end of the month with -1 meaning the last day
        of the month.  All fixed day values are clamped to valid days, so for
        example '-d 31' will run on February 28.
    
        If the fixed day parameter is a value in ([Mon, Tue, Wed, Thu, Fri, Sat,
        Sun] if locale is set to English) it is interpreted as a fixed day of the
        week.
    
        Otherwise, if the parameter value starts with a '+', then it is interpreted
        as an recurrence interval of that many days.
    
        If no plus-sign-starting parameter is specified, the recurrence period
        defaults to the unit larger than all the fixed parameters.   e.g. '-M 5'
        means every hour at 5 minutes past, and -H 3, -M 1 means 3:01 every day.
    
        At least one optional parameter must be provided.
    
        All parameters accept multiple comma-separated values.  If multiple
        parameters have multiple values, all combinations of those values are used.
    
        All fixed units not specified lower than the recurrence period default to
        the lowest valid value, e.g. -m +2 will be scheduled at 12:00am the first of
        every other month.  One exception is the largest fixed value is day of the
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
        cron add -H 3 -d-1 {#foo}
    
        Run a query every 8 hours
        cron add -H +8 {#foo}
    
        Run a query every Wednesday and Sunday at midnight and noon
        cron add -H 0,12 -d Wed,Sun {#foo}
    
        Run a query every other day at 3:57pm
        cron add -d +2 -M 57 -H 15 {#foo}
    
    positional arguments:
      query                 Storm query in curly braces
    
    optional arguments:
      -h, --help            show this help message and exit
      --minute MINUTE, -M MINUTE
      --hour HOUR, -H HOUR
      --day DAY, -d DAY     day of week, day of month or number of days
      --month MONTH, -m MONTH
      --year YEAR, -y YEAR
      --hourly HOURLY
      --daily DAILY
      --monthly MONTHLY
      --yearly YEARLY
    


**Example:**

TBD



cron list
+++++++++

``cron list`` lists existing cron jobs in a Cortex that the current user can view / modify based on their permissions.

**Syntax:**



.. parsed-literal::

    cli> cron list -h
    usage: 
    List existing cron jobs in a cortex.
    
    Syntax:
        cron list
    
    Example:
        cli> cron list
        user       iden       recurs? now? # start last start       last end         query
        <None>     4ad2218a.. N       N          1 2018-12-14T15:53 2018-12-14T15:53 #foo
        <None>     f6b6aebd.. Y       N          3 2018-12-14T16:25 2018-12-14T16:25 #foo
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

TBD



cron stat
+++++++++

``cron stat`` displays statistics about a cron job. ``cron stat`` requires the iden (ID, identifier) prefix of the cron job to be displayed, which can be obtained with the `cron list`_ command.

**Syntax:**



.. parsed-literal::

    cli> cron stat -h
    usage: 
    Gives detailed information about a single cron job.
    
    Syntax:
        cron stat <iden prefix>
    
    Notes:
        Any prefix that matches exactly one valid cron job iden is accepted.
    
    positional arguments:
      prefix      Cron job iden prefix
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

TBD



cron mod
++++++++

``cron mod`` allows you to modify the `storm`_ query executed by a cron job. ``cron mod`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `cron list`_ command.

Once created, a cron job’s schedule (including jobs created with `at`_ ) cannot be modified. A new job must be added and the old job removed.

**Syntax:**



.. parsed-literal::

    cli> cron mod -h
    usage: 
    Changes an existing cron job's query.
    
    Syntax:
        cron mod <iden prefix> <new query>
    
    Notes:
        Any prefix that matches exactly one valid cron iden is accepted.
    
    positional arguments:
      prefix      Cron job iden prefix
      query       New Storm query in curly braces
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

TBD



cron del
++++++++

``cron del`` deletes the specified cron job. Cron jobs remain in a Cortex until explicitly removed. ``cron del`` requires the iden (ID, identifier) prefix of the cron job to be removed, which can be obtained with the `cron list`_ command.

**Syntax:**



.. parsed-literal::

    cli> cron del -h
    usage: 
    Deletes a single cron job.
    
    Syntax:
        cron del <iden prefix>
    
    Notes:
        Any prefix that matches exactly one valid cron job iden is accepted.
    
    positional arguments:
      prefix      Cron job iden prefix
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

TBD



.. _syn-kill:

kill
----

The ``kill`` command terminates a task/query executing within a Cortex. ``kill`` requires the iden (ID, identifier) or iden prefix of the task to be terminated, which can be obtained with the `ps`_ command.

**Syntax:**



.. parsed-literal::

    cli> help kill
    === kill
    
        Kill a running task/query within the cortex.
    
        Syntax:
            kill <iden>
    
        Users may specify a partial iden GUID in order to kill
        exactly one matching process based on the partial guid.
        


**Example:**

TBD



.. _syn-locs:

locs
----

The ``locs`` command prints a json-compatible dictionary of local CLI variables where the value is a repr of the object.

**Syntax:**



.. parsed-literal::

    cli> help locs
    === locs
    
        List the current locals for a given CLI object.
        


**Example:**

TBD



.. _syn-log:

log
---

The ``log`` command creates a local log of `storm`_ commands executed during your current session.

**Syntax:**



.. parsed-literal::

    cli> help log
    === log
    
        Add a storm log to the local command session.
    
        Syntax:
            log (--on|--off) [--splices-only] [--format (mpk|jsonl)] [--path /path/to/file]
    
        Required Arguments:
            --on: Enables logging of storm messages to a file.
            --off: Disables message logging and closes the current storm file.
    
        Optional Arguments:
            --splices-only: Only records splices. Does not record any other messages.
            --format: The format used to save messages to disk. Defaults to msgpack (mpk).
            --path: The path to the log file.  This will append messages to a existing file.
    
        Notes:
            By default, the log file contains all messages received from the execution of
            a Storm query by the current CLI. By default, these messages are saved to a
            file located in ~/.syn/stormlogs/storm_(date).(format).
    
        Examples:
            # Enable logging all messages to mpk files (default)
            log --on
    
            # Disable logging and close the current file
            log --off
    
            # Enable logging, but only log splices. Log them as jsonl instead of mpk.
            log --on --splices-only --format jsonl
    
            # Enable logging, but log to a custom path:
            log --on --path /my/aweome/log/directory/storm20010203.mpk
    
        


**Example:**

TBD



.. _syn-ps:

ps
--

The ``ps`` command displays the tasks/queries currently running in a Cortex.

**Syntax:**



.. parsed-literal::

    cli> help ps
    === ps
    
        List running tasks in the cortex.
        


**Example:**

TBD



.. _syn-quit:

quit
----

The ``quit`` command terminates the current Synapse session and exits from the command line interpreter.

**Syntax:**



.. parsed-literal::

    cli> help quit
    === quit
    
        Quit the current command line interpreter.
    
        Example:
    
            quit
        


.. _syn-storm:

storm
-----

The ``storm`` command executes a Synapse Storm query. Storm is the native Synapse query language used to lift, modify, model and analyze data in a Cortex and execute any loaded Synapse modules. The Storm query language is covered in detail starting with the :ref:`storm-ref-intro` section of the Synapse User Guide.

**Syntax:**



.. parsed-literal::

    cli> help storm
    === storm
    
        Execute a storm query.
    
        Syntax:
            storm <query>
    
        Arguments:
            query: The storm query
    
        Optional Arguments:
            --hide-tags: Do not print tags
            --hide-props: Do not print secondary properties
            --hide-unknown: Do not print messages which do not have known handlers.
            --raw: Print the nodes in their raw format
                (overrides --hide-tags and --hide-props)
            --debug: Display cmd debug information along with nodes in raw format
                (overrides --hide-tags, --hide-props and raw)
            --path: Get path information about returned nodes.
            --graph: Get graph information about returned nodes.
    
        Examples:
            storm inet:ipv4=1.2.3.4
            storm --debug inet:ipv4=1.2.3.4
        


.. _syn-trigger:

trigger
-------

The ``trigger`` command manipulates triggers in a Cortex. A trigger is a rule stored in a Cortex that enables the automatic execution of a Storm query when a particular event occurs (e.g., an IP address node being added to the Cortex).

``trigger`` has multiple subcommands, including:

- `trigger help`_
- `trigger add`_
- `trigger list`_
- `trigger mod`_
- `trigger del`_

**Syntax:**



.. parsed-literal::

    cli> help trigger
    === trigger
    
    Manipulate triggers in a cortex.
    
    Triggers are rules persistently stored in a cortex such that storm queries
    automatically run when a particular event happens.
    
    A subcommand is required.  Use `trigger -h` for more detailed help.
    


trigger help
++++++++++++

``trigger`` includes detailed help describing its individual subcommands.

**Syntax:**



.. parsed-literal::

    cli> trigger -h
    usage: trigger [-h] {list,add,del,mod} ...
    
    Manipulate triggers in a cortex.
    
    Triggers are rules persistently stored in a cortex such that storm queries
    automatically run when a particular event happens.
    
    A subcommand is required.  Use `trigger -h` for more detailed help.
    
    optional arguments:
      -h, --help          show this help message and exit
    
    subcommands:
      {list,add,del,mod}
        list              List triggers you're allowed to manipulate
        add               add a trigger
        del               delete a trigger
        mod               change an existing trigger query
    


trigger add
+++++++++++

``trigger add`` adds a new trigger to a Cortex.

**Syntax:**



.. parsed-literal::

    cli> trigger add -h
    usage: 
    Add triggers in a cortex.
    
    Syntax: trigger add condition <object> [#tag] query
    
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
    
    Tag names must start with #.
    
    The added tag is provided to the query as an embedded variable '$tag'.
    
    Simple one level tag globbing is supported, only at the end after a period,
    that is aka.* matches aka.foo and aka.bar but not aka.foo.bar.  aka* is not
    supported.
    
    Examples:
        # Adds a tag to every inet:ipv4 added
        trigger add node:add inet:ipv4 {[ +#mytag ]}
    
        # Adds a tag #todo to every node as it is tagged #aka
        trigger add tag:add #aka {[ +#todo ]}
    
        # Adds a tag #todo to every inet:ipv4 as it is tagged #aka
        trigger add tag:add inet:ipv4 #aka {[ +#todo ]}
    
    positional arguments:
      {tag:add,prop:set,node:add,tag:del,node:del}
                            Condition on which to trigger
      arguments             [form] [#tag] [prop] {query}
    
    optional arguments:
      -h, --help            show this help message and exit
    


**Example:**

<stuff>



trigger list
++++++++++++

``trigger list`` lists the current triggers in a Cortex.

**Syntax:**



.. parsed-literal::

    cli> trigger list -h
    usage: 
    List existing triggers in a cortex.
    
    Syntax:
        trigger list
    
    Example:
        cli> trigger list
        user       iden         cond      object                    storm query
        <None>     739719ff..   prop:set  testtype10.intprop            [ testint=6 ]
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

<stuff>



trigger mod
+++++++++++

``trigger mod`` allows you to modify the `storm`_ query associated with a given trigger. ``trigger mod`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `trigger list`_ command.

Once created, a trigger’s condition, object, and tag parameters cannot be modified. To change these parameters, a new trigger must be added and the old trigger removed.

**Syntax:**



.. parsed-literal::

    cli> trigger mod -h
    usage: 
    Changes an existing trigger's query.
    
    Syntax:
        trigger mod <iden prefix> <new query>
    
    Notes:
        Any prefix that matches exactly one valid trigger iden is accepted.
    
    positional arguments:
      prefix      Trigger iden prefix
      query       Storm query in curly braces
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

<stuff>


trigger del
+++++++++++

``trigger del`` removes the specified trigger from a Cortex. ``trigger del`` requires the iden (ID, identifier) prefix of the cron job to be modified, which can be obtained with the `trigger list`_ command.

**Syntax:**



.. parsed-literal::

    cli> trigger del -h
    usage: 
    Delete an existing trigger.
    
    Syntax:
        trigger del <iden prefix>
    
    Notes:
        Any prefix that matches exactly one valid trigger iden is accepted.
    
    positional arguments:
      prefix      Trigger iden prefix
    
    optional arguments:
      -h, --help  show this help message and exit
    


**Example:**

<stuff>


