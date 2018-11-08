import synapse.common as s_common
import synapse.lib.cli as s_cli
import synapse.lib.trigger as s_trigger

class TriggerList(s_cli.Cmd):
    '''
    List existing triggers in a cortex.

    Triggers are rules persistently stored in a cortex such that storm queries automatically run when a particular
    event happens.

    Syntax:
        trigger.list

    Example:
        trigger.list
        (FIXME example output)
    '''
    _cmd_name = 'trigger.list'

    _cmd_syntax = (
        ('condition', {'type': 'enum', 'enum:vals': s_trigger.Conditions}),
        ('first_parm', {'type': 'valu'}),
        ('rest', {'type': 'glob'}),
    )

    async def runCmdOpts(self, opts):

        core = self.getCmdItem()

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

class TriggerDel(s_cli.Cmd):
    '''
    Delete an existing trigger.

    Triggers are rules persistently stored in a cortex such that storm queries automatically run when a particular
    event happens.

    Syntax:
        trigger.del <iden prefix>

    Notes:
        Any prefix that matches exactly one valid trigger iden is accepted.
    '''
    _cmd_name = 'trigger.del'

    _cmd_syntax = (
        ('prefix', {'type': 'valu'}),
    )

    async def runCmdOpts(self, opts):
        prefix = opts.get('prefix')
        if prefix is None:
            self.printf(self.__doc__)
            return
        core = self.getCmdItem()
        iden = await _match_idens(self, core, prefix)
        if iden is None:
            return
        await core.delTrigger(iden)
        self.printf(f'Deleted trigger {s_common.ehex(iden)}')

class TriggerMod(s_cli.Cmd):
    '''
    Modifies an existing trigger to change the query.

    Syntax:
        trigger.mod <iden prefix> <new query>

    Notes:
        Any prefix that matches exactly one valid trigger iden is accepted.
    '''
    _cmd_name = 'trigger.mod'

    _cmd_syntax = (
        ('prefix', {'type': 'valu'}),
        ('query', {'type': 'glob'}),
    )

    async def runCmdOpts(self, opts):
        prefix = opts.get('prefix')
        query = opts.get('query')
        if prefix is None:
            self.printf(self.__doc__)
            return
        core = self.getCmdItem()
        iden = await _match_idens(self, core, prefix)
        if iden is None:
            return
        await core.updateTrigger(iden, query)
        self.printf(f'Modified trigger {s_common.ehex(iden)}')

class TriggerAdd(s_cli.Cmd):
    '''
    Add triggers in a cortex.

    Triggers are rules persistently stored in a cortex such that storm queries
    automatically run when a particular event happens.

    Syntax: trigger.add condition <object> [#tag] query

    Notes:
        Valid values for condition are:
            * tag:add
            * tag:del
            * node:add
            * node:del
            * prop:set

    When condition is tag:add or tag:del, you may optionally provide a form name
    to restrict the trigger firing on only tags added or deleted from nodes of
    those forms.

    The added tag is provided to the query as an embedded variable '$tag'.

    Simple one level tag globbing is supported, only at the end after a period,
    that is aka.* matches aka.foo and aka.bar but not aka.foo.bar.  aka* is not
    supported.

    Examples:
        # Adds a tag #todo to every node as it is tagged #aka
        trigger.add tag:add #aka [ +#todo ]

        # Adds a tag #todo to every inet:ipv4 as it is tagged #aka
        trigger.add tag:add inet:ipv4 #aka [ +#todo ]
    '''
    _cmd_name = 'trigger.add'

    _cmd_syntax = (
        ('condition', {'type': 'enum', 'enum:vals': s_trigger.Conditions}),
        ('first_parm', {'type': 'valu'}),
        ('rest', {'type': 'glob'}),
    )

    async def runCmdOpts(self, opts):
        rest = opts.get('rest')
        cond = opts.get('condition')
        parm1 = opts.get('first_parm')
        if rest is None or cond is None or parm1 is None:
            self.printf(self.__doc__)
            return

        cond = cond.lower()

        if cond not in s_trigger.Conditions:
            self.printf('Unrecognized condition')
            return

        form, tag, prop, query = None, None, None, rest

        if cond.startswith('tag'):
            if rest.startswith('#'):
                form = parm1
                try:
                    tag, query = rest[1:].split(maxsplit=1)
                except ValueError:
                    self.printf('Missing query')
                    return
            else:
                if parm1[0] != '#':
                    self.printf('Expected tag starting with #')
                    return
                tag = parm1[1:]
                query = rest

        elif cond.startswith('node'):
            form = parm1
        else:
            prop = parm1

        core = self.getCmdItem()

        await core.addTrigger(cond, query, info={'form': form, 'tag': tag, 'prop': prop})
