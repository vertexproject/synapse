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
import synapse.lib.base as s_base
import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.scrape as s_scrape
import synapse.lib.grammar as s_grammar
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled
import synapse.lib.version as s_version
import synapse.lib.stormctrl as s_stormctrl
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

wgetdescr = '''Retrieve bytes from a URL and store them in the axon. Yields inet:urlfile nodes.

Examples:

    # Specify custom headers and parameters
    inet:fqdn=vertex.link | wget --headers $lib.dict("User-Agent"="Foo/Bar") --params $lib.dict("clientid"="42")

    # Download multiple URL targets without inbound nodes
    wget https://vertex.link https://vtx.lk
'''

reqValidPkgdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'version': {
            'type': 'string',
            'pattern': s_version.semverstr,
        },
        'synapse_minversion': {
            'type': ['array', 'null'],
            'items': {'type': 'number'}
        },
        'modules': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/module'}
        },
        'docs': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/doc'},
        },
        'logo': {
            'type': 'object',
            'properties': {
                'mime': {'type': 'string'},
                'file': {'type': 'string'},
            },
            'additionalProperties': True,
            'required': ['mime', 'file'],
        },
        'commands': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/command'},
        },
        'desc': {'type': 'string'},
        'svciden': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'onload': {'type': 'string'},
        'author': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'name': {'type': 'string'},
            },
            'required': ['name', 'url'],
        },
        'depends': {
            'properties': {
                'requires': {'type': 'array', 'items': {'$ref': '#/definitions/require'}},
                'conflicts': {'type': 'array', 'items': {'$ref': '#/definitions/conflict'}},
            },
            'additionalProperties': True,
        },
        'perms': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'perm': {'type': 'array', 'items': {'type': 'string'}},
                    'desc': {'type': 'string'},
                    'gate': {'type': 'string'},
                },
                'required': ['perm', 'desc', 'gate'],
            },
        },
    },
    'additionalProperties': True,
    'required': ['name', 'version'],
    'definitions': {
        'doc': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'},
            },
            'additionalProperties': True,
            'required': ['title', 'content'],
        },
        'module': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'storm': {'type': 'string'},
                'modconf': {'type': 'object'},
                'asroot': {'type': 'boolean'},
                'asroot:perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
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
                'cmdargs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdarg'},
                },
                'cmdinputs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdinput'},
                },
                'storm': {'type': 'string'},
                'forms': {'$ref': '#/definitions/cmdformhints'},
                'perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
            },
            'additionalProperties': True,
            'required': ['name', 'storm']
        },
        'cmdarg': {
            'type': 'array',
            'items': [
                {'type': 'string'},
                {
                    'type': 'object',
                    'properties': {
                        'help': {'type': 'string'},
                        'default': {},
                        'dest': {'type': 'string'},
                        'required': {'type': 'boolean'},
                        'action': {'type': 'string'},
                        'nargs': {'type': ['string', 'integer']},
                        'type': {
                            'type': 'string',
                            'enum': list(s_datamodel.Model().types)
                        },
                    },
                }
            ],
            'additionalItems': False,
        },
        'cmdinput': {
            'type': 'object',
            'properties': {
                'form': {'type': 'string'},
                'help': {'type': 'string'},
            },
            'additionalProperties': True,
            'required': ['form'],
        },
        # deprecated
        'cmdformhints': {
            'type': 'object',
            'properties': {
                'input': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'string',
                    }
                },
                'output': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'string',
                    }
                },
                'nodedata': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'array',
                        'items': [
                            {'type': 'string'},
                            {'type': 'string'},
                        ],
                        'additionalItems': False,
                    },
                },
            }
        },
        'require': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'},
            },
            'additionalItems': True,
            'required': ('name', 'version'),
        },
        'conflict': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'},
            },
            'additionalItems': True,
            'required': ('name',),
        },
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
        'name': 'pkg.perms.list',
        'descr': 'List any permissions declared by the package.',
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
                if $pdef.perms {
                    $lib.print("Package ({name}) defines the following permissions:", name=$cmdopts.name)
                    for $permdef in $pdef.perms {
                        $permtext = $lib.str.join('.', $permdef.perm).ljust(32)
                        $lib.print("{permtext} : {desc}", permtext=$permtext, desc=$permdef.desc)
                    }
                } else {
                    $lib.print("Package ({name}) contains no permissions definitions.", name=$cmdopts.name)
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
            ('--ssl-noverify', {'default': False, 'action': 'store_true',
                'help': 'Specify to disable SSL verification of the server.'}),
        ),
        'storm': '''
            init {
                $ssl = $lib.true
                if $cmdopts.ssl_noverify { $ssl = $lib.false }

                $resp = $lib.inet.http.get($cmdopts.url, ssl_verify=$ssl)

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

                $pkg.url = $cmdopts.url
                $pkg.loaded = $lib.time.now()

                $pkd = $lib.pkg.add($pkg)

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
            } else {
                $view.wipeLayer()
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
            ('--query', {'help': 'Query for the trigger to execute.', 'required': True,
                         'dest': 'storm', }),
            ('--async', {'default': False, 'action': 'store_true',
                         'help': 'Make the trigger run in the background.'}),
            ('--disabled', {'default': False, 'action': 'store_true',
                            'help': 'Create the trigger in disabled state.'}),
            ('--name', {'help': 'Human friendly name of the trigger.'}),
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
        'cmdargs': (),
        'storm': '''
            $triggers = $lib.trigger.list()

            if $triggers {

                $lib.print("user       iden                             en?    async? cond      object                    storm query")

                for $trigger in $triggers {
                    $user = $trigger.username.ljust(10)
                    $iden = $trigger.iden.ljust(12)
                    $async = $lib.model.type(bool).repr($trigger.async).ljust(6)
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

                    $lib.print("{user} {iden} {enabled} {async} {cond} {obj} {obj2} {query}",
                              user=$user, iden=$iden, enabled=$enabled, async=$async, cond=$cond,
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
            ('view', {'help': 'New storm query for the cron job.'}),
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
            $crons = $lib.cron.list()

            if $crons {
                $lib.print("user       iden       view       en? rpt? now? err? # start last start       last end         query")

                for $cron in $crons {

                    $job = $cron.pprint()

                    $user = $job.user.ljust(10)
                    $view = $job.viewshort.ljust(10)
                    $iden = $job.idenshort.ljust(10)
                    $enabled = $job.enabled.ljust(3)
                    $isrecur = $job.isrecur.ljust(4)
                    $isrunning = $job.isrunning.ljust(4)
                    $iserr = $job.iserr.ljust(4)
                    $startcount = $lib.str.format("{startcount}", startcount=$job.startcount).ljust(7)
                    $laststart = $job.laststart.ljust(16)
                    $lastend = $job.lastend.ljust(16)

       $lib.print("{user} {iden} {view} {enabled} {isrecur} {isrunning} {iserr} {startcount} {laststart} {lastend} {query}",
                               user=$user, iden=$iden, view=$view, enabled=$enabled, isrecur=$isrecur,
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
                    $nodes = $lib.list()
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
        ),
        'storm': '''
            function addNoteNode(text) {
                [ meta:note=* :text=$text :creator=$lib.user.iden :created=now ]
                return($node)
            }
            init { $note = $addNoteNode($cmdopts.text) }
            [ <(about)+ { yield $note } ]
        ''',
    },
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

        s_scope.set('storm:dmon', self.iden)

        info = {'iden': self.iden, 'name': self.ddef.get('name', 'storm dmon')}
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

            text = self.ddef.get('storm')
            opts = self.ddef.get('stormopts', {})
            vars = opts.setdefault('vars', {})
            vars.setdefault('auto', {'iden': self.iden, 'type': 'dmon'})

            viewiden = opts.get('view')
            view = self.core.getView(viewiden)
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

        # declare path builtins as non-runtsafe
        self.runtvars = {
            'node': False,
            'path': False,
        }

        # inherit runtsafe vars from our root
        if self.root is not None:
            self.runtvars.update(root.runtvars)

        # all vars/ctors are de-facto runtsafe
        self.runtvars.update({k: True for k in self.vars.keys()})
        self.runtvars.update({k: True for k in self.ctors.keys()})

        self.proxies = {}

        self._loadRuntVars(query)
        self.onfini(self._onRuntFini)

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
                        continue

                    if not ok and item is None:
                        return

                    raise item

        return genr()

    async def emit(self, item):
        await self.emitq.put((True, item))

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

        mesg = 'User can not read layer.'
        raise s_exc.AuthDeny(mesg=mesg)

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

    def tick(self):
        pass

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

    def confirm(self, perms, gateiden=None, default=False):
        '''
        Raise AuthDeny if user doesn't have global permissions and write layer permissions
        '''
        if self.asroot:
            return
        return self.user.confirm(perms, gateiden=gateiden, default=default)

    def allowed(self, perms, gateiden=None, default=False):
        if self.asroot:
            return True
        return self.user.allowed(perms, gateiden=gateiden, default=default)

    def _loadRuntVars(self, query):
        # do a quick pass to determine which vars are per-node.
        for oper in query.kids:
            for name, isrunt in oper.getRuntVars(self):
                # once runtsafe, always runtsafe
                if self.runtvars.get(name):
                    continue
                self.runtvars[name] = isrunt

    async def execute(self, genr=None):
        with s_provenance.claim('storm', q=self.query.text, user=self.user.iden):
            async for item in self.query.iterNodePaths(self, genr=genr):
                self.tick()
                yield item

    async def _snapFromOpts(self, opts):

        snap = self.snap

        if opts is not None:

            viewiden = opts.get('view')
            if viewiden is not None:

                view = snap.core.views.get(viewiden)
                if view is None:
                    raise s_exc.NoSuchView(iden=viewiden)

                self.user.confirm(('view', 'read'), gateiden=viewiden)
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

        self.inputs = None

        self.reqopts = []

        self.add_argument('--help', '-h', action='store_true', default=False, help='Display the command usage.')

    def set_inputs(self, idefs):
        self.inputs = list(idefs)

    def add_argument(self, *names, **opts):

        assert len(names)

        argtype = opts.get('type')
        if argtype is not None and argtype not in s_datamodel.Model().types:
            mesg = f'Argument type "{argtype}" is not a valid model type name'
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
                    valu = s_datamodel.Model().type(argtype).norm(valu)[0]
                except Exception:
                    mesg = f'Invalid value for type ({argtype}): {valu}'
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
                        valu = s_datamodel.Model().type(argtype).norm(valu)[0]
                    except Exception:
                        mesg = f'Invalid value for type ({argtype}): {valu}'
                        return self.help(mesg=mesg)

                opts[dest] = valu

            return True

        if nargs in ('*', '+'):

            while todo and not self._is_opt(todo[0]):

                valu = todo.popleft()

                if argtype is not None:
                    try:
                        valu = s_datamodel.Model().type(argtype).norm(valu)[0]
                    except Exception:
                        mesg = f'Invalid value for type ({argtype}): {valu}'
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
                    valu = s_datamodel.Model().type(argtype).norm(valu)[0]
                except Exception:
                    mesg = f'Invalid value for type ({argtype}): {valu}'
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
        helpstr = argdef.get('help', 'No help available.')
        defval = argdef.get('default', s_common.novalu)
        if defval is not s_common.novalu and oact not in ('store_true', 'store_false'):
            if isinstance(defval, (tuple, list, dict)):
                defval = pprint.pformat(defval, indent=34, width=100)
                if '\n' in defval:
                    defval = '\n' + defval
            helpstr = f'{helpstr} (default: {defval})'
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
        return Parser(prog=self.getName(), descr=self.getDescr())

    async def setArgv(self, argv):

        self.argv = argv

        try:
            self.opts = self.pars.parse_args(self.argv)
        except s_exc.BadSyntax:  # pragma: no cover
            pass

        for line in self.pars.mesgs:
            await self.runt.snap.printf(line)

        return not self.pars.exited

    async def execStormCmd(self, runt, genr):  # pragma: no cover
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

        return pars

    async def execStormCmd(self, runt, genr):

        name = self.getName()
        perm = ('storm', 'asroot', 'cmd') + tuple(name.split('.'))

        asroot = runt.allowed(perm)
        if self.asroot and not asroot:
            mesg = f'Command ({name}) elevates privileges.  You need perm: storm.asroot.cmd.{name}'
            raise s_exc.AuthDeny(mesg=mesg)

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
                raise s_exc.AuthDeny(mesg=mesg)

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

        if self.runtsafe:

            if not isinstance(self.opts.genr, types.AsyncGeneratorType):
                raise s_exc.BadArg(mesg='The genr argument must yield nodes')

            size = await s_stormtypes.toint(self.opts.size, noneok=True)
            doyield = await s_stormtypes.tobool(self.opts.cond)

            try:
                count = 0
                if doyield:

                    # in a runtsafe yield case we drop all the nodes
                    async for item in genr:
                        await asyncio.sleep(0)

                    async for item in self.opts.genr:
                        yield item
                        count += 1
                        if size is not None and count >= size:
                            return
                else:

                    # in a runtsafe non-yield case we pass nodes through
                    async for origitem in genr:
                        yield origitem

                    async for item in self.opts.genr:
                        await asyncio.sleep(0)
                        count += 1
                        if size is not None and count >= size:
                            return
            finally:
                await self.opts.genr.aclose()

            return

        # non-runtsafe
        async for item in genr:

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

                    yield item
            finally:
                await self.opts.genr.aclose()

class HelpCmd(Cmd):
    '''
    List available commands and a brief description for each.

    Examples:

        // Get all available commands and their brief descriptions.

        help

        // Only get commands which have "model" in the name.

        help model
    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('command', nargs='?',
                          help='Only list commands and their brief description whose name contains the argument.')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'help does not support per-node invocation'
            raise s_exc.StormRuntimeError(mesg=mesg)

        async for item in genr:
            yield item

        stormcmds = sorted(runt.snap.core.getStormCmds())

        if self.opts.command:
            stormcmds = [c for c in stormcmds if self.opts.command in c[0]]
            if not stormcmds:
                await runt.printf(f'No commands found matching "{self.opts.command}"')
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

class DiffCmd(Cmd):
    '''
    Generate a list of nodes with changes in the top layer of the current view.
    '''
    name = 'diff'

    async def execStormCmd(self, runt, genr):

        if runt.snap.view.parent is None:
            mesg = 'You may only generate a diff in a forked view.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        async for item in genr:
            yield item

        async for buid, sode in runt.snap.view.layers[0].getStorNodes():
            node = await runt.snap.getNodeByBuid(buid)
            yield node, runt.initPath(node)

class MergeCmd(Cmd):
    '''
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

        // Merge ou:org nodes, but when merging tags, only merge tags one level
        // below the rep.vt and rep.whoxy tags.

        ou:org | merge --include-tags rep.vt.* rep.whoxy.* --apply

        // Only merge tags, and exclude any tags in the cno tag tree.

        ou:org | merge --only-tags --exclude-tags cno.** --apply

    '''
    name = 'merge'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--apply', default=False, action='store_true',
                          help='Execute the merge changes.')
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

            def propfilter(prop):
                if prop in self.opts.include_props:
                    return False
                return True

            return propfilter

        if self.opts.exclude_props:

            def propfilter(prop):
                if prop in self.opts.exclude_props:
                    return True
                return False

            return propfilter

        return None

    async def execStormCmd(self, runt, genr):

        if runt.snap.view.parent is None:
            mesg = 'You may only merge nodes in forked views'
            raise s_exc.CantMergeView(mesg=mesg)

        notags = self.opts.no_tags
        onlytags = self.opts.only_tags

        tagfilter = self._getTagFilter()
        propfilter = self._getPropFilter()

        layr0 = runt.snap.view.layers[0].iden
        layr1 = runt.snap.view.layers[1].iden

        if self.opts.diff:

            async for node, path in genr:
                yield node, path

            async def diffgenr():
                async for buid, sode in runt.snap.view.layers[0].getStorNodes():
                    node = await runt.snap.getNodeByBuid(buid)
                    yield node, runt.initPath(node)

            genr = diffgenr()

        async for node, path in genr:

            # the timestamp for the adds/subs of each node merge will match
            nodeiden = node.iden()
            meta = {'user': runt.user.iden, 'time': s_common.now()}

            sodes = await node.getStorNodes()
            sode = sodes[0]

            adds = []
            subs = []

            async def sync():

                if not self.opts.apply:
                    adds.clear()
                    subs.clear()
                    return

                if adds:
                    addedits = [(node.buid, node.form.name, adds)]
                    await runt.snap.view.parent.storNodeEdits(addedits, meta=meta)
                    adds.clear()

                if subs:
                    subedits = [(node.buid, node.form.name, subs)]
                    await runt.snap.view.storNodeEdits(subedits, meta=meta)
                    subs.clear()

            # check all node perms first
            form = sode.get('form')
            if form == 'syn:tag':
                if notags:
                    continue
            else:
                # avoid merging a tag if the node won't exist below us
                if onlytags:
                    for undr in sodes[1:]:
                        if undr.get('valu') is not None:
                            break
                    else:
                        continue

            if not onlytags or form == 'syn:tag':
                valu = sode.get('valu')
                if valu is not None:

                    if tagfilter and form == 'syn:tag' and tagfilter(valu[0]):
                        continue

                    if not self.opts.apply:
                        valurepr = node.form.type.repr(valu[0])
                        await runt.printf(f'{nodeiden} {form} = {valurepr}')
                    else:
                        runt.confirm(('node', 'del', form), gateiden=layr0)
                        runt.confirm(('node', 'add', form), gateiden=layr1)

                        adds.append((s_layer.EDIT_NODE_ADD, valu, ()))
                        subs.append((s_layer.EDIT_NODE_DEL, valu, ()))

                for name, (valu, stortype) in sode.get('props', {}).items():

                    full = node.form.prop(name).full
                    if propfilter:
                        if name[0] == '.':
                            if propfilter(name):
                                continue
                        else:
                            if propfilter(full):
                                continue

                    if not self.opts.apply:
                        valurepr = node.form.prop(name).type.repr(valu)
                        await runt.printf(f'{nodeiden} {form}:{name} = {valurepr}')
                    else:
                        runt.confirm(('node', 'prop', 'del', full), gateiden=layr0)
                        runt.confirm(('node', 'prop', 'set', full), gateiden=layr1)

                        adds.append((s_layer.EDIT_PROP_SET, (name, valu, None, stortype), ()))
                        subs.append((s_layer.EDIT_PROP_DEL, (name, valu, stortype), ()))

            if not notags:
                for tag, valu in sode.get('tags', {}).items():

                    if tagfilter and tagfilter(tag):
                        continue

                    tagperm = tuple(tag.split('.'))
                    if not self.opts.apply:
                        valurepr = ''
                        if valu != (None, None):
                            tagrepr = runt.model.type('ival').repr(valu)
                            valurepr = f' = {tagrepr}'
                        await runt.printf(f'{nodeiden} {form}#{tag}{valurepr}')
                    else:
                        runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr0)
                        runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=layr1)

                        adds.append((s_layer.EDIT_TAG_SET, (tag, valu, None), ()))
                        subs.append((s_layer.EDIT_TAG_DEL, (tag, valu), ()))

                for tag, tagdict in sode.get('tagprops', {}).items():

                    if tagfilter and tagfilter(tag):
                        continue

                    for prop, (valu, stortype) in tagdict.items():
                        tagperm = tuple(tag.split('.'))
                        if not self.opts.apply:
                            valurepr = repr(valu)
                            await runt.printf(f'{nodeiden} {form}#{tag}:{prop} = {valurepr}')
                        else:
                            runt.confirm(('node', 'tag', 'del') + tagperm, gateiden=layr0)
                            runt.confirm(('node', 'tag', 'add') + tagperm, gateiden=layr1)

                            adds.append((s_layer.EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype), ()))
                            subs.append((s_layer.EDIT_TAGPROP_DEL, (tag, prop, valu, stortype), ()))

            if not onlytags or form == 'syn:tag':

                layr = runt.snap.view.layers[0]
                async for name, valu in layr.iterNodeData(node.buid):
                    if not self.opts.apply:
                        valurepr = repr(valu)
                        await runt.printf(f'{nodeiden} {form} DATA {name} = {valurepr}')
                    else:
                        runt.confirm(('node', 'data', 'pop', name), gateiden=layr0)
                        runt.confirm(('node', 'data', 'set', name), gateiden=layr1)

                        adds.append((s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()))
                        subs.append((s_layer.EDIT_NODEDATA_DEL, (name, valu), ()))
                        if len(adds) >= 1000:
                            await sync()

                async for edge in layr.iterNodeEdgesN1(node.buid):
                    verb = edge[0]
                    if not self.opts.apply:
                        name, dest = edge
                        await runt.printf(f'{nodeiden} {form} +({name})> {dest}')
                    else:
                        runt.confirm(('node', 'edge', 'del', verb), gateiden=layr0)
                        runt.confirm(('node', 'edge', 'add', verb), gateiden=layr1)

                        adds.append((s_layer.EDIT_EDGE_ADD, edge, ()))
                        subs.append((s_layer.EDIT_EDGE_DEL, edge, ()))
                        if len(adds) >= 1000:
                            await sync()

            await sync()

            # TODO API to clear one node from the snap cache?
            runt.snap.livenodes.pop(node.buid, None)
            yield await runt.snap.getNodeByBuid(node.buid), path

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

    Examples:

        #badstuff +inet:ipv4 ->* | uniq

    '''

    name = 'uniq'
    readonly = True

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
    readonly = True

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
    readonly = True

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

        async for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.layerConfirm(('node', 'tag', 'del', *tag.split('.')))

            runt.layerConfirm(('node', 'del', node.form.name))

            await node.delete(force=self.opts.force)

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
    which were lifted. This does yield the nodes counted.

    Example:

        foo:bar:size=20 | count

    '''
    name = 'count'
    readonly = True

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

    NOTE: Variables are passed through but nodes are not

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
                'opts': opts,
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

        runtprims = await s_stormtypes.toprim(self.runt.vars)
        runtvars = {k: v for (k, v) in runtprims.items() if s_msgpack.isok(v)}

        opts = {
            'user': runt.user.iden,
            'view': runt.snap.view.iden,
            'vars': runtvars,
        }

        _query = await s_stormtypes.tostr(self.opts.query)
        query = await runt.getStormQuery(_query)

        # make sure the subquery *could* have run with existing vars
        query.validate(runt)

        coro = self.execStormTask(query, opts)
        runt.snap.core.schedCoro(coro)

class ParallelCmd(Cmd):
    '''
    Execute part of a query pipeline in parallel.
    This can be useful to minimize round-trip delay during enrichments.

    Examples:
        inet:ipv4#foo | parallel { $place = $lib.import(foobar).lookup(:latlong) [ :place=$place ] }

    NOTE: Storm variables set within the parallel query pipelines do not interact.
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

    async def pipeline(self, runt, query, inq, outq):
        try:
            async with runt.getSubRuntime(query) as subr:
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
        query = await runt.getStormQuery(self.opts.query)

        query.validate(runt)

        async with await s_base.Base.anit() as base:

            inq = asyncio.Queue(maxsize=size)
            outq = asyncio.Queue(maxsize=size)

            async def pump():
                try:
                    async for pumpitem in genr:
                        await inq.put(pumpitem)
                    [await inq.put(None) for i in range(size)]
                except asyncio.CancelledError:  # pragma: no cover
                    raise
                except Exception as e:
                    await outq.put(e)

            base.schedCoro(pump())
            for i in range(size):
                base.schedCoro(self.pipeline(runt, query, inq, outq))

            exited = 0
            while True:

                item = await outq.get()
                if isinstance(item, Exception):
                    raise item

                if item is None:
                    exited += 1
                    if exited == size:
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
                        subg = s_common.agen((node, path.fork(node)))
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
                        subg = s_common.agen((node, path.fork(node)))
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

        except asyncio.CancelledError:  # pragma: no cover
            raise

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

        text = self.opts.query

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

        # Scrape properties inbound nodes and yield newly scraped nodes.
        inet:search:query | scrape --yield

        # Skip re-fanging text before scraping.
        inet:search:query | scrape --skiprefang
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
                    for form, valu in s_scrape.scrape(text, refang=self.opts.dorefang):
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

                for form, valu in s_scrape.scrape(text, refang=self.opts.dorefang):

                    try:
                        nnode = await node.snap.addNode(form, valu)
                        npath = path.fork(nnode)

                        if refs:
                            if node.form.isrunt:
                                mesg = f'Edges cannot be used with runt nodes: {node.form.full}'
                                await runt.warn(mesg)
                            else:
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
    readonly = True

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--maxtimestamp', type='int', default=None,
                          help='Only yield splices which occurred on or before this timestamp.')
        pars.add_argument('--mintimestamp', type='int', default=None,
                          help='Only yield splices which occurred on or after this timestamp.')
        pars.add_argument('--maxtime', type='str', default=None,
                          help='Only yield splices which occurred on or before this time.')
        pars.add_argument('--mintime', type='str', default=None,
                          help='Only yield splices which occurred on or after this time.')

        return pars

    async def execStormCmd(self, runt, genr):

        s_common.deprecated('splices.list')
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
            if prop is None:  # pragma: no cover
                mesg = f'No property named {name}.'
                raise s_exc.NoSuchProp(mesg=mesg, name=name, form=node.form.name)

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
            if prop is None:  # pragma: no cover
                mesg = f'No property named {name}.'
                raise s_exc.NoSuchProp(mesg=mesg, name=name, form=node.form.name)

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

        s_common.deprecated('splices.undo')
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

        async with await s_spooled.Set.anit(dirn=self.runt.snap.core.dirn) as idenset:

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

                    async for node in self.iterEdgeNodes(verb, idenset, n2):
                        yield node, _path.fork(node)

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
    The once command ensures that a node makes it through the once command but a single time,
    even across independent queries. The gating is keyed by a required name parameter to
    the once command, so a node can be run through different queries, each a single time, so
    long as the names differ.

    For example, to run an enrichment command on a set of nodes just once:

        file:bytes#my.files | once enrich:foo | enrich.foo

    If you insert the once command with the same name on the same nodes, they will be
    dropped from the pipeline. So in the above example, if we run it again, the enrichment
    will not run a second time, as all the nodes will be dropped from the pipeline before
    reaching the enrich.foo portion of the pipeline.

    Simlarly, running this:

        file:bytes#my.files | once enrich:foo

    Also yields no nodes. And even though the rest of the pipeline is different, this query:

        file:bytes#my.files | once enrich:foo | enrich.bar

    would not run the enrich.bar command, as the name "enrich:foo" has already been seen to
    occur on the file:bytes passing through the once command, so all of the nodes will be
    dropped from the pipeline.

    However, this query:

        file:bytes#my.files | once look:at:my:nodes

    Would yield all the file:bytes tagged with #my.files, as the name parameter given to
    the once command differs from the original "enrich:foo".

    The once command utilizes a node's nodedata cache, and you can use the --asof parameter
    to update the named action's timestamp in order to bypass/update the once timestamp. So
    this command:

        inet:ipv4#my.addresses | once node:enrich --asof now | my.enrich.command

    Will yield all the enriched nodes the first time around. The second time that command is
    run, all of those nodes will be re-enriched, as the asof timestamp will be greater the
    second time around, so no nodes will be dropped.

    As state tracking data for the once command is stored as nodedata, it is stored in your
    view's write layer, making it view-specific. So if you have two views, A and B, and they
    do not share any layers between them, and you execute this query in view A:

        inet:ipv4=8.8.8.8 | once enrich:address | enrich.baz

    And then you run it in view B, the node will still pass through the once command to the
    enrich.baz portion of the pipeline, as the nodedata for the once command does not yet
    exist in view B.
    '''
    name = 'once'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('name', type='str', help='Name of the action to only perform once.')
        pars.add_argument('--asof', default=None, type='time', help='The associated time the name was updated/performed.')
        return pars

    async def execStormCmd(self, runt, genr):
        async for node, path in genr:
            name = await s_stormtypes.tostr(self.opts.name)
            key = f'once:{name}'
            envl = await node.getData(key)
            if not envl:
                if self.opts.asof:
                    envl = {'asof': self.opts.asof}
                else:
                    envl = {'asof': s_common.now()}
                await node.setData(key, envl)
                yield node, path
            else:
                ts = envl.get('asof')
                if not ts:
                    envl['asof'] = s_common.now()
                    await node.setData(key, envl)
                    yield node, path
                else:
                    norm = self.opts.asof
                    if norm and norm > ts:
                        envl['asof'] = norm
                        await node.setData(key, envl)
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
        if not runt.user.isAdmin():
            mesg = 'The runas command requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

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

        async with await s_spooled.Dict.anit(dirn=self.runt.snap.core.dirn) as counters:
            async with await s_spooled.Dict.anit(dirn=self.runt.snap.core.dirn) as pathvars:

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
