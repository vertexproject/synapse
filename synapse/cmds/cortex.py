import synapse.lib.cli as s_cli
import synapse.lib.tufo as s_tufo
import synapse.lib.scope as s_scope

class AskCmd(s_cli.Cmd):
    '''
    Execute a query.

    Examples:

        ask <query>          optional: --debug --props

        ask --debug          inet:ipv4=0
        ask --props          inet:ipv4="0.0.0.0"
        ask --debug --props  inet:ipv4=0x01020304
    '''

    _cmd_name = 'ask'
    _cmd_syntax = (
        ('--debug',{}),
        ('--props',{}),
        ('query',{'type':'glob'}),
    )

    def runCmdOpts(self, opts):
        ques = opts.get('query')
        if ques == None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()
        resp = core.ask(ques)

        oplog = resp.get('oplog')

        # check for an error condition
        if oplog and oplog[-1].get('excinfo'):
            opts['debug'] = 1

        if opts.get('debug'):

            self.printf('oplog:')
            for opfo in resp.get('oplog'):
                mnem = opfo.get('mnem')
                took = opfo.get('took')
                self.printf('    %s (took:%d) %r' % (mnem,took,opfo))

            self.printf('')

            self.printf('options:')
            for name,valu in sorted(resp.get('options').items()):
                self.printf('    %s = %s' % (name,valu))

            self.printf('')

            self.printf('limits:')
            for name,valu in sorted(resp.get('limits').items()):
                self.printf('    %s = %s' % (name,valu))

            self.printf('')

        def nodevalu(t):
            return repr( t[1].get( t[1].get('tufo:form') ) )

        nodes = list(sorted( resp.get('data'), key=nodevalu))

        if len(nodes) == 0:
            self.printf('(0 results)')
            return

        forms = set([ node[1].get('tufo:form') for node in nodes ])

        fsize = max([ len(f) for f in forms ])

        for node in nodes:
            form = node[1].get('tufo:form')
            valu = node[1].get(form)

            tags = sorted(s_tufo.tags(node,leaf=True))
            tags = [ '#'+tag for tag in tags ]

            # FIXME local typelib and datamodel
            disp = core.getPropRepr(form,valu)
            self.printf('%s = %s - %s' % (form.ljust(fsize),disp,' '.join(tags)))
            if opts.get('props'):
                pref = form + ':'
                flen = len(form)
                for prop in sorted([ k for k in node[1].keys() if k.startswith(pref) ]):
                    valu = node[1].get(prop)
                    disp = core.getPropRepr(prop,valu)
                    self.printf('    %s = %s' % (prop[flen:],disp))

        self.printf('(%d results)' % (len(nodes),))

        return resp

class AddNodeCmd(s_cli.Cmd):
    '''
    Form a node in the cortex.

    Examples:

        addnode <prop> <valu> [<secprop>=<valu>...]

        addnode inet:ipv4 0.0.0.0
        addnode inet:ipv4 0x01020304
        addnode inet:ipv4 1

        # add a node and specify secondary props
        addnode syn:seq woot width=8
    '''

    _cmd_name = 'addnode'
    _cmd_syntax = (
        ('--tags',{'type':'valu'}),
        ('prop',{'type':'valu'}),
        ('valu',{'type':'valu'}),
        ('props',{'type':'kwlist'}),
    )

    def runCmdOpts(self, opts):

        prop = opts.get('prop')
        valu = opts.get('valu')
        if prop == None or valu == None:
            self.printf(self.__doc__)
            return

        tags = ()

        tstr = opts.get('tags')
        if tstr != None:
            tags = tstr.split(',')

        kwlist = opts.get('props')
        props = dict( opts.get('props') )

        core = self.getCmdItem()

        node = core.formTufoByProp(prop,valu,**props)
        if tags:
            node = core.addTufoTags(node,tags)

        self.printf('formed: %r' % (node,))

class AddTagCmd(s_cli.Cmd):
    '''
    Add a tag by query.

    Examples:

        addtag <tag> <query>

        addtag cooltag inet:ipv4="127.0.0.1"
    '''

    _cmd_name = 'addtag'
    _cmd_syntax = (
        ('tag',{'type':'valu'}),
        ('query',{'type':'glob'}),
    )

    def runCmdOpts(self, opts):

        tag = opts.get('tag')
        if tag == None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

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
    '''
    Delete tags by query.

    Examples:

        deltag <tag> <query>

        deltag cooltag inet:ipv4="127.0.0.1"
    '''

    _cmd_name = 'deltag'
    _cmd_syntax = (
        ('tag',{'type':'valu'}),
        ('query',{'type':'glob'}),
    )

    def runCmdOpts(self, opts):

        tag = opts.get('tag')
        if tag == None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

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

class NextSeqCmd(s_cli.Cmd):
    '''
    Generate and display the next id in the named sequence.

    Usage:

        nextseq <name>

    '''
    _cmd_name = 'nextseq'
    _cmd_syntax = (
        ('name',{'type':'valu'}),
    )

    def runCmdOpts(self, opts):
        name = opts.get('name')
        if name == None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()
        valu = core.nextSeqValu(name)
        self.printf('next in sequence (%s): %s' % (name,valu))

