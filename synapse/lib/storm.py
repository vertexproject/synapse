import types
import pprint
import asyncio
import logging
import argparse
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.ast as s_ast
import synapse.lib.auth as s_auth
import synapse.lib.base as s_base
import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.snap as s_snap
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.scope as s_scope
import synapse.lib.autodoc as s_autodoc
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.spooled as s_spooled
import synapse.lib.hashitem as s_hashitem
import synapse.lib.stormctrl as s_stormctrl
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
        * edge:add
        * edge:del

When condition is tag:add or tag:del, you may optionally provide a form name
to restrict the trigger to fire only on tags added or deleted from nodes of
those forms.

The added tag is provided to the query in the ``$auto`` dictionary variable under
``$auto.opts.tag``. Usage of the ``$tag`` variable is deprecated and it will no longer
be populated in Synapse v3.0.0.

Simple one level tag globbing is supported, only at the end after a period,
that is aka.* matches aka.foo and aka.bar but not aka.foo.bar. aka* is not
supported.

When the condition is edge:add or edge:del, you may optionally provide a
form name or a destination form name to only fire on edges added or deleted
from nodes of those forms.

Examples:
    # Adds a tag to every inet:ipv4 added
    trigger.add node:add --form inet:ipv4 --query {[ +#mytag ]}

    # Adds a tag #todo to every node as it is tagged #aka
    trigger.add tag:add --tag aka --query {[ +#todo ]}

    # Adds a tag #todo to every inet:ipv4 as it is tagged #aka
    trigger.add tag:add --form inet:ipv4 --tag aka --query {[ +#todo ]}

    # Adds a tag #todo to the N1 node of every refs edge add
    trigger.add edge:add --verb refs --query {[ +#todo ]}

    # Adds a tag #todo to the N1 node of every seen edge delete, provided that
    # both nodes are of form file:bytes
    trigger.add edge:del --verb seen --form file:bytes --n2form file:bytes --query {[ +#todo ]}
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

wgetdescr = '''Retrieve bytes from a URL and store them in the axon. Yields inet:urlfile nodes.

Examples:

    # Specify custom headers and parameters
    inet:url=https://vertex.link/foo.bar.txt | wget --headers ({"User-Agent": "Foo/Bar"}) --params ({"clientid": "42"})

    # Download multiple URL targets without inbound nodes
    wget https://vertex.link https://vtx.lk
'''

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
                if $info.name { $name = $info.name.ljust(20) }
                else { $name = '                    ' }

                $lib.print("    {iden}:  ({name}): {status}", iden=$info.iden, name=$name, status=$info.status)
            }
        ''',
    },
    {
        'name': 'feed.list',
        'descr': 'List the feed functions available in the Cortex',
        'cmdargs': (),
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
            ('--mirror', {'help': 'A telepath URL of an upstream layer/view to mirror.', 'type': 'str'}),
            ('--growsize', {'help': 'Amount to grow the map size when necessary.', 'type': 'int'}),
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
        'name': 'layer.pull.add',
        'descr': 'Add a pull configuration to a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to pull to.'}),
            ('src', {'help': 'Telepath url of the source layer to pull from.'}),
            ('--offset', {'help': 'Layer offset to begin pulling from',
                          'type': 'int',
                          'default': 0}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $pdef = $layr.addPull($cmdopts.src, $cmdopts.offset)
            if $pdef {
                $lib.print("Layer pull added: {iden}", iden=$pdef.iden)
            }
        ''',
    },
    {
        'name': 'layer.pull.del',
        'descr': 'Delete a pull configuration from a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to modify.'}),
            ('iden', {'help': 'Iden of the pull configuration to delete.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $retn = $layr.delPull($cmdopts.iden)
            $lib.print("Layer pull deleted.")
        ''',
    },
    {
        'name': 'layer.pull.list',
        'descr': 'Get a list of the pull configurations for a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to retrieve pull configurations for.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $lib.print($layr.repr())

            $pulls = $layr.get(pulls)
            if $pulls {
                $lib.print('Pull Iden                        | User                 | Time                |     Offset | URL')
                $lib.print('------------------------------------------------------------------------------------------------------------------------------------------')
                for ($iden, $pdef) in $pulls {
                    $user = $lib.auth.users.get($pdef.user)
                    if $user { $user = $user.name.ljust(20) }
                    else { $user = $pdef.user }

                    $tstr = $lib.time.format($pdef.time, '%Y-%m-%d %H:%M:%S')
                    $ostr = $lib.cast(str, $pdef.offs).rjust(10)
                    $lib.print("{iden} | {user} | {time} | {offs} | {url}", iden=$iden, time=$tstr, user=$user, offs=$ostr, url=$pdef.url)
                }
            } else {
                $lib.print('No pulls configured.')
            }
        ''',
    },
    {
        'name': 'layer.push.add',
        'descr': 'Add a push configuration to a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to push from.'}),
            ('dest', {'help': 'Telepath url of the layer to push to.'}),
            ('--offset', {'help': 'Layer offset to begin pushing from.',
                          'type': 'int',
                          'default': 0}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $pdef = $layr.addPush($cmdopts.dest, $cmdopts.offset)
            if $pdef {
                $lib.print("Layer push added: {iden}", iden=$pdef.iden)
            }
        ''',
    },
    {
        'name': 'layer.push.del',
        'descr': 'Delete a push configuration from a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to modify.'}),
            ('iden', {'help': 'Iden of the push configuration to delete.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $retn = $layr.delPush($cmdopts.iden)
            $lib.print("Layer push deleted.")
        ''',
    },
    {
        'name': 'layer.push.list',
        'descr': 'Get a list of the push configurations for a layer.',
        'cmdargs': (
            ('layr', {'help': 'Iden of the layer to retrieve push configurations for.'}),
        ),
        'storm': '''
            $layr = $lib.layer.get($cmdopts.layr)
            $lib.print($layr.repr())

            $pushs = $layr.get(pushs)
            if $pushs {
                $lib.print('Push Iden                        | User                 | Time                |     Offset | URL')
                $lib.print('------------------------------------------------------------------------------------------------------------------------------------------')
                for ($iden, $pdef) in $pushs {
                    $user = $lib.auth.users.get($pdef.user)
                    if $user { $user = $user.name.ljust(20) }
                    else { $user = $pdef.user }

                    $tstr = $lib.time.format($pdef.time, '%Y-%m-%d %H:%M:%S')
                    $ostr = $lib.cast(str, $pdef.offs).rjust(10)
                    $lib.print("{iden} | {user} | {time} | {offs} | {url}", iden=$iden, time=$tstr, user=$user, offs=$ostr, url=$pdef.url)
                }
            } else {
                $lib.print('No pushes configured.')
            }
        ''',
    },
    {
        'name': 'pkg.list',
        'descr': 'List the storm packages loaded in the cortex.',
        'cmdargs': (
            ('--verbose', {'default': False, 'action': 'store_true',
                'help': 'Display build time for each package.'}),
        ),
        'storm': '''
            init {
                $conf = ({
                    "columns": [
                        {"name": "name", "width": 40},
                        {"name": "vers", "width": 10},
                    ],
                    "separators": {
                        "row:outline": false,
                        "column:outline": false,
                        "header:row": "#",
                        "data:row": "",
                        "column": "",
                    },
                })
                if $cmdopts.verbose {
                    $conf.columns.append(({"name": "time", "width": 20}))
                }
                $printer = $lib.tabular.printer($conf)
            }

            $pkgs = $lib.pkg.list()

            if $($pkgs.size() > 0) {
                $lib.print('Loaded storm packages:')
                $lib.print($printer.header())
                for $pkg in $pkgs {
                    $row = (
                        $pkg.name, $pkg.version,
                    )
                    if $cmdopts.verbose {
                        try {
                            $row.append($lib.time.format($pkg.build.time, '%Y-%m-%d %H:%M:%S'))
                        } catch StormRuntimeError as _ {
                            $row.append('not available')
                        }
                    }
                    $lib.print($printer.row($row))
                }
            } else {
                $lib.print('No storm packages installed.')
            }
        '''
    },
    {
        'name': 'pkg.perms.list',
        'descr': 'List any permissions declared by the package.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package.', 'type': 'str'}),
        ),
        'storm': '''
            $pdef = $lib.null
            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pdef = $pkg
                    break
                }
            }

            if (not $pdef) {
                $lib.warn(`Package ({$cmdopts.name}) not found!`)
            } else {
                if $pdef.perms {
                    $lib.print(`Package ({$cmdopts.name}) defines the following permissions:`)
                    for $permdef in $pdef.perms {
                        $defv = $permdef.default
                        if ( $defv = $lib.null ) {
                            $defv = $lib.false
                        }
                        $text = `{$lib.str.join('.', $permdef.perm).ljust(32)} : {$permdef.desc} ( default: {$defv} )`
                        $lib.print($text)
                    }
                } else {
                    $lib.print(`Package ({$cmdopts.name}) contains no permissions definitions.`)
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
        'name': 'pkg.docs',
        'descr': 'Display documentation included in a storm package.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package.'}),
        ),
        'storm': '''
            $pdef = $lib.null
            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pdef = $pkg
                    break
                }
            }

            if (not $pdef) {
                $lib.warn("Package ({name}) not found!", name=$cmdopts.name)
            } else {
                if $pdef.docs {
                    for $doc in $pdef.docs {
                        $lib.print($doc.content)
                    }
                } else {
                    $lib.print("Package ({name}) contains no documentation.", name=$cmdopts.name)
                }
            }
        '''
    },
    {
        'name': 'pkg.load',
        'descr': 'Load a storm package from an HTTP URL.',
        'cmdargs': (
            ('url', {'help': 'The HTTP URL to load the package from.'}),
            ('--raw', {'default': False, 'action': 'store_true',
                'help': 'Response JSON is a raw package definition without an envelope.'}),
            ('--verify', {'default': False, 'action': 'store_true',
                'help': 'Enforce code signature verification on the storm package.'}),
            ('--ssl-noverify', {'default': False, 'action': 'store_true',
                'help': 'Specify to disable SSL verification of the server.'}),
        ),
        'storm': '''
            init {
                $ssl = $lib.true
                if $cmdopts.ssl_noverify { $ssl = $lib.false }

                $headers = ({'X-Synapse-Version': $lib.str.join('.', $lib.version.synapse())})

                $resp = $lib.inet.http.get($cmdopts.url, ssl_verify=$ssl, headers=$headers)

                if ($resp.code != 200) {
                    $lib.warn("pkg.load got HTTP code: {code} for URL: {url}", code=$resp.code, url=$cmdopts.url)
                    $lib.exit()
                }

                $reply = $resp.json()
                if $cmdopts.raw {
                    $pkg = $reply
                } else {
                    if ($reply.status != "ok") {
                        $lib.warn("pkg.load got JSON error: {code} for URL: {url}", code=$reply.code, url=$cmdopts.url)
                        $lib.exit()
                    }

                    $pkg = $reply.result
                }

                $pkd = $lib.pkg.add($pkg, verify=$cmdopts.verify)

                $lib.print("Loaded Package: {name} @{version}", name=$pkg.name, version=$pkg.version)
            }
        ''',
    },
    {
        'name': 'version',
        'descr': 'Show version metadata relating to Synapse.',
        'storm': '''
            $comm = $lib.version.commit()
            $synv = $lib.version.synapse()

            if $synv {
                $synv = $lib.str.join('.', $synv)
            }

            if $comm {
                $comm = $comm.slice(0,7)
            }

            $lib.print('Synapse Version: {s}', s=$synv)
            $lib.print('Commit Hash: {c}', c=$comm)
        ''',
    },
    {
        'name': 'view.add',
        'descr': 'Add a view to the cortex.',
        'cmdargs': (
            ('--name', {'default': None, 'help': 'The name of the new view.'}),
            ('--worldreadable', {'type': 'bool', 'default': False, 'help': 'Grant read access to the `all` role.'}),
            ('--layers', {'default': [], 'nargs': '*', 'help': 'Layers for the view.'}),
        ),
        'storm': '''
            $view = $lib.view.add($cmdopts.layers, name=$cmdopts.name, worldreadable=$cmdopts.worldreadable)
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
            } else {
                $view.swapLayer()
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
            ('--verb', {'help': 'Edge verb to fire on.'}),
            ('--n2form', {'help': 'The form of the n2 node to fire on.'}),
            ('--query', {'help': 'Query for the trigger to execute.', 'required': True,
                         'dest': 'storm', }),
            ('--async', {'default': False, 'action': 'store_true',
                         'help': 'Make the trigger run in the background.'}),
            ('--disabled', {'default': False, 'action': 'store_true',
                            'help': 'Create the trigger in disabled state.'}),
            ('--name', {'help': 'Human friendly name of the trigger.'}),
            ('--view', {'help': 'The view to add the trigger to.'})
        ),
        'storm': '''
            $opts = $lib.copy($cmdopts)
            // Set valid tdef keys
            $opts.enabled = (not $opts.disabled)
            $opts.help = $lib.undef
            $opts.disabled = $lib.undef
            $trig = $lib.trigger.add($opts)
            $lib.print("Added trigger: {iden}", iden=$trig.iden)
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
        'cmdargs': (
            ('--all', {'help': 'List every trigger in every readable view, rather than just the current view.', 'action': 'store_true'}),
        ),
        'storm': '''
            $triggers = $lib.trigger.list($cmdopts.all)

            if $triggers {

                $lib.print("user       iden                             view                             en?    async? cond      object                    storm query")

                for $trigger in $triggers {
                    $user = $trigger.username.ljust(10)
                    $iden = $trigger.iden.ljust(12)
                    $view = $trigger.view.ljust(12)
                    ($ok, $async) = $lib.trycast(bool, $trigger.async)
                    if $ok {
                        $async = $lib.model.type(bool).repr($async).ljust(6)
                    } else {
                        $async = $lib.model.type(bool).repr($lib.false).ljust(6)
                    }
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

                    $lib.print(`{$user} {$iden} {$view} {$enabled} {$async} {$cond} {$obj} {$obj2} {$trigger.storm}`)
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
            ('--pool', {'action': 'store_true', 'default': False,
                'help': 'Allow the cron job to be run by a mirror from the query pool.'}),
            ('--minute', {'help': 'Minute value for job or recurrence period.'}),
            ('--name', {'help': 'An optional name for the cron job.'}),
            ('--doc', {'help': 'An optional doc string for the cron job.'}),
            ('--hour', {'help': 'Hour value for job or recurrence period.'}),
            ('--day', {'help': 'Day value for job or recurrence period.'}),
            ('--month', {'help': 'Month value for job or recurrence period.'}),
            ('--year', {'help': 'Year value for recurrence period.'}),
            ('--hourly', {'help': 'Fixed parameters for an hourly job.'}),
            ('--daily', {'help': 'Fixed parameters for a daily job.'}),
            ('--monthly', {'help': 'Fixed parameters for a monthly job.'}),
            ('--yearly', {'help': 'Fixed parameters for a yearly job.'}),
            ('--iden', {'help': 'Fixed iden to assign to the cron job'}),
            ('--view', {'help': 'View to run the cron job against'}),
        ),
        'storm': '''
            $cron = $lib.cron.add(query=$cmdopts.query,
                                  minute=$cmdopts.minute,
                                  hour=$cmdopts.hour,
                                  day=$cmdopts.day,
                                  pool=$cmdopts.pool,
                                  month=$cmdopts.month,
                                  year=$cmdopts.year,
                                  hourly=$cmdopts.hourly,
                                  daily=$cmdopts.daily,
                                  monthly=$cmdopts.monthly,
                                  yearly=$cmdopts.yearly,
                                  iden=$cmdopts.iden,
                                  view=$cmdopts.view,)

            if $cmdopts.doc { $cron.set(doc, $cmdopts.doc) }
            if $cmdopts.name { $cron.set(name, $cmdopts.name) }

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
            ('--now', {'help': 'Execute immediately.', 'default': False, 'action': 'store_true'}),
            ('--iden', {'help': 'A set iden to assign to the new cron job'}),
            ('--view', {'help': 'View to run the cron job against'}),
        ),
        'storm': '''
            $cron = $lib.cron.at(query=$cmdopts.query,
                                 minute=$cmdopts.minute,
                                 hour=$cmdopts.hour,
                                 day=$cmdopts.day,
                                 dt=$cmdopts.dt,
                                 now=$cmdopts.now,
                                 iden=$cmdopts.iden,
                                 view=$cmdopts.view)

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
        'name': 'cron.move',
        'descr': "Move a cron job from one view to another",
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid cron job iden is accepted.'}),
            ('view', {'help': 'View to move the cron job to.'}),
        ),
        'storm': '''
            $iden = $lib.cron.move($cmdopts.iden, $cmdopts.view)
            $lib.print("Moved cron job {iden} to view {view}", iden=$iden, view=$cmdopts.view)
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
        'name': 'cron.cleanup',
        'descr': "Delete all completed at jobs",
        'cmdargs': (),
        'storm': '''
            $crons = $lib.cron.list()
            $count = 0

            if $crons {
                for $cron in $crons {
                    $job = $cron.pack()
                    if (not $job.recs) {
                        $lib.cron.del($job.iden)
                        $count = ($count + 1)
                    }
                }
            }
            $lib.print("{count} cron/at jobs deleted.", count=$count)
        ''',
    },

    {
        'name': 'cron.list',
        'descr': "List existing cron jobs in the cortex.",
        'cmdargs': (),
        'storm': '''
            init {
                $conf = ({
                    "columns": [
                        {"name": "user", "width": 24},
                        {"name": "iden", "width": 10},
                        {"name": "view", "width": 10},
                        {"name": "en?", "width": 3},
                        {"name": "rpt?", "width": 4},
                        {"name": "now?", "width": 4},
                        {"name": "err?", "width": 4},
                        {"name": "# start", "width": 7},
                        {"name": "last start", "width": 16},
                        {"name": "last end", "width": 16},
                        {"name": "query", "newlines": "split"},
                    ],
                    "separators": {
                        "row:outline": false,
                        "column:outline": false,
                        "header:row": "#",
                        "data:row": "",
                        "column": "",
                        },
                })
                $printer = $lib.tabular.printer($conf)
            }
            $crons = $lib.cron.list()
            if $crons {
                $lib.print($printer.header())
                for $cron in $crons {
                    $job = $cron.pprint()
                    $row = (
                        $job.user, $job.idenshort, $job.viewshort, $job.enabled,
                        $job.isrecur, $job.isrunning, $job.iserr, `{$job.startcount}`,
                        $job.laststart, $job.lastend, $job.query
                    )
                    $lib.print($printer.row($row))
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
                $lib.print(`pool:            {$job.pool}`)
                $lib.print('recurring:       {isrecur}', isrecur=$job.isrecur)
                $lib.print('# starts:        {startcount}', startcount=$job.startcount)
                $lib.print('# errors:        {errcount}', errcount=$job.errcount)
                $lib.print('last start time: {laststart}', laststart=$job.laststart)
                $lib.print('last end time:   {lastend}', lastend=$job.lastend)
                $lib.print('last result:     {lastresult}', lastresult=$job.lastresult)
                $lib.print('query:           {query}', query=$job.query)

                if $lib.len($job.lasterrs) {
                    $lib.print('most recent errors:')
                    for $err in $job.lasterrs {
                        $lib.print('                 {err}', err=$err)
                    }
                }

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
    },
    {
        'name': 'wget',
        'descr': wgetdescr,
        'cmdargs': (
            ('urls', {'nargs': '*', 'help': 'URLs to download.'}),
            ('--no-ssl-verify', {'default': False, 'action': 'store_true', 'help': 'Ignore SSL certificate validation errors.'}),
            ('--timeout', {'default': 300, 'type': 'int', 'help': 'Configure the timeout for the download operation.'}),
            ('--params', {'default': None, 'help': 'Provide a dict containing url parameters.'}),
            ('--headers', {
                'default': {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'help': 'Provide a Storm dict containing custom request headers.'}),
            ('--no-headers', {'default': False, 'action': 'store_true', 'help': 'Do NOT use any default headers.'}),
        ),
        'storm': '''
        init {
            $count = (0)

            $params = $cmdopts.params
            $headers = $cmdopts.headers
            if $cmdopts.no_headers { $headers = $lib.null }
        }

        $ssl = (not $cmdopts.no_ssl_verify)
        $timeout = $cmdopts.timeout

        if $node {
            $count = ($count + 1)
            if $cmdopts.urls {
                $urls = $cmdopts.urls
            } else {
                if ($node.form() != "inet:url") {
                    $lib.warn("wget can only take inet:url nodes as input without args.")
                    $lib.exit()
                }
                $urls = ($node.value(),)
            }
            for $url in $urls {
                -> { yield $lib.axon.urlfile($url, params=$params, headers=$headers, ssl=$ssl, timeout=$timeout) }
            }
        }

        if ($count = 0) {
            for $url in $cmdopts.urls {
                yield $lib.axon.urlfile($url, params=$params, headers=$headers, ssl=$ssl, timeout=$timeout)
            }
        }
        ''',
    },
    {
        'name': 'nodes.import',
        'descr': 'Import a nodes file hosted at a URL into the cortex. Yields created nodes.',
        'cmdargs': (
            ('urls', {'nargs': '*', 'help': 'URL(s) to fetch nodes file from'}),
            ('--no-ssl-verify', {'default': False, 'action': 'store_true', 'help': 'Ignore SSL certificate validation errors.'}),
        ),
        'storm': '''
        init {
            $count = (0)
            function fetchnodes(url, ssl) {
                $resp = $lib.inet.http.get($url, ssl_verify=$ssl)
                if ($resp.code = 200) {
                    $nodes = ()
                    for $valu in $resp.msgpack() {
                        $nodes.append($valu)
                    }
                    yield $lib.feed.genr("syn.nodes", $nodes)
                } else {
                    $lib.exit("nodes.import got HTTP error code: {code} for {url}", code=$resp.code, url=$url)
                }
            }
        }

        $ssl = (not $cmdopts.no_ssl_verify)

        if $node {
            $count = ($count + 1)
            if ($node.form() != "inet:url") {
                $lib.exit("nodes.import can only take inet:url nodes as input without args")
            }
            $inurls = ($node.value(),)
            for $url in $inurls {
                -> { yield $fetchnodes($url, $ssl) }
            }
        }

        if ($count = 0) {
            for $url in $cmdopts.urls {
                for $valu in $fetchnodes($url, $ssl) {
                    yield $valu
                }
            }
        }

        ''',
    },
    {
        'name': 'note.add',
        'descr': 'Add a new meta:note node and link it to the inbound nodes using an -(about)> edge.',
        'cmdargs': (
            ('text', {'type': 'str', 'help': 'The note text to add to the nodes.'}),
            ('--type', {'type': 'str', 'help': 'The note type.'}),
            ('--yield', {'default': False, 'action': 'store_true',
                'help': 'Yield the newly created meta:note node.'}),
        ),
        'storm': '''
            init {
                function addNoteNode(text, type) {
                    if $type { $type = $lib.cast(meta:note:type:taxonomy, $type) }
                    [ meta:note=* :text=$text :creator=$lib.user.iden :created=.created :updated=.created ]
                    if $type {[ :type=$type ]}
                    return($node)
                }

                $yield = $cmdopts.yield
                $note = $addNoteNode($cmdopts.text, $cmdopts.type)
            }

            [ <(about)+ { yield $note } ]

            if $yield { spin }
            if $yield { yield $note }
        ''',
    },
    {
        'name': 'uptime',
        'descr': 'Print the uptime for the Cortex or a connected service.',
        'cmdargs': (
            ('name', {'type': 'str', 'nargs': '?',
                      'help': 'The name, or iden, of the service (if not provided defaults to the Cortex).'}),
        ),
        'storm': '''
            $resp = $lib.cell.uptime(name=$cmdopts.name)
            $uptime = $lib.model.type(duration).repr($resp.uptime)
            $starttime = $lib.time.format($resp.starttime, "%Y-%m-%d %H:%M:%S")
            $lib.print("up {uptime} (since {since})", uptime=$uptime, since=$starttime)
        ''',
    },
)

@s_cache.memoize(size=1024)
def queryhash(text):
    return s_common.queryhash(text)

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
        futs = [dmon.stop() for dmon in self.dmons.values()]
        if not futs:
            return
        logger.debug(f'Stopping [{len(futs)}] Dmons')
        await asyncio.gather(*futs)
        logger.debug('Stopped Dmons')

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
        dmon = self.dmons.pop(iden, None)
        if dmon:
            await dmon.fini()

    async def start(self):
        '''
        Start all the dmons.
        '''
        if self.enabled:
            return
        dmons = list(self.dmons.values())
        if not dmons:
            self.enabled = True
            return
        logger.debug('Starting Dmons')
        for dmon in dmons:
            await dmon.run()
        self.enabled = True
        logger.debug('Started Dmons')

    async def stop(self):
        '''
        Stop all the dmons.
        '''
        if not self.enabled:
            return
        await self._stopAllDmons()
        self.enabled = False

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
        self.enabled = ddef.get('enabled')
        self.user = core.auth.user(ddef.get('user'))

        self.count = 0
        self.status = 'initialized'
        self.err_evnt = asyncio.Event()
        self.runlog = collections.deque((), 2000)

        self.onfini(self.stop)

    async def stop(self):
        logger.debug(f'Stopping Dmon {self.iden}', extra={'synapse': {'iden': self.iden}})
        if self.task is not None:
            self.task.cancel()
        self.task = None
        logger.debug(f'Stopped Dmon {self.iden}', extra={'synapse': {'iden': self.iden}})

    async def run(self):
        if self.task:  # pragma: no cover
            raise s_exc.SynErr(mesg=f'Dmon - {self.iden} - has a current task and cannot start a new one.',
                               iden=self.iden)
        self.task = self.schedCoro(self.dmonloop())

    async def bump(self):
        await self.stop()
        await self.run()

    def pack(self):
        retn = dict(self.ddef)
        retn['count'] = self.count
        retn['status'] = self.status
        retn['err'] = self.err_evnt.is_set()
        return retn

    def _runLogAdd(self, mesg):
        self.runlog.append((s_common.now(), mesg))

    def _getRunLog(self):
        return list(self.runlog)

    async def dmonloop(self):

        logger.debug(f'Starting Dmon {self.iden}', extra={'synapse': {'iden': self.iden}})

        s_scope.set('user', self.user)
        s_scope.set('storm:dmon', self.iden)

        text = self.ddef.get('storm')
        opts = self.ddef.get('stormopts', {})

        vars = await s_stormtypes.toprim(opts.get('vars', {}), use_list=True)
        vars.setdefault('auto', {'iden': self.iden, 'type': 'dmon'})
        opts['vars'] = vars

        viewiden = opts.get('view')

        info = {'iden': self.iden, 'name': self.ddef.get('name', 'storm dmon'), 'view': viewiden}
        await self.core.boss.promote('storm:dmon', user=self.user, info=info)

        def dmonPrint(evnt):
            self._runLogAdd(evnt)
            mesg = evnt[1].get('mesg', '')
            logger.info(f'Dmon - {self.iden} - {mesg}', extra={'synapse': {'iden': self.iden}})

        def dmonWarn(evnt):
            self._runLogAdd(evnt)
            mesg = evnt[1].get('mesg', '')
            logger.warning(f'Dmon - {self.iden} - {mesg}', extra={'synapse': {'iden': self.iden}})

        while not self.isfini:

            if self.user.info.get('locked'):
                self.status = 'fatal error: user locked'
                logger.warning(f'Dmon user is locked. Stopping Dmon {self.iden}.',
                               extra={'synapse': {'iden': self.iden}})
                return

            view = self.core.getView(viewiden, user=self.user)
            if view is None:
                self.status = 'fatal error: invalid view'
                logger.warning(f'Dmon View is invalid. Stopping Dmon {self.iden}.',
                               extra={'synapse': {'iden': self.iden}})
                return

            try:

                self.status = 'running'
                async with await self.core.snap(user=self.user, view=view) as snap:
                    snap.cachebuids = False

                    snap.on('warn', dmonWarn)
                    snap.on('print', dmonPrint)
                    self.err_evnt.clear()

                    async for nodepath in snap.storm(text, opts=opts, user=self.user):
                        # all storm tasks yield often to prevent latency
                        self.count += 1
                        await asyncio.sleep(0)

                    logger.warning(f'Dmon query exited: {self.iden}', extra={'synapse': {'iden': self.iden}})

                    self.status = 'sleeping'

            except s_stormctrl.StormExit:
                self.status = 'sleeping'

            except asyncio.CancelledError:
                self.status = 'stopped'
                raise

            except Exception as e:
                self._runLogAdd(('err', s_common.excinfo(e)))
                logger.exception(f'Dmon error ({self.iden})', extra={'synapse': {'iden': self.iden}})
                self.status = f'error: {e}'
                self.err_evnt.set()

            # bottom of the loop... wait it out
            await self.waitfini(timeout=1)

class Runtime(s_base.Base):
    '''
    A Runtime represents the instance of a running query.

    The runtime should maintain a firm API boundary using the snap.
    Parallel query execution requires that the snap be treated as an
    opaque object which is called through, but not dereferenced.

    '''

    _admin_reason = s_auth._allowedReason(True, isadmin=True)
    async def __anit__(self, query, snap, opts=None, user=None, root=None):

        await s_base.Base.__anit__(self)

        if opts is None:
            opts = {}

        self.vars = {}
        self.ctors = {
            'lib': s_stormtypes.LibBase,
        }

        self.opts = opts
        self.snap = snap
        self.user = user
        self.debug = opts.get('debug', False)
        self.asroot = False

        self.root = root
        self.funcscope = False

        self.query = query

        self.spawn_log_conf = await self.snap.core._getSpawnLogConf()

        self.readonly = opts.get('readonly', False)  # EXPERIMENTAL: Make it safe to run untrusted queries
        self.model = snap.core.getDataModel()

        self.task = asyncio.current_task()
        self.emitq = None

        self.inputs = []    # [synapse.lib.node.Node(), ...]

        self.iden = s_common.guid()

        varz = self.opts.get('vars')
        if varz is not None:
            for valu in varz.values():
                if isinstance(valu, s_base.Base):
                    valu.incref()
            self.vars.update(varz)

        self._initRuntVars(query)

        self.proxies = {}

        self.onfini(self._onRuntFini)

    def _initRuntVars(self, query):

        # declare path builtins as non-runtsafe
        self.runtvars = {
            'node': False,
            'path': False,
        }

        # inherit runtsafe vars from our root
        if self.root is not None:
            self.runtvars.update(self.root.runtvars)
            self.runtvars.update({k: True for k in self.root.getScopeVars().keys()})

        # all vars/ctors are de-facto runtsafe
        self.runtvars.update({k: True for k in self.vars.keys()})
        self.runtvars.update({k: True for k in self.ctors.keys()})

        self._loadRuntVars(query)

    def getScopeVars(self):
        '''
        Return a dict of all the vars within this and all parent scopes.
        '''
        varz = {}
        if self.root:
            varz.update(self.root.getScopeVars())

        varz.update(self.vars)
        return varz

    async def emitter(self):

        self.emitq = asyncio.Queue(maxsize=1)
        async def fill():
            try:
                async for item in self.execute():
                    await asyncio.sleep(0)
                await self.emitq.put((False, None))

            except asyncio.CancelledError: # pragma: no cover
                raise

            except s_stormctrl.StormStop:
                await self.emitq.put((False, None))

            except Exception as e:
                await self.emitq.put((False, e))

        self.schedCoro(fill())

        async def genr():

            async with self:
                while not self.isfini:
                    ok, item = await self.emitq.get()
                    if ok:
                        yield item
                        self.emitevt.set()
                        continue

                    if not ok and item is None:
                        return

                    raise item

        self.emitevt = asyncio.Event()
        return genr()

    async def emit(self, item):
        if self.emitq is None:
            mesg = 'Cannot emit from outside of an emitter function'
            raise s_exc.StormRuntimeError(mesg=mesg)

        self.emitevt.clear()
        await self.emitq.put((True, item))
        await self.emitevt.wait()

    async def _onRuntFini(self):
        # fini() any Base objects constructed by this runtime
        for valu in list(self.vars.values()):
            if isinstance(valu, s_base.Base):
                await valu.fini()

    async def reqGateKeys(self, gatekeys):
        if self.asroot:
            return
        await self.snap.core.reqGateKeys(gatekeys)

    async def reqUserCanReadLayer(self, layriden):

        if self.asroot:
            return

        for view in self.snap.core.viewsbylayer.get(layriden, ()):
            if self.user.allowed(('view', 'read'), gateiden=view.iden):
                return

        # check the old way too...
        if self.user.allowed(('layer', 'read'), gateiden=layriden):
            return

        mesg = f'User ({self.user.name}) can not read layer.'
        raise s_exc.AuthDeny(mesg=mesg, user=self.user.iden, username=self.user.name)

    async def dyncall(self, iden, todo, gatekeys=()):
        # bypass all perms checks if we are running asroot
        if self.asroot:
            gatekeys = ()
        return await self.snap.core.dyncall(iden, todo, gatekeys=gatekeys)

    async def dyniter(self, iden, todo, gatekeys=()):
        # bypass all perms checks if we are running asroot
        if self.asroot:
            gatekeys = ()
        async for item in self.snap.core.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    async def getStormQuery(self, text):
        return await self.snap.core.getStormQuery(text)

    async def coreDynCall(self, todo, perm=None):
        gatekeys = ()
        if perm is not None:
            gatekeys = ((self.user.iden, perm, None),)
        # bypass all perms checks if we are running asroot
        if self.asroot:
            gatekeys = ()
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
        return bool(self.runtvars.get(name))

    async def printf(self, mesg):
        return await self.snap.printf(mesg)

    async def warn(self, mesg, **info):
        return await self.snap.warn(mesg, **info)

    async def warnonce(self, mesg, **info):
        return await self.snap.warnonce(mesg, **info)

    def cancel(self):
        self.task.cancel()

    def initPath(self, node):
        return s_node.Path(dict(self.vars), [node])

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

        if self.root is not None:
            valu = self.root.getVar(name, defv=s_common.novalu)
            if valu is not s_common.novalu:
                return valu

        return defv

    def _isRootScope(self, name):
        if self.root is None:
            return False
        if not self.funcscope:
            return True
        if name in self.root.vars:
            return True
        return self.root._isRootScope(name)

    async def _setVar(self, name, valu):

        oldv = self.vars.get(name, s_common.novalu)
        if oldv is valu:
            return

        if isinstance(oldv, s_base.Base):
            await oldv.fini()

        if isinstance(valu, s_base.Base):
            valu.incref()

        self.vars[name] = valu

    async def setVar(self, name, valu):

        if name in self.ctors or name in self.vars:
            await self._setVar(name, valu)
            return

        if self._isRootScope(name):
            return await self.root.setVar(name, valu)

        await self._setVar(name, valu)
        return

    async def popVar(self, name):

        if self._isRootScope(name):
            return self.root.popVar(name)

        oldv = self.vars.pop(name, s_common.novalu)
        if isinstance(oldv, s_base.Base):
            await oldv.fini()

        return oldv

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
        if self.asroot:
            return
        iden = self.snap.wlyr.iden
        return self.user.confirm(perms, gateiden=iden)

    def isAdmin(self, gateiden=None):
        if self.asroot:
            return True
        return self.user.isAdmin(gateiden=gateiden)

    def reqAdmin(self, gateiden=None, mesg=None):
        if not self.asroot:
            self.user.reqAdmin(gateiden=gateiden, mesg=mesg)

    def confirm(self, perms, gateiden=None, default=None):
        '''
        Raise AuthDeny if the user doesn't have the permission.

        Notes:
            An elevated runtime with asroot=True will always return True.

        Args:
            perms (tuple): The permission tuple.
            gateiden (str): The gateiden.
            default (bool): The default value.

        Returns:
            True: If the permission is allowed.

        Raises:
            AuthDeny: If the user does not have the permission.
        '''
        if self.asroot:
            return

        if default is None:
            default = False

            permdef = self.snap.core.getPermDef(perms)
            if permdef:
                default = permdef.get('default', False)

        return self.user.confirm(perms, gateiden=gateiden, default=default)

    def allowed(self, perms, gateiden=None, default=None):
        if self.asroot:
            return True

        if default is None:
            default = False

            permdef = self.snap.core.getPermDef(perms)
            if permdef:
                default = permdef.get('default', False)

        return self.user.allowed(perms, gateiden=gateiden, default=default)

    def allowedReason(self, perms, gateiden=None, default=None):
        if self.asroot:
            return self._admin_reason

        return self.snap.core._propAllowedReason(self.user, perms, gateiden=gateiden, default=default)

    def confirmPropSet(self, prop, layriden=None):
        if self.asroot:
            return

        if layriden is None:
            layriden = self.snap.wlyr.iden

        return self.snap.core.confirmPropSet(self.user, prop, layriden=layriden)

    def confirmPropDel(self, prop, layriden=None):
        if self.asroot:
            return

        if layriden is None:
            layriden = self.snap.wlyr.iden

        return self.snap.core.confirmPropDel(self.user, prop, layriden=layriden)

    def confirmEasyPerm(self, item, perm, mesg=None):
        if not self.asroot:
            self.snap.core._reqEasyPerm(item, self.user, perm, mesg=mesg)

    def allowedEasyPerm(self, item, perm):
        if self.asroot:
            return True
        return self.snap.core._hasEasyPerm(item, self.user, perm)

    def _loadRuntVars(self, query):
        # do a quick pass to determine which vars are per-node.
        for oper in query.kids:
            for name, isrunt in oper.getRuntVars(self):
                # once runtsafe, always runtsafe
                if self.runtvars.get(name):
                    continue
                self.runtvars[name] = isrunt

    def setGraph(self, gdef):
        if self.root is not None:
            self.root.setGraph(gdef)
        else:
            self.opts['graph'] = gdef

    def getGraph(self):
        if self.root is not None:
            return self.root.getGraph()
        return self.opts.get('graph')

    async def execute(self, genr=None):
        try:

            async with contextlib.aclosing(self.query.iterNodePaths(self, genr=genr)) as nodegenr:
                nodegenr, empty = await s_ast.pullone(nodegenr)

                if empty:
                    return

                rules = self.opts.get('graph')
                if rules not in (False, None):
                    if rules is True:
                        rules = {'degrees': None, 'refs': True}
                    elif isinstance(rules, str):
                        rules = await self.snap.core.getStormGraph(rules)

                    subgraph = s_ast.SubGraph(rules)
                    nodegenr = subgraph.run(self, nodegenr)

                async for item in nodegenr:
                    yield item

        except RecursionError:
            mesg = 'Maximum Storm pipeline depth exceeded.'
            raise s_exc.RecursionLimitHit(mesg=mesg, query=self.query.text) from None

    async def _snapFromOpts(self, opts):

        snap = self.snap

        if opts is not None:

            viewiden = opts.get('view')
            if viewiden is not None:

                view = snap.core.views.get(viewiden)
                if view is None:
                    raise s_exc.NoSuchView(mesg=f'No such view iden={viewiden}', iden=viewiden)

                self.confirm(('view', 'read'), gateiden=viewiden)
                snap = await view.snap(self.user)

        return snap

    @contextlib.asynccontextmanager
    async def getSubRuntime(self, query, opts=None):
        '''
        Yield a runtime with shared scope that will populate changes upward.
        '''
        async with await self.initSubRuntime(query, opts=opts) as runt:
            yield runt

    async def initSubRuntime(self, query, opts=None):
        '''
        Construct and return sub-runtime with a shared scope.
        ( caller must fini )
        '''
        snap = await self._snapFromOpts(opts)

        runt = await Runtime.anit(query, snap, user=self.user, opts=opts, root=self)
        if self.debug:
            runt.debug = True
        runt.asroot = self.asroot
        runt.readonly = self.readonly

        return runt

    @contextlib.asynccontextmanager
    async def getCmdRuntime(self, query, opts=None):
        '''
        Yield a runtime with proper scoping for use in executing a pure storm command.
        '''
        async with await Runtime.anit(query, self.snap, user=self.user, opts=opts) as runt:
            if self.debug:
                runt.debug = True
            runt.asroot = self.asroot
            runt.readonly = self.readonly
            yield runt

    async def getModRuntime(self, query, opts=None):
        '''
        Construct a non-context managed runtime for use in module imports.
        '''
        runt = await Runtime.anit(query, self.snap, user=self.user, opts=opts)
        if self.debug:
            runt.debug = True
        runt.asroot = self.asroot
        runt.readonly = self.readonly
        return runt

    async def storm(self, text, opts=None, genr=None):
        '''
        Execute a storm runtime which inherits from this storm runtime.
        '''
        if opts is None:
            opts = {}
        query = await self.snap.core.getStormQuery(text)
        async with self.getSubRuntime(query, opts=opts) as runt:
            async for item in runt.execute(genr=genr):
                await asyncio.sleep(0)
                yield item

    async def getOneNode(self, propname, valu, filt=None, cmpr='='):
        '''
        Return exactly 1 node by <prop> <cmpr> <valu>
        '''
        opts = {'vars': {'propname': propname, 'valu': valu}}

        nodes = []
        try:

            async for node in self.snap.nodesByPropValu(propname, cmpr, valu):

                await asyncio.sleep(0)

                if filt is not None and not await filt(node):
                    continue

                if len(nodes) == 1:
                    mesg = 'Ambiguous value for single node lookup: {propname}^={valu}'
                    raise s_exc.StormRuntimeError(mesg=mesg)

                nodes.append(node)

            if len(nodes) == 1:
                return nodes[0]

        except s_exc.BadTypeValu:
            return None

class Parser:

    def __init__(self, prog=None, descr=None, root=None, model=None, cdef=None):

        if root is None:
            root = self

        if model is None:
            model = s_datamodel.Model()
        self.model = model

        self.prog = prog
        self.descr = descr
        self.cdef = cdef

        self.exc = None

        self.root = root
        self.exited = False
        self.mesgs = []

        self.optargs = {}
        self.posargs = []
        self.allargs = []

        self.inputs = None

        self.reqopts = []

        self.add_argument('--help', '-h', action='store_true', default=False, help='Display the command usage.')

    def set_inputs(self, idefs):
        self.inputs = list(idefs)

    def add_argument(self, *names, **opts):

        assert len(names)

        argtype = opts.get('type')
        if argtype is not None and argtype not in s_schemas.datamodel_basetypes:
            mesg = f'Argument type "{argtype}" is not a valid model type name'
            raise s_exc.BadArg(mesg=mesg, argtype=str(argtype))

        choices = opts.get('choices')
        if choices is not None and opts.get('action') in ('store_true', 'store_false'):
            mesg = f'Argument choices are not supported when action is store_true or store_false'
            raise s_exc.BadArg(mesg=mesg, argtype=str(argtype))

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
        if opts.pop('help', None):
            mesg = None
            if opts or posargs:
                mesg = f'Extra arguments and flags are not supported with the help flag: {self.prog} {" ".join(argv)}'
            self.help(mesg)
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
        choices = argdef.get('choices')

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
                    valu = self.model.type(argtype).norm(valu)[0]
                except Exception:
                    mesg = f'Invalid value for type ({argtype}): {valu}'
                    return self.help(mesg=mesg)

            if choices is not None and valu not in choices:
                marg = name if name.startswith('-') else f'<{name}>'
                cstr = ', '.join(str(c) for c in choices)
                mesg = f'Invalid choice for argument {marg} (choose from: {cstr}): {valu}'
                return self.help(mesg=mesg)

            opts[dest] = valu
            return True

        if nargs == '?':

            opts.setdefault(dest, argdef.get('default'))

            if todo and not self._is_opt(todo[0]):

                valu = todo.popleft()
                if argtype is not None:
                    try:
                        valu = self.model.type(argtype).norm(valu)[0]
                    except Exception:
                        mesg = f'Invalid value for type ({argtype}): {valu}'
                        return self.help(mesg=mesg)

                if choices is not None and valu not in choices:
                    marg = name if name.startswith('-') else f'<{name}>'
                    cstr = ', '.join(str(c) for c in choices)
                    mesg = f'Invalid choice for argument {marg} (choose from: {cstr}): {valu}'
                    return self.help(mesg=mesg)

                opts[dest] = valu

            return True

        if nargs in ('*', '+'):

            while todo and not self._is_opt(todo[0]):

                valu = todo.popleft()

                if argtype is not None:
                    try:
                        valu = self.model.type(argtype).norm(valu)[0]
                    except Exception:
                        mesg = f'Invalid value for type ({argtype}): {valu}'
                        return self.help(mesg=mesg)

                if choices is not None and valu not in choices:
                    marg = name if name.startswith('-') else f'<{name}>'
                    cstr = ', '.join(str(c) for c in choices)
                    mesg = f'Invalid choice for argument {marg} (choose from: {cstr}): {valu}'
                    return self.help(mesg=mesg)

                vals.append(valu)

            if nargs == '+' and len(vals) == 0:
                mesg = f'At least one argument is required for {name}.'
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
                    valu = self.model.type(argtype).norm(valu)[0]
                except Exception:
                    mesg = f'Invalid value for type ({argtype}): {valu}'
                    return self.help(mesg=mesg)

            if choices is not None and valu not in choices:
                marg = name if name.startswith('-') else f'<{name}>'
                cstr = ', '.join(str(c) for c in choices)
                mesg = f'Invalid choice for argument {marg} (choose from: {cstr}): {valu}'
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

        if self.cdef is not None and (endpoints := self.cdef.get('endpoints')):
            self._printf('')
            self._printf('Endpoints:')
            self._printf('')
            base_w = 32
            wrap_w = 120 - base_w
            for endpoint in endpoints:
                path = endpoint['path']
                desc = endpoint.get('desc', '')
                base = f'    {path}'
                wrap_desc = self._wrap_text(desc, wrap_w) if desc else ['']
                self._printf(f'{base:<{base_w-2}}: {wrap_desc[0]}')
                for ln in wrap_desc[1:]:
                    self._printf(f'{"":<{base_w}}{ln}')

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

        if self.inputs:
            self._printf('')
            self._printf('Inputs:')
            self._printf('')
            formsize = max([len(idef['form']) for idef in self.inputs])
            for idef in self.inputs:
                form = idef.get('form').ljust(formsize)
                text = f'    {form}'
                desc = idef.get('help')
                if desc:
                    text += f' - {desc}'
                self._printf(text)

        if mesg is not None:
            self.exc = s_exc.BadArg(mesg=mesg)

        self.exited = True
        return False

    def _wrap_text(self, text, width):
        lines, curline, curlen = [], [], 0
        for word in text.split():
            if curlen + len(word) + bool(curline) > width:
                lines.append(' '.join(curline))
                curline, curlen = [word], len(word)
            else:
                curline.append(word)
                curlen += len(word) + bool(curline)
        if curline:
            lines.append(' '.join(curline))
        return lines

    def _print_optarg(self, names, argdef):

        dest = self._get_dest_str(argdef)
        oact = argdef.get('action', 'store')

        if oact in ('store_true', 'store_false'):
            base = f'  {names[0]}'
        else:
            base = f'  {names[0]} {dest}'

        defval = argdef.get('default', s_common.novalu)
        choices = argdef.get('choices')
        helpstr = argdef.get('help', 'No help available.')

        if defval is not s_common.novalu and oact not in ('store_true', 'store_false'):
            if isinstance(defval, (tuple, list, dict)):
                defval_ls = pprint.pformat(defval, width=120).split('\n')
                defval = '\n'.join(ln.strip() for ln in defval_ls)

            if choices is None:
                if (lambda tst: '\n' in tst if isinstance(tst, str) else False)(defval):
                    helpstr = f'{helpstr} (default: \n{defval})'
                else:
                    helpstr = f'{helpstr} (default: {defval})'
            else:
                cstr = ', '.join(str(c) for c in choices)
                helpstr = f'{helpstr} (default: {defval}, choices: {cstr})'

        elif choices is not None:
            cstr = ', '.join(str(c) for c in choices)
            helpstr = f'{helpstr} (choices: {cstr})'

        helplst = helpstr.split('\n')
        if helplst and not helplst[0].strip():
            helplst = helplst[1:]
        min_space = min((len(ln) - len(ln.lstrip()) for ln in helplst if ln.strip()), default=0)

        base_w = 32
        wrap_w = 120 - base_w

        first = helplst[0][min_space:]
        wrap_first = self._wrap_text(first, wrap_w)
        self._printf(f'{base:<{base_w-2}}: {wrap_first[0]}')

        for ln in wrap_first[1:]: self._printf(f'{"":<{base_w}}{ln}')
        for ln in helplst[1:]:
            lead_s = len(ln) - len(ln.lstrip())
            rel_ind = lead_s - min_space
            ind = ' ' * (base_w + rel_ind)
            wrapped = self._wrap_text(ln.lstrip(), wrap_w - rel_ind)
            for wl in wrapped:
                self._printf(f'{ind}{wl}')

    def _print_posarg(self, name, argdef):
        dest = self._get_dest_str(argdef)
        helpstr = argdef.get('help', 'No help available')

        choices = argdef.get('choices')
        if choices is not None:
            cstr = ', '.join(str(c) for c in choices)
            helpstr = f'{helpstr} (choices: {cstr})'

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
        about Synapse forms which are possible input and output nodes that a Cmd may recognize. A list of
        (key, form) tuples may also be added to provide information about forms which may have additional
        nodedata added to them by the Cmd.

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
                    'nodedata': (
                        ('foodata', 'inet:http:request'),
                        ('bardata', 'inet:ipv4'),
                    ),
                }

    '''
    name = 'cmd'
    pkgname = ''
    svciden = ''
    asroot = False
    readonly = False
    forms = {}  # type: ignore

    def __init__(self, runt, runtsafe):

        self.opts = None
        self.argv = None

        self.runt = runt
        self.runtsafe = runtsafe

        self.pars = self.getArgParser()
        self.pars.printf = runt.snap.printf

    def isReadOnly(self):
        return self.readonly

    @classmethod
    def getCmdBrief(cls):
        return cls.__doc__.strip().split('\n')[0]

    def getName(self):
        return self.name

    def getDescr(self):
        return self.__class__.__doc__

    def getArgParser(self):
        return Parser(prog=self.getName(), descr=self.getDescr(), model=self.runt.model)

    async def setArgv(self, argv):

        self.argv = argv

        try:
            self.opts = self.pars.parse_args(self.argv)
        except s_exc.BadSyntax:  # pragma: no cover
            pass

        for line in self.pars.mesgs:
            await self.runt.snap.printf(line)

        if self.pars.exc is not None:
            raise self.pars.exc

        return not self.pars.exited

    async def execStormCmd(self, runt, genr):  # pragma: no cover
        ''' Abstract base method '''
        raise s_exc.NoSuchImpl(mesg='Subclass must implement execStormCmd')
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
        nodedata = cls.forms.get('nodedata')

        if inpt:
            props['input'] = tuple(inpt)

        if outp:
            props['output'] = tuple(outp)

        if nodedata:
            props['nodedata'] = tuple(nodedata)

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

    # pure commands are all "readonly" safe because their perms are enforced
    # by the underlying runtime executing storm operations that are readonly
    # or not
    readonly = True

    def __init__(self, cdef, runt, runtsafe):
        self.cdef = cdef
        Cmd.__init__(self, runt, runtsafe)
        self.asroot = cdef.get('asroot', False)

    def getDescr(self):
        return self.cdef.get('descr', 'no documentation provided')

    def getName(self):
        return self.cdef.get('name')

    def getArgParser(self):

        pars = Cmd.getArgParser(self)
        for name, opts in self.cdef.get('cmdargs', ()):
            pars.add_argument(name, **opts)

        inputs = self.cdef.get('cmdinputs')
        if inputs:
            pars.set_inputs(inputs)

        pars.cdef = self.cdef
        return pars

    async def execStormCmd(self, runt, genr):

        name = self.getName()
        perm = ('storm', 'asroot', 'cmd') + tuple(name.split('.'))

        asroot = runt.allowed(perm)
        if self.asroot and not asroot:
            mesg = f'Command ({name}) elevates privileges.  You need perm: storm.asroot.cmd.{name}'
            raise s_exc.AuthDeny(mesg=mesg, user=runt.user.iden, username=runt.user.name)

        # if a command requires perms, check em!
        # ( used to create more intuitive perm boundaries )
        perms = self.cdef.get('perms')
        if perms is not None:
            allowed = False
            for perm in perms:
                if runt.allowed(perm):
                    allowed = True
                    break

            if not allowed:
                permtext = ' or '.join(('.'.join(p) for p in perms))
                mesg = f'Command ({name}) requires permission: {permtext}'
                raise s_exc.AuthDeny(mesg=mesg, user=runt.user.iden, username=runt.user.name)

        text = self.cdef.get('storm')
        query = await runt.snap.core.getStormQuery(text)

        cmdopts = s_stormtypes.CmdOpts(self)

        opts = {
            'vars': {
                'cmdopts': cmdopts,
                'cmdconf': self.cdef.get('cmdconf', {}),
            }
        }

        if self.runtsafe:
            data = {'pathvars': {}}
            async def genx():
                async for xnode, xpath in genr:
                    data['pathvars'] = xpath.vars.copy()
                    xpath.initframe(initvars={'cmdopts': cmdopts})
                    yield xnode, xpath

            async with runt.getCmdRuntime(query, opts=opts) as subr:
                subr.asroot = asroot
                async for node, path in subr.execute(genr=genx()):
                    path.finiframe()
                    path.vars.update(data['pathvars'])
                    yield node, path
        else:
            async with runt.getCmdRuntime(query, opts=opts) as subr:
                subr.asroot = asroot

                async for node, path in genr:
                    pathvars = path.vars.copy()
                    async def genx():
                        path.initframe(initvars={'cmdopts': cmdopts})
                        yield node, path

                    async for xnode, xpath in subr.execute(genr=genx()):
                        xpath.finiframe()
                        xpath.vars.update(pathvars)
                        yield xnode, xpath

class DivertCmd(Cmd):
    '''
    Either consume a generator or yield it's results based on a conditional.

    NOTE: This command is purpose built to facilitate the --yield convention
          common to storm commands.

    NOTE: The genr argument must not be a function that returns, else it will
          be invoked for each inbound node.

    Example:
        divert $cmdopts.yield $fooBarBaz()
    '''
    name = 'divert'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('cond', help='The conditional value for the yield option.')
        pars.add_argument('genr', help='The generator function value that yields nodes.')
        pars.add_argument('--size', default=None, help='The max number of times to iterate the generator.')
        return pars

    async def execStormCmd(self, runt, genr):

        async def run(item):
            if not isinstance(self.opts.genr, types.AsyncGeneratorType):
                raise s_exc.BadArg(mesg='The genr argument must yield nodes')

            size = await s_stormtypes.toint(self.opts.size, noneok=True)
            doyield = await s_stormtypes.tobool(self.opts.cond)

            try:
                count = 0
                if doyield:

                    async for genritem in self.opts.genr:
                        yield genritem
                        count += 1
                        if size is not None and count >= size:
                            break
                else:

                    async for genritem in self.opts.genr:
                        await asyncio.sleep(0)
                        count += 1
                        if size is not None and count >= size:
                            break

                    if item is not None:
                        yield item

            finally:
                await self.opts.genr.aclose()

        empty = True
        async for item in genr:
            empty = False
            async for runitem in run(item):
                yield runitem

        if empty:
            async for runitem in run(None):
                yield runitem

class BatchCmd(Cmd):
    '''
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
    '''
    name = 'batch'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('cond', help='The conditional value for the yield option.')
        pars.add_argument('query', help='The query to execute with batched nodes.')
        pars.add_argument('--size', default=10,
                          help='The number of nodes to collect before running the batched query (max 10000).')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'batch arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        size = await s_stormtypes.toint(self.opts.size)
        if size > 10000:
            mesg = f'Specified batch size ({size}) is above the maximum (10000).'
            raise s_exc.StormRuntimeError(mesg=mesg)

        _query = await s_stormtypes.tostr(self.opts.query)
        query = await runt.getStormQuery(_query)
        doyield = await s_stormtypes.tobool(self.opts.cond)

        async with runt.getSubRuntime(query, opts={'vars': {'nodes': []}}) as subr:

            nodeset = []
            pathset = []

            async for node, path in genr:

                nodeset.append(node)
                pathset.append(path)

                if len(nodeset) >= size:
                    await subr.setVar('nodes', nodeset)
                    subp = None
                    async for subp in subr.execute():
                        await asyncio.sleep(0)
                        if doyield:
                            yield subp

                    if not doyield:
                        for item in zip(nodeset, pathset):
                            await asyncio.sleep(0)
                            if subp is not None:
                                item[1].vars.update(subp[1].vars)
                            yield item

                    nodeset.clear()
                    pathset.clear()

            if len(nodeset) > 0:
                await subr.setVar('nodes', nodeset)
                subp = None
                async for subp in subr.execute():
                    await asyncio.sleep(0)
                    if doyield:
                        yield subp

                if not doyield:
                    for item in zip(nodeset, pathset):
                        await asyncio.sleep(0)
                        if subp is not None:
                            item[1].vars.update(subp[1].vars)
                        yield item

class HelpCmd(Cmd):
    '''
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

    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('-v', '--verbose', default=False, action='store_true',
                          help='Display detailed help when available.')
        pars.add_argument('item', nargs='?',
                          help='List information about a subset of commands or a specific item.')
        return pars

    async def execStormCmd(self, runt, genr):

        node = None
        async for node, path in genr:
            await self._runHelp(runt)
            yield node, path

        if node is None and self.runtsafe:
            await self._runHelp(runt)

    async def _runHelp(self, runt: Runtime):

        item = self.opts.item

        if item is not None and \
                not isinstance(item, (str, s_node.Node, s_node.Path, s_stormtypes.StormType)) and \
                not callable(item):
            mesg = f'Item must be a Storm type name, a Storm library, or a Storm command name to search for. Got' \
                   f' {await s_stormtypes.totype(item, basetypes=True)}'
            raise s_exc.BadArg(mesg=mesg)

        if isinstance(item, s_stormtypes.Lib):
            await self._handleLibHelp(item, runt, verbose=self.opts.verbose)
            return

        if isinstance(item, s_stormtypes.StormType):
            if item._storm_typename in s_stormtypes.registry.known_types:
                await self._handleTypeHelp(item._storm_typename, runt, verbose=self.opts.verbose)
                return
            raise s_exc.BadArg(mesg=f'Unknown storm type encountered: {s_stormtypes.totype(item, basetypes=True)}')

        if isinstance(item, s_node.Node):
            await self._handleTypeHelp('node', runt, verbose=self.opts.verbose)
            return

        if isinstance(item, s_node.Path):
            await self._handleTypeHelp('node:path', runt, verbose=self.opts.verbose)
            return

        # Handle $lib.inet.http.get / $str.split / $lib.gen.orgByName
        if callable(item):

            if hasattr(item, '__func__'):
                # https://docs.python.org/3/reference/datamodel.html#instance-methods
                await self._handleBoundMethod(item, runt, verbose=self.opts.verbose)
                return

            if hasattr(item, '_storm_runtime_lib_func'):
                await self._handleStormLibMethod(item, runt, verbose=self.opts.verbose)
                return

            styp = await s_stormtypes.totype(item, basetypes=True)
            if styp in ('telepath:proxy:method', 'telepath:proxy:genrmethod'):
                raise s_exc.BadArg(mesg='help does not support Telepath proxy methods.')

            raise s_exc.BadArg(mesg='help does not currently support runtime defined functions.')

        foundtype = False
        if item in s_stormtypes.registry.known_types:
            foundtype = True
            await self._handleTypeHelp(item, runt, verbose=self.opts.verbose)

        return await self._handleGenericCommandHelp(item, runt, foundtype=foundtype)

    async def _handleGenericCommandHelp(self, item, runt, foundtype=False):

        stormcmds = sorted(runt.snap.core.getStormCmds())

        if item:
            stormcmds = [c for c in stormcmds if item in c[0]]
            if not stormcmds:
                if not foundtype:
                    await runt.printf(f'No commands found matching "{item}"')
                    return

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

            if foundtype:
                await runt.printf('')
                await runt.printf('*' * 80)
                await runt.printf('')

            await runt.printf('The following Storm commands are available:')

            maxlen = max(len(x[0]) for x in stormcmds)

            for name, ctor in stormcmds:
                cmdinfo = f'{name:<{maxlen}}: {ctor.getCmdBrief()}'
                pkgcmds.setdefault(pkgmap.get(name, 'synapse'), []).append(cmdinfo)

            syncmds = pkgcmds.pop('synapse', [])
            if syncmds:

                await runt.printf(f'package: synapse')

                for cmd in syncmds:
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

    async def _handleLibHelp(self, lib: s_stormtypes.Lib, runt: Runtime, verbose: bool =False):

        try:
            preamble = self._getChildLibs(lib)
        except s_exc.NoSuchName as e:
            raise s_exc.BadArg(mesg='Help does not currently support imported Storm modules.') from None

        page = s_autodoc.RstHelp()

        if hasattr(lib, '_storm_lib_path'):
            libsinfo = s_stormtypes.registry.getLibDocs(lib)

            s_autodoc.runtimeDocStormTypes(page, libsinfo,
                                           islib=True,
                                           oneline=not verbose,
                                           preamble=preamble,
                                           )
        else:
            page.addLines(*preamble)

        for line in page.lines:
            await runt.printf(line)

    def _getChildLibs(self, lib: s_stormtypes.Lib):
        corelibs = self.runt.snap.core.getStormLib(lib.name)
        if corelibs is None:
            raise s_exc.NoSuchName(mesg=f'Cannot find lib name [{lib.name}]')

        data = []
        lines = []

        libbase = ('lib',) + lib.name
        q = collections.deque()
        for child, lnfo in corelibs[1].items():
            q.append(((child,), lnfo))
        while q:
            child, lnfo = q.popleft()
            path = libbase + child
            _, subs, cnfo = lnfo
            ctor = cnfo.get('ctor')
            if ctor:
                data.append((path, ctor))
            for sub, lnfo in subs.items():
                _sub = child + (sub,)
                q.append((_sub, lnfo))
        if not data:
            return lines

        data = sorted(data, key=lambda x: x[0])

        lines.append('The following libraries are available:')
        lines.append('')
        for path, ctor in data:
            name = f'${".".join(path)}'
            desc = ctor.__doc__.strip().split('\n')[0]
            lines.append(f'{name.ljust(30)}: {desc}')
        lines.append('')

        return lines

    async def _handleTypeHelp(self, styp: str, runt: Runtime, verbose: bool =False):
        typeinfo = s_stormtypes.registry.getTypeDocs(styp)
        page = s_autodoc.RstHelp()

        s_autodoc.runtimeDocStormTypes(page, typeinfo,
                                       islib=False,
                                       oneline=not verbose,
                                       )
        for line in page.lines:
            await runt.printf(line)

    async def _handleBoundMethod(self, func, runt: Runtime, verbose: bool =False):
        # Bound methods must be bound to a Lib or Prim object.
        # Determine what they are, get those docs exactly, and then render them.

        cls = func.__self__
        fname = func.__name__

        if isinstance(cls, s_stormtypes.Lib):
            libsinfo = s_stormtypes.registry.getLibDocs(cls)
            for lifo in libsinfo:
                nlocs = []
                for locl in lifo['locals']:
                    ltyp = locl.get('type')
                    if not isinstance(ltyp, dict):
                        continue
                    if ltyp.get('_funcname', '') == fname:
                        nlocs.append(locl)
                lifo['locals'] = nlocs
                if len(lifo['locals']) == 0:
                    await runt.warn(f'Unable to find doc for {func}')

            page = s_autodoc.RstHelp()

            s_autodoc.runtimeDocStormTypes(page, libsinfo,
                                           islib=True,
                                           addheader=False,
                                           oneline=not verbose,
                                           )
            for line in page.lines:
                await runt.printf(line)

        elif isinstance(cls, s_stormtypes.Prim):
            typeinfo = s_stormtypes.registry.getTypeDocs(cls._storm_typename)
            for lifo in typeinfo:
                lifo['locals'] = [loc for loc in lifo['locals'] if loc.get('type', {}).get('_funcname', '') == fname]
                if len(lifo['locals']) == 0:
                    await runt.warn(f'Unable to find doc for {func}')

            page = s_autodoc.RstHelp()

            s_autodoc.runtimeDocStormTypes(page, typeinfo,
                                           islib=False,
                                           oneline=not verbose,
                                           )
            for line in page.lines:
                await runt.printf(line)

        else:  # pragma: no cover
            raise s_exc.StormRuntimeError(mesg=f'Unknown bound method {func}')

    async def _handleStormLibMethod(self, func, runt: Runtime, verbose: bool =False):
        # Storm library methods must be derived from a library definition.
        # Determine the parent lib and get those docs exactly, and then render them.

        cls = getattr(func, '_storm_runtime_lib', None)
        fname = getattr(func, '_storm_runtime_lib_func', None)

        if isinstance(cls, s_stormtypes.Lib):
            libsinfo = s_stormtypes.registry.getLibDocs(cls)
            for lifo in libsinfo:
                nlocs = []
                for locl in lifo['locals']:
                    if locl.get('name') == fname:
                        nlocs.append(locl)
                lifo['locals'] = nlocs
                if len(lifo['locals']) == 0:
                    await runt.warn(f'Unable to find doc for {func}')

            page = s_autodoc.RstHelp()

            s_autodoc.runtimeDocStormTypes(page, libsinfo,
                                           islib=True,
                                           addheader=False,
                                           oneline=not verbose,
                                           )
            for line in page.lines:
                await runt.printf(line)

        else:  # pragma: no cover
            raise s_exc.StormRuntimeError(mesg=f'Unknown runtime lib method {func} {cls} {fname}')

class DiffCmd(Cmd):
    '''
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
    '''
    name = 'diff'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--tag', default=None, nargs='*',
                          help='Lift only nodes with the given tag (or tags) in the top layer.')
        pars.add_argument('--prop', default=None, help='Lift nodes with changes to the given property the top layer.')
        return pars

    async def execStormCmd(self, runt, genr):

        if runt.snap.view.parent is None:
            mesg = 'You may only generate a diff in a forked view.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        async for item in genr:
            yield item

        if self.opts.tag and self.opts.prop:
            mesg = 'You may specify --tag *or* --prop but not both.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if self.opts.tag:

            tagnames = [await s_stormtypes.tostr(tag) for tag in self.opts.tag]

            layr = runt.snap.view.layers[0]

            async for _, buid, sode in layr.liftByTags(tagnames):
                node = await self.runt.snap._joinStorNode(buid, {layr.iden: sode})
                if node is not None:
                    yield node, runt.initPath(node)

            return

        if self.opts.prop:

            propname = await s_stormtypes.tostr(self.opts.prop)

            prop = self.runt.snap.core.model.prop(propname)
            if prop is None:
                mesg = f'The property {propname} does not exist.'
                raise s_exc.NoSuchProp(mesg=mesg)

            if prop.isform:
                liftform = prop.name
                liftprop = None
            elif prop.isuniv:
                liftform = None
                liftprop = prop.name
            else:
                liftform = prop.form.name
                liftprop = prop.name

            layr = runt.snap.view.layers[0]
            async for _, buid, sode in layr.liftByProp(liftform, liftprop):
                node = await self.runt.snap._joinStorNode(buid, {layr.iden: sode})
                if node is not None:
                    yield node, runt.initPath(node)

            return

        async for buid, sode in runt.snap.view.layers[0].getStorNodes():
            node = await runt.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, runt.initPath(node)

class CopyToCmd(Cmd):
    '''
    Copy nodes from the current view into another view.

    Examples:

        // Copy all nodes tagged with #cno.mal.redtree to the target view.

        #cno.mal.redtree | copyto 33c971ac77943da91392dadd0eec0571
    '''
    name = 'copyto'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--no-data', default=False, action='store_true',
                          help='Do not copy node data to the destination view.')
        pars.add_argument('view', help='The destination view ID to copy the nodes to.')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'copyto arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        iden = await s_stormtypes.tostr(self.opts.view)

        view = runt.snap.core.getView(iden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view: {iden=}', iden=iden)

        runt.confirm(('view', 'read'), gateiden=view.iden)

        layriden = view.layers[0].iden

        async with await view.snap(user=runt.user) as snap:

            async for node, path in genr:

                runt.confirm(node.form.addperm, gateiden=layriden)
                for name in node.props.keys():
                    runt.confirmPropSet(node.form.props[name], layriden=layriden)

                for tag in node.tags.keys():
                    runt.confirm(('node', 'tag', 'add', *tag.split('.')), gateiden=layriden)

                if not self.opts.no_data:
                    async for name in node.iterDataKeys():
                        runt.confirm(('node', 'data', 'set', name), gateiden=layriden)

                async with snap.getEditor() as editor:

                    proto = await editor.addNode(node.ndef[0], node.ndef[1])

                    for name, valu in node.props.items():

                        prop = node.form.prop(name)
                        if prop.info.get('ro'):
                            if name == '.created':
                                proto.props['.created'] = valu
                                continue

                            curv = proto.get(name)
                            if curv is not None and curv != valu:
                                valurepr = prop.type.repr(curv)
                                mesg = f'Cannot overwrite read only property with conflicting ' \
                                       f'value: {node.iden()} {prop.full} = {valurepr}'
                                await runt.snap.warn(mesg)
                                continue

                        await proto.set(name, valu)

                    for name, valu in node.tags.items():
                        await proto.addTag(name, valu=valu)

                    for tagname, tagprops in node.tagprops.items():
                        for propname, valu in tagprops.items():
                            await proto.setTagProp(tagname, propname, valu)

                    if not self.opts.no_data:
                        async for name, valu in node.iterData():
                            await proto.setData(name, valu)

                    verbs = {}
                    async for (verb, n2iden) in node.iterEdgesN1():

                        if not verbs.get(verb):
                            runt.confirm(('node', 'edge', 'add', verb), gateiden=layriden)
                            verbs[verb] = True

                        n2node = await snap.getNodeByBuid(s_common.uhex(n2iden))
                        if n2node is None:
                            continue

                        await proto.addEdge(verb, n2iden)

                    # for the reverse edges, we'll need to make edits to the n1 node
                    async for (verb, n1iden) in node.iterEdgesN2():

                        if not verbs.get(verb):
                            runt.confirm(('node', 'edge', 'add', verb), gateiden=layriden)
                            verbs[verb] = True

                        n1proto = await editor.getNodeByBuid(s_common.uhex(n1iden))
                        if n1proto is not None:
                            await n1proto.addEdge(verb, s_common.ehex(node.buid))

                yield node, path

class MergeCmd(Cmd):
    '''
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
    '''
    name = 'merge'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--apply', default=False, action='store_true',
                          help='Execute the merge changes.')
        pars.add_argument('--wipe', default=False, action='store_true',
                          help='Replace the top layer in the view with a fresh layer.')
        pars.add_argument('--no-tags', default=False, action='store_true',
                          help='Do not merge tags/tagprops or syn:tag nodes.')
        pars.add_argument('--only-tags', default=False, action='store_true',
                          help='Only merge tags/tagprops or syn:tag nodes.')
        pars.add_argument('--include-tags', default=[], nargs='*',
                          help='Include specific tags/tagprops or syn:tag nodes when '
                               'merging, others are ignored. Tag glob expressions may '
                               'be used to specify the tags.')
        pars.add_argument('--exclude-tags', default=[], nargs='*',
                          help='Exclude specific tags/tagprops or syn:tag nodes from merge.'
                               'Tag glob expressions may be used to specify the tags.')
        pars.add_argument('--include-props', default=[], nargs='*',
                          help='Include specific props when merging, others are ignored.')
        pars.add_argument('--exclude-props', default=[], nargs='*',
                          help='Exclude specific props from merge.')
        pars.add_argument('--diff', default=False, action='store_true',
                          help='Enumerate all changes in the current layer.')
        return pars

    def _getTagFilter(self):
        if self.opts.include_tags:
            globs = s_cache.TagGlobs()
            for name in self.opts.include_tags:
                globs.add(name, True)

            def tagfilter(tag):
                if globs.get(tag):
                    return False
                return True

            return tagfilter

        if self.opts.exclude_tags:
            globs = s_cache.TagGlobs()
            for name in self.opts.exclude_tags:
                globs.add(name, True)

            def tagfilter(tag):
                if globs.get(tag):
                    return True
                return False

            return tagfilter

        return None

    def _getPropFilter(self):
        if self.opts.include_props:

            _include_props = set(self.opts.include_props)

            def propfilter(prop):
                return prop not in _include_props

            return propfilter

        if self.opts.exclude_props:

            _exclude_props = set(self.opts.exclude_props)

            def propfilter(prop):
                return prop in _exclude_props

            return propfilter

        return None

    async def _checkNodePerms(self, node, sode, runt, allows):

        layr0 = runt.snap.view.layers[0].iden
        layr1 = runt.snap.view.layers[1].iden

        if not allows['forms'] and sode.get('valu') is not None:
            if not self.opts.wipe:
                runt.confirm(('node', 'del', node.form.name), gateiden=layr0)
            runt.confirm(('node', 'add', node.form.name), gateiden=layr1)

        if not allows['props']:
            for name in sode.get('props', {}).keys():
                prop = node.form.prop(name)
                if not self.opts.wipe:
                    runt.confirmPropDel(prop, layriden=layr0)
                runt.confirmPropSet(prop, layriden=layr1)

        if not allows['tags']:

            tags = []
            tagadds = []
            for tag, valu in sode.get('tags', {}).items():
                if valu != (None, None):
                    tagadds.append(tag)
                    tagperm = tuple(tag.split('.'))
                    if not self.opts.wipe:
                        runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr0)
                    runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=layr1)
                else:
                    tags.append((len(tag), tag))

            for _, tag in sorted(tags, reverse=True):
                look = tag + '.'
                if any([tagadd.startswith(look) for tagadd in tagadds]):
                    continue

                tagadds.append(tag)
                tagperm = tuple(tag.split('.'))
                if not self.opts.wipe:
                    runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr0)
                runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=layr1)

            for tag in sode.get('tagprops', {}).keys():
                tagperm = tuple(tag.split('.'))
                if not self.opts.wipe:
                    runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr0)
                runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=layr1)

        if not allows['ndata']:
            async for name in runt.snap.view.layers[0].iterNodeDataKeys(node.buid):
                if not self.opts.wipe:
                    runt.confirm(('node', 'data', 'pop', name), gateiden=layr0)
                runt.confirm(('node', 'data', 'set', name), gateiden=layr1)

        if not allows['edges']:
            async for verb in runt.snap.view.layers[0].iterNodeEdgeVerbsN1(node.buid):
                if not self.opts.wipe:
                    runt.confirm(('node', 'edge', 'del', verb), gateiden=layr0)
                runt.confirm(('node', 'edge', 'add', verb), gateiden=layr1)

    async def execStormCmd(self, runt, genr):

        if runt.snap.view.parent is None:
            mesg = 'You may only merge nodes in forked views'
            raise s_exc.CantMergeView(mesg=mesg)

        if self.opts.wipe:
            mesg = 'merge --wipe requires view admin'
            runt.reqAdmin(gateiden=runt.snap.view.iden, mesg=mesg)
            runt.confirm(('layer', 'del'), gateiden=runt.snap.view.layers[0].iden)

        notags = self.opts.no_tags
        onlytags = self.opts.only_tags
        doapply = self.opts.apply

        tagfilter = self._getTagFilter()
        propfilter = self._getPropFilter()

        layr0 = runt.snap.view.layers[0]
        layr1 = runt.snap.view.layers[1]

        doperms = doapply and not (runt.isAdmin(gateiden=layr0.iden) and runt.isAdmin(gateiden=layr1.iden))

        if doperms:
            if not self.opts.wipe:
                allows = {
                    'forms': runt.user.allowed(('node', 'del'), gateiden=layr0.iden, deepdeny=True) and
                             runt.user.allowed(('node', 'add'), gateiden=layr1.iden, deepdeny=True),
                    'props': runt.user.allowed(('node', 'prop', 'del'), gateiden=layr0.iden, deepdeny=True) and
                             runt.user.allowed(('node', 'prop', 'set'), gateiden=layr1.iden, deepdeny=True),
                    'tags': runt.user.allowed(('node', 'tag', 'del'), gateiden=layr0.iden, deepdeny=True) and
                            runt.user.allowed(('node', 'tag', 'add'), gateiden=layr1.iden, deepdeny=True),
                    'ndata': runt.user.allowed(('node', 'data', 'pop'), gateiden=layr0.iden, deepdeny=True) and
                             runt.user.allowed(('node', 'data', 'set'), gateiden=layr1.iden, deepdeny=True),
                    'edges': runt.user.allowed(('node', 'edge', 'del'), gateiden=layr0.iden, deepdeny=True) and
                             runt.user.allowed(('node', 'edge', 'add'), gateiden=layr1.iden, deepdeny=True),
                }
            else:
                allows = {
                    'forms': runt.user.allowed(('node', 'add'), gateiden=layr1.iden, deepdeny=True),
                    'props': runt.user.allowed(('node', 'prop', 'set'), gateiden=layr1.iden, deepdeny=True),
                    'tags': runt.user.allowed(('node', 'tag', 'add'), gateiden=layr1.iden, deepdeny=True),
                    'ndata': runt.user.allowed(('node', 'data', 'set'), gateiden=layr1.iden, deepdeny=True),
                    'edges': runt.user.allowed(('node', 'edge', 'add'), gateiden=layr1.iden, deepdeny=True),
                }

            doperms = not all(allows.values())

        if self.opts.diff:

            async for node, path in genr:
                yield node, path

            async def diffgenr():
                async for buid, sode in layr0.getStorNodes():
                    node = await runt.snap.getNodeByBuid(buid)
                    if node is not None:
                        yield node, runt.initPath(node)

            genr = diffgenr()

        async with await runt.snap.view.parent.snap(user=runt.user) as snap:
            snap.strict = False

            snap.on('warn', runt.snap.dist)

            meta = {'user': runt.user.iden}

            if doapply:
                editor = s_snap.SnapEditor(snap, meta=meta)

            async for node, path in genr:

                # the timestamp for the adds/subs of each node merge will match
                nodeiden = node.iden()

                meta['time'] = s_common.now()

                sodes = await node.getStorNodes()
                sode = sodes[0]

                subs = []

                # check all node perms first
                if doperms:
                    await self._checkNodePerms(node, sode, runt, allows)

                form = node.form.name
                if form == 'syn:tag':
                    if notags:
                        await asyncio.sleep(0)
                        continue
                else:
                    # avoid merging a tag if the node won't exist below us
                    if onlytags:
                        for undr in sodes[1:]:
                            if undr.get('valu') is not None:
                                break
                        else:
                            await asyncio.sleep(0)
                            continue

                protonode = None
                delnode = False
                if not onlytags or form == 'syn:tag':
                    valu = sode.get('valu')
                    if valu is not None:

                        if tagfilter is not None and form == 'syn:tag' and tagfilter(valu[0]):
                            await asyncio.sleep(0)
                            continue

                        if not doapply:
                            valurepr = node.form.type.repr(valu[0])
                            await runt.printf(f'{nodeiden} {form} = {valurepr}')
                        else:
                            delnode = True
                            if (protonode := await editor.addNode(form, valu[0])) is None:
                                await asyncio.sleep(0)
                                continue

                    elif doapply:
                        if (protonode := await editor.addNode(form, node.ndef[1], norminfo={})) is None:
                            await asyncio.sleep(0)
                            continue

                    for name, (valu, stortype) in sode.get('props', {}).items():

                        prop = node.form.prop(name)
                        if propfilter is not None:
                            if name[0] == '.':
                                if propfilter(name):
                                    continue
                            else:
                                if propfilter(prop.full):
                                    continue

                        if prop.info.get('ro'):
                            if name == '.created':
                                if doapply:
                                    protonode.props['.created'] = valu
                                    if not self.opts.wipe:
                                        subs.append((s_layer.EDIT_PROP_DEL, (name, valu, stortype), ()))
                                continue

                            isset = False
                            for undr in sodes[1:]:
                                props = undr.get('props')
                                if props is not None:
                                    curv = props.get(name)
                                    if curv is not None:
                                        isset = curv[0] != valu
                                        break

                            if isset:
                                valurepr = prop.type.repr(curv[0])
                                mesg = f'Cannot merge read only property with conflicting ' \
                                       f'value: {nodeiden} {form}:{name} = {valurepr}'
                                await runt.snap.warn(mesg)
                                continue

                        if not doapply:
                            valurepr = prop.type.repr(valu)
                            await runt.printf(f'{nodeiden} {form}:{name} = {valurepr}')
                        else:
                            await protonode.set(name, valu)
                            if not self.opts.wipe:
                                subs.append((s_layer.EDIT_PROP_DEL, (name, valu, stortype), ()))

                if doapply and protonode is None:
                    if (protonode := await editor.addNode(form, node.ndef[1], norminfo={})) is None:
                        await asyncio.sleep(0)
                        continue

                if not notags:
                    for tag, valu in sode.get('tags', {}).items():

                        if tagfilter is not None and tagfilter(tag):
                            continue

                        if not doapply:
                            valurepr = ''
                            if valu != (None, None):
                                tagrepr = runt.model.type('ival').repr(valu)
                                valurepr = f' = {tagrepr}'
                            await runt.printf(f'{nodeiden} {form}#{tag}{valurepr}')
                        else:
                            await protonode.addTag(tag, valu)
                            if not self.opts.wipe:
                                subs.append((s_layer.EDIT_TAG_DEL, (tag, valu), ()))

                    for tag, tagdict in sode.get('tagprops', {}).items():

                        if tagfilter is not None and tagfilter(tag):
                            continue

                        for prop, (valu, stortype) in tagdict.items():
                            if not doapply:
                                valurepr = repr(valu)
                                await runt.printf(f'{nodeiden} {form}#{tag}:{prop} = {valurepr}')
                            else:
                                await protonode.setTagProp(tag, prop, valu)
                                if not self.opts.wipe:
                                    subs.append((s_layer.EDIT_TAGPROP_DEL, (tag, prop, valu, stortype), ()))

                if not onlytags or form == 'syn:tag':

                    async for name, valu in s_coro.pause(layr0.iterNodeData(node.buid)):
                        if not doapply:
                            valurepr = repr(valu)
                            await runt.printf(f'{nodeiden} {form} DATA {name} = {valurepr}')
                        else:
                            await protonode.setData(name, valu)
                            if not self.opts.wipe:
                                subs.append((s_layer.EDIT_NODEDATA_DEL, (name, valu), ()))

                    async for edge in s_coro.pause(layr0.iterNodeEdgesN1(node.buid)):
                        name, dest = edge
                        if not doapply:
                            await runt.printf(f'{nodeiden} {form} +({name})> {dest}')
                        else:
                            await protonode.addEdge(name, dest)
                            if not self.opts.wipe:
                                subs.append((s_layer.EDIT_EDGE_DEL, edge, ()))

                if delnode and not self.opts.wipe:
                    subs.append((s_layer.EDIT_NODE_DEL, valu, ()))

                if doapply:
                    await editor.flushEdits()

                    if subs:
                        subedits = [(node.buid, node.form.name, subs)]
                        await runt.snap.applyNodeEdits(subedits, nodecache={node.buid: node}, meta=meta)

                runt.snap.clearCachedNode(node.buid)
                yield await runt.snap.getNodeByBuid(node.buid), path

            if doapply and self.opts.wipe:
                await runt.snap.view.swapLayer()

