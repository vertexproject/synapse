import asyncio
import logging
import argparse
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.ast as s_ast
import synapse.lib.base as s_base
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.scrape as s_scrape
import synapse.lib.grammar as s_grammar
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

addtriggerdescr = '''
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
'''

addcrondescr = '''
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
'''

atcrondescr = '''
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
'''

reqValidPkgdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'version': {
            'type': ['array', 'number'],
            'items': {'type': 'number'}
        },
        'modules': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/module'}
        },
        'commands': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/command'}
        },
        'desc': {'type': 'string'},
        'svciden': {'type': ['string', 'null'], 'pattern': s_config.re_iden}
    },
    'additionalProperties': True,
    'required': ['name', 'version'],
    'definitions': {
        'module': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'storm': {'type': 'string'}
            },
            'additionalProperties': True,
            'required': ['name', 'storm']
        },
        'command': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'pattern': s_grammar.re_scmd
                },
                'storm': {'type': 'string'}
            },
            'additionalProperties': True,
            'required': ['name', 'storm']
        }
    }
})

reqValidDdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'storm': {'type': 'string'},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'enabled': {'type': 'boolean', 'default': True},
        'stormopts': {
            'oneOf': [
                {'type': 'null'},
                {'$ref': '#/definitions/stormopts'}
            ]
        }
    },
    'additionalProperties': True,
    'required': ['iden', 'user', 'storm'],
    'definitions': {
        'stormopts': {
            'type': 'object',
            'properties': {
                'spawn': {'type': 'boolean'},
                'repr': {'type': 'boolean'},
                'path': {'type': 'string'},
                'show': {'type': 'array', 'items': {'type': 'string'}}
            },
            'additionalProperties': True,
        },
    }
})

