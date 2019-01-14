import asyncio
import logging
import argparse
import collections

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.ast as s_ast
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

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

        self.task = asyncio.current_task()

        self.inputs = []    # [synapse.lib.node.Node(), ...]

        self.iden = s_common.guid()

        varz = self.opts.get('vars')
        if varz is not None:
            self.vars.update(varz)

        self.elevated = False

        # used by the digraph projection logic
        self._graph_done = {}
        self._graph_want = collections.deque()

    async def printf(self, mesg):
        return await self.snap.printf(mesg)

    async def warn(self, mesg, **info):
        return await self.snap.warn(mesg, **info)

    def elevate(self):

        if self.user is not None:
            if not self.user.admin:
                raise s_exc.AuthDeny(mesg='user is not admin', user=self.user.name)

        self.elevated = True

    def tick(self):
        pass

    def cancel(self):
        self.task.cancel()

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

    async def getInput(self):

        for node in self.inputs:
            yield node, self.initPath(node)

        for ndef in self.opts.get('ndefs', ()):

            node = await self.snap.getNodeByNdef(ndef)
            if node is not None:
                yield node, self.initPath(node)

        for iden in self.opts.get('idens', ()):

            buid = s_common.uhex(iden)
            if len(buid) != 32:
                raise s_exc.NoSuchIden(mesg='Iden must be 32 bytes', iden=iden)

            node = await self.snap.getNodeByBuid(buid)
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
        perm = '.'.join(args)
        raise s_exc.AuthDeny(perm=perm, user=self.user.name)

    async def execStormQuery(self, query):
        count = 0
        for node, path in self.iterStormQuery(query):
            count += 1
        return count

    async def iterStormQuery(self, query):
        # init any options from the query
        # (but dont override our own opts)
        for name, valu in query.opts.items():
            self.opts.setdefault(name, valu)

        async for node, path in query.iterNodePaths(self):
            self.tick()
            yield node, path

class Parser(argparse.ArgumentParser):

    def __init__(self, prog=None, descr=None):

        self.exited = False
        self.mesgs = []

        argparse.ArgumentParser.__init__(self,
                                         prog=prog,
                                         description=descr,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)

    def exit(self, status=0, message=None):
        '''
        Argparse expects exit() to be a terminal function and not return.
        As such, this function must raise an exception which will be caught
        by Cmd.hasValidOpts.
        '''
        self.exited = True
        if message is not None:
            self.mesgs.extend(message.split('\n'))
        raise s_exc.BadSyntaxError(mesg=message, prog=self.prog, status=status)

    def _print_message(self, text, fd=None):
        '''
        Note:  this overrides an existing method in ArgumentParser
        '''
        # Since we have the async->sync->async problem, queue up and print at exit
        self.mesgs.extend(text.split('\n'))

class Cmd:
    '''
    A one line description of the command.

    Command usage details and long form description.

    Example:

        cmd --help
    '''
    name = 'cmd'

    def __init__(self, argv):
        self.opts = None
        self.argv = argv
        self.pars = self.getArgParser()

    @classmethod
    def getCmdBrief(cls):
        return cls.__doc__.strip().split('\n')[0]

    def getArgParser(self):
        return Parser(prog=self.name, descr=self.__class__.__doc__)

    async def hasValidOpts(self, snap):

        self.pars.printf = snap.printf
        try:
            self.opts = self.pars.parse_args(self.argv)
        except s_exc.BadSyntaxError as e:
            pass
        for line in self.pars.mesgs:
            await snap.printf(line)
        return not self.pars.exited

    async def execStormCmd(self, runt, genr):
        ''' Abstract base method '''
        raise s_exc.NoSuchImpl('Subclass must implement execStormCmd')