class MoveNodesCmd(Cmd):
    '''
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
    '''
    name = 'movenodes'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--apply', default=False, action='store_true',
                          help='Execute the move changes.')
        pars.add_argument('--srclayers', default=None, nargs='*',
                          help='Specify layers to move storage nodes from (defaults to all below the top layer)')
        pars.add_argument('--destlayer', default=None,
                          help='Layer to move storage nodes to (defaults to the top layer)')
        pars.add_argument('--precedence', default=None, nargs='*',
                          help='Layer precedence for resolving conflicts (defaults to bottom up)')
        return pars

    async def _checkNodePerms(self, node, sodes, layrdata):

        for layr, sode in sodes.items():
            if layr == self.destlayr:
                continue

            if sode.get('valu') is not None:
                self.runt.confirm(('node', 'del', node.form.name), gateiden=layr)
                self.runt.confirm(('node', 'add', node.form.name), gateiden=self.destlayr)

            for name, (valu, stortype) in sode.get('props', {}).items():
                full = node.form.prop(name).full
                self.runt.confirm(('node', 'prop', 'del', full), gateiden=layr)
                self.runt.confirm(('node', 'prop', 'set', full), gateiden=self.destlayr)

            for tag, valu in sode.get('tags', {}).items():
                tagperm = tuple(tag.split('.'))
                self.runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr)
                self.runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=self.destlayr)

            for tag, tagdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in tagdict.items():
                    tagperm = tuple(tag.split('.'))
                    self.runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr)
                    self.runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=self.destlayr)

            for name in layrdata[layr]:
                self.runt.confirm(('node', 'data', 'pop', name), gateiden=layr)
                self.runt.confirm(('node', 'data', 'set', name), gateiden=self.destlayr)

            async for edge in self.lyrs[layr].iterNodeEdgesN1(node.buid):
                verb = edge[0]
                self.runt.confirm(('node', 'edge', 'del', verb), gateiden=layr)
                self.runt.confirm(('node', 'edge', 'add', verb), gateiden=self.destlayr)

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'movenodes arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if len(runt.snap.view.layers) < 2:
            mesg = 'You may only move nodes in views with multiple layers.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        layridens = {layr.iden: layr for layr in runt.snap.view.layers}

        if self.opts.srclayers:
            srclayrs = self.opts.srclayers
            for layr in srclayrs:
                if layr not in layridens:
                    mesg = f'No layer with iden {layr} in this view, cannot move nodes.'
                    raise s_exc.BadOperArg(mesg=mesg, layr=layr)
        else:
            srclayrs = [layr.iden for layr in runt.snap.view.layers[1:]]

        if self.opts.destlayer:
            self.destlayr = self.opts.destlayer
            if self.destlayr not in layridens:
                mesg = f'No layer with iden {self.destlayr} in this view, cannot move nodes.'
                raise s_exc.BadOperArg(mesg=mesg, layr=self.destlayr)
        else:
            self.destlayr = runt.snap.view.layers[0].iden

        if self.destlayr in srclayrs:
            mesg = f'Source layer {self.destlayr} cannot also be the destination layer.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        self.adds = []
        self.subs = {}
        self.lyrs = {}
        self.runt = runt

        if self.opts.precedence:
            layrlist = srclayrs + [self.destlayr]
            for layr in self.opts.precedence:
                if layr not in layridens:
                    mesg = f'No layer with iden {layr} in this view, cannot be used to specify precedence.'
                    raise s_exc.BadOperArg(mesg=mesg, layr=layr)
                layrlist.remove(layr)

            if len(layrlist) > 0:
                mesg = 'All source layers and the destination layer must be included when ' \
                       f'specifying precedence (missing {layrlist}).'
                raise s_exc.BadOperArg(mesg=mesg, layrlist=layrlist)
            layerord = self.opts.precedence
        else:
            layerord = layridens.keys()

        for layr in layerord:
            if layr == self.destlayr or layr in srclayrs:
                self.lyrs[layr] = layridens[layr]

            if layr in srclayrs:
                self.subs[layr] = []

        async for node, path in genr:

            # the timestamp for the adds/subs of each node merge will match
            nodeiden = node.iden()
            meta = {'user': runt.user.iden, 'time': s_common.now()}

            # get nodedata keys per layer
            sodes = {}
            layrdata = {}
            for layr in self.lyrs.keys():
                sodes[layr] = await self.lyrs[layr].getStorNode(node.buid)
                layrkeys = set()
                async for name in self.lyrs[layr].iterNodeDataKeys(node.buid):
                    layrkeys.add(name)
                layrdata[layr] = layrkeys

            # check all perms
            if self.opts.apply:
                await self._checkNodePerms(node, sodes, layrdata)

            delnodes = []
            for layr, sode in sodes.items():
                if layr == self.destlayr:
                    continue

                valu = sode.get('valu')
                if valu is not None:
                    valurepr = node.form.type.repr(valu[0])
                    if not self.opts.apply:
                        await runt.printf(f'{self.destlayr} add {nodeiden} {node.form.name} = {valurepr}')
                        await runt.printf(f'{layr} delete {nodeiden} {node.form.name} = {valurepr}')
                    else:
                        self.adds.append((s_layer.EDIT_NODE_ADD, valu, ()))
                        delnodes.append((layr, valu))

            await self._moveProps(node, sodes, meta)
            await self._moveTags(node, sodes, meta)
            await self._moveTagProps(node, sodes, meta)
            await self._moveNodeData(node, layrdata, meta)
            await self._moveEdges(node, meta)

            for layr, valu in delnodes:
                edit = [(node.buid, node.form.name, [(s_layer.EDIT_NODE_DEL, valu, ())])]
                await self.lyrs[layr].storNodeEdits(edit, meta=meta)

            runt.snap.livenodes.pop(node.buid, None)
            yield await runt.snap.getNodeByBuid(node.buid), path

    async def _sync(self, node, meta):

        if not self.opts.apply:
            return

        if self.adds:
            addedits = [(node.buid, node.form.name, self.adds)]
            await self.lyrs[self.destlayr].storNodeEdits(addedits, meta=meta)
            self.adds.clear()

        for srclayr, edits in self.subs.items():
            if edits:
                subedits = [(node.buid, node.form.name, edits)]
                await self.lyrs[srclayr].storNodeEdits(subedits, meta=meta)
                edits.clear()

    async def _moveProps(self, node, sodes, meta):

        ecnt = 0
        movekeys = set()
        form = node.form.name
        nodeiden = node.iden()

        for layr, sode in sodes.items():
            for name, (valu, stortype) in sode.get('props', {}).items():

                if (stortype in (s_layer.STOR_TYPE_IVAL, s_layer.STOR_TYPE_MINTIME, s_layer.STOR_TYPE_MAXTIME)
                    or name not in movekeys) and not layr == self.destlayr:

                    if not self.opts.apply:
                        valurepr = node.form.prop(name).type.repr(valu)
                        await self.runt.printf(f'{self.destlayr} set {nodeiden} {form}:{name} = {valurepr}')
                    else:
                        self.adds.append((s_layer.EDIT_PROP_SET, (name, valu, None, stortype), ()))
                        ecnt += 1

                movekeys.add(name)

                if not layr == self.destlayr:
                    if not self.opts.apply:
                        valurepr = node.form.prop(name).type.repr(valu)
                        await self.runt.printf(f'{layr} delete {nodeiden} {form}:{name} = {valurepr}')
                    else:
                        self.subs[layr].append((s_layer.EDIT_PROP_DEL, (name, None, stortype), ()))
                        ecnt += 1

                if ecnt >= 1000:
                    await self._sync(node, meta)
                    ecnt = 0

        await self._sync(node, meta)

    async def _moveTags(self, node, sodes, meta):

        ecnt = 0
        form = node.form.name
        nodeiden = node.iden()

        for layr, sode in sodes.items():
            for tag, valu in sode.get('tags', {}).items():

                if not layr == self.destlayr:
                    if not self.opts.apply:
                        valurepr = ''
                        if valu != (None, None):
                            tagrepr = self.runt.model.type('ival').repr(valu)
                            valurepr = f' = {tagrepr}'
                        await self.runt.printf(f'{self.destlayr} set {nodeiden} {form}#{tag}{valurepr}')
                        await self.runt.printf(f'{layr} delete {nodeiden} {form}#{tag}{valurepr}')
                    else:
                        self.adds.append((s_layer.EDIT_TAG_SET, (tag, valu, None), ()))
                        self.subs[layr].append((s_layer.EDIT_TAG_DEL, (tag, None), ()))
                        ecnt += 2

                if ecnt >= 1000:
                    await self._sync(node, meta)
                    ecnt = 0

        await self._sync(node, meta)

    async def _moveTagProps(self, node, sodes, meta):

        ecnt = 0
        movekeys = set()
        form = node.form.name
        nodeiden = node.iden()

        for layr, sode in sodes.items():
            for tag, tagdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in tagdict.items():
                    if (stortype in (s_layer.STOR_TYPE_IVAL, s_layer.STOR_TYPE_MINTIME, s_layer.STOR_TYPE_MAXTIME)
                        or (tag, prop) not in movekeys) and not layr == self.destlayr:
                        if not self.opts.apply:
                            valurepr = repr(valu)
                            mesg = f'{self.destlayr} set {nodeiden} {form}#{tag}:{prop} = {valurepr}'
                            await self.runt.printf(mesg)
                        else:
                            self.adds.append((s_layer.EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype), ()))
                            ecnt += 1

                    movekeys.add((tag, prop))

                    if not layr == self.destlayr:
                        if not self.opts.apply:
                            valurepr = repr(valu)
                            await self.runt.printf(f'{layr} delete {nodeiden} {form}#{tag}:{prop} = {valurepr}')
                        else:
                            self.subs[layr].append((s_layer.EDIT_TAGPROP_DEL, (tag, prop, None, stortype), ()))
                            ecnt += 1

                    if ecnt >= 1000:
                        await self._sync(node, meta)
                        ecnt = 0

        await self._sync(node, meta)

    async def _moveNodeData(self, node, layrdata, meta):

        ecnt = 0
        movekeys = set()
        form = node.form.name
        nodeiden = node.iden()

        for layr in self.lyrs.keys():
            for name in layrdata[layr]:
                if name not in movekeys and not layr == self.destlayr:
                    if not self.opts.apply:
                        await self.runt.printf(f'{self.destlayr} set {nodeiden} {form} DATA {name}')
                    else:
                        (retn, valu) = await self.lyrs[layr].getNodeData(node.buid, name)
                        if retn:
                            self.adds.append((s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()))
                            ecnt += 1

                        await asyncio.sleep(0)

                movekeys.add(name)

                if not layr == self.destlayr:
                    if not self.opts.apply:
                        await self.runt.printf(f'{layr} delete {nodeiden} {form} DATA {name}')
                    else:
                        self.subs[layr].append((s_layer.EDIT_NODEDATA_DEL, (name, None), ()))
                        ecnt += 1

                if ecnt >= 1000:
                    await self._sync(node, meta)
                    ecnt = 0

        await self._sync(node, meta)

    async def _moveEdges(self, node, meta):

        ecnt = 0
        form = node.form.name
        nodeiden = node.iden()

        for iden, layr in self.lyrs.items():
            if not iden == self.destlayr:
                async for edge in layr.iterNodeEdgesN1(node.buid):
                    if not self.opts.apply:
                        name, dest = edge
                        await self.runt.printf(f'{self.destlayr} add {nodeiden} {form} +({name})> {dest}')
                        await self.runt.printf(f'{iden} delete {nodeiden} {form} +({name})> {dest}')
                    else:
                        self.adds.append((s_layer.EDIT_EDGE_ADD, edge, ()))
                        self.subs[iden].append((s_layer.EDIT_EDGE_DEL, edge, ()))
                        ecnt += 2

                    if ecnt >= 1000:
                        await self._sync(node, meta)
                        ecnt = 0

        await self._sync(node, meta)

