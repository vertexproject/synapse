import shlex
import argparse
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache

class Runtime:
    '''
    A Runtime represents the instance of a running query.
    '''
    def __init__(self, snap, opts=None, user=None):

        if opts is None:
            opts = {}

        self.vars = {}
        self.opts = opts
        self.snap = snap
        self.user = user

        self.inputs = []    # [synapse.lib.node.Node(), ...]

        self.iden = s_common.guid()

        varz = self.opts.get('vars')
        if varz is not None:
            self.vars.update(varz)

        self.canceled = False
        self.elevated = False

        # used by the di-graph projection logic
        self._graph_done = {}
        self._graph_want = collections.deque()

    def printf(self, mesg):
        return self.snap.printf(mesg)

    def warn(self, mesg, **info):
        return self.snap.warn(mesg, **info)

    def elevate(self):

        if self.user is not None:
            if not self.user.admin:
                raise s_exc.AuthDeny(mesg='user is not admin')

        self.elevated = True

    def tick(self):

        if self.canceled:
            raise s_exc.Canceled()

    def cancel(self):
        self.canceled = True

    def initPath(self, node):
        return s_node.Path(self, dict(self.vars), [node])

    def getOpt(self, name, defval=None):
        return self.opts.get(name, defval)

    def setOpt(self, name, valu):
        self.opts[name] = valu

    def addInput(self, node):
        '''
        Add a Node() object as input to the query runtime.
        '''
        self.inputs.append(node)

    def getInput(self):

        for node in self.inputs:
            yield node, self.initPath(node)

        for ndef in self.opts.get('ndefs', ()):

            node = self.snap.getNodeByNdef(ndef)
            if node is not None:
                yield node, self.initPath(node)

        for iden in self.opts.get('idens', ()):

            buid = s_common.uhex(iden)

            node = self.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, self.initPath(node)

    @s_cache.memoize(size=100)
    def allowed(self, *args):

        # a user will be set by auth subsystem if enabled
        if self.user is None:
            return

        if self.elevated:
            return

        if self.user.allowed(args, elev=False):
            return

        # fails will not be cached...
        perm = ':'.join(args)
        raise s_exc.AuthDeny(perm=perm)

    def execStormQuery(self, query):
        count = 0
        for node, path in self.iterStormQuery(query):
            count += 1
        return count

    def iterStormQuery(self, query):
        # init any options from the query
        # (but dont override our own opts)
        for name, valu in query.opts.items():
            self.opts.setdefault(name, valu)

        for node, path in query.iterNodePaths(self):
            self.tick()
            yield node, path

class Parser(argparse.ArgumentParser):

    def __init__(self, prog=None, descr=None):

        self.printf = None
        self.exited = False

        argparse.ArgumentParser.__init__(self,
            prog=prog,
            description=descr,
            formatter_class=argparse.RawDescriptionHelpFormatter)

    def exit(self, *args, **kwargs):
        # yea....  newp.
        self.exited = True

    def _print_message(self, text, fd=None):

        if self.printf is None:
            return

        for line in text.split('\n'):
            self.printf(line)

class Cmd:
    '''
    A one line description of the command.

    Command usage details and long form description.

    Example:

        cmd --help
    '''
    name = 'cmd'

    def __init__(self, text):
        self.opts = None
        self.text = text
        self.argv = self.getCmdArgv()
        self.pars = self.getArgParser()

    @classmethod
    def getCmdBrief(clas):
        return clas.__doc__.strip().split('\n')[0]

    def getCmdArgv(self):
        return shlex.split(self.text)

    def getArgParser(self):
        return Parser(prog=self.name, descr=self.__class__.__doc__)

    def reqValidOpts(self, snap):
        self.pars.printf = snap.printf
        self.opts = self.pars.parse_args(self.argv)
        if self.pars.exited:
            raise s_exc.BadStormSyntax(name=self.name, text=self.text)

    def execStormCmd(self, runt, genr):
        # override me!
        yield from self.runStormCmd(runt.snap, genr)

    def runStormCmd(self, snap, genr):
        # Older API.  Prefer execStormCmd().
        yield from genr