class HelpCmd(Cmd):
    '''
    List available commands and a brief description for each.
    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('command', nargs='?', help='Show the help output for a given command.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for item in genr:
            yield item

        if not self.opts.command:
            for name, ctor in sorted(runt.snap.core.getStormCmds()):
                await runt.printf('%.20s: %s' % (name, ctor.getCmdBrief()))

        await runt.printf('')
        await runt.printf('For detailed help on any command, use <cmd> --help')

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

    async def execStormCmd(self, runt, genr):

        count = 0
        async for item in genr:

            yield item
            count += 1

            if count >= self.opts.count:
                await runt.printf(f'limit reached: {self.opts.count}')
                break

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

    async def execStormCmd(self, runt, genr):

        buidset = set()

        async for node, path in genr:

            if node.buid in buidset:
                continue

            buidset.add(node.buid)
            yield node, path

class MaxCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the highest value for a property.

    Examples:

        file:bytes +#foo.bar | max size

    '''

    name = 'max'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('propname')
        return pars

    async def execStormCmd(self, runt, genr):

        maxvalu = None
        maxitem = None

        pname = self.opts.propname
        prop = None
        if not pname.startswith((':', '.')):
            # Are we a full prop name?
            prop = runt.snap.core.model.prop(pname)
            if prop is None or prop.isform:
                mesg = f'{self.name} argument requires a relative secondary ' \
                    f'property name or a full path to the secondary property.'
                raise s_exc.BadSyntaxError(mesg=mesg, valu=pname)

        if prop:
            name = prop.name
            form = prop.form
        else:
            form = None
            name = pname.strip(':')

        async for node, path in genr:

            if form and node.form is not form:
                continue

            valu = node.get(name)
            if valu is None:
                continue

            if maxvalu is None or valu > maxvalu:
                maxvalu = valu
                maxitem = (node, path)

        if maxitem:
            yield maxitem

class MinCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the lowest value for a property.

    Examples:

        file:bytes +#foo.bar | min size

    '''
    name = 'min'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('propname')
        return pars

    async def execStormCmd(self, runt, genr):

        minvalu = None
        minitem = None

        pname = self.opts.propname
        prop = None
        if not pname.startswith((':', '.')):
            # Are we a full prop name?
            prop = runt.snap.core.model.prop(pname)
            if prop is None or prop.isform:
                mesg = f'{self.name} argument requires a relative secondary ' \
                    f'property name or a full path to the secondary property.'
                raise s_exc.BadSyntaxError(mesg=mesg, valu=pname)

        if prop:
            name = prop.name
            form = prop.form
        else:
            form = None
            name = pname.strip(':')

        async for node, path in genr:

            if form and node.form is not form:
                continue

            valu = node.get(name)
            if valu is None:
                continue

            if minvalu is None or valu < minvalu:
                minvalu = valu
                minitem = (node, path)

        if minitem:
            yield minitem

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

    async def execStormCmd(self, runt, genr):

        if self.opts.force:
            if runt.user is not None and not runt.user.admin:
                mesg = '--force requires admin privs.'
                raise s_exc.AuthDeny(mesg=mesg)

        i = 0
        async for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.allowed('tag:del', *tag.split('.'))

            runt.allowed('node:del', node.form.name)

            await node.delete(force=self.opts.force)

            i += 1
            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

        # a bit odd, but we need to be detected as a generator
        if False:
            yield

class SudoCmd(Cmd):
    '''
    Use admin privileges to bypass standard query permissions.

    Example:

        sudo | [ inet:fqdn=vertex.link ]
    '''
    name = 'sudo'

    async def execStormCmd(self, runt, genr):
        runt.elevate()
        async for item in genr:
            yield item

# TODO
# class AddNodeCmd(Cmd):     # addnode inet:ipv4 1.2.3.4 5.6.7.8
# class DelPropCmd(Cmd):     # | delprop baz
# class SetPropCmd(Cmd):     # | setprop foo bar
# class AddTagCmd(Cmd):      # | addtag --time 2015 #hehe.haha
# class DelTagCmd(Cmd):      # | deltag #foo.bar
# class SeenCmd(Cmd):        # | seen --from <guid>update .seen and seen=(src,node).seen
# class SourcesCmd(Cmd):     # | sources ( <nodes> -> seen:ndef :source -> source )

class ReIndexCmd(Cmd):
    '''
    Use admin privileges to re index/normalize node properties.

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
        pars.add_argument('--form-counts', default=False, action='store_true', help='Re-calculate all form counts.')
        return pars

    async def execStormCmd(self, runt, genr):

        snap = runt.snap

        if snap.user is not None and not snap.user.admin:
            await snap.warn('reindex requires an admin')
            return

        # are we re-indexing a type?
        if self.opts.type is not None:

            # is the type also a form?
            form = snap.model.forms.get(self.opts.type)

            if form is not None:

                await snap.printf(f'reindex form: {form.name}')

                async for buid, norm in snap.xact.iterFormRows(form.name):
                    await snap.stor(form.getSetOps(buid, norm))

            for prop in snap.model.getPropsByType(self.opts.type):

                await snap.printf(f'reindex prop: {prop.full}')

                formname = prop.form.name

                async for buid, norm in snap.xact.iterPropRows(formname, prop.name):
                    await snap.stor(prop.getSetOps(buid, norm))

            return

        if self.opts.subs:

            async for node, path in genr:

                form, valu = node.ndef
                norm, info = node.form.type.norm(valu)

                subs = info.get('subs')
                if subs is not None:
                    for subn, subv in subs.items():
                        if node.form.props.get(subn):
                            await node.set(subn, subv, init=True)

                yield node, path

            return

        if self.opts.form_counts:
            await snap.printf(f'reindex form counts (full) beginning...')
            await snap.core._calcFormCounts()
            await snap.printf(f'...done')
            return

        raise s_exc.SynErr('reindex was not told what to do!')


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

    async def execStormCmd(self, runt, genr):
        snap = runt.snap

        nodes = [node async for node in snap.getNodesBy('syn:tag', self.opts.oldtag)]
        if not nodes:
            raise s_exc.BadOperArg(mesg='Cannot move a tag which does not exist.',
                                   oldtag=self.opts.oldtag)
        oldt = nodes[0]
        oldstr = oldt.ndef[1]
        oldsize = len(oldstr)
        oldparts = oldstr.split('.')
        noldparts = len(oldparts)

        newt = await snap.addNode('syn:tag', self.opts.newtag)
        newstr = newt.ndef[1]

        if oldstr == newstr:
            raise s_exc.BadOperArg(mesg='Cannot retag a tag to the same valu.',
                                   newtag=newstr, oldtag=oldstr)

        retag = {oldstr: newstr}

        # first we set all the syn:tag:isnow props
        async for node in snap.getNodesBy('syn:tag', self.opts.oldtag, cmpr='^='):

            tagstr = node.ndef[1]
            tagparts = tagstr.split('.')
            # Are we in the same tree?
            if tagparts[:noldparts] != oldparts:
                continue

            newtag = newstr + tagstr[oldsize:]

            newnode = await snap.addNode('syn:tag', newtag)

            olddoc = node.get('doc')
            if olddoc is not None:
                await newnode.set('doc', olddoc)

            oldtitle = node.get('title')
            if oldtitle is not None:
                await newnode.set('title', oldtitle)

            # Copy any tags over to the newnode if any are present.
            for k, v in node.tags.items():
                await newnode.addTag(k, v)

            retag[tagstr] = newtag
            await node.set('isnow', newtag)

        # now we re-tag all the nodes...
        count = 0
        async for node in snap.getNodesBy(f'#{oldstr}'):

            count += 1

            tags = list(node.tags.items())
            tags.sort(reverse=True)

            for name, valu in tags:

                newt = retag.get(name)
                if newt is None:
                    continue

                await node.delTag(name)
                await node.addTag(newt, valu=valu)

        await snap.printf(f'moved tags on {count} nodes.')

        async for node, path in genr:
            yield node, path