class LimitCmd(Cmd):
    '''
    Limit the number of nodes generated by the query in the given position.

    Example:

        inet:ipv4 | limit 10
    '''

    name = 'limit'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('count', type='int', help='The maximum number of nodes to yield.')
        return pars

    async def execStormCmd(self, runt, genr):

        count = 0
        async for item in genr:

            yield item
            count += 1

            if count >= self.opts.count:
                break

class UniqCmd(Cmd):
    '''
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
    '''

    name = 'uniq'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('value', nargs='?', help='A relative property or variable to uniq by.')
        return pars

    async def execStormCmd(self, runt, genr):

        async with await s_spooled.Set.anit(dirn=self.runt.snap.core.dirn) as uniqset:

            if len(self.argv) > 0:
                async for node, path in genr:

                    valu = await s_stormtypes.toprim(self.opts.value)
                    valu = s_hashitem.hashitem(valu)
                    if valu in uniqset:
                        await asyncio.sleep(0)
                        continue

                    await uniqset.add(valu)
                    yield node, path

            else:
                async for node, path in genr:

                    if node.buid in uniqset:
                        # all filters must sleep
                        await asyncio.sleep(0)
                        continue

                    await uniqset.add(node.buid)
                    yield node, path

class MaxCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the highest value for an expression.

    Examples:

        // Yield the file:bytes node with the highest :size property
        file:bytes#foo.bar | max :size

        // Yield the file:bytes node with the highest value for $tick
        file:bytes#foo.bar +.seen ($tick, $tock) = .seen | max $tick

        // Yield the it:dev:str node with the longest length
        it:dev:str | max $lib.len($node.value())

    '''

    name = 'max'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('valu', help='The property or variable to use for comparison.')
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
    Consume nodes and yield only the one node with the lowest value for an expression.

    Examples:

        // Yield the file:bytes node with the lowest :size property
        file:bytes#foo.bar | min :size

        // Yield the file:bytes node with the lowest value for $tick
        file:bytes#foo.bar +.seen ($tick, $tock) = .seen | min $tick

        // Yield the it:dev:str node with the shortest length
        it:dev:str | min $lib.len($node.value())

    '''
    name = 'min'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('valu', help='The property or variable to use for comparison.')
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
        pars.add_argument('--delbytes', default=False, action='store_true',
                          help='For file:bytes nodes, remove the bytes associated with the '
                               'sha256 property from the axon as well if present.')
        pars.add_argument('--deledges', default=False, action='store_true',
                          help='Delete N2 light edges before deleting the node.')
        return pars

    async def execStormCmd(self, runt, genr):

        force = await s_stormtypes.tobool(self.opts.force)
        delbytes = await s_stormtypes.tobool(self.opts.delbytes)
        deledges = await s_stormtypes.tobool(self.opts.deledges)

        if force:
            if runt.user is not None and not runt.isAdmin():
                mesg = '--force requires admin privs.'
                raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        if delbytes:
            runt.confirm(('storm', 'lib', 'axon', 'del'))
            await runt.snap.core.getAxon()
            axon = runt.snap.core.axon

        async for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.layerConfirm(('node', 'tag', 'del', *tag.split('.')))

            runt.layerConfirm(('node', 'del', node.form.name))

            if deledges:
                async with await s_spooled.Set.anit(dirn=self.runt.snap.core.dirn) as edges:
                    seenverbs = set()

                    async for (verb, n2iden) in node.iterEdgesN2():
                        if verb not in seenverbs:
                            runt.layerConfirm(('node', 'edge', 'del', verb))
                            seenverbs.add(verb)
                        await edges.add((verb, n2iden))

                    async with self.runt.snap.getEditor() as editor:
                        async for (verb, n2iden) in edges:
                            n2 = await editor.getNodeByBuid(s_common.uhex(n2iden))
                            if n2 is not None:
                                if await n2.delEdge(verb, node.iden()) and len(editor.protonodes) >= 1000:
                                    await self.runt.snap.applyNodeEdits(editor.getNodeEdits())
                                    editor.protonodes.clear()

            if delbytes and node.form.name == 'file:bytes':
                sha256 = node.props.get('sha256')
                if sha256:
                    sha256b = s_common.uhex(sha256)
                    await axon.del_(sha256b)

            await node.delete(force=force)

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

        if not self.runtsafe:
            mesg = 'movetag arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

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

        newname, newinfo = await snap.getTagNorm(await s_stormtypes.tostr(self.opts.newtag))
        newparts = newname.split('.')

        runt.layerConfirm(('node', 'tag', 'del', *oldparts))
        runt.layerConfirm(('node', 'tag', 'add', *newparts))

        newt = await snap.addNode('syn:tag', newname, norminfo=newinfo)
        newstr = newt.ndef[1]

        if oldstr == newstr:
            raise s_exc.BadOperArg(mesg='Cannot retag a tag to the same valu.',
                                   newtag=newstr, oldtag=oldstr)

        # do some sanity checking on the new tag to make sure we're not creating a loop
        tagcycle = [newstr]
        isnow = newt.get('isnow')
        while isnow:
            if isnow in tagcycle:
                raise s_exc.BadOperArg(mesg=f'Pre-existing cycle detected when moving {oldstr} to tag {newstr}',
                                       cycle=tagcycle)
            tagcycle.append(isnow)
            newtag = await snap.addNode('syn:tag', isnow)
            isnow = newtag.get('isnow')
            await asyncio.sleep(0)

        if oldstr in tagcycle:
            raise s_exc.BadOperArg(mesg=f'Tag cycle detected when moving tag {oldstr} to tag {newstr}',
                                   cycle=tagcycle)

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

            olddocurl = node.get('doc:url')
            if olddocurl is not None:
                await newnode.set('doc:url', olddocurl)

            oldtitle = node.get('title')
            if oldtitle is not None:
                await newnode.set('title', oldtitle)

            # Copy any tags over to the newnode if any are present.
            for k, v in node.tags.items():
                await newnode.addTag(k, v)
                await asyncio.sleep(0)

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
                    await asyncio.sleep(0)
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
    readonly = True

    async def execStormCmd(self, runt, genr):

        if False:  # make this method an async generator function
            yield None

        async for node, path in genr:
            await asyncio.sleep(0)

