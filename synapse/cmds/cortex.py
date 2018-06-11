import pprint

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
