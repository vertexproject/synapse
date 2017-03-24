import synapse.lib.cli as s_cli
import synapse.lib.tufo as s_tufo
import synapse.lib.scope as s_scope

class AskCmd(s_cli.Cmd):

    _cmd_name = 'ask'
    _cmd_syntax = (
        ('--debug',{}),
        ('query',{'type':'glob'}),
    )

    def runCmdOpts(self, opts):
        ques = opts.get('query')
        core = s_scope.get('syn:cmd:core')
        if core == None:
            self.printf('no connected cortex. see "open" cmd.')
            return None

        resp = core.ask(ques)
        # {'oplog': [{'mnem': 'lift', 'add': 0, 'took': 1, 'sub': 0}], 'data': [], 'options': {'uniq': 1}, 'limits': {'touch': None, 'lift': None, 'time': None}}

        if opts.get('debug'):

            self.printf('oplog:')
            for opfo in resp.get('oplog'):
                mnem = opfo.get('mnem')
                took = opfo.get('took')
                self.printf('    %s (took:%d) %r' % (mnem,took,opfo))

            self.printf('options:')
            for name,valu in sorted(resp.get('options').items()):
                self.printf('    %s = %s' % (name,valu))

            self.printf('limits:')
            for name,valu in sorted(resp.get('limits').items()):
                self.printf('    %s = %s' % (name,valu))

        def nodevalu(t):
            return t[1].get( t[1].get('tufo:form') )

        nodes = list(sorted( resp.get('data'), key=nodevalu))

        for node in nodes:
            form = node[1].get('tufo:form')
            valu = node[1].get(form)

            tags = s_tufo.tags(node)

            # FIXME local typelib and datamodel
            disp = core.getPropRepr(form,valu)
            self.printf('%s - %s' % (disp,','.join(tags)))

        return resp

class OpenCmd(s_cli.Cmd):
    _cmd_name = 'open'
    _cmd_syntax = (
        ('url',{'type':'valu'}),
    )
    def runCmdOpts(self, opts):
        url = opts.get('url')
        self.printf('connecting to: %s' % (url,))
        core = s_cortex.openurl(url)
        s_scope.set('syn:cmd:core',core)
        return core

class AddNodeCmd(s_cli.Cmd):
    _cmd_name = 'addnode'
    _cmd_syntax = (
        ('prop',{'type':'valu'}),
        ('valu',{'type':'valu'}),
    )
    def runCmdOpts(self, opts):

        core = s_scope.get('syn:cmd:core')

        prop = opts.get('prop')
        valu = opts.get('valu')

        node = core.formTufoByFrob(prop,valu)
        self.printf('formed: %r' % (node,))

class AddTagCmd(s_cli.Cmd):
    _cmd_name = 'addtag'
    _cmd_syntax = (
        ('tag',{'type':'valu'}),
        ('query',{'type':'glob'}),
    )
    def runCmdOpts(self, opts):

        tag = opts.get('tag')
        core = s_scope.get('syn:cmd:core')

        nodes = core.eval( opts.get('query') )
        if not nodes:
            self.printf('0 nodes...')
            return

        self.printf('adding %s to %d nodes...' % (tag,len(nodes)))

        for node in nodes:

            node = core.addTufoTag(node,tag)

            form = node[1].get('tufo:form')
            valu = node[1].get(form)

            tags = s_tufo.tags(node)

            # FIXME local typelib and datamodel
            disp = core.getPropRepr(form,valu)
            self.printf('%s - %s' % (disp,','.join(tags)))

class DelTagCmd(s_cli.Cmd):
    _cmd_name = 'deltag'
    _cmd_syntax = (
        ('tag',{'type':'valu'}),
        ('query',{'type':'glob'}),
    )
    def runCmdOpts(self, opts):

        tag = opts.get('tag')
        core = s_scope.get('syn:cmd:core')

        nodes = core.eval( opts.get('query') )
        if not nodes:
            self.printf('0 nodes...')
            return

        self.printf('removing %s from %d nodes...' % (tag,len(nodes)))

        for node in nodes:

            node = core.delTufoTag(node,tag)

            form = node[1].get('tufo:form')
            valu = node[1].get(form)

            tags = s_tufo.tags(node)

            # FIXME local typelib and datamodel
            disp = core.getPropRepr(form,valu)
            self.printf('%s - %s' % (disp,','.join(tags)))

def initCoreCli(cli=None,outp=None):
    '''
    Initialize a Cli() object with cortex related commands.
    '''
    if cli == None:
        cli = s_cli.Cli(outp=outp)

    cli.addCmdClass(AskCmd)
    cli.addCmdClass(OpenCmd)
    cli.addCmdClass(AddTagCmd)
    cli.addCmdClass(DelTagCmd)
    cli.addCmdClass(AddNodeCmd)

    return cli