class CountCmd(Cmd):
    '''
    Iterate through query results, and print the resulting number of nodes
    which were lifted. This does not yield the nodes counted, unless the
    --yield switch is provided.

    Example:

        # Count the number of IPV4 nodes with a given ASN.
        inet:ipv4:asn=20 | count

        # Count the number of IPV4 nodes with a given ASN and yield them.
        inet:ipv4:asn=20 | count --yield

    '''
    name = 'count'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--yield', default=False, action='store_true',
                          dest='yieldnodes', help='Yield inbound nodes.')
        return pars

    async def execStormCmd(self, runt, genr):

        i = 0
        async for item in genr:
            if self.opts.yieldnodes:
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
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('iden', nargs='*', type='str', default=[],
                          help='Iden to lift nodes by. May be specified multiple times.')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'iden argument must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        async for x in genr:
            yield x

        for iden in self.opts.iden:
            try:
                buid = s_common.uhex(iden)
            except Exception:
                await asyncio.sleep(0)
                await runt.warn(f'Failed to decode iden: [{iden}]')
                continue
            if len(buid) != 32:
                await asyncio.sleep(0)
                await runt.warn(f'iden must be 32 bytes [{iden}]')
                continue

            node = await runt.snap.getNodeByBuid(buid)
            if node is None:
                await asyncio.sleep(0)
                continue
            yield node, runt.initPath(node)