stormcmds = (
    {
        'name': 'queue.add',
        'descr': 'Add a queue to the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name of the new queue.'}),
        ),
        'storm': '''
            $lib.queue.add($cmdopts.name)
            $lib.print("queue added: {name}", name=$cmdopts.name)
        ''',
    },
    {
        'name': 'queue.del',
        'descr': 'Remove a queue from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name of the queue to remove.'}),
        ),
        'storm': '''
            $lib.queue.del($cmdopts.name)
            $lib.print("queue removed: {name}", name=$cmdopts.name)
        ''',
    },
    {
        'name': 'queue.list',
        'descr': 'List the queues in the cortex.',
        'storm': '''
            $lib.print('Storm queue list:')
            for $info in $lib.queue.list() {
                $name = $info.name.ljust(32)
                $lib.print("    {name}:  size: {size} offs: {offs}", name=$name, size=$info.size, offs=$info.offs)
            }
        ''',
    },
    {
        'name': 'dmon.list',
        'descr': 'List the storm daemon queries running in the cortex.',
        'cmdargs': (),
        'storm': '''
            $lib.print('Storm daemon list:')
            for $info in $lib.dmon.list() {
                $name = $info.name.ljust(20)
                $lib.print("    {iden}:  ({name}): {status}", iden=$info.iden, name=$name, status=$info.status)
            }
        ''',
    },
    {
        'name': 'feed.list',
        'descr': 'List the feed functions available in the Cortex',
        'cmdrargs': (),
        'storm': '''
            $lib.print('Storm feed list:')
            for $flinfo in $lib.feed.list() {
                $flname = $flinfo.name.ljust(30)
                $lib.print("    ({name}): {desc}", name=$flname, desc=$flinfo.desc)
            }
        '''
    },
    {
        'name': 'layer.add',
        'descr': 'Add a layer to the cortex.',
        'cmdargs': (
            ('--lockmemory', {'help': 'Should the layer lock memory for performance.',
                              'action': 'store_true'}),
            ('--readonly', {'help': 'Should the layer be readonly.',
                            'action': 'store_true'}),
            ('--growsize', {'help': 'Amount to grow the map size when necessary.', 'type': int}),
            ('--upstream', {'help': 'One or more telepath urls to receive updates from.'}),
            ('--name', {'help': 'The name of the layer.'}),
        ),
        'storm': '''
            $layr = $lib.layer.add($cmdopts)
            $lib.print($layr.repr())
            $lib.print("Layer added.")
        ''',
    },
    {
        'name': 'layer.set',
        'descr': 'Set a layer option.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the layer to modify.'}),
            ('name', {'help': 'The name of the layer property to set.'}),
            ('valu', {'help': 'The value to set the layer property to.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.iden)
            $layr.set($cmdopts.name, $cmdopts.valu)
            $lib.print($layr.repr())
            $lib.print('Layer updated.')
        ''',
    },
    {
        'name': 'layer.del',
        'descr': 'Delete a layer from the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the layer to delete.'}),
        ),
        'storm': '''
            $lib.layer.del($cmdopts.iden)
            $lib.print("Layer deleted: {iden}", iden=$cmdopts.iden)
        ''',
    },
    {
        'name': 'layer.get',
        'descr': 'Get a layer from the cortex.',
        'cmdargs': (
            ('iden', {'nargs': '?',
                      'help': 'Iden of the layer to get. If no iden is provided, the main layer will be returned.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.iden)
            $lib.print($layr.repr())
        ''',
    },
    {
        'name': 'layer.list',
        'descr': 'List the layers in the cortex.',
        'cmdargs': (),
        'storm': '''
            $lib.print('Layers:')
            for $layr in $lib.layer.list() {
                $lib.print($layr.repr())
            }
        ''',
    },
    {
        'name': 'pkg.list',
        'descr': 'List the storm packages loaded in the cortex.',
        'cmdrargs': (),
        'storm': '''
            $pkgs = $lib.pkg.list()

            if $($pkgs.size() = 0) {

                $lib.print('No storm packages installed.')

            } else {
                $lib.print('Loaded storm packages:')
                for $pkg in $pkgs {
                    $lib.print("{name}: {vers}", name=$pkg.name.ljust(32), vers=$pkg.version)
                }
            }
        '''
    },
    {
        'name': 'pkg.del',
        'descr': 'Remove a storm package from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package to remove.'}),
        ),
        'storm': '''

            $pkgs = $lib.set()

            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pkgs.add($pkg.name)
                }
            }

            if $($pkgs.size() = 0) {

                $lib.print('No package names match "{name}". Aborting.', name=$cmdopts.name)

            } elif $($pkgs.size() = 1) {

                $name = $pkgs.list().index(0)
                $lib.print('Removing package: {name}', name=$name)
                $lib.pkg.del($name)

            } else {

                $lib.print('Multiple package names match "{name}". Aborting.', name=$cmdopts.name)

            }
        '''
    },
    {
        'name': 'view.add',
        'descr': 'Add a view to the cortex.',
        'cmdargs': (
            ('--name', {'default': None, 'help': 'The name of the new view.'}),
            ('--layers', {'default': [], 'nargs': '*', 'help': 'Layers for the view.'}),
        ),
        'storm': '''
            $view = $lib.view.add($cmdopts.layers, name=$cmdopts.name)
            $lib.print($view.repr())
            $lib.print("View added.")
        ''',
    },
    {
        'name': 'view.del',
        'descr': 'Delete a view from the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the view to delete.'}),
        ),
        'storm': '''
            $lib.view.del($cmdopts.iden)
            $lib.print("View deleted: {iden}", iden=$cmdopts.iden)
        ''',
    },
    {
        'name': 'view.set',
        'descr': 'Set a view option.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the view to modify.'}),
            ('name', {'help': 'The name of the view property to set.'}),
            ('valu', {'help': 'The value to set the view property to.'}),
        ),
        'storm': '''
            $view = $lib.view.get($cmdopts.iden)
            $view.set($cmdopts.name, $cmdopts.valu)
            $lib.print($view.repr())
            $lib.print("View updated.")
        ''',
    },
    {
        'name': 'view.fork',
        'descr': 'Fork a view in the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the view to fork.'}),
            ('--name', {'default': None, 'help': 'Name for the newly forked view.'}),
        ),
        'storm': '''
            $forkview = $lib.view.get($cmdopts.iden).fork(name=$cmdopts.name)
            $lib.print($forkview.repr())
            $lib.print("View {iden} forked to new view: {forkiden}", iden=$cmdopts.iden, forkiden=$forkview.iden)
        ''',
    },
    {
        'name': 'view.get',
        'descr': 'Get a view from the cortex.',
        'cmdargs': (
            ('iden', {'nargs': '?',
                      'help': 'Iden of the view to get. If no iden is provided, the main view will be returned.'}),
        ),
        'storm': '''
            $view = $lib.view.get($cmdopts.iden)
            $lib.print($view.repr())
        ''',
    },
    {
        'name': 'view.list',
        'descr': 'List the views in the cortex.',
        'cmdargs': (),
        'storm': '''
            $lib.print("")
            for $view in $lib.view.list() {
                $lib.print($view.repr())
                $lib.print("")
            }
        ''',
    },
    {
        'name': 'view.merge',
        'descr': 'Merge a forked view into its parent view.',
        'cmdargs': (
            ('iden', {'help': 'Iden of the view to merge.'}),
            ('--delete', {'default': False, 'action': 'store_true',
                          'help': 'Once the merge is complete, delete the layer and view.'}),
        ),
        'storm': '''
            $view = $lib.view.get($cmdopts.iden)

            $view.merge()

            if $cmdopts.delete {
                $layriden = $view.pack().layers.index(0).iden

                $lib.view.del($view.iden)
                $lib.layer.del($layriden)
            }
            $lib.print("View merged: {iden}", iden=$cmdopts.iden)
        ''',
    },
    {
        'name': 'trigger.add',
        'descr': addtriggerdescr,
        'cmdargs': (
            ('condition', {'help': 'Condition for the trigger.'}),
            ('--form', {'help': 'Form to fire on.'}),
            ('--tag', {'help': 'Tag to fire on.'}),
            ('--prop', {'help': 'Property to fire on.'}),
            ('--query', {'help': 'Query for the trigger to execute.', 'required': True}),
            ('--disabled', {'default': False, 'action': 'store_true',
                            'help': 'Create the trigger in disabled state.'}),
        ),
        'storm': '''
            $trig = $lib.trigger.add($cmdopts)

            $lib.print("Added trigger: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'trigger.del',
        'descr': 'Delete a trigger from the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid trigger iden is accepted.'}),
        ),
        'storm': '''
            $iden = $lib.trigger.del($cmdopts.iden)
            $lib.print("Deleted trigger: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'trigger.mod',
        'descr': "Modify an existing trigger's query.",
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid trigger iden is accepted.'}),
            ('query', {'help': 'New storm query for the trigger.'}),
        ),
        'storm': '''
            $iden = $lib.trigger.mod($cmdopts.iden, $cmdopts.query)
            $lib.print("Modified trigger: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'trigger.list',
        'descr': "List existing triggers in the cortex.",
        'cmdargs': (),
        'storm': '''
            $triggers = $lib.trigger.list()

            if $triggers {

                $lib.print("user       iden                             en?    cond      object                    storm query")

                for $trigger in $triggers {
                    $user = $trigger.username.ljust(10)
                    $iden = $trigger.iden.ljust(12)
                    $enabled = $lib.model.type(bool).repr($trigger.enabled).ljust(6)
                    $cond = $trigger.cond.ljust(9)

                    $fo = ""
                    if $trigger.form {
                        $fo = $trigger.form
                    }

                    $pr = ""
                    if $trigger.prop {
                        $pr = $trigger.prop
                    }

                    if $cond.startswith('tag:') {
                        $obj = $fo.ljust(14)
                        $obj2 = $trigger.tag.ljust(10)

                    } else {
                        if $pr {
                            $obj = $pr.ljust(14)
                        } elif $fo {
                            $obj = $fo.ljust(14)
                        } else {
                            $obj = '<missing>     '
                        }
                        $obj2 = '          '
                    }

                    $lib.print("{user} {iden} {enabled} {cond} {obj} {obj2} {query}",
                              user=$user, iden=$iden, enabled=$enabled, cond=$cond,
                              obj=$obj, obj2=$obj2, query=$trigger.storm)
                }
            } else {
                $lib.print("No triggers found")
            }
        ''',
    },
    {
        'name': 'trigger.enable',
        'descr': 'Enable a trigger in the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid trigger iden is accepted.'}),
        ),
        'storm': '''
            $iden = $lib.trigger.enable($cmdopts.iden)
            $lib.print("Enabled trigger: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'trigger.disable',
        'descr': 'Disable a trigger in the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid trigger iden is accepted.'}),
        ),
        'storm': '''
            $iden = $lib.trigger.disable($cmdopts.iden)
            $lib.print("Disabled trigger: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'cron.add',
        'descr': addcrondescr,
        'cmdargs': (
            ('query', {'help': 'Query for the cron job to execute.'}),
            ('--minute', {'help': 'Minute value for job or recurrence period.'}),
            ('--hour', {'help': 'Hour value for job or recurrence period.'}),
            ('--day', {'help': 'Day value for job or recurrence period.'}),
            ('--month', {'help': 'Month value for job or recurrence period.'}),
            ('--year', {'help': 'Year value for recurrence period.'}),
            ('--hourly', {'help': 'Fixed parameters for an hourly job.'}),
            ('--daily', {'help': 'Fixed parameters for a daily job.'}),
            ('--monthly', {'help': 'Fixed parameters for a monthly job.'}),
            ('--yearly', {'help': 'Fixed parameters for a yearly job.'}),
        ),
        'storm': '''
            $cron = $lib.cron.add(query=$cmdopts.query,
                                  minute=$cmdopts.minute,
                                  hour=$cmdopts.hour,
                                  day=$cmdopts.day,
                                  month=$cmdopts.month,
                                  year=$cmdopts.year,
                                  hourly=$cmdopts.hourly,
                                  daily=$cmdopts.daily,
                                  monthly=$cmdopts.monthly,
                                  yearly=$cmdopts.yearly)

            $lib.print("Created cron job: {iden}", iden=$cron.iden)
        ''',
    },
    {
        'name': 'cron.at',
        'descr': atcrondescr,
        'cmdargs': (
            ('query', {'help': 'Query for the cron job to execute.'}),
            ('--minute', {'help': 'Minute(s) to execute at.'}),
            ('--hour', {'help': 'Hour(s) to execute at.'}),
            ('--day', {'help': 'Day(s) to execute at.'}),
            ('--dt', {'help': 'Datetime(s) to execute at.'}),
        ),
        'storm': '''
            $cron = $lib.cron.at(query=$cmdopts.query,
                                 minute=$cmdopts.minute,
                                 hour=$cmdopts.hour,
                                 day=$cmdopts.day,
                                 dt=$cmdopts.dt)

            $lib.print("Created cron job: {iden}", iden=$cron.iden)
        ''',
    },
    {
        'name': 'cron.del',
        'descr': 'Delete a cron job from the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
        ),
        'storm': '''
            $lib.cron.del($cmdopts.iden)
            $lib.print("Deleted cron job: {iden}", iden=$cmdopts.iden)
        ''',
    },
    {
        'name': 'cron.mod',
        'descr': "Modify an existing cron job's query.",
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
            ('query', {'help': 'New storm query for the cron job.'}),
        ),
        'storm': '''
            $iden = $lib.cron.mod($cmdopts.iden, $cmdopts.query)
            $lib.print("Modified cron job: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'cron.list',
        'descr': "List existing cron jobs in the cortex.",
        'cmdargs': (),
        'storm': '''
            $crons = $lib.cron.list()

            if $crons {
                $lib.print("user       iden       en? rpt? now? err? # start last start       last end         query")

                for $cron in $crons {

                    $job = $cron.pprint()

                    $user = $job.user.ljust(10)
                    $iden = $job.idenshort.ljust(10)
                    $enabled = $job.enabled.ljust(3)
                    $isrecur = $job.isrecur.ljust(4)
                    $isrunning = $job.isrunning.ljust(4)
                    $iserr = $job.iserr.ljust(4)
                    $startcount = $lib.str.format("{startcount}", startcount=$job.startcount).ljust(7)
                    $laststart = $job.laststart.ljust(16)
                    $lastend = $job.lastend.ljust(16)

       $lib.print("{user} {iden} {enabled} {isrecur} {isrunning} {iserr} {startcount} {laststart} {lastend} {query}",
                               user=$user, iden=$iden, enabled=$enabled, isrecur=$isrecur,
                               isrunning=$isrunning, iserr=$iserr, startcount=$startcount,
                               laststart=$laststart, lastend=$lastend, query=$job.query)
                }
            } else {
                $lib.print("No cron jobs found")
            }
        ''',
    },
    {
        'name': 'cron.stat',
        'descr': "Gives detailed information about a cron job.",
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
        ),
        'storm': '''
            $cron = $lib.cron.get($cmdopts.iden)

            if $cron {
                $job = $cron.pprint()

                $lib.print('iden:            {iden}', iden=$job.iden)
                $lib.print('user:            {user}', user=$job.user)
                $lib.print('enabled:         {enabled}', enabled=$job.enabled)
                $lib.print('recurring:       {isrecur}', isrecur=$job.isrecur)
                $lib.print('# starts:        {startcount}', startcount=$job.startcount)
                $lib.print('last start time: {laststart}', laststart=$job.laststart)
                $lib.print('last end time:   {lastend}', lastend=$job.lastend)
                $lib.print('last result:     {lastresult}', lastresult=$job.lastresult)
                $lib.print('query:           {query}', query=$job.query)

                if $job.recs {
                    $lib.print('entries:         incunit    incval required')

                    for $rec in $job.recs {
                        $incunit = $lib.str.format('{incunit}', incunit=$rec.incunit).ljust(10)
                        $incval = $lib.str.format('{incval}', incval=$rec.incval).ljust(6)

                        $lib.print('                 {incunit} {incval} {reqdict}',
                                   incunit=$incunit, incval=$incval, reqdict=$rec.reqdict)
                    }
                } else {
                    $lib.print('entries:         <None>')
                }
            }
        ''',
    },
    {
        'name': 'cron.enable',
        'descr': 'Enable a cron job in the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
        ),
        'storm': '''
            $iden = $lib.cron.enable($cmdopts.iden)
            $lib.print("Enabled cron job: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'cron.disable',
        'descr': 'Disable a cron job in the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
        ),
        'storm': '''
            $iden = $lib.cron.disable($cmdopts.iden)
            $lib.print("Disabled cron job: {iden}", iden=$iden)
        ''',
    },
    {
        'name': 'ps.list',
        'descr': 'List running tasks in the cortex.',
        'cmdargs': (
            ('--verbose', {'default': False, 'action': 'store_true', 'help': 'Enable verbose output.'}),
        ),
        'storm': '''
            $tasks = $lib.ps.list()

            for $task in $tasks {
                $lib.print("task iden: {iden}", iden=$task.iden)
                $lib.print("    name: {name}", name=$task.name)
                $lib.print("    user: {user}", user=$task.user)
                $lib.print("    status: {status}", status=$task.status)
                $lib.print("    start time: {start}", start=$lib.time.format($task.tick, '%Y-%m-%d %H:%M:%S'))
                $lib.print("    metadata:")
                if $cmdopts.verbose {
                    $lib.pprint($task.info, prefix='    ')
                } else {
                    $lib.pprint($task.info, prefix='    ', clamp=120)
                }
            }

            $lib.print("{tlen} tasks found.", tlen=$tasks.size())
        ''',
    },
    {
        'name': 'ps.kill',
        'descr': 'Kill a running task/query within the cortex.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid process iden is accepted.'}),
        ),
        'storm': '''
            $kild = $lib.ps.kill($cmdopts.iden)
            $lib.print("kill status: {kild}", kild=$kild)
        ''',
    }
)

class DmonManager(s_base.Base):
    '''
    Manager for StormDmon objects.
    '''
    async def __anit__(self, core):
        await s_base.Base.__anit__(self)
        self.core = core
        self.dmons = {}
        self.enabled = False

        self.onfini(self._finiAllDmons)

    async def _finiAllDmons(self):
        await asyncio.gather(*[dmon.fini() for dmon in self.dmons.values()])

    async def _stopAllDmons(self):
        await asyncio.gather(*[dmon.stop() for dmon in self.dmons.values()])

    async def addDmon(self, iden, ddef):
        dmon = await StormDmon.anit(self.core, iden, ddef)
        self.dmons[iden] = dmon
        # TODO Remove default=True when dmon enabled CRUD is implemented
        if self.enabled and ddef.get('enabled', True):
            await dmon.run()
        return dmon

    def getDmonRunlog(self, iden):
        dmon = self.dmons.get(iden)
        if dmon is not None:
            return dmon._getRunLog()
        return ()

    def getDmon(self, iden):
        return self.dmons.get(iden)

    def getDmonDef(self, iden):
        dmon = self.dmons.get(iden)
        if dmon:
            return dmon.pack()

    def getDmonDefs(self):
        return list(d.pack() for d in self.dmons.values())

    async def popDmon(self, iden):
        '''Remove the dmon and fini it if its exists.'''
        logger.debug(f'Poping dmon {iden}')
        dmon = self.dmons.pop(iden, None)
        if dmon:
            await dmon.fini()

    async def start(self):
        '''
        Start all the dmons.
        '''
        if self.enabled:
            return
        for dmon in list(self.dmons.values()):
            await dmon.run()
        self.enabled = True

    async def stop(self):
        '''
        Stop all the dmons.
        '''
        if not self.enabled:
            return
        await self._stopAllDmons()
        self.enabled = False

    # TODO write enable/disable APIS.
    # 1. Set dmon.status to 'disabled'
    # 2. Be aware of ddef enabled flag to set status to 'disabled'.
    # async def enableDmon(self, iden):
    #     pass
    # async def disableDmon(self, iden):
    #     pass

class StormDmon(s_base.Base):
    '''
    A background storm runtime which is restarted by the cortex.
    '''
    async def __anit__(self, core, iden, ddef):

        await s_base.Base.__anit__(self)

        self.core = core
        self.iden = iden
        self.ddef = ddef

        self.task = None
        self.loop_task = None
        self.enabled = ddef.get('enabled')
        self.user = core.auth.user(ddef.get('user'))

        self.count = 0
        self.status = 'initialized'
        self.err_evnt = asyncio.Event()
        self.runlog = collections.deque((), 2000)

        self.onfini(self.stop)

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
        if self.loop_task is not None:
            self.loop_task.cancel()
        self.status = 'stopped'

    async def run(self):
        self.task = self.schedCoro(self._run())

    def pack(self):
        retn = dict(self.ddef)
        retn['count'] = self.count
        retn['status'] = self.status
        retn['err'] = self.err_evnt.is_set()
        return retn

    async def _run(self):
        name = self.ddef.get('name', 'storm dmon')
        info = {'iden': self.iden, 'name': name}
        await self.core.boss.promote('storm:dmon:main', user=self.user, info=info)
        while not self.isfini:
            try:
                logger.info(f'Dmon loop starting ({self.iden})')
                synt = await self.core.boss.execute(self._innr_run(),
                                                    name='storm:dmon:loop',
                                                    user=self.user,
                                                    info=info)
                self.loop_task = synt.task
                await synt.waitfini()
                # We have to give the callbacks a chance to run
                # so that we can determine the status of the task
                await asyncio.sleep(0)
                if self.loop_task.cancelled():
                    # Restart the loop right away
                    continue
                # Check and re-raise exceptions
                exc = self.loop_task.exception()
                if exc:
                    raise exc
            except asyncio.CancelledError:
                if self.loop_task:
                    self.loop_task.cancel()
                self.status = f'fatal error: Dmon main cancelled'
                self.err_evnt.set()
                logger.warning(f'Dmon main cancelled ({self.iden})')
                raise
            except s_exc.NoSuchView as e:
                if self.loop_task:
                    self.loop_task.cancel()
                self.status = f'fatal error: invalid view (iden={e.get("iden")})'
                logger.warning(f'Dmon View is invalid. Exiting Dmon: ({self.iden})')
                raise
            except Exception as e:  # pragma: no cover
                self.status = f'error: {e}'
                self.err_evnt.set()
                logger.exception(f'Dmon error during loop task execution ({self.iden})')
                await self.waitfini(timeout=1)

    def _runLogAdd(self, mesg):
        self.runlog.append((s_common.now(), mesg))

    def _getRunLog(self):
        return list(self.runlog)

    async def _innr_run(self):

        s_scope.set('storm:dmon', self.iden)

        text = self.ddef.get('storm')
        opts = self.ddef.get('stormopts', {})
        view_iden = opts.get('view')
        view = self.core.getView(view_iden)
        if view is None:
            raise s_exc.NoSuchView(iden=view_iden)

        def dmonPrint(evnt):
            self._runLogAdd(evnt)
            mesg = evnt[1].get('mesg', '')
            logger.info(f'Dmon - {self.iden} - {mesg}')

        def dmonWarn(evnt):
            self._runLogAdd(evnt)
            mesg = evnt[1].get('mesg', '')
            logger.info(f'Dmon - {self.iden} - WARNING: {mesg}')

        while not self.isfini:

            try:

                self.status = 'running'
                async with await self.core.snap(user=self.user, view=view) as snap:

                    snap.on('warn', dmonWarn)
                    snap.on('print', dmonPrint)
                    self.err_evnt.clear()

                    async for nodepath in snap.storm(text, opts=opts, user=self.user):
                        # all storm tasks yield often to prevent latency
                        self.count += 1
                        await asyncio.sleep(0)

                    logger.warning(f'Dmon query exited: {self.iden}')

                    self.status = 'exited'
                    await self.waitfini(timeout=1)

            except asyncio.CancelledError:
                logger.warning(f'Dmon loop cancelled: ({self.iden})')
                raise

            except Exception as e:
                self._runLogAdd(('err', s_common.excinfo(e)))
                logger.exception(f'Dmon error ({self.iden})')
                self.status = f'error: {e}'
                self.err_evnt.set()
                await self.waitfini(timeout=1)

class Runtime:
    '''
    A Runtime represents the instance of a running query.

    The runtime should maintain a firm API boundary using the snap.
    Parallel query execution requires that the snap be treated as an
    opaque object which is called through, but not dereferenced.

    '''
    def __init__(self, snap, opts=None, user=None):

        if opts is None:
            opts = {}

        self.vars = {}
        self.ctors = {
            'lib': s_stormtypes.LibBase,
        }

        self.opts = opts
        self.snap = snap
        self.user = user

        self.model = snap.core.getDataModel()

        self.task = asyncio.current_task()

        self.inputs = []    # [synapse.lib.node.Node(), ...]

        self.iden = s_common.guid()

        varz = self.opts.get('vars')
        if varz is not None:
            self.vars.update(varz)

        self.runtvars = set()
        self.runtvars.update(self.vars.keys())
        self.runtvars.update(self.ctors.keys())
        self.isModuleRunt = False
        self.globals = set()
        self.modulefuncs = {}

        self.proxies = {}

    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.snap.core.dyncall(iden, todo, gatekeys=gatekeys)

    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.snap.core.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    async def getStormQuery(self, text):
        return self.snap.core.getStormQuery(text)

    async def coreDynCall(self, todo, perm=None):
        gatekeys = ()
        if perm is not None:
            gatekeys = ((self.user.iden, perm, None),)
        return await self.snap.core.dyncall('cortex', todo, gatekeys=gatekeys)

    async def getTeleProxy(self, url, **opts):

        flat = tuple(sorted(opts.items()))
        prox = self.proxies.get((url, flat))
        if prox is not None:
            return prox

        prox = await s_telepath.openurl(url, **opts)

        self.proxies[(url, flat)] = prox
        self.snap.onfini(prox.fini)

        return prox

    def isRuntVar(self, name):
        if name in self.runtvars:
            return True
        return False

    async def printf(self, mesg):
        return await self.snap.printf(mesg)

    async def warn(self, mesg, **info):
        return await self.snap.warn(mesg, **info)

    def tick(self):
        pass

    def cancel(self):
        self.task.cancel()

    def initPath(self, node):
        return s_node.Path(self, dict(self.vars), [node])

    def getOpt(self, name, defval=None):
        return self.opts.get(name, defval)

    def setOpt(self, name, valu):
        self.opts[name] = valu

    def getVar(self, name, defv=None):

        item = self.vars.get(name, s_common.novalu)
        if item is not s_common.novalu:
            return item

        ctor = self.ctors.get(name)
        if ctor is not None:
            item = ctor(self)
            self.vars[name] = item
            return item

        return defv

    def setVar(self, name, valu):
        self.vars[name] = valu

    def addInput(self, node):
        '''
        Add a Node() object as input to the query runtime.
        '''
        self.inputs.append(node)

    async def getInput(self):

        for node in self.inputs:
            yield node, self.initPath(node)

        for ndef in self.opts.get('ndefs', ()):

            node = await self.snap.getNodeByNdef(ndef)
            if node is not None:
                yield node, self.initPath(node)

        for iden in self.opts.get('idens', ()):

            buid = s_common.uhex(iden)
            if len(buid) != 32:
                raise s_exc.NoSuchIden(mesg='Iden must be 32 bytes', iden=iden)

            node = await self.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, self.initPath(node)

    def layerConfirm(self, perms):
        iden = self.snap.wlyr.iden
        return self.user.confirm(perms, gateiden=iden)

    def confirm(self, perms, gateiden=None):
        '''
        Raise AuthDeny if user doesn't have global permissions and write layer permissions

        '''
        return self.user.confirm(perms, gateiden=gateiden)

    def loadRuntVars(self, query):
        # do a quick pass to determine which vars are per-node.
        for oper in query.kids:
            for name in oper.getRuntVars(self):
                if self.isModuleRunt and isinstance(oper, s_ast.Function):
                    self.modulefuncs[name] = oper
                self.runtvars.add(name)

    async def iterStormQuery(self, query, genr=None):

        with s_provenance.claim('storm', q=query.text, user=self.user.iden):

            self.loadRuntVars(query)

            # init any options from the query
            # (but dont override our own opts)
            for name, valu in query.opts.items():
                self.opts.setdefault(name, valu)

            async for node, path in query.iterNodePaths(self, genr=genr):
                self.tick()
                yield node, path

    def canPropName(self, name):
        if name not in self.modulefuncs and name not in self.ctors:
            return True
        return False

    async def getScopeRuntime(self, query, opts=None, impd=False):
        '''
        Derive a new runt off of an existing runt. It will pass down any global level vars. It has to
        re run the oper.run function on any function opers so that it gets the correct context of
        variable values and functions.
        '''
        runt = Runtime(self.snap, user=self.user, opts=opts)
        # imported implies module level
        runt.isModuleRunt = impd
        if not impd:  # respect the import boundary

            # if we are a top level module we need to
            # push down our runtvars
            if self.isModuleRunt:
                for name in self.runtvars:
                    valu = self.vars.get(name, s_common.novalu)
                    if valu is s_common.novalu:
                        continue
                    if self.canPropName(name):
                        runt.globals.add(name)
                        runt.runtvars.add(name)
                        runt.vars[name] = valu

            # propagate down all the global variables
            for name in self.globals:
                if self.canPropName(name):
                    runt.vars[name] = self.vars[name]
                    runt.globals.add(name)
                    runt.runtvars.add(name)

            # regardless of module level, we have to reload the module functions
            # we were given so they run with the right runt. We need this so we have
            # the whole function telescoping going on, and module level variables get
            # set to the right values
            runt.modulefuncs = dict(self.modulefuncs)
            for name, oper in self.modulefuncs.items():
                runt.runtvars.add(name)
                async for item in oper.run(runt, s_common.agen()):
                    pass  # pragma: no cover

        runt.loadRuntVars(query)
        return runt

    async def propBackGlobals(self, runt):
        '''
        From a called runt (passed in by parameter), propagate the vars we know to be global
        to the module back up into the calling runt. *Don't* propagate any functions, since
        those need the context of which runt they're being called from, and just for safety
        don't mess with the base lib object.
        '''
        for name in runt.globals:
            valu = runt.vars.get(name, s_common.novalu)
            if valu is s_common.novalu:
                continue
            if not self.canPropName(name):
                # don't override our parent's version of a function
                continue
            self.vars[name] = valu

class Parser:

    def __init__(self, prog=None, descr=None, root=None):

        if root is None:
            root = self

        self.prog = prog
        self.descr = descr

        self.root = root
        self.exited = False
        self.mesgs = []

        self.optargs = {}
        self.posargs = []
        self.allargs = []

        self.reqopts = []

        self.add_argument('--help', '-h', action='store_true', default=False, help='Display the command usage.')

    def add_argument(self, *names, **opts):

        assert len(names)

        dest = self._get_dest(names)
        opts.setdefault('dest', dest)
        self.allargs.append((names, opts))

        if opts.get('required'):
            self.reqopts.append((names, opts))

        for name in names:
            self._add_arg(name, opts)

    def _get_dest(self, names):
        names = [n.strip('-').replace('-', '_') for n in names]
        names = list(sorted(names, key=lambda x: len(x)))
        return names[-1]

    def _printf(self, *msgs):
        self.mesgs.extend(msgs)

    def _add_arg(self, name, opts):

        if name.startswith('-'):
            self.optargs[name] = opts
            return

        self.posargs.append((name, opts))

    def _is_opt(self, valu):
        if not isinstance(valu, str):
            return False
        return self.optargs.get(valu) is not None

    def parse_args(self, argv):

        posargs = []
        todo = collections.deque(argv)

        opts = {}

        while todo:

            item = todo.popleft()

            # non-string args must be positional or nargs to an optarg
            if not isinstance(item, str):
                posargs.append(item)
                continue

            argdef = self.optargs.get(item)
            if argdef is None:
                posargs.append(item)
                continue

            dest = argdef.get('dest')

            oact = argdef.get('action', 'store')
            if oact == 'store_true':
                opts[dest] = True
                continue

            if oact == 'store_false':
                opts[dest] = False
                continue

            if oact == 'append':

                vals = opts.get(dest)
                if vals is None:
                    vals = opts[dest] = []

                fakeopts = {}
                if not self._get_store(item, argdef, todo, fakeopts):
                    return

                vals.append(fakeopts.get(dest))
                continue

            assert oact == 'store'
            if not self._get_store(item, argdef, todo, opts):
                return

        # check for help before processing other args
        if opts.get('help'):
            self.help()
            return

        # process positional arguments
        todo = collections.deque(posargs)

        for name, argdef in self.posargs:
            if not self._get_store(name, argdef, todo, opts):
                return

        if todo:
            delta = len(posargs) - len(todo)
            mesg = f'Expected {delta} positional arguments. Got {len(posargs)}: {posargs!r}'
            self.help(mesg)
            return

        for _, argdef in self.allargs:
            if 'default' in argdef:
                opts.setdefault(argdef['dest'], argdef['default'])

        for names, argdef in self.reqopts:
            dest = argdef.get('dest')
            if dest not in opts:
                namestr = ','.join(names)
                mesg = f'Missing a required option: {namestr}'
                self.help(mesg)
                return

        retn = argparse.Namespace()

        [setattr(retn, name, valu) for (name, valu) in opts.items()]

        return retn

    def _get_store(self, name, argdef, todo, opts):

        dest = argdef.get('dest')
        nargs = argdef.get('nargs')
        argtype = argdef.get('type')

        vals = []
        if nargs is None:

            if not todo or self._is_opt(todo[0]):
                if name.startswith('-'):
                    mesg = f'An argument is required for {name}.'
                else:
                    mesg = f'The argument <{name}> is required.'
                return self.help(mesg)

            valu = todo.popleft()
            if argtype is not None:
                try:
                    valu = argtype(valu)
                except Exception:
                    mesg = f'Invalid value for type ({str(argtype)}): {valu}'
                    return self.help(mesg=mesg)

            opts[dest] = valu
            return True

        if nargs == '?':

            # ? will have an implicit default value of None
            opts.setdefault(dest, None)

            if todo and not self._is_opt(todo[0]):

                valu = todo.popleft()
                if argtype is not None:
                    try:
                        valu = argtype(valu)
                    except Exception:
                        mesg = f'Invalid value for type ({str(argtype)}): {valu}'
                        return self.help(mesg=mesg)

                opts[dest] = valu

            return True

        if nargs in ('*', '+'):

            while todo and not self._is_opt(todo[0]):

                valu = todo.popleft()

                if argtype is not None:
                    try:
                        valu = argtype(valu)
                    except Exception:
                        mesg = f'Invalid value for type ({str(argtype)}): {valu}'
                        return self.help(mesg=mesg)

                vals.append(valu)

            if nargs == '+' and len(vals) == 0:
                mesg = 'At least one argument is required for {name}.'
                return self.help(mesg)

            opts[dest] = vals
            return True

        for _ in range(nargs):

            if not todo or self._is_opt(todo[0]):
                mesg = f'{nargs} arguments are required for {name}.'
                return self.help(mesg)

            valu = todo.popleft()
            if argtype is not None:
                try:
                    valu = argtype(valu)
                except Exception:
                    mesg = f'Invalid value for type ({str(argtype)}): {valu}'
                    return self.help(mesg=mesg)

            vals.append(valu)

        opts[dest] = vals
        return True

    def help(self, mesg=None):

        posnames = [f'<{name}>' for (name, argdef) in self.posargs]

        posargs = ' '.join(posnames)

        if self.descr is not None:
            self._printf('')
            self._printf(self.descr)
            self._printf('')

        self._printf(f'Usage: {self.prog} [options] {posargs}')

        options = [x for x in self.allargs if x[0][0].startswith('-')]

        self._printf('')
        self._printf('Options:')
        self._printf('')

        for names, argdef in options:
            self._print_optarg(names, argdef)

        if self.posargs:

            self._printf('')
            self._printf('Arguments:')
            self._printf('')

            for name, argdef in self.posargs:
                self._print_posarg(name, argdef)

        if mesg is not None:
            self._printf('')
            self._printf(f'ERROR: {mesg}')

        self.exited = True
        return False

    def _print_optarg(self, names, argdef):
        dest = self._get_dest_str(argdef)
        oact = argdef.get('action', 'store')
        if oact in ('store_true', 'store_false'):
            base = f'  {names[0]}'.ljust(30)
        else:
            base = f'  {names[0]} {dest}'.ljust(30)
        helpstr = argdef.get('help', 'No help available')
        self._printf(f'{base}: {helpstr}')

    def _print_posarg(self, name, argdef):
        dest = self._get_dest_str(argdef)
        helpstr = argdef.get('help', 'No help available')
        base = f'  {dest}'.ljust(30)
        self._printf(f'{base}: {helpstr}')

    def _get_dest_str(self, argdef):

        dest = argdef.get('dest')
        nargs = argdef.get('nargs')

        if nargs == '*':
            return f'[<{dest}> ...]'

        if nargs == '+':
            return f'<{dest}> [<{dest}> ...]'

        if nargs == '?':
            return f'[{dest}]'

        return f'<{dest}>'

class Cmd:
    '''
    A one line description of the command.

    Command usage details and long form description.

    Example:

        cmd --help

    Notes:
        Python Cmd implementers may override the ``forms`` attribute with a dictionary to provide information
        about Synapse forms which are possible input and output nodes that a Cmd may recognize.

        Example:

            ::

                {
                    'input': (
                        'inet:ipv4',
                        'tel:mob:telem',
                    ),
                    'output': (
                        'geo:place',
                    ),
                }

    '''
    name = 'cmd'
    pkgname = ''
    svciden = ''
    forms = {}  # type: ignore

    def __init__(self, runt, runtsafe):

        self.opts = None
        self.argv = None

        self.runt = runt
        self.runtsafe = runtsafe

        self.pars = self.getArgParser()
        self.pars.printf = runt.snap.printf

    @classmethod
    def getCmdBrief(cls):
        return cls.__doc__.strip().split('\n')[0]

    def getName(self):
        return self.name

    def getDescr(self):
        return self.__class__.__doc__

    def getArgParser(self):
        return Parser(prog=self.getName(), descr=self.getDescr())

    async def setArgv(self, argv):

        self.argv = argv

        try:
            self.opts = self.pars.parse_args(self.argv)
        except s_exc.BadSyntax: # pragma: no cover
            pass

        for line in self.pars.mesgs:
            await self.runt.snap.printf(line)

        return not self.pars.exited

    async def execStormCmd(self, runt, genr): # pragma: no cover
        ''' Abstract base method '''
        raise s_exc.NoSuchImpl('Subclass must implement execStormCmd')
        for item in genr:
            yield item

    @classmethod
    def getStorNode(cls, form):
        ndef = (form.name, form.type.norm(cls.name)[0])
        buid = s_common.buid(ndef)

        props = {
            'doc': cls.getCmdBrief()
        }

        inpt = cls.forms.get('input')
        outp = cls.forms.get('output')

        if inpt:
            props['input'] = tuple(inpt)

        if outp:
            props['output'] = tuple(outp)

        if cls.svciden:
            props['svciden'] = cls.svciden

        if cls.pkgname:
            props['package'] = cls.pkgname

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms,
        })

class PureCmd(Cmd):

    def __init__(self, cdef, runt, runtsafe):
        self.cdef = cdef
        Cmd.__init__(self, runt, runtsafe)

    def getDescr(self):
        return self.cdef.get('descr', 'no documentation provided')

    def getName(self):
        return self.cdef.get('name')

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        for name, opts in self.cdef.get('cmdargs', ()):
            pars.add_argument(name, **opts)
        return pars

    async def execStormCmd(self, runt, genr):

        text = self.cdef.get('storm')
        query = runt.snap.core.getStormQuery(text)

        opts = {
            'vars': {
                'cmdopts': None,
                'cmdconf': self.cdef.get('cmdconf', {})
            }
        }
        with runt.snap.getStormRuntime(opts=opts, user=runt.user) as subr:

            if self.opts is not None:
                subr.setVar('cmdopts', vars(self.opts))

            subr.setVar('cmdconf', self.cdef.get('cmdconf', {}))

            async def wrapgenr():

                async for node, path in genr:

                    # In the event of a non-runtsafe command invocation our
                    # setArgv() method will be called with an argv computed
                    # for each node, so we need to remap cmdopts into our path & subr
                    cmdopts = vars(self.opts)
                    path.initframe(initvars={'cmdopts': cmdopts}, initrunt=subr)
                    subr.setVar('cmdopts', cmdopts)
                    yield node, path

            subr.loadRuntVars(query)

            async for node, path in subr.iterStormQuery(query, genr=wrapgenr()):
                path.finiframe(subr)
                yield node, path

class HelpCmd(Cmd):
    '''
    List available commands and a brief description for each.
    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('command', nargs='?', help='Show the help output for a given command.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for item in genr:
            yield item

        if not self.opts.command:
            stormcmds = sorted(runt.snap.core.getStormCmds())
            stormpkgs = await runt.snap.core.getStormPkgs()

            pkgsvcs = {}
            pkgcmds = {}
            pkgmap = {}

            for pkg in stormpkgs:
                svciden = pkg.get('svciden')
                pkgname = pkg.get('name')

                for cmd in pkg.get('commands', []):
                    pkgmap[cmd.get('name')] = pkgname

                ssvc = runt.snap.core.getStormSvc(svciden)
                if ssvc is not None:
                    pkgsvcs[pkgname] = f'{ssvc.name} ({svciden})'

            if stormcmds:
                maxlen = max(len(x[0]) for x in stormcmds)

                for name, ctor in stormcmds:
                    cmdinfo = f'{name:<{maxlen}}: {ctor.getCmdBrief()}'
                    pkgcmds.setdefault(pkgmap.get(name, 'synapse'), []).append(cmdinfo)

                await runt.printf(f'package: synapse')

                for cmd in pkgcmds.pop('synapse', []):
                    await runt.printf(cmd)

                await runt.printf('')

                for name, cmds in sorted(pkgcmds.items()):
                    svcinfo = pkgsvcs.get(name)

                    if svcinfo:
                        await runt.printf(f'service: {svcinfo}')

                    await runt.printf(f'package: {name}')

                    for cmd in cmds:
                        await runt.printf(cmd)

                    await runt.printf('')

        await runt.printf('For detailed help on any command, use <cmd> --help')

class LimitCmd(Cmd):
    '''
    Limit the number of nodes generated by the query in the given position.

    Example:

        inet:ipv4 | limit 10
    '''

    name = 'limit'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('count', type=int, help='The maximum number of nodes to yield.')
        return pars

    async def execStormCmd(self, runt, genr):

        count = 0
        async for item in genr:

            yield item
            count += 1

            if count >= self.opts.count:
                await runt.printf(f'limit reached: {self.opts.count}')
                break

class UniqCmd(Cmd):
    '''
    Filter nodes by their uniq iden values.
    When this is used a Storm pipeline, only the first instance of a
    given node is allowed through the pipeline.

    Examples:

        #badstuff +inet:ipv4 ->* | uniq

    '''

    name = 'uniq'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        return pars

    async def execStormCmd(self, runt, genr):

        buidset = set()

        async for node, path in genr:

            if node.buid in buidset:
                # all filters must sleep
                await asyncio.sleep(0)
                continue

            buidset.add(node.buid)
            yield node, path

class MaxCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the highest value for a property or variable.

    Examples:

        file:bytes +#foo.bar | max :size

        file:bytes +#foo.bar +.seen ($tick, $tock) = .seen | max $tick

    '''

    name = 'max'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('valu')
        return pars

    async def execStormCmd(self, runt, genr):

        maxvalu = None
        maxitem = None

        ivaltype = self.runt.snap.core.model.type('ival')

        async for item in genr:

            valu = await s_stormtypes.toprim(self.opts.valu)
            if valu is None:
                continue

            if isinstance(valu, (list, tuple)):
                if valu == (None, None):
                    continue

                ival, info = ivaltype.norm(valu)
                valu = ival[1]

            valu = s_stormtypes.intify(valu)

            if maxvalu is None or valu > maxvalu:
                maxvalu = valu
                maxitem = item

        if maxitem:
            yield maxitem

class MinCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the lowest value for a property.

    Examples:

        file:bytes +#foo.bar | min :size

        file:bytes +#foo.bar | min .seen
    '''
    name = 'min'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('valu')
        return pars

    async def execStormCmd(self, runt, genr):

        minvalu = None
        minitem = None

        ivaltype = self.runt.snap.core.model.type('ival')

        async for node, path in genr:

            valu = await s_stormtypes.toprim(self.opts.valu)
            if valu is None:
                continue

            if isinstance(valu, (list, tuple)):
                if valu == (None, None):
                    continue

                ival, info = ivaltype.norm(valu)
                valu = ival[0]

            valu = s_stormtypes.intify(valu)

            if minvalu is None or valu < minvalu:
                minvalu = valu
                minitem = (node, path)

        if minitem:
            yield minitem

class DelNodeCmd(Cmd):
    '''
    Delete nodes produced by the previous query logic.

    (no nodes are returned)

    Example

        inet:fqdn=vertex.link | delnode
    '''
    name = 'delnode'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        forcehelp = 'Force delete even if it causes broken references (requires admin).'
        pars.add_argument('--force', default=False, action='store_true', help=forcehelp)
        return pars

    async def execStormCmd(self, runt, genr):

        if self.opts.force:
            if runt.user is not None and not runt.user.isAdmin():
                mesg = '--force requires admin privs.'
                raise s_exc.AuthDeny(mesg=mesg)

        i = 0
        async for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.layerConfirm(('node', 'tag', 'del', *tag.split('.')))

            runt.layerConfirm(('node', 'del', node.form.name))

            await node.delete(force=self.opts.force)

            i += 1
            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

        # a bit odd, but we need to be detected as a generator
        if False:
            yield

class ReIndexCmd(Cmd):
    '''
    Use admin privileges to re index/normalize node properties.

    NOTE: Currently does nothing but is reserved for future use.
    '''
    name = 'reindex'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        return pars

    async def execStormCmd(self, runt, genr):
        mesg = 'reindex currently does nothing but is reserved for future use'
        await runt.snap.warn(mesg)

        # Make this a generator
        if False:
            yield

class SudoCmd(Cmd):
    '''
    Deprecated sudo command.

    Left in for 2.x.x so that Storm command with it are still valid to execute.
    '''
    name = 'sudo'

    async def execStormCmd(self, runt, genr):
        s_common.deprecated('stormcmd:sudo')

        mesg = 'Sudo is deprecated and does nothing in ' \
               '2.x.x and will be removed in 3.0.0.'

        await runt.snap.warn(mesg)
        async for node, path in genr:
            yield node, path

class MoveTagCmd(Cmd):
    '''
    Rename an entire tag tree and preserve time intervals.

    Example:

        movetag foo.bar baz.faz.bar
    '''
    name = 'movetag'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('oldtag', help='The tag tree to rename.')
        pars.add_argument('newtag', help='The new tag tree name.')
        return pars

    async def execStormCmd(self, runt, genr):
        snap = runt.snap

        opts = {'vars': {'tag': self.opts.oldtag}}
        nodes = await snap.nodes('syn:tag=$tag', opts=opts)

        if not nodes:
            raise s_exc.BadOperArg(mesg='Cannot move a tag which does not exist.',
                                   oldtag=self.opts.oldtag)
        oldt = nodes[0]
        oldstr = oldt.ndef[1]
        oldsize = len(oldstr)
        oldparts = oldstr.split('.')
        noldparts = len(oldparts)

        newt = await snap.addNode('syn:tag', self.opts.newtag)
        newstr = newt.ndef[1]

        if oldstr == newstr:
            raise s_exc.BadOperArg(mesg='Cannot retag a tag to the same valu.',
                                   newtag=newstr, oldtag=oldstr)

        retag = {oldstr: newstr}

        # first we set all the syn:tag:isnow props
        oldtag = self.opts.oldtag.strip('#')
        async for node in snap.nodesByPropValu('syn:tag', '^=', oldtag):

            tagstr = node.ndef[1]
            tagparts = tagstr.split('.')
            # Are we in the same tree?
            if tagparts[:noldparts] != oldparts:
                continue

            newtag = newstr + tagstr[oldsize:]

            newnode = await snap.addNode('syn:tag', newtag)

            olddoc = node.get('doc')
            if olddoc is not None:
                await newnode.set('doc', olddoc)

            oldtitle = node.get('title')
            if oldtitle is not None:
                await newnode.set('title', oldtitle)

            # Copy any tags over to the newnode if any are present.
            for k, v in node.tags.items():
                await newnode.addTag(k, v)

            retag[tagstr] = newtag
            await node.set('isnow', newtag)

        # now we re-tag all the nodes...
        count = 0
        async for node in snap.nodesByTag(oldstr):

            count += 1

            tags = list(node.tags.items())
            tags.sort(reverse=True)

            for name, valu in tags:

                newt = retag.get(name)
                if newt is None:
                    continue

                # Capture tagprop information before moving tags
                tgfo = {tagp: node.getTagProp(name, tagp) for tagp in node.getTagProps(name)}

                # Move the tags
                await node.delTag(name)
                await node.addTag(newt, valu=valu)

                # re-apply any captured tagprop data
                for tagp, tagp_valu in tgfo.items():
                    await node.setTagProp(newt, tagp, tagp_valu)

        await snap.printf(f'moved tags on {count} nodes.')

        async for node, path in genr:
            yield node, path

class SpinCmd(Cmd):
    '''
    Iterate through all query results, but do not yield any.
    This can be used to operate on many nodes without returning any.

    Example:

        foo:bar:size=20 [ +#hehe ] | spin

    '''
    name = 'spin'

    async def execStormCmd(self, runt, genr):

        if False:  # make this method an async generator function
            yield None

        async for node, path in genr:
            await asyncio.sleep(0)

class CountCmd(Cmd):
    '''
    Iterate through query results, and print the resulting number of nodes
    which were lifted. This does yield the nodes counted.

    Example:

        foo:bar:size=20 | count

    '''
    name = 'count'

    async def execStormCmd(self, runt, genr):

        i = 0
        async for item in genr:

            yield item
            i += 1

        await runt.printf(f'Counted {i} nodes.')

class IdenCmd(Cmd):
    '''
    Lift nodes by iden.

    Example:

        iden b25bc9eec7e159dce879f9ec85fb791f83b505ac55b346fcb64c3c51e98d1175 | count
    '''
    name = 'iden'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('iden', nargs='*', type=str, default=[],
                          help='Iden to lift nodes by. May be specified multiple times.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for x in genr:
            yield x

        for iden in self.opts.iden:
            try:
                buid = s_common.uhex(iden)
            except Exception:
                await runt.warn(f'Failed to decode iden: [{iden}]')
                continue
            if len(buid) != 32:
                await runt.warn(f'iden must be 32 bytes [{iden}]')
                continue

            node = await runt.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, runt.initPath(node)

class SleepCmd(Cmd):
    '''
    Introduce a delay between returning each result for the storm query.

    NOTE: This is mostly used for testing / debugging.

    Example:

        #foo.bar | sleep 0.5

    '''
    name = 'sleep'

    async def execStormCmd(self, runt, genr):
        async for item in genr:
            yield item
            await asyncio.sleep(self.opts.delay)

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('delay', type=float, default=1, help='Delay in floating point seconds.')
        return pars

class GraphCmd(Cmd):
    '''
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

    '''
    name = 'graph'

    def getArgParser(self):

        pars = Cmd.getArgParser(self)
        pars.add_argument('--degrees', type=int, default=1, help='How many degrees to graph out.')

        pars.add_argument('--pivot', default=[], action='append',
                          help='Specify a storm pivot for all nodes. (must quote)')
        pars.add_argument('--filter', default=[], action='append',
                          help='Specify a storm filter for all nodes. (must quote)')

        pars.add_argument('--no-edges', default=False, action='store_true',
                          help='Do not include light weight edges in the per-node output.')
        pars.add_argument('--form-pivot', default=[], nargs=2, action='append',
                          help='Specify a <form> <pivot> form specific pivot.')
        pars.add_argument('--form-filter', default=[], nargs=2, action='append',
                          help='Specify a <form> <filter> form specific filter.')

        pars.add_argument('--refs', default=False, action='store_true',
                          help='Do automatic in-model pivoting with node.getNodeRefs().')
        pars.add_argument('--yield-filtered', default=False, action='store_true', dest='yieldfiltered',
                          help='Yield nodes which would be filtered. This still performs pivots to collect edge data,'
                               'but does not yield pivoted nodes.')
        pars.add_argument('--no-filter-input', default=True, action='store_false', dest='filterinput',
                          help='Do not drop input nodes if they would match a filter.')

        return pars

    async def execStormCmd(self, runt, genr):

        rules = {
            'degrees': self.opts.degrees,

            'pivots': [],
            'filters': [],

            'forms': {},

            'refs': self.opts.refs,
            'filterinput': self.opts.filterinput,
            'yieldfiltered': self.opts.yieldfiltered,

        }

        if self.opts.no_edges:
            rules['edges'] = False

        for pivo in self.opts.pivot:
            rules['pivots'].append(pivo[1:-1])

        for filt in self.opts.filter:
            rules['filters'].append(filt[1:-1])

        for name, pivo in self.opts.form_pivot:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['pivots'].append(pivo[1:-1])

        for name, filt in self.opts.form_filter:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['filters'].append(filt[1:-1])

        subg = s_ast.SubGraph(rules)

        async for node, path in subg.run(runt, genr):
            yield node, path

class TeeCmd(Cmd):
    '''
    Execute multiple Storm queries on each node in the input stream, joining output streams together.

    Commands are executed in order they are given.

    Examples:

        # Perform a pivot out and pivot in on a inet:ivp4 node
        inet:ipv4=1.2.3.4 | tee { -> * } { <- * }

        # Also emit the inbound node
        inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }

    '''
    name = 'tee'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--join', '-j', default=False, action='store_true',
                          help='Emit inbound nodes after processing storm queries.')

        pars.add_argument('query', nargs='*',
                          help='Specify a query to execute on the input nodes.')

        return pars

    async def execStormCmd(self, runt, genr):

        if not self.opts.query:
            raise s_exc.StormRuntimeError(mesg='Tee command must take at least one query as input.',
                                          name=self.name)

        hasnodes = False
        async for node, path in genr:  # type: s_node.Node, s_node.Path
            hasnodes = True
            for text in self.opts.query:
                text = text[1:-1]
                # This does update path with any vars set in the last npath (node.storm behavior)
                async for nnode, npath in node.storm(text, user=runt.user, path=path):
                    yield nnode, npath

            if self.opts.join:
                yield node, path

        if not hasnodes:
            for text in self.opts.query:
                text = text[1:-1]
                query = await runt.getStormQuery(text)
                subr = await runt.getScopeRuntime(query)
                async for nnode, npath in subr.iterStormQuery(query):
                    yield nnode, npath

class TreeCmd(Cmd):
    '''
    Walk elements of a tree using a recursive pivot.

    Examples:

        # pivot upward yielding each FQDN
        inet:fqdn=www.vertex.link | tree { :domain -> inet:fqdn }
    '''
    name = 'tree'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('query', help='The pivot query')
        return pars

    async def execStormCmd(self, runt, genr):

        text = self.opts.query[1:-1]

        async def recurse(node, path):

            yield node, path

            async for nnode, npath in node.storm(text, user=runt.user, path=path):
                async for item in recurse(nnode, npath):
                    yield item

        async for node, path in genr:
            async for nodepath in recurse(node, path):
                yield nodepath

class ScrapeCmd(Cmd):
    '''
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
    '''

    name = 'scrape'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--refs', '-r', default=False, action='store_true',
                          help='Create refs light edges to any scraped nodes from the input node')
        pars.add_argument('--yield', dest='doyield', default=False, action='store_true',
                          help='Include newly scraped nodes in the output')
        pars.add_argument('values', nargs='*',
                          help='Specific relative properties or variables to scrape')
        return pars

    async def execStormCmd(self, runt, genr):

        if self.runtsafe and len(self.opts.values):

            # a bit of a special case.  we may be runtsafe with 0
            async for nodepath in genr:
                if not self.opts.doyield:
                    yield nodepath

            for item in self.opts.values:
                text = str(await s_stormtypes.toprim(item))

                try:
                    for form, valu in s_scrape.scrape(text):
                        addnode = await runt.snap.addNode(form, valu)
                        if self.opts.doyield:
                            yield addnode, runt.initPath(addnode)

                except s_exc.BadTypeValu as e:
                    await runt.warn(f'BadTypeValue for {form}="{valu}"')

            return

        async for node, path in genr:  # type: s_node.Node, s_node.Path

            refs = await s_stormtypes.toprim(self.opts.refs)

            # TODO some kind of repr or as-string option on toprims
            todo = await s_stormtypes.toprim(self.opts.values)

            # if a list of props haven't been specified, then default to ALL of them
            if not todo:
                todo = list(node.props.values())

            for text in todo:

                text = str(text)

                for form, valu in s_scrape.scrape(text):

                    try:
                        nnode = await node.snap.addNode(form, valu)
                        npath = path.fork(nnode)

                        if refs:
                            await node.addEdge('refs', nnode.iden())

                        if self.opts.doyield:
                            yield nnode, npath

                    except s_exc.BadTypeValu as e:
                        await runt.warn(f'BadTypeValue for {form}="{valu}"')

            if not self.opts.doyield:
                yield node, path

