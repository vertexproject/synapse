import argparse
import functools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cli as s_cli
import synapse.lib.syntax as s_syntax
import synapse.lib.trigger as s_trigger

AddHelp = '''
Add triggers in a cortex.

Syntax: triggeradd condition <object> [#tag] query

Notes:
    Valid values for condition are:
        * tag:add
        * tag:del
        * node:add
        * node:del
        * prop:set

When condition is tag:add or tag:del, you may optionally provide a form name
to restrict the trigger firing on only tags added or deleted form nodes of
those forms.

Tag names must start with #.

The added tag is provided to the query as an embedded variable '$tag'.

Simple one level tag globbing is supported, only at the end after a period,
that is aka.* matches aka.foo and aka.bar but not aka.foo.bar.  aka* is not
supported.

Examples:
    # Adds a tag to ever inet:ipv4 added
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
    user       iden         cond      object                    storm query
    <None>     739719ff..   prop:set  testtype10.intprop            [ testint=6 ]
'''

DelHelp = '''
Delete an existing trigger.

Syntax:
    trigger del <iden prefix>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

ModHelp = '''
Modifies an existing trigger to change the query.

Syntax:
    trigger mod <iden prefix> <new query>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

class CmdArgParser(argparse.ArgumentParser):

    def __init__(self, print_target, **kwargs):
        self._print_target = print_target
        argparse.ArgumentParser.__init__(self, **kwargs)

    def exit(self, status=0, message=None):
        '''
        Argparse expects exit() to be a terminal function and not return.
        As such, this function must raise an exception
        '''
        if message is not None:
            self._print_target.printf(message)
        raise s_exc.BadSyntaxError(mesg=message, prog=self.prog, status=status)

    def _print_message(self, text, fd=None):
        '''
        Note:  this overrides an existing method in ArgumentParser
        '''
        self._print_target.printf(text)

class Trigger(s_cli.Cmd):
    '''
    Manipulate triggers in a cortex.  Triggers are rules persistently stored in
    a cortex such that storm queries automatically run when a particular event
    happens.

    A subcommand is required.
    '''
    _cmd_name = 'trigger'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),
    )

    async def _match_idens(self, core, prefix):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        idens = [iden for iden, trig in await core.listTriggers()]
        matches = [iden for iden in idens if s_common.ehex(iden).startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized triggers')
        else:
            self.printf('Error: provided iden matches more than one trigger')
        return None

    def _make_argparser(self):

        def print_message(text, fd=None):
            self.printf(text)

        def exit(status=0, message=None):
            if message is not None:
                self.printf(message)
            raise s_exc.BadSyntaxError(mesg=message, prog=self.prog, status=status)

        parser = CmdArgParser(self, prog='trigger', description=self.__doc__)
        parser._print_target = self

        subparsers = parser.add_subparsers(title='subcommands', required=True, dest='cmd',
                                           parser_class=functools.partial(CmdArgParser, self))

        subparsers.add_parser('list', help="List triggers you're allowed to manipulate", usage=ListHelp)

        parser_add = subparsers.add_parser('add', help='add a trigger', usage=AddHelp)
        parser_add.add_argument('condition', choices=s_trigger.Conditions, type=str.lower,
                                help='Condition on which to trigger')
        parser_add.add_argument('args', metavar='arguments', nargs='+', help='[form] [#tag] [prop] {query}')

        parser_del = subparsers.add_parser('del', help='delete a trigger', usage=DelHelp)
        parser_del.add_argument('prefix', help='Trigger iden prefix')

        parser_mod = subparsers.add_parser('mod', help='change an existing trigger query', usage=ModHelp)
        parser_mod.add_argument('prefix', help='Trigger iden prefix')
        parser_mod.add_argument('query', help='Storm query in curly braces')
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

        if cond.startswith('node') and form is None:
            self.printf('Missing form parameter')
            return

        if cond.startswith('prop') and prop is None:
            self.printf('Missing prop parameter')
            return

        # Remove the curly braces
        query = query[1:-1]

        await core.addTrigger(cond, query, info={'form': form, 'tag': tag, 'prop': prop})

    async def _handle_list(self, core, opts):
        triglist = await core.listTriggers()
        self.printf(f'{"user":10} {"iden":12} {"cond":9} {"object":14} {"":10} {"storm query"}')
        for iden, trig in triglist:
            idenf = s_common.ehex(iden)[:8] + '..'
            user = trig.get('user') or '<None>'
            query = trig.get('storm') or '<missing>'
            cond = trig.get('cond') or '<missing'
            if cond.startswith('tag:'):
                tag = '#' + (trig.get('tag') or '<missing>')
                form = trig.get('form') or ''
                obj, obj2 = form, tag
            else:
                obj, obj2 = trig.get('prop') or trig.get('form') or '<missing>', ''

            self.printf(f'{user:10} {idenf:12} {cond:9} {obj:14} {obj2:10} {query}')

    async def _handle_mod(self, core, opts):
        prefix = opts.prefix
        query = opts.query
        assert prefix
        if not query.startswith('{'):
            self.printf('Expected second argument to start with {')
            return
        # remove the curly braces
        query = query[1:-1]
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.updateTrigger(iden, query)
        self.printf(f'Modified trigger {s_common.ehex(iden)}')

    async def _handle_del(self, core, opts):
        prefix = opts.prefix
        assert prefix is not None
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.delTrigger(iden)
        self.printf(f'Deleted trigger {s_common.ehex(iden)}')

    async def runCmdOpts(self, opts):
        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        parseinfo = await s_syntax.getRemoteParseInfo(core)
        argv = s_syntax.Parser(parseinfo, line).stormcmd()
        try:
            opts = self._make_argparser().parse_args(argv)
        except s_exc.BadSyntaxError:
            return

        handlers = {
            'add': self._handle_add,
            'list': self._handle_list,
            'mod': self._handle_mod,
            'del': self._handle_del,
        }
        await handlers[opts.cmd](core, opts)
