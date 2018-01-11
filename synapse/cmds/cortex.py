import json

import synapse.lib.cli as s_cli
import synapse.lib.tufo as s_tufo
import synapse.lib.storm as s_storm

class AskCmd(s_cli.Cmd):
    '''
    Execute a query.

    Examples:

        ask <query>          optional: --debug --[props|raw]

        ask --debug          inet:ipv4=0
        ask --props          inet:ipv4="0.0.0.0"
        ask --raw            inet:ipv4="0.0.0.0"
        ask --debug --props  inet:ipv4=0x01020304
    '''

    _cmd_name = 'ask'
    _cmd_syntax = (
        ('--debug', {}),
        ('--props', {}),
        ('--raw', {}),
        ('query', {'type': 'glob'}),
    )

    def runCmdOpts(self, opts):

        ques = opts.get('query')
        if ques is None:
            self.printf(self.__doc__)
            return

        if opts.get('props') and opts.get('raw'):
            self.printf('Cannot specify --raw and --props together.')
            return

        core = self.getCmdItem()
        resp = core.ask(ques)
        uniprops = core.getUnivProps()

        oplog = resp.get('oplog')

        # check for an error condition
        if oplog and oplog[-1].get('excinfo'):
            opts['debug'] = 1

        if opts.get('debug'):

            self.printf('oplog:')
            for opfo in resp.get('oplog'):
                mnem = opfo.get('mnem')
                took = opfo.get('took')
                self.printf('    %s (took:%d) %r' % (mnem, took, opfo))

            self.printf('')

            self.printf('options:')
            for name, valu in sorted(resp.get('options').items()):
                self.printf('    %s = %s' % (name, valu))

            self.printf('')

            self.printf('limits:')
            for name, valu in sorted(resp.get('limits').items()):
                self.printf('    %s = %s' % (name, valu))

            self.printf('')

        def nodevalu(t):
            return repr(t[1].get(t[1].get('tufo:form')))

        nodes = list(sorted(resp.get('data'), key=nodevalu))

        if len(nodes) == 0:
            self.printf('(0 results)')
            return

        forms = set([node[1].get('tufo:form') for node in nodes])

        fsize = max([len(f) for f in forms])

        # Short circuit any fancy formatting and dump the raw node content as json
        if opts.get('raw'):
            self.printf(json.dumps(nodes, sort_keys=True, indent=2))
            self.printf('(%d results)' % (len(nodes),))
            return resp

        show = resp.get('show', {})
        cols = show.get('columns')

        if cols is not None:

            shlp = s_storm.ShowHelp(core, show)
            rows = shlp.rows(nodes)
            pads = shlp.pad(rows)

            for pad in pads:
                self.printf(' '.join(pad))

        else:

            for node in nodes:

                form = node[1].get('tufo:form')
                valu = node[1].get(form)

                leafs = set(s_tufo.tags(node, leaf=True))

                taglines = []
                for tag in sorted(s_tufo.tags(node)):

                    prop = '#' + tag
                    asof = node[1].get(prop)

                    ival = s_tufo.ival(node, prop)
                    if ival is None and tag not in leafs:
                        continue

                    mesg = '%s (added %s)' % (prop, core.getTypeRepr('time', asof))
                    if ival is not None:
                        mins = core.getTypeRepr('time', ival[0])
                        maxs = core.getTypeRepr('time', ival[1])
                        mesg += ' %s  -  %s' % (mins, maxs)

                    taglines.append(mesg)

                # FIXME local typelib and datamodel
                disp = core.getPropRepr(form, valu)

                self.printf('%s = %s' % (form.ljust(fsize), disp))
                for line in taglines:
                    self.printf('    %s' % (line,))

                if opts.get('props'):
                    pref = form + ':'
                    flen = len(form)
                    for prop in sorted([k for k in node[1].keys() if k.startswith(pref)]):
                        valu = node[1].get(prop)
                        disp = core.getPropRepr(prop, valu)
                        self.printf('    %s = %s' % (prop[flen:], disp))
                    for prop in uniprops:
                        valu = node[1].get(prop)
                        if valu is None:  # pragma: no cover
                            continue
                        disp = core.getPropRepr(prop, valu)
                        self.printf('    %s = %s' % (prop, disp))

        self.printf('(%d results)' % (len(nodes),))

        return resp
