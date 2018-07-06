import pprint

import synapse.exc as s_exc
import synapse.lib.cli as s_cli
import synapse.reactor as s_reactor


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

    def __init__(self, cli, **opts):
        s_cli.Cmd.__init__(self, cli, **opts)
        self.reac = s_reactor.Reactor()
        self.reac.act('node', self._onNode)
        self.reac.act('init', self._onInit)
        self.reac.act('fini', self._onFini)
        self.reac.act('print', self._onPrint)
        self.reac.act('warn', self._onWarn)

    def _onNode(self, mesg):

        node = mesg[1]
        opts = node[1].pop('_opts', {})
        formname = node[0][0]

        formvalu = node[1].get('repr')
        if formvalu is None:
            formvalu = str(node[0][1])

        if opts.get('raw'):
            self.printf(repr(node))
            return

        self.printf('%.20s = %s' % (formname, formvalu))

        if not opts.get('hide-props'):

            for name, valu in sorted(node[1]['props'].items()):

                valu = node[1]['reprs'].get(name, valu)

                if name[0] != '.':
                    name = ':' + name

                self.printf(f'        {name} = {valu}')

        if not opts.get('hide-tags'):

            for name, valu in sorted(node[1]['tags'].items()):
                self.printf(f'        #{name} = {valu}')

    def _onInit(self, mesg):
        pass

    def _onFini(self, mesg):
        took = mesg[1].get('took')
        took = max(took, 1)

        count = mesg[1].get('count')
        pers = float(count) / float(took / 1000)
        self.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))

    def _onPrint(self, mesg):
        self.printf(mesg[1].get('mesg'))

    def _onWarn(self, mesg):
        warn = mesg[1].get('mesg')
        self.printf(f'WARNING: {warn}')

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

            else:
                if mesg[0] == 'node':
                    # Tuck the opts into the node dictionary since
                    # they control node metadata display
                    mesg[1][1]['_opts'] = opts
                try:
                    self.reac.react(mesg)
                except s_exc.NoSuchAct as e:
                    self.printf(repr(mesg))
