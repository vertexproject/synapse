import pprint

import synapse.reactor as s_reactor

import synapse.lib.cli as s_cli

class StormCmd(s_cli.Cmd):
    '''
    Execute a storm query.

    Syntax:
        storm <query>

    Arguments:
        query: The storm query

    Optional Arguments:
        --hide-tags: Do not print tags
        --hide-props: Do not print secondary properties
        --raw: Print the nodes in their raw format
            (overrides --hide-tags and --hide-props)
        --debug: Display cmd debug information along with nodes in raw format
            (overrides --hide-tags, --hide-props and raw)

    Examples:
        storm inet:ipv4=1.2.3.4
        storm --debug inet:ipv4=1.2.3.4
    '''

    _cmd_name = 'storm'
    _cmd_syntax = (
        ('--hide-tags', {}),
        ('--hide-props', {}),
        ('--raw', {}),
        ('--debug', {}),
        ('query', {'type': 'glob'}),
    )

    def runCmdOpts(self, opts):

        text = opts.get('query')
        if text is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()
        stormopts = {'repr': True}
        self.printf('')

        for mesg in core.storm(text, opts=stormopts):

            if opts.get('debug'):
                self.printf(pprint.pformat(mesg))

            elif mesg[0] == 'node':
                node = mesg[1]
                formname = node[0][0]

                formvalu = node[1].get('repr')
                if formvalu is None:
                    formvalu = str(node[0][1])

                if opts.get('raw'):
                    self.printf(repr(node))
                    continue

                self.printf('%.20s: %s' % (formname, formvalu))

                if not opts.get('hide-props'):

                    for name, valu in sorted(node[1]['props'].items()):

                        valu = node[1]['reprs'].get(name, valu)

                        if name[0] != '.':
                            name = ':' + name

                        self.printf(f'        {name} = {valu}')

                if not opts.get('hide-tags'):

                    for name, valu in sorted(node[1]['tags'].items()):
                        self.printf(f'        #{name} = {valu}')

            elif mesg[0] == 'init':
                pass

            elif mesg[0] == 'fini':
                took = mesg[1].get('took')
                took = max(took, 1)

                count = mesg[1].get('count')
                pers = float(count) / float(took / 1000)
                self.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))

                continue

            elif mesg[0] == 'print':
                self.printf(mesg[1].get('mesg'))

            elif mesg[0] == 'warn':
                warn = mesg[1].get('mesg')
                self.printf(f'WARNING: {warn}')

            else:
                self.printf(repr(mesg))

class QueueCmd(s_cli.Cmd):
    '''
    Manage Cortex queues.

    Syntax:
        queue <arguments>

    Keyword Arguments:
        --act: Queue configuration action to take - `add`, `del`, `set`, `get`.
        defaults to `act`.
        --name: Name of the queue to work with. Optional with the `get` action.
        --type: Type of the queue to create or set.
        --desc: Description of the queue (for end users).
        --url: URL used to connect to the queue.

    Examples:
        # Add a queue
        queue --act add --name qt1 --type cryotank --desc "A queue" --url tcp://1.2.3.4:8080/cryo/qt1:1
        # List the details for the queue "qt1"
        queue --name qt1
        # List all queue details
        queue
        # Set the url for qt1
        queue --act set --name qt1 --url tcp://1.2.3.4:8080/cryo/qt1:2
        # Set the description for qt1
        queue --act set --name qt1 --desc "A really cool queue!"
        # Delete a queue
        queue --act del --name qt1
    '''
    _cmd_name = 'queue'
    _cmd_syntax = (
        ('--act', {'type': 'enum',
                   'defval': 'get',
                   'enum:vals': ('add', 'del', 'set', 'get')}),
        ('--name', {'type': 'valu'}),
        ('--type', {'type': 'valu'}),
        ('--desc', {'type': 'valu'}),
        ('--url', {'type': 'valu'}),
    )

    def __init__(self, cli, **opts):
        s_cli.Cmd.__init__(self, cli, **opts)

        self.reac = s_reactor.Reactor()
        self.reac.act('add', self._onAdd)
        self.reac.act('del', self._onDel)
        self.reac.act('get', self._onGet)
        self.reac.act('set', self._onSet)

    def _onAdd(self, mesg):
        act, opts = mesg
        core = self.getCmdItem()

        name = opts.get('name')
        info = {}
        if not name:
            self.printf('--name required to add queue.')
            return
        for key in ('type', 'url', 'desc'):
            valu = opts.get(key)
            if not valu:
                self.printf(f'--{key} required to add queue.')
                return
            info[key] = valu
        conf = (name, info)
        core.addQueue(conf)
        self.printf(f'Added queue conf [{conf}.]')

    def _onDel(self, mesg):
        act, opts = mesg
        core = self.getCmdItem()

        name = opts.get('name')
        self.printf('D')
        ret = core.delQueue(name)
        if ret:
            self.printf(f'Deleted queue [{name}].')
        else:
            self.printf(f'Queue does not exist [{name}].')

    def _onGet(self, mesg):
        act, opts = mesg
        core = self.getCmdItem()

        name = opts.get('name')
        if name:
            queues = [core.getQueue(name)]
        else:
            queues = core.getQueues()
        self.printf('Configured queues:')
        for conf in queues:
            self.printf(pprint.pformat(conf))

    def _onSet(self, mesg):
        act, opts = mesg
        core = self.getCmdItem()

        name = opts.get('name')
        for key in ('type', 'url', 'desc'):
            valu = opts.get(key)
            if valu:
                core.setQueueKey(name, key, valu)
                self.printf(f'Set queue [{name}] key [{key}] to [{valu}]')

    def runCmdOpts(self, opts):
        act = opts.get('act')
        self.reac.react((act, opts))
