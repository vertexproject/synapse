import binascii
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
        self.printf(f'{"user":10} {"buid":12} {"cond":9} {"object":14} {"":10} {"storm query"}')
        for buid, trig in triglist:
            buidf = binascii.hexlify(buid)[:8].decode() + '..'
            user = trig.get('user') or '<None>'
            query = trig.get('storm') or '<missing>'
            cond = trig.get('cond') or '<missing'
            if cond.startswith('tag:'):
                tag = '#' + (trig.get('tag') or '<missing>')
                form = trig.get('form')
                if form is None:
                    obj, obj2 = tag, ''
                else:
                    obj, obj2 = form, tag
            else:
                obj, obj2 = trig.get('prop') or trig.get('form') or '<missing>', ''

            self.printf(f'{user:10} {buidf:12} {cond:9} {obj:14} {obj2:10} {query}')

async def _match_buids(self, core, prefix):
    '''
    Returns the buid that starts with prefix.  Prints out error and returns None if it doesn't match
    exactly one.
    '''
    prefix = prefix.encode()
    buids = [buid for buid, trig in await core.listTriggers()]
    matches = [buid for buid in buids if binascii.hexlify(buid).startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        self.printf('Error: provided buid does not match any valid authorized triggers')
    else:
        self.printf('Error: provided buid matches more than one trigger')
    return None

class TriggerDel(s_cli.Cmd):
    '''
    Delete an existing trigger.

    Triggers are rules persistently stored in a cortex such that storm queries automatically run when a particular
    event happens.

    Syntax:
        trigger.del <buid prefix>

    Notes:
        Any prefix that matches exactly one valid trigger buid is accepted.
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
        buid = await _match_buids(self, core, prefix)
        if buid is None:
            return
        await core.delTrigger(buid)
        self.printf(f'Deleted trigger {binascii.hexlify(buid).decode()}')

class TriggerMod(s_cli.Cmd):
    '''
    Modifies an existing trigger to change the query.

    Syntax:
        trigger.mod <buid prefix> <new query>

    Notes:
        Any prefix that matches exactly one valid trigger buid is accepted.
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
        buid = await _match_buids(self, core, prefix)
        if buid is None:
            return
        await core.updateTrigger(buid, query)
        self.printf(f'Modified trigger {binascii.hexlify(buid).decode()}')

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
                tag, query = rest[1:].split(maxsplit=1)
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

        await core.addTrigger(cond, query, form=form, tag=tag, prop=prop)