class SpliceListCmd(Cmd):
    '''
    Retrieve a list of splices backwards from the end of the splicelog.

    Examples:

        # Show the last 10 splices.
        splice.list | limit 10

        # Show splices after a specific time.
        splice.list --mintime "2020/01/06 15:38:10.991"

        # Show splices from a specific timeframe.
        splice.list --mintimestamp 1578422719360 --maxtimestamp 1578422719367

    Notes:

        If both a time string and timestamp value are provided for a min or max,
        the timestamp will take precedence over the time string value.
    '''

    name = 'splice.list'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--maxtimestamp', type=int, default=None,
                          help='Only yield splices which occurred on or before this timestamp.')
        pars.add_argument('--mintimestamp', type=int, default=None,
                          help='Only yield splices which occurred on or after this timestamp.')
        pars.add_argument('--maxtime', type=str, default=None,
                          help='Only yield splices which occurred on or before this time.')
        pars.add_argument('--mintime', type=str, default=None,
                          help='Only yield splices which occurred on or after this time.')

        return pars

    async def execStormCmd(self, runt, genr):

        maxtime = None
        if self.opts.maxtimestamp:
            maxtime = self.opts.maxtimestamp
        elif self.opts.maxtime:
            try:
                maxtime = s_time.parse(self.opts.maxtime, chop=True)
            except s_exc.BadTypeValu as e:
                mesg = f'Error during maxtime parsing - {str(e)}'

                raise s_exc.StormRuntimeError(mesg=mesg, valu=self.opts.maxtime) from None

        mintime = None
        if self.opts.mintimestamp:
            mintime = self.opts.mintimestamp
        elif self.opts.mintime:
            try:
                mintime = s_time.parse(self.opts.mintime, chop=True)
            except s_exc.BadTypeValu as e:
                mesg = f'Error during mintime parsing - {str(e)}'

                raise s_exc.StormRuntimeError(mesg=mesg, valu=self.opts.mintime) from None

        i = 0

        async for splice in runt.snap.core.spliceHistory(runt.user):

            splicetime = splice[1].get('time')
            if splicetime is None:
                splicetime = 0

            if maxtime and maxtime < splicetime:
                continue

            if mintime and mintime > splicetime:
                return

            guid = s_common.guid(splice)

            buid = s_common.buid(splice[1]['ndef'])
            iden = s_common.ehex(buid)

            props = {'.created': s_common.now(),
                     'splice': splice,
                     'type': splice[0],
                     'iden': iden,
                     'form': splice[1]['ndef'][0],
                     'time': splicetime,
                     'user': splice[1].get('user'),
                     'prov': splice[1].get('prov'),
                     }

            prop = splice[1].get('prop')
            if prop:
                props['prop'] = prop

            tag = splice[1].get('tag')
            if tag:
                props['tag'] = tag

            if 'valu' in splice[1]:
                props['valu'] = splice[1]['valu']
            elif splice[0] == 'node:del':
                props['valu'] = splice[1]['ndef'][1]

            if 'oldv' in splice[1]:
                props['oldv'] = splice[1]['oldv']

            fullnode = (buid, {
                'ndef': ('syn:splice', guid),
                'tags': {},
                'props': props,
                'tagprops': {},
            })

            node = s_node.Node(runt.snap, fullnode)

            yield (node, runt.initPath(node))

            i += 1
            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