class HelpCmd(Cmd):
    '''
    List available commands and a brief description for each.
    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('command', nargs='?', help='Show the help output for a given command.')
        return pars

    def runStormCmd(self, snap, genr):

        yield from genr

        if not self.opts.command:
            for name, ctor in sorted(snap.core.getStormCmds()):
                snap.printf('%.20s: %s' % (name, ctor.getCmdBrief()))

        snap.printf('')
        snap.printf('For detailed help on any command, use <cmd> --help')

class LimitCmd(Cmd):
    '''
    Limit the number of nodes generated by the query in the given position.

    Example:

        inet:ipv4 | limit 10
    '''

    name = 'limit'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('count', type=int, help='The maximum number of nodes to yield.')
        return pars

    def runStormCmd(self, snap, genr):

        for count, item in enumerate(genr):

            if count >= self.opts.count:
                snap.printf(f'limit reached: {self.opts.count}')
                break

            yield item

class UniqCmd(Cmd):
    '''
    Filter nodes by their uniq iden values.
    When this is used a Storm pipeline, only the first instance of a
    given node is allowed through the pipeline.

    Examples:

        #badstuff +inet:ipv4 ->* | uniq

    '''

    name = 'uniq'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        return pars

    def runStormCmd(self, snap, genr):
        buidset = set()
        for node, path in genr:
            if node.buid in buidset:
                continue
            buidset.add(node.buid)
            yield node, path

class DelNodeCmd(Cmd):
    '''
    Delete nodes produced by the previous query logic.

    (no nodes are returned)

    Example

        inet:fqdn=vertex.link | delnode
    '''
    name = 'delnode'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        forcehelp = 'Force delete even if it causes broken references (requires admin).'
        pars.add_argument('--force', default=False, action='store_true', help=forcehelp)
        return pars

    def execStormCmd(self, runt, genr):

        if self.opts.force:
            if runt.user is not None and not runt.user.admin:
                mesg = '--force requires admin privs.'
                self._onAuthDeny(mesg)
                return

        for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.allowed('tag:del', *tag.split('.'))

            runt.allowed('node:del', node.form.name)

            node.delete(force=self.opts.force)

        # a bit odd, but we need to be detected as a generator
        yield from ()

class SudoCmd(Cmd):
    '''
    Use admin priviliges to bypass standard query permissions.

    Example:

        sudo | [ inet:fqdn=vertex.link ]
    '''
    name = 'sudo'

    def execStormCmd(self, runt, genr):
        runt.elevate()
        yield from genr

# TODO
#class AddNodeCmd(Cmd):     # addnode inet:ipv4 1.2.3.4 5.6.7.8
#class DelPropCmd(Cmd):     # | delprop baz
#class SetPropCmd(Cmd):     # | setprop foo bar
#class AddTagCmd(Cmd):      # | addtag --time 2015 #hehe.haha
#class DelTagCmd(Cmd):      # | deltag #foo.bar
#class SeenCmd(Cmd):        # | seen --from <guid>update .seen and seen=(src,node).seen
#class SourcesCmd(Cmd):     # | sources ( <nodes> -> seen:ndef :source -> source )

class ReIndexCmd(Cmd):
    '''
    Use admin priviliges to re index/normalize node properties.

    Example:

        foo:bar | reindex --subs

        reindex --type inet:ipv4

    NOTE: This is mostly for model updates and migrations.
          Use with caution and be very sure of what you are doing.
    '''
    name = 'reindex'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('--type', default=None, help='Re-index all properties of a specified type.')
        pars.add_argument('--subs', default=False, action='store_true', help='Re-parse and set sub props.')
        return pars

    def runStormCmd(self, snap, genr):

        if snap.user is not None and not snap.user.admin:
            snap.warn('reindex requires an admin')
            return

        snap.elevated = True
        snap.writeable()

        # are we re-indexing a type?
        if self.opts.type is not None:

            # is the type also a form?
            form = snap.model.forms.get(self.opts.type)

            if form is not None:

                snap.printf(f'reindex form: {form.name}')
                for buid, norm in snap.xact.iterFormRows(form.name):
                    snap.stor(form.getSetOps(buid, norm))

            for prop in snap.model.getPropsByType(self.opts.type):

                snap.printf(f'reindex prop: {prop.full}')

                formname = prop.form.name

                for buid, norm in snap.xact.iterPropRows(formname, prop.name):
                    snap.stor(prop.getSetOps(buid, norm))

            return

        for node, path in genr:

            form, valu = node.ndef
            norm, info = node.form.type.norm(valu)

            subs = info.get('subs')
            if subs is not None:
                for subn, subv in subs.items():
                    if node.form.props.get(subn):
                        node.set(subn, subv)

            yield node, path

class MoveTagCmd(Cmd):
    '''
    Rename an entire tag tree and preserve time intervals.

    Example:

        movetag #foo.bar #baz.faz.bar
    '''
    name = 'movetag'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('oldtag', help='The tag tree to rename.')
        pars.add_argument('newtag', help='The new tag tree name.')
        return pars

    def runStormCmd(self, snap, genr):

        oldt = snap.addNode('syn:tag', self.opts.oldtag)
        oldstr = oldt.ndef[1]
        oldsize = len(oldstr)

        newt = snap.addNode('syn:tag', self.opts.newtag)
        newstr = newt.ndef[1]

        retag = {oldstr: newstr}

        # first we set all the syn:tag:isnow props
        for node in snap.getNodesBy('syn:tag', self.opts.oldtag, cmpr='^='):

            tagstr = node.ndef[1]
            if tagstr == oldstr: # special case for exact match
                node.set('isnow', newstr)
                continue

            newtag = newstr + tagstr[oldsize:]

            newnode = snap.addNode('syn:tag', newtag)

            olddoc = node.get('doc')
            if olddoc is not None:
                newnode.set('doc', olddoc)

            oldtitle = node.get('title')
            if oldtitle is not None:
                newnode.set('title', oldtitle)

            retag[tagstr] = newtag
            node.set('isnow', newtag)

        # now we re-tag all the nodes...
        count = 0
        for node in snap.getNodesBy(f'#{oldstr}'):

            count += 1

            tags = list(node.tags.items())
            tags.sort(reverse=True)

            for name, valu in tags:

                newt = retag.get(name)
                if newt is None:
                    continue

                node.delTag(name)
                node.addTag(newt, valu=valu)

        snap.printf(f'moved tags on {count} nodes.')

        for node, path in genr:
            yield node, path

class SpinCmd(Cmd):
    '''
    Iterate through all query results, but do not yield any.
    This can be used to operate on many nodes without returning any.

    Example:

        foo:bar:size=20 [ +#hehe ] | spin

    '''
    name = 'spin'

    def runStormCmd(self, snap, genr):

        yield from ()

        for node, path in genr:
            pass

class CountCmd(Cmd):
    '''
    Iterate through query results, and print the resulting number of nodes
    which were lifted. This does yield the nodes counted.

    Example:

        foo:bar:size=20 | count

    '''
    name = 'count'

    def runStormCmd(self, snap, genr):

        i = 0
        for i, (node, path) in enumerate(genr, 1):
            yield node, path

        snap.printf(f'Counted {i} nodes.')

class IdenCmd(Cmd):
    '''
    Lift nodes by iden.

    Example:

        iden b25bc9eec7e159dce879f9ec85fb791f83b505ac55b346fcb64c3c51e98d1175 | count
    '''
    name = 'iden'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('iden', nargs='*', type=str, default=[],
                          help='Iden to lift nodes by. May be specified multiple times.')
        return pars

    def execStormCmd(self, runt, genr):

        yield from genr

        for iden in self.opts.iden:
            try:
                buid = s_common.uhex(iden)
            except Exception as e:
                runt.warn(f'Failed to decode iden: [{iden}]')
                continue

            node = runt.snap.getNodeByBuid(buid)
            if node:
                yield node, runt.initPath(node)
