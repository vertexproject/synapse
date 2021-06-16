import functools

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cli as s_cli
import synapse.lib.cmd as s_cmd
import synapse.lib.parser as s_parser
import synapse.lib.trigger as s_trigger

AddHelp = '''
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
'''

ListHelp = '''
List existing triggers in a cortex.

Syntax:
    trigger list

Example:
    cli> trigger list
    user       iden         en? cond      object                    storm query
    root       607e9d97..   Y   prop:set  test:type10.intprop            [test:int=6]

'''

DelHelp = '''
Delete an existing trigger.

Syntax:
    trigger del <iden prefix>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

ModHelp = '''
Changes an existing trigger's query.

Syntax:
    trigger mod <iden prefix> <new query>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

EnableHelp = '''
Enable an existing trigger.

Syntax:
    trigger enable <iden prefix>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

DisableHelp = '''
Disable an existing trigger.

Syntax:
    trigger disable <iden prefix>

Notes:
    Any prefix that matches exactly one valid trigger is accepted.
'''

class Trigger(s_cli.Cmd):
    '''
Manipulate triggers in a cortex.

Triggers are rules persistently stored in a cortex such that storm queries
automatically run when a particular event happens.

A subcommand is required.  Use `trigger -h` for more detailed help.
'''
    _cmd_name = 'trigger'

    _cmd_syntax = (('line', {'type': 'glob'}),)  # type: ignore

    async def _match_idens(self, core, prefix, view=None):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        triglist = await self._get_list(core, view)
        matches = [trig['iden'] for trig in triglist if trig['iden'].startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized triggers')
        else:
            self.printf('Error: provided iden matches more than one trigger')
        return None

    def _make_argparser(self):

        parser = s_cmd.Parser(prog='trigger', outp=self, description=self.__doc__)
        help = 'The iden of the view where the trigger is/will be applied.  Defaults to the cortex default view.'
        parser.add_argument('--view', type=str, default=None, help=help)

        subparsers = parser.add_subparsers(title='subcommands', required=True, dest='cmd',
                                           parser_class=functools.partial(s_cmd.Parser, outp=self))

        subparsers.add_parser('list', help="List triggers you're allowed to manipulate", usage=ListHelp)

        parser_add = subparsers.add_parser('add', help='add a trigger', usage=AddHelp)
        parser_add.add_argument('condition', choices=s_trigger.Conditions, type=str.lower,
                                help='Condition on which to trigger')
        parser_add.add_argument('--disabled', action='store_true', help='Create the trigger in disabled state')
        parser_add.add_argument('args', metavar='arguments', nargs='+', help='[form] [#tag] [prop] {query}')

        parser_del = subparsers.add_parser('del', help='delete a trigger', usage=DelHelp)
        parser_del.add_argument('prefix', help='Trigger iden prefix')

        parser_mod = subparsers.add_parser('mod', help='change an existing trigger query', usage=ModHelp)
        parser_mod.add_argument('prefix', help='Trigger iden prefix')
        parser_mod.add_argument('query', help='Storm query in curly braces')

        parser_en = subparsers.add_parser('enable', help='enable an existing trigger', usage=EnableHelp)
        parser_en.add_argument('prefix', help='trigger iden prefix')

        parser_dis = subparsers.add_parser('disable', help='disable an existing trigger', usage=DisableHelp)
        parser_dis.add_argument('prefix', help='trigger iden prefix')

        return parser

    async def _handle_add(self, core, opts):
        if len(opts.args) < 2:
            self.printf('Missing argument for trigger add')
            return
        form, tag, prop, query = None, None, None, None
        cond = opts.condition

        for arg in opts.args:
            if arg.startswith('#'):
                if tag is not None:
                    self.printf('Only a single tag is allowed')
                    return
                tag = arg[1:]
            elif arg.startswith('{'):
                if query is not None:
                    self.printf('Only a single query is allowed')
                    return
                query = arg
            else:
                if cond.startswith('prop'):
                    if prop is not None:
                        self.printf('Only a single prop is allowed')
                        return
                    prop = arg
                else:
                    if form is not None:
                        self.printf('Only a single form is allowed')
                        return
                    form = arg

        if query is None:
            self.printf('Missing query parameter')
            return

        if cond.startswith('tag') and tag is None:
            self.printf('Missing tag parameter')
            return

        elif cond.startswith('node'):
            if form is None:
                self.printf('Missing form parameter')
                return
            if tag is not None:
                self.printf('node:* does not support a tag')
                return

        elif cond.startswith('prop'):
            if prop is None:
                self.printf('Missing prop parameter')
                return
            if tag is not None:
                self.printf('prop:set does not support a tag')
                return

        # Remove the curly braces
        query = query[1:-1]

        tdef = {'cond': cond, 'storm': query}

        if form is not None:
            tdef['form'] = form

        if prop is not None:
            tdef['prop'] = prop

        if tag is not None:
            tdef['tag'] = tag

        opts = {'vars': {'tdef': tdef}, 'view': opts.view}

        iden = await core.callStorm('return($lib.trigger.add($tdef).iden)', opts=opts)

        self.printf(f'Added trigger {iden}')

    async def _get_list(self, core, view):
        opts = {'view': view}
        return await core.callStorm('return($lib.trigger.list())', opts=opts)

    async def _handle_list(self, core, opts):
        triglist = await self._get_list(core, opts.view)

        if not triglist:
            self.printf('No triggers found')
            return

        self.printf(f'{"user":10} {"iden":12} {"en?":3} {"cond":9} {"object":14} {"":10} {"storm query"}')

        for trig in triglist:
            iden = trig['iden']
            idenf = iden[:8] + '..'
            user = trig.get('username', '<None>')
            query = trig.get('storm', '<missing>')
            cond = trig.get('cond', '<missing')
            enabled = 'Y' if trig.get('enabled', True) else 'N'
            if cond.startswith('tag:'):
                tag = '#' + trig.get('tag', '<missing>')
                form = trig.get('form', '')
                obj, obj2 = form, tag
            else:
                obj = trig.get('prop', trig.get('form', '<missing>'))
                obj2 = ''

            self.printf(f'{user:10} {idenf:12} {enabled:3} {cond:9} {obj:14} {obj2:10} {query}')

    async def _handle_mod(self, core, opts):
        prefix = opts.prefix
        query = opts.query
        if not query.startswith('{'):
            self.printf('Expected second argument to start with {')
            return
        # remove the curly braces
        query = query[1:-1]
        iden = await self._match_idens(core, prefix, view=opts.view)
        if iden is None:
            return

        opts = {'vars': {'iden': iden, 'storm': query}, 'view': opts.view}
        await core.callStorm('$lib.trigger.get($iden).set(storm, $storm)', opts=opts)

        self.printf(f'Modified trigger {iden}')

    async def _handle_del(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix, view=opts.view)
        if iden is None:
            return

        opts = {'vars': {'iden': iden}, 'view': opts.view}
        await core.callStorm('$lib.trigger.del($iden)', opts=opts)

        self.printf(f'Deleted trigger {iden}')

    async def _handle_enable(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix, view=opts.view)
        if iden is None:
            return
        opts = {'vars': {'iden': iden}, 'view': opts.view}
        await core.callStorm('$lib.trigger.get($iden).set(enabled, $(1))', opts=opts)
        self.printf(f'Enabled trigger {iden}')

    async def _handle_disable(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix, view=opts.view)
        if iden is None:
            return
        opts = {'vars': {'iden': iden}, 'view': opts.view}
        await core.callStorm('$lib.trigger.get($iden).set(enabled, $(0))', opts=opts)
        self.printf(f'Disabled trigger {iden}')

    async def runCmdOpts(self, opts):

        s_common.deprecated('cmdr> trigger')

        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        argv = s_parser.Parser(line).cmdrargs()
        try:
            opts = self._make_argparser().parse_args(argv)
        except s_exc.ParserExit:
            return

        handlers = {
            'add': self._handle_add,
            'del': self._handle_del,
            'disable': self._handle_disable,
            'enable': self._handle_enable,
            'list': self._handle_list,
            'mod': self._handle_mod,
        }
        await handlers[opts.cmd](core, opts)