class SleepCmd(Cmd):
    '''
    Introduce a delay between returning each result for the storm query.

    NOTE: This is mostly used for testing / debugging.

    Example:

        #foo.bar | sleep 0.5

    '''
    name = 'sleep'
    readonly = True

    async def execStormCmd(self, runt, genr):
        async for item in genr:
            yield item
            await self.runt.waitfini(self.opts.delay)

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('delay', type='float', default=1, help='Delay in floating point seconds.')
        return pars

class GraphCmd(Cmd):
    '''
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

    '''
    name = 'graph'

    def getArgParser(self):

        pars = Cmd.getArgParser(self)
        pars.add_argument('--degrees', type='int', default=1, help='How many degrees to graph out.')

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

        if not self.runtsafe:
            mesg = 'graph arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

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
            rules['pivots'].append(pivo)

        for filt in self.opts.filter:
            rules['filters'].append(filt)

        for name, pivo in self.opts.form_pivot:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['pivots'].append(pivo)

        for name, filt in self.opts.form_filter:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['filters'].append(filt)

        subg = s_ast.SubGraph(rules)

        async for node, path in subg.run(runt, genr):
            yield node, path

class ViewExecCmd(Cmd):
    '''
    Execute a storm query in a different view.

    NOTE: Variables are passed through but nodes are not. The behavior of this command may be
    non-intuitive in relation to the way storm normally operates. For further information on
    behavior and limitations when using `view.exec`, reference the `view.exec` section of the
    Synapse User Guide: https://v.vtx.lk/view-exec.

    Examples:

        // Move some tagged nodes to another view
        inet:fqdn#foo.bar $fqdn=$node.value() | view.exec 95d5f31f0fb414d2b00069d3b1ee64c6 { [ inet:fqdn=$fqdn ] }
    '''

    name = 'view.exec'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('view', help='The GUID of the view in which the query will execute.')
        pars.add_argument('storm', help='The storm query to execute on the view.')
        return pars

    async def execStormCmd(self, runt, genr):

        # nodes may not pass across views, but their path vars may
        node = None
        async for node, path in genr:

            view = await s_stormtypes.tostr(self.opts.view)
            text = await s_stormtypes.tostr(self.opts.storm)

            opts = {
                'vars': path.vars,
                'view': view,
            }

            query = await runt.getStormQuery(text)
            async with runt.getSubRuntime(query, opts=opts) as subr:
                async for item in subr.execute():
                    await asyncio.sleep(0)

            yield node, path

        if node is None and self.runtsafe:
            view = await s_stormtypes.tostr(self.opts.view)
            text = await s_stormtypes.tostr(self.opts.storm)
            query = await runt.getStormQuery(text)

            opts = {'view': view}
            async with runt.getSubRuntime(query, opts=opts) as subr:
                async for item in subr.execute():
                    await asyncio.sleep(0)