class SpliceUndoCmd(Cmd):
    '''
    Reverse the actions of syn:splice runt nodes.

    Examples:

        # Undo the last 5 splices.
        splice.list | limit 5 | splice.undo

        # Undo splices after a specific time.
        splice.list --mintime "2020/01/06 15:38:10.991" | splice.undo

        # Undo splices from a specific timeframe.
        splice.list --mintimestamp 1578422719360 --maxtimestamp 1578422719367 | splice.undo
    '''

    name = 'splice.undo'

    def __init__(self, runt, runtsafe):
        self.undo = {
            'prop:set': self.undoPropSet,
            'prop:del': self.undoPropDel,
            'node:add': self.undoNodeAdd,
            'node:del': self.undoNodeDel,
            'tag:add': self.undoTagAdd,
            'tag:del': self.undoTagDel,
            'tag:prop:set': self.undoTagPropSet,
            'tag:prop:del': self.undoTagPropDel,
        }
        Cmd.__init__(self, runt, runtsafe)

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        forcehelp = 'Force delete nodes even if it causes broken references (requires admin).'
        pars.add_argument('--force', default=False, action='store_true', help=forcehelp)
        return pars

    async def undoPropSet(self, runt, splice, node):

        name = splice.props.get('prop')
        if name == '.created':
            return

        if node:
            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            oldv = splice.props.get('oldv')
            if oldv is not None:
                runt.layerConfirm(('node', 'prop', 'set', prop.full))
                await node.set(name, oldv)
            else:
                runt.layerConfirm(('node', 'prop', 'del', prop.full))
                await node.pop(name)

    async def undoPropDel(self, runt, splice, node):

        name = splice.props.get('prop')
        if name == '.created':
            return

        if node:
            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            valu = splice.props.get('valu')

            runt.layerConfirm(('node', 'prop', 'set', prop.full))
            await node.set(name, valu)

    async def undoNodeAdd(self, runt, splice, node):

        if node:
            for tag in node.tags.keys():
                runt.layerConfirm(('node', 'tag', 'del', *tag.split('.')))

            runt.layerConfirm(('node', 'del', node.form.name))
            await node.delete(force=self.opts.force)

    async def undoNodeDel(self, runt, splice, node):

        if node is None:
            form = splice.props.get('form')
            valu = splice.props.get('valu')

            if form and (valu is not None):
                runt.layerConfirm(('node', 'add', form))
                await runt.snap.addNode(form, valu)

    async def undoTagAdd(self, runt, splice, node):

        if node:
            tag = splice.props.get('tag')
            parts = tag.split('.')
            runt.layerConfirm(('node', 'tag', 'del', *parts))

            await node.delTag(tag)

            oldv = splice.props.get('oldv')
            if oldv is not None:
                runt.layerConfirm(('node', 'tag', 'add', *parts))
                await node.addTag(tag, valu=oldv)

    async def undoTagDel(self, runt, splice, node):

        if node:
            tag = splice.props.get('tag')
            parts = tag.split('.')
            runt.layerConfirm(('node', 'tag', 'add', *parts))

            valu = splice.props.get('valu')
            if valu is not None:
                await node.addTag(tag, valu=valu)

    async def undoTagPropSet(self, runt, splice, node):

        if node:
            tag = splice.props.get('tag')
            parts = tag.split('.')

            prop = splice.props.get('prop')

            oldv = splice.props.get('oldv')
            if oldv is not None:
                runt.layerConfirm(('node', 'tag', 'add', *parts))
                await node.setTagProp(tag, prop, oldv)
            else:
                runt.layerConfirm(('node', 'tag', 'del', *parts))
                await node.delTagProp(tag, prop)

    async def undoTagPropDel(self, runt, splice, node):

        if node:
            tag = splice.props.get('tag')
            parts = tag.split('.')
            runt.layerConfirm(('node', 'tag', 'add', *parts))

            prop = splice.props.get('prop')

            valu = splice.props.get('valu')
            if valu is not None:
                await node.setTagProp(tag, prop, valu)

    async def execStormCmd(self, runt, genr):

        if self.opts.force:
            if not runt.user.isAdmin():
                mesg = '--force requires admin privs.'
                raise s_exc.AuthDeny(mesg=mesg)

        i = 0

        async for node, path in genr:

            if not node.form.name == 'syn:splice':
                mesg = 'splice.undo only accepts syn:splice nodes'
                raise s_exc.StormRuntimeError(mesg=mesg, form=node.form.name)

            if False:  # make this method an async generator function
                yield None

            splicetype = node.props.get('type')

            if splicetype in self.undo:

                iden = node.props.get('iden')
                if iden is None:
                    continue

                buid = s_common.uhex(iden)
                if len(buid) != 32:
                    raise s_exc.NoSuchIden(mesg='Iden must be 32 bytes', iden=iden)

                splicednode = await runt.snap.getNodeByBuid(buid)

                await self.undo[splicetype](runt, node, splicednode)
            else:
                raise s_exc.StormRuntimeError(mesg='Unknown splice type.', splicetype=splicetype)

            i += 1
            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)