class SpinCmd(Cmd):
    '''
    Iterate through all query results, but do not yield any.
    This can be used to operate on many nodes without returning any.

    Example:

        foo:bar:size=20 [ +#hehe ] | spin

    '''
    name = 'spin'

    async def execStormCmd(self, runt, genr):

        if False:  # make this method an async generator function
            yield None

        i = 0

        async for node, path in genr:
            i += 1

            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

class CountCmd(Cmd):
    '''
    Iterate through query results, and print the resulting number of nodes
    which were lifted. This does yield the nodes counted.

    Example:

        foo:bar:size=20 | count

    '''
    name = 'count'

    async def execStormCmd(self, runt, genr):

        i = 0
        async for item in genr:
            yield item
            i += 1

            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

        await runt.printf(f'Counted {i} nodes.')

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

    async def execStormCmd(self, runt, genr):

        async for x in genr:
            yield x

        for iden in self.opts.iden:
            try:
                buid = s_common.uhex(iden)
            except Exception as e:
                await runt.warn(f'Failed to decode iden: [{iden}]')
                continue
            if len(buid) != 32:
                await runt.warn(f'iden must be 32 bytes [{iden}]')
                continue

            node = await runt.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, runt.initPath(node)

class NoderefsCmd(Cmd):
    '''
    Get nodes adjacent to inbound nodes, up to n degrees away.

    Examples:
        The following examples show long-form options. Short form options exist and
        should be easier for regular use.

        Get all nodes 1 degree away from a input node:

            ask inet:ipv4=1.2.3.4 | noderefs

        Get all nodes 1 degree away from a input node and include the source node:

            ask inet:ipv4=1.2.3.4 | noderefs --join

        Get all nodes 3 degrees away from a input node and include the source node:

            ask inet:ipv4=1.2.3.4 | noderefs --join --degrees 3

        Do not include nodes of a given form in the output or traverse across them:

            ask inet:ipv4=1.2.3.4 | noderefs --omit-form inet:dns:a

        Do not traverse across nodes of a given form (but include them in the output):

            ask inet:ipv4=1.2.3.4 | noderefs --omit-traversal-form inet:dns:a

        Do not include nodes with a specific tag in the output or traverse across them:

            ask inet:ipv4=1.2.3.4 | noderefs --omit-tag omit.nopiv

        Do not traverse across nodes with a sepcific tag (but include them in the output):

            ask inet:ipv4=1.2.3.4 | noderefs --omit-traversal-tag omit.nopiv

        Accept multiple inbound nodes, and unique the output set of nodes across all input nodes:

            ask inet:ipv4=1.2.3.4 inet:ipv4=1.2.3.5 | noderefs --degrees 4 --unique

    '''
    name = 'noderefs'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('-d', '--degrees', type=int, default=1, action='store',
                          help='Number of degrees to traverse from the source node.')
        pars.add_argument('-te', '--traverse-edge', default=False, action='store_true',
                          help='Traverse Edge type nodes, if encountered, to '
                               'the opposite side of them, if the opposite '
                               'side has not yet been encountered.')
        pars.add_argument('-j', '--join', default=False, action='store_true',
                          help='Include source nodes in the output of the refs command.')
        pars.add_argument('-otf', '--omit-traversal-form', action='append', default=[], type=str,
                          help='Form to omit traversal of. Nodes of forms will still be the output.')
        pars.add_argument('-ott', '--omit-traversal-tag', action='append', default=[], type=str,
                          help='Tags to omit traversal of. Nodes with these '
                               'tags will still be in the output.')
        pars.add_argument('-of', '--omit-form', action='append', default=[], type=str,
                          help='Forms which will not be included in the '
                               'output or traversed.')
        pars.add_argument('-ot', '--omit-tag', action='append', default=[], type=str,
                          help='Forms which have these tags will not not be '
                               'included in the output or traversed.')
        pars.add_argument('-u', '--unique', action='store_true', default=False,
                          help='Unique the output across ALL input nodes, instead of each input node at a time.')
        return pars

    async def execStormCmd(self, runt, genr):

        self.snap = runt.snap

        self.omit_traversal_forms = set(self.opts.omit_traversal_form)
        self.omit_traversal_tags = set(self.opts.omit_traversal_tag)
        self.omit_forms = set(self.opts.omit_form)
        self.omit_tags = set(self.opts.omit_tag)
        self.ndef_props = [prop for prop in self.snap.model.props.values()
                           if isinstance(prop.type, s_types.Ndef)]

        if self.opts.degrees < 1:
            raise s_exc.BadOperArg(mesg='degrees must be greater than or equal to 1', arg='degrees')

        visited = set()

        async for node, path in genr:

            if self.opts.join:
                yield node, path

            if self.opts.unique is False:
                visited = set()

            # Don't revisit the inbound node from genr
            visited.add(node.buid)

            async for nnode, npath in self.doRefs(node, path, visited):
                yield nnode, npath

    async def doRefs(self, srcnode, srcpath, visited):

        srcqueue = collections.deque()
        srcqueue.append((srcnode, srcpath))

        degrees = self.opts.degrees

        while degrees:
            # Decrement degrees
            degrees = degrees - 1
            newqueue = collections.deque()
            while True:
                try:
                    snode, spath = srcqueue.pop()
                except IndexError as e:
                    # We've exhausted srcqueue, loop back around
                    srcqueue = newqueue
                    break

                async for pnode, ppath in self.getRefs(snode, spath):
                    await asyncio.sleep(0)

                    if pnode.buid in visited:
                        continue

                    visited.add(pnode.buid)

                    # Are we clear to yield this node?
                    if pnode.ndef[0] in self.omit_forms:
                        continue

                    if self.omit_tags.intersection(set(pnode.tags.keys())):
                        continue

                    yield pnode, ppath

                    # Can we traverse across this node?
                    if pnode.ndef[0] in self.omit_traversal_forms:
                        continue
                    if self.omit_traversal_tags.intersection(set(pnode.tags.keys())):
                        continue
                    # We're clear to circle back around to revisit nodes
                    # pointed by this node.
                    newqueue.append((pnode, ppath))

    async def getRefs(self, srcnode, srcpath):

        # Pivot out to secondary properties which are forms.
        for name, valu in srcnode.props.items():

            prop = srcnode.form.props.get(name)
            if prop is None:  # pragma: no cover
                # this should be impossible
                logger.warning(f'node prop is not form prop: {srcnode.form.name} {name}')
                continue

            if isinstance(prop.type, s_types.Ndef):
                pivo = await self.snap.getNodeByNdef(valu)
                if pivo is None:
                    continue  # pragma: no cover
                yield pivo, srcpath.fork(pivo)
                continue

            if isinstance(prop.type, s_types.NodeProp):
                qprop, qvalu = valu
                async for pivo in self.snap.getNodesBy(qprop, qvalu):
                    yield pivo, srcpath.fork(pivo)

            form = self.snap.model.forms.get(prop.type.name)
            if form is None:
                continue

            pivo = await self.snap.getNodeByNdef((form.name, valu))
            if pivo is None:
                continue  # pragma: no cover

            yield pivo, srcpath.fork(pivo)

        # Pivot in - pick up nodes who have secondary properties who have the same
        # type as me!
        name, valu = srcnode.ndef
        for prop in self.snap.model.propsbytype.get(name, ()):
            # Do not do pivot-in when we know we don't want the form of the resulting node.
            if prop.form.full in self.omit_forms:
                continue
            async for pivo in self.snap.getNodesBy(prop.full, valu):
                yield pivo, srcpath.fork(pivo)

        # Pivot to any Ndef properties we haven't pivoted to yet
        for prop in self.ndef_props:

            async for pivo in self.snap.getNodesBy(prop.full, srcnode.ndef):

                if self.opts.traverse_edge and isinstance(pivo.form.type, s_types.Edge):

                    # Determine if srcnode.ndef is n1 or n2, and pivot to the other side
                    if srcnode.ndef == pivo.get('n1'):
                        npivo = await self.snap.getNodeByNdef(pivo.get('n2'))
                        if npivo is None:  # pragma: no cover
                            logger.warning('n2 does not exist for edge? [%s]', pivo.ndef)
                            continue
                        # Ensure that the path includes the edge node we are traversing across.
                        _path = srcpath.fork(pivo)
                        yield npivo, _path.fork(npivo)
                        continue

                    if srcnode.ndef == pivo.get('n2'):
                        npivo = await self.snap.getNodeByNdef(pivo.get('n1'))
                        if npivo is None:  # pragma: no cover
                            logger.warning('n1 does not exist for edge? [%s]', pivo.ndef)
                            continue
                        # Ensure that the path includes the edge node we are traversing across.
                        _path = srcpath.fork(pivo)
                        yield npivo, _path.fork(npivo)
                        continue

                    logger.warning('edge type has no n1/n2 property. [%s]', pivo.ndef)  # pragma: no cover
                    continue  # pragma: no cover

                yield pivo, srcpath.fork(pivo)