class BackgroundCmd(Cmd):
    '''
    Execute a query pipeline as a background task.
    NOTE: Variables are passed through but nodes are not
    '''
    name = 'background'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('query', help='The query to execute in the background.')
        return pars

    async def execStormTask(self, query, opts):

        core = self.runt.snap.core
        user = core._userFromOpts(opts)
        info = {'query': query.text,
                'view': opts['view'],
                'background': True}

        await core.boss.promote('storm', user=user, info=info)

        async with core.getStormRuntime(query, opts=opts) as runt:
            async for item in runt.execute():
                await asyncio.sleep(0)

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'The background query must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        async for item in genr:
            yield item

        _query = await s_stormtypes.tostr(self.opts.query)
        query = await runt.getStormQuery(_query)

        # make sure the subquery *could* have run
        async with runt.getSubRuntime(query) as subr:
            query.validate(subr)

        runtprims = await s_stormtypes.toprim(self.runt.getScopeVars(), use_list=True)
        runtvars = {k: v for (k, v) in runtprims.items() if s_msgpack.isok(v)}

        opts = {
            'user': runt.user.iden,
            'view': runt.snap.view.iden,
            'vars': runtvars,
        }

        coro = self.execStormTask(query, opts)
        runt.snap.core.schedCoro(coro)

class ParallelCmd(Cmd):
    '''
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
    '''
    name = 'parallel'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--size', default=8,
            help='The number of parallel Storm pipelines to execute.')

        pars.add_argument('query',
            help='The query to execute in parallel.')

        return pars

    async def nextitem(self, inq):
        while True:
            item = await inq.get()
            if item is None:
                return

            yield item

    async def pipeline(self, runt, query, inq, outq, runtvars):

        opts = {'vars': runtvars}

        try:
            async with runt.getCmdRuntime(query, opts=opts) as subr:
                async for item in subr.execute(genr=self.nextitem(inq)):
                    await outq.put(item)

            await outq.put(None)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            await outq.put(e)

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'parallel arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        size = await s_stormtypes.toint(self.opts.size)

        _query = await s_stormtypes.tostr(self.opts.query)
        query = await runt.getStormQuery(_query)

        async with runt.getSubRuntime(query) as subr:
            query.validate(subr)

        async with await s_base.Base.anit() as base:

            inq = asyncio.Queue(maxsize=size)
            outq = asyncio.Queue(maxsize=size)

            runtvars = self.runt.getScopeVars()

            tsks = 0
            try:
                while tsks < size:
                    await inq.put(await genr.__anext__())
                    base.schedCoro(self.pipeline(runt, query, inq, outq, runtvars))
                    tsks += 1
            except StopAsyncIteration:
                [await inq.put(None) for i in range(tsks)]

            # If a full set of tasks were created, keep pumping nodes into the queue
            if tsks == size:
                async def pump():
                    try:
                        async for pumpitem in genr:
                            await inq.put(pumpitem)
                        [await inq.put(None) for i in range(size)]
                    except Exception as e:
                        await outq.put(e)

                base.schedCoro(pump())

            # If no tasks were created, make a full set
            elif tsks == 0:
                tsks = size
                for i in range(size):
                    base.schedCoro(self.pipeline(runt, query, inq, outq, runtvars))
                [await inq.put(None) for i in range(tsks)]

            exited = 0
            while True:

                item = await outq.get()
                if isinstance(item, Exception):
                    raise item

                if item is None:
                    exited += 1
                    if exited == tsks:
                        return
                    continue

                yield item