class SleepCmd(Cmd):
    '''
    Introduce a delay between returning each result for the storm query.

    NOTE: This is mostly used for testing / debugging.

    Example:

        #foo.bar | sleep 0.5

    '''
    name = 'sleep'

    async def execStormCmd(self, runt, genr):
        async for item in genr:
            yield item
            await asyncio.sleep(self.opts.delay)

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('delay', type=float, default=1, help='Delay in floating point seconds.')
        return pars

class GraphCmd(Cmd):
    '''
    Generate a subgraph from the given input nodes and command line options.
    '''
    name = 'graph'

    def getArgParser(self):

        pars = Cmd.getArgParser(self)
        pars.add_argument('--degrees', type=int, default=1, help='How many degrees to graph out.')

        pars.add_argument('--pivot', default=[], action='append', help='Specify a storm pivot for all nodes. (must quote)')
        pars.add_argument('--filter', default=[], action='append', help='Specify a storm filter for all nodes. (must quote)')

        pars.add_argument('--form-pivot', default=[], nargs=2, action='append', help='Specify a <form> <pivot> form specific pivot.')
        pars.add_argument('--form-filter', default=[], nargs=2, action='append', help='Specify a <form> <filter> form specific filter.')

        return pars

    async def execStormCmd(self, runt, genr):

        rules = {
            'degrees': self.opts.degrees,

            'pivots': [],
            'filters': [],

            'forms': {},
        }

        for pivo in self.opts.pivot:
            rules['pivots'].append(pivo[1:-1])

        for filt in self.opts.filter:
            rules['filters'].append(filt[1:-1])

        for name, pivo in self.opts.form_pivot:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['pivots'].append(pivo[1:-1])

        for name, filt in self.opts.form_filter:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['filters'].append(filt[1:-1])

        subg = s_ast.SubGraph(rules)

        genr = subg.run(runt, genr)

        async for node, path in subg.run(runt, genr):
            yield node, path