class TeeCmd(Cmd):
    '''
    Execute multiple Storm queries on each node in the input stream, joining output streams together.

    Commands are executed in order they are given; unless the ``--parallel`` switch is provided.

    Examples:

        # Perform a pivot out and pivot in on a inet:ivp4 node
        inet:ipv4=1.2.3.4 | tee { -> * } { <- * }

        # Also emit the inbound node
        inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }

        # Execute multiple enrichment queries in parallel.
        inet:ipv4=1.2.3.4 | tee -p { enrich.foo } { enrich.bar } { enrich.baz }

    '''
    name = 'tee'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--join', '-j', default=False, action='store_true',
                          help='Emit inbound nodes after processing storm queries.')

        pars.add_argument('--parallel', '-p', default=False, action='store_true',
                          help='Run the storm queries in parallel instead of sequence. The node output order is not guaranteed.')

        pars.add_argument('query', nargs='*',
                          help='Specify a query to execute on the input nodes.')

        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'tee arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if not self.opts.query:
            raise s_exc.StormRuntimeError(mesg='Tee command must take at least one query as input.',
                                          name=self.name)

        async with contextlib.AsyncExitStack() as stack:

            runts = []
            query_arguments = await s_stormtypes.toprim(self.opts.query)
            queries = []
            for arg in query_arguments:
                if isinstance(arg, str):
                    queries.append(arg)
                    continue
                # if a argument is a container/iterable, we'll add
                # whatever content is in it as query text
                for text in arg:
                    queries.append(text)

            for text in queries:
                query = await runt.getStormQuery(text)
                subr = await stack.enter_async_context(runt.getSubRuntime(query))
                runts.append(subr)

            size = len(runts)
            outq_size = size * 2
            node = None
            async for node, path in genr:

                if self.opts.parallel and runts:

                    outq = asyncio.Queue(maxsize=outq_size)
                    for subr in runts:
                        subg = s_common.agen((node, path.fork(node, None)))
                        self.runt.snap.schedCoro(self.pipeline(subr, outq, genr=subg))

                    exited = 0

                    while True:
                        item = await outq.get()

                        if isinstance(item, Exception):
                            raise item

                        if item is None:
                            exited += 1
                            if exited == size:
                                break
                            continue  # pragma: no cover

                        yield item

                else:

                    for subr in runts:
                        subg = s_common.agen((node, path.fork(node, None)))
                        async for subitem in subr.execute(genr=subg):
                            yield subitem

                if self.opts.join:
                    yield node, path

            if node is None and self.runtsafe:
                if self.opts.parallel and runts:

                    outq = asyncio.Queue(maxsize=outq_size)
                    for subr in runts:
                        self.runt.snap.schedCoro(self.pipeline(subr, outq))

                    exited = 0

                    while True:
                        item = await outq.get()

                        if isinstance(item, Exception):
                            raise item

                        if item is None:
                            exited += 1
                            if exited == size:
                                break
                            continue  # pragma: no cover

                        yield item

                else:
                    for subr in runts:
                        async for subitem in subr.execute():
                            yield subitem

    async def pipeline(self, runt, outq, genr=None):
        try:
            async for subitem in runt.execute(genr=genr):
                await outq.put(subitem)

            await outq.put(None)

        except Exception as e:
            await outq.put(e)


class TreeCmd(Cmd):
    '''
    Walk elements of a tree using a recursive pivot.

    Examples:

        # pivot upward yielding each FQDN
        inet:fqdn=www.vertex.link | tree { :domain -> inet:fqdn }
    '''
    name = 'tree'
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('query', help='The pivot query')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'tree query must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        text = await s_stormtypes.tostr(self.opts.query)

        async def recurse(node, path):

            yield node, path

            async for nnode, npath in node.storm(runt, text, path=path):
                async for item in recurse(nnode, npath):
                    yield item

        try:

            async for node, path in genr:
                async for nodepath in recurse(node, path):
                    yield nodepath

        except s_exc.RecursionLimitHit:
            raise s_exc.StormRuntimeError(mesg='tree command exceeded maximum depth') from None

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

        # Scrape the primary property from the inbound nodes.
        it:dev:str | scrape $node.repr()

        # Scrape properties inbound nodes and yield newly scraped nodes.
        inet:search:query | scrape --yield

        # Skip re-fanging text before scraping.
        inet:search:query | scrape --skiprefang

        # Limit scrape to specific forms.
        inet:search:query | scrape --forms (inet:fqdn, inet:ipv4)
    '''

    name = 'scrape'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--refs', '-r', default=False, action='store_true',
                          help='Create refs light edges to any scraped nodes from the input node')
        pars.add_argument('--yield', dest='doyield', default=False, action='store_true',
                          help='Include newly scraped nodes in the output')
        pars.add_argument('--skiprefang', dest='dorefang', default=True, action='store_false',
                          help='Do not remove de-fanging from text before scraping')
        pars.add_argument('--forms', default=[],
                          help='Only scrape values which match specific forms.')
        pars.add_argument('values', nargs='*',
                          help='Specific relative properties or variables to scrape')
        return pars

    async def execStormCmd(self, runt, genr):

        node = None
        async for node, path in genr:  # type: s_node.Node, s_node.Path

            refs = await s_stormtypes.toprim(self.opts.refs)
            forms = await s_stormtypes.toprim(self.opts.forms)
            refang = await s_stormtypes.tobool(self.opts.dorefang)

            if isinstance(forms, str):
                forms = forms.split(',')
            elif not isinstance(forms, (tuple, list, set)):
                forms = (forms,)

            # TODO some kind of repr or as-string option on toprims
            todo = await s_stormtypes.toprim(self.opts.values)

            # if a list of props haven't been specified, then default to ALL of them
            if not todo:
                todo = list(node.props.values())

            link = {'type': 'scrape'}
            for text in todo:

                text = str(text)

                async for (form, valu, _) in self.runt.snap.view.scrapeIface(text, refang=refang):
                    if forms and form not in forms:
                        continue

                    nnode = await node.snap.addNode(form, valu)
                    npath = path.fork(nnode, link)

                    if refs:
                        if node.form.isrunt:
                            mesg = f'Edges cannot be used with runt nodes: {node.form.full}'
                            await runt.warn(mesg)
                        else:
                            await node.addEdge('refs', nnode.iden())

                    if self.opts.doyield:
                        yield nnode, npath

            if not self.opts.doyield:
                yield node, path

        if self.runtsafe and node is None:

            forms = await s_stormtypes.toprim(self.opts.forms)
            refang = await s_stormtypes.tobool(self.opts.dorefang)

            if isinstance(forms, str):
                forms = forms.split(',')
            elif not isinstance(forms, (tuple, list, set)):
                forms = (forms,)

            for item in self.opts.values:
                text = str(await s_stormtypes.toprim(item))

                async for (form, valu, _) in self.runt.snap.view.scrapeIface(text, refang=refang):
                    if forms and form not in forms:
                        continue

                    addnode = await runt.snap.addNode(form, valu)
                    if self.opts.doyield:
                        yield addnode, runt.initPath(addnode)

class LiftByVerb(Cmd):
    '''
    Lift nodes from the current view by an light edge verb.

    Examples:

        # Lift all the n1 nodes for the light edge "foo"
        lift.byverb "foo"

        # Lift all the n2 nodes for the light edge "foo"
        lift.byverb --n2 "foo"

    Notes:

        Only a single instance of a node will be yielded from this command
        when that node is lifted via the light edge membership.
    '''
    name = 'lift.byverb'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('verb', type='str', required=True,
                          help='The edge verb to lift nodes by.')
        pars.add_argument('--n2', action='store_true', default=False,
                          help='Lift by the N2 value instead of N1 value.')
        return pars

    async def iterEdgeNodes(self, verb, idenset, n2=False):
        if n2:
            async for (_, _, n2) in self.runt.snap.view.getEdges(verb):
                if n2 in idenset:
                    continue
                await idenset.add(n2)
                node = await self.runt.snap.getNodeByBuid(s_common.uhex(n2))
                if node:
                    yield node
        else:
            async for (n1, _, _) in self.runt.snap.view.getEdges(verb):
                if n1 in idenset:
                    continue
                await idenset.add(n1)
                node = await self.runt.snap.getNodeByBuid(s_common.uhex(n1))
                if node:
                    yield node

    async def execStormCmd(self, runt, genr):

        core = self.runt.snap.core

        async with await s_spooled.Set.anit(dirn=core.dirn, cell=core) as idenset:

            if self.runtsafe:
                verb = await s_stormtypes.tostr(self.opts.verb)
                n2 = self.opts.n2

                async for x in genr:
                    yield x

                async for node in self.iterEdgeNodes(verb, idenset, n2):
                    yield node, runt.initPath(node)

            else:
                async for _node, _path in genr:
                    verb = await s_stormtypes.tostr(self.opts.verb)
                    n2 = self.opts.n2

                    yield _node, _path

                    link = {'type': 'runtime'}
                    async for node in self.iterEdgeNodes(verb, idenset, n2):
                        yield node, _path.fork(node, link)

class EdgesDelCmd(Cmd):
    '''
    Bulk delete light edges from input nodes.

    Examples:

        # Delete all "foo" light edges from an inet:ipv4
        inet:ipv4=1.2.3.4 | edges.del foo

        # Delete light edges with any verb from a node
        inet:ipv4=1.2.3.4 | edges.del *

        # Delete all "foo" light edges to an inet:ipv4
        inet:ipv4=1.2.3.4 | edges.del foo --n2
    '''
    name = 'edges.del'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('verb', type='str', help='The verb of light edges to delete.')

        pars.add_argument('--n2', action='store_true', default=False,
                          help='Delete light edges where input node is N2 instead of N1.')
        return pars

    async def delEdges(self, node, verb, n2=False):
        if n2:
            n2iden = node.iden()
            async for (v, n1iden) in node.iterEdgesN2(verb):
                n1 = await self.runt.snap.getNodeByBuid(s_common.uhex(n1iden))
                if n1 is not None:
                    await n1.delEdge(v, n2iden)

        else:
            async for (v, n2iden) in node.iterEdgesN1(verb):
                await node.delEdge(v, n2iden)

    async def execStormCmd(self, runt, genr):

        if self.runtsafe:
            n2 = self.opts.n2
            verb = await s_stormtypes.tostr(self.opts.verb)

            if verb == '*':
                runt.layerConfirm(('node', 'edge', 'del'))
                verb = None
            else:
                runt.layerConfirm(('node', 'edge', 'del', verb))

            async for node, path in genr:
                await self.delEdges(node, verb, n2)
                yield node, path

        else:
            async for node, path in genr:
                n2 = self.opts.n2
                verb = await s_stormtypes.tostr(self.opts.verb)

                if verb == '*':
                    runt.layerConfirm(('node', 'edge', 'del'))
                    verb = None
                else:
                    runt.layerConfirm(('node', 'edge', 'del', verb))

                await self.delEdges(node, verb, n2)
                yield node, path

class OnceCmd(Cmd):
    '''
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
    '''
    name = 'once'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('name', type='str', help='Name of the action to only perform once.')
        pars.add_argument('--asof', default=None, type='time', help='The associated time the name was updated/performed.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for node, path in genr:

            tick = s_common.now()
            name = await s_stormtypes.tostr(self.opts.name)
            key = f'once:{name}'

            envl = await node.getData(key)

            if envl is not None:
                asof = self.opts.asof

                last = envl.get('tick')

                # edge case to account for old storage format
                if last is None:
                    await node.setData(key, {'tick': tick})

                if last is None or asof is None or last > asof:
                    await asyncio.sleep(0)
                    continue

            await node.setData(key, {'tick': tick})

            yield node, path

class TagPruneCmd(Cmd):
    '''
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
    '''
    name = 'tag.prune'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('tags', default=[], nargs='*', help='Names of tags to prune.')
        return pars

    def hasChildTags(self, node, tag):
        pref = tag + '.'
        for ntag in node.tags:
            if ntag.startswith(pref):
                return True
        return False

    async def execStormCmd(self, runt, genr):

        if self.runtsafe:
            tagargs = [await s_stormtypes.tostr(t) for t in self.opts.tags]

            tags = {}
            for tag in tagargs:
                root = tag.split('.')[0]
                runt.layerConfirm(('node', 'tag', 'del', root))
                tags[tag] = s_chop.tags(tag)[-2::-1]

            async for node, path in genr:
                for tag, parents in tags.items():
                    await node.delTag(tag)

                    for parent in parents:
                        if not self.hasChildTags(node, parent):
                            await node.delTag(parent)
                        else:
                            break

                yield node, path

        else:
            permcache = set([])

            async for node, path in genr:
                tagargs = [await s_stormtypes.tostr(t) for t in self.opts.tags]

                tags = {}
                for tag in tagargs:
                    root = tag.split('.')[0]
                    if root not in permcache:
                        runt.layerConfirm(('node', 'tag', 'del', root))
                        permcache.add(root)

                    tags[tag] = s_chop.tags(tag)[-2::-1]

                for tag, parents in tags.items():
                    await node.delTag(tag)

                    for parent in parents:
                        if not self.hasChildTags(node, parent):
                            await node.delTag(parent)
                        else:
                            break

                yield node, path

class RunAsCmd(Cmd):
    '''
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
    '''

    name = 'runas'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('user', help='The user name or iden to execute the storm query as.')
        pars.add_argument('storm', help='The storm query to execute.')
        pars.add_argument('--asroot', default=False, action='store_true', help='Propagate asroot to query subruntime.')

        return pars

    async def execStormCmd(self, runt, genr):

        if not runt.isAdmin():
            mesg = 'The runas command requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        core = runt.snap.core

        node = None
        async for node, path in genr:

            user = await s_stormtypes.tostr(self.opts.user)
            text = await s_stormtypes.tostr(self.opts.storm)

            user = await core.auth.reqUserByNameOrIden(user)
            query = await runt.getStormQuery(text)

            opts = {'vars': path.vars}

            async with await core.snap(user=user, view=runt.snap.view) as snap:
                async with await Runtime.anit(query, snap, user=user, opts=opts, root=runt) as subr:
                    subr.debug = runt.debug
                    subr.readonly = runt.readonly

                    if self.opts.asroot:
                        subr.asroot = runt.asroot

                    async for item in subr.execute():
                        await asyncio.sleep(0)

            yield node, path

        if node is None and self.runtsafe:
            user = await s_stormtypes.tostr(self.opts.user)
            text = await s_stormtypes.tostr(self.opts.storm)

            query = await runt.getStormQuery(text)
            user = await core.auth.reqUserByNameOrIden(user)

            opts = {'user': user}

            async with await core.snap(user=user, view=runt.snap.view) as snap:
                async with await Runtime.anit(query, snap, user=user, opts=opts, root=runt) as subr:
                    subr.debug = runt.debug
                    subr.readonly = runt.readonly

                    if self.opts.asroot:
                        subr.asroot = runt.asroot

                    async for item in subr.execute():
                        await asyncio.sleep(0)

class IntersectCmd(Cmd):
    '''
    Yield an intersection of the results of running inbound nodes through a pivot.

    NOTE:
        This command must consume the entire inbound stream to produce the intersection.
        This type of stream consuming before yielding results can cause the query to appear
        laggy in comparison with normal incremental stream operations.

    Examples:

        // Show the it:mitre:attack:technique nodes common to several groups

        it:mitre:attack:group*in=(G0006, G0007) | intersect { -> it:mitre:attack:technique }
    '''
    name = 'intersect'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('query', type='str', required=True, help='The pivot query to run each inbound node through.')

        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'intersect arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        core = self.runt.snap.core

        async with await s_spooled.Dict.anit(dirn=core.dirn, cell=core) as counters:
            async with await s_spooled.Dict.anit(dirn=core.dirn, cell=core) as pathvars:

                text = await s_stormtypes.tostr(self.opts.query)
                query = await runt.getStormQuery(text)

                # Note: The intersection works by counting the # of nodes inbound to the command.
                # For each node which is emitted from the pivot, we increment a counter, mapping
                # the buid -> count. We then iterate over the counter, and only yield nodes which
                # have a buid -> count equal to the # of inbound nodes we consumed.

                count = 0
                async for node, path in genr:
                    count += 1
                    await asyncio.sleep(0)
                    async with runt.getSubRuntime(query) as subr:
                        subg = s_common.agen((node, path))
                        async for subn, subp in subr.execute(genr=subg):
                            curv = counters.get(subn.buid)
                            if curv is None:
                                await counters.set(subn.buid, 1)
                            else:
                                await counters.set(subn.buid, curv + 1)
                            await pathvars.set(subn.buid, await s_stormtypes.toprim(subp.vars))
                            await asyncio.sleep(0)

                for buid, hits in counters.items():

                    if hits != count:
                        await asyncio.sleep(0)
                        continue

                    node = await runt.snap.getNodeByBuid(buid)
                    if node is not None:
                        path = runt.initPath(node)
                        path.vars.update(pathvars.get(buid))
                        yield (node, path)
