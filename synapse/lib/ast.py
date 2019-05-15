import fnmatch
import logging
import itertools
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.types as s_types
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

async def agen(*items):
    for item in items:
        yield item

class StormCtrlFlow(Exception):
    def __init__(self, item=None):
        self.item = item

class StormBreak(StormCtrlFlow):
    pass

class StormContinue(StormCtrlFlow):
    pass

class AstNode:
    '''
    Base class for all nodes in the STORM abstract syntax tree.
    '''

    def __init__(self, kids=()):
        self.kids = []
        [self.addKid(k) for k in kids]

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}'

    def __repr__(self):
        return self.repr()

    def addKid(self, astn):

        indx = len(self.kids)
        self.kids.append(astn)

        astn.parent = self
        astn.pindex = indx

    def setKid(self, indx, astn):

        self.kids[indx] = astn

        astn.parent = self
        astn.pindex = indx

    def replace(self, astn):
        self.parent.setKid(self.pindex, astn)

    def sibling(self, offs=1):
        '''
        Return sibling node by relative offset from self.
        '''
        indx = self.pindex + offs

        if indx < 0:
            return None

        if indx >= len(self.parent.kids):
            return None

        return self.parent.kids[indx]

    def iterright(self):
        '''
        Yield "rightward" siblings until None.
        '''
        offs = 1
        while True:

            sibl = self.sibling(offs)
            if sibl is None:
                break

            yield sibl
            offs += 1

    def format(self, depth=0):

        yield (depth, self.repr())

        for kid in self.kids:
            for item in kid.format(depth=depth + 1):
                yield item

    def init(self, core):
        self.core = core
        [k.init(core) for k in self.kids]
        self.prepare()

    def prepare(self):
        pass

    def optimize(self):
        [k.optimize() for k in self.kids]

    def __iter__(self):
        for kid in self.kids:
            yield kid

    def getRuntVars(self, runt):
        for kid in self.kids:
            for name in kid.getRuntVars(runt):
                yield name

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

class Query(AstNode):

    def __init__(self, kids=()):

        AstNode.__init__(self, kids=kids)

        self.text = ''

        # for options parsed from the query itself
        self.opts = {}

    async def run(self, runt, genr):

        for oper in self.kids:
            genr = oper.run(runt, genr)

        async for node, path in genr:

            runt.tick()

            yield node, path

    async def iterNodePaths(self, runt):

        count = 0
        subgraph = None

        rules = runt.getOpt('graph')

        if rules not in (False, None):
            if rules is True:
                rules = {'degrees': None, 'pivots': ('-> *',)}

            subgraph = SubGraph(rules)

        self.optimize()

        # turtles all the way down...
        genr = runt.getInput()

        for oper in self.kids:
            genr = oper.run(runt, genr)

        if subgraph is not None:
            genr = subgraph.run(runt, genr)

        async for node, path in genr:

            runt.tick()

            yield node, path

            count += 1

            limit = runt.getOpt('limit')
            if limit is not None and count >= limit:
                await runt.printf('limit reached: %d' % (limit,))
                break

class SubGraph:
    '''
    An Oper like object which generates a subgraph.

    Notes:

        The rules format for the subgraph is shaped like the following::

                rules = {

                    'degrees': 1,

                    'filters': [
                        '-(#foo or #bar)',
                        '-(foo:bar or baz:faz)',
                    ],

                    'pivots': [
                        '-> * | limit 100',
                        '<- * | limit 100',
                    ]

                    'forms': {

                        'inet:fqdn':{
                            'filters': [],
                            'pivots': [],
                        }

                        '*': {
                            'filters': [],
                            'pivots': [],
                        },
                    },
                }

        Nodes which were original seeds have path.meta('graph:seed').

        All nodes have path.meta('edges') which is a list of (iden, info) tuples.

    '''

    def __init__(self, rules):

        self.omits = {}
        self.rules = rules

        self.rules.setdefault('forms', {})
        self.rules.setdefault('pivots', ())
        self.rules.setdefault('filters', ())
        self.rules.setdefault('degrees', 1)

    async def omit(self, node):

        answ = self.omits.get(node.buid)
        if answ is not None:
            return answ

        for filt in self.rules.get('filters'):
            if await node.filter(filt, user=self.user):
                self.omits[node.buid] = True
                return True

        rules = self.rules['forms'].get(node.form.name)
        if rules is None:
            rules = self.rules['forms'].get('*')

        if rules is None:
            self.omits[node.buid] = False
            return False

        for filt in rules.get('filters', ()):
            if await node.filter(filt, user=self.user):
                self.omits[node.buid] = True
                return True

        self.omits[node.buid] = False
        return False

    async def pivots(self, node):

        for pivq in self.rules.get('pivots'):

            async for pivo in node.storm(pivq, user=self.user):
                yield pivo

        rules = self.rules['forms'].get(node.form.name)
        if rules is None:
            rules = self.rules['forms'].get('*')

        if rules is None:
            return

        for pivq in rules.get('pivots', ()):
            async for pivo in node.storm(pivq, user=self.user):
                yield pivo

    async def run(self, runt, genr):

        done = {}
        degrees = self.rules.get('degrees')

        self.user = runt.user

        async for node, path in genr:

            if await self.omit(node):
                continue

            path.meta('graph:seed', True)

            todo = collections.deque([(node, path, 0)])

            while todo:

                tnode, tpath, tdist = todo.popleft()

                # filter out nodes that we've already done at
                # the given distance or less... (best possible)
                donedist = done.get(tnode.buid)
                if donedist is not None and donedist <= tdist:
                    continue

                done[tnode.buid] = tdist

                edges = set()
                ndist = tdist + 1

                async for pivn, pivp in self.pivots(tnode):

                    if await self.omit(pivn):
                        continue

                    edges.add(pivn.iden())

                    if degrees is not None and ndist > degrees:
                        continue

                    todo.append((pivn, pivp, ndist))

                edgelist = [(iden, {}) for iden in edges]
                tpath.meta('edges', edgelist)

                if donedist is None:
                    yield tnode, tpath

class Oper(AstNode):
    pass

class SubQuery(Oper):

    async def run(self, runt, genr):

        subq = self.kids[0]

        async for item in genr:

            await s_common.aspin(subq.run(runt, agen(item)))

            yield item

    async def inline(self, runt, genr):
        async for item in self.kids[0].run(runt, genr):
            yield item

class ForLoop(Oper):

    def getRuntVars(self, runt):

        if not self.kids[1].isRuntSafe(runt):
            return

        if isinstance(self.kids[0], VarList):
            for name in self.kids[0].value():
                yield name

        else:
            yield self.kids[0].value()

        for name in self.kids[2].getRuntVars(runt):
            yield name

    async def run(self, runt, genr):

        subq = self.kids[2]
        name = self.kids[0].value()

        count = 0
        async for node, path in genr:

            count += 1

            for item in await self.kids[1].compute(path):

                if isinstance(name, (list, tuple)):

                    if len(name) != len(item):
                        raise s_exc.StormVarListError(names=name, vals=item)

                    for x, y in itertools.zip_longest(name, item):
                        path.setVar(x, y)
                        runt.setVar(x, y)

                else:
                    # set both so inner subqueries have it in their runtime
                    path.setVar(name, item)
                    runt.setVar(name, item)

                try:

                    newg = agen((node, path))
                    await s_common.aspin(subq.inline(runt, newg))

                except StormBreak:
                    break

                except StormContinue:
                    continue

            yield node, path

        # no nodes and a runt safe value should execute once
        if count == 0 and self.kids[1].isRuntSafe(runt):

            for item in await self.kids[1].runtval(runt):

                if isinstance(name, (list, tuple)):

                    if len(name) != len(item):
                        raise s_exc.StormVarListError(names=name, vals=item)

                    for x, y in itertools.zip_longest(name, item):
                        runt.setVar(x, y)

                else:
                    runt.setVar(name, item)

                try:
                    async for jtem in subq.inline(runt, agen()):
                        yield jtem

                except StormBreak:
                    break

                except StormContinue:
                    continue

class CmdOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        argv = self.kids[1].value()

        ctor = runt.snap.core.getStormCmd(name)
        if ctor is None:
            mesg = 'Storm command not found.'
            raise s_exc.NoSuchName(name=name, mesg=mesg)

        scmd = ctor(argv)

        if not await scmd.hasValidOpts(runt.snap):
            return

        with s_provenance.claim('stormcmd', name=name, argv=argv):

            async for item in scmd.execStormCmd(runt, genr):
                yield item

class VarSetOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        vkid = self.kids[1]

        async for node, path in genr:
            valu = await vkid.compute(path)
            path.setVar(name, valu)
            runt.setVar(name, valu)
            yield node, path

        if vkid.isRuntSafe(runt):

            valu = await vkid.runtval(runt)
            runt.setVar(name, valu)

    def getRuntVars(self, runt):
        if not self.kids[1].isRuntSafe(runt):
            return
        yield self.kids[0].value()

class VarListSetOper(Oper):

    async def run(self, runt, genr):

        names = self.kids[0].value()
        vkid = self.kids[1]

        async for node, path in genr:

            item = await vkid.compute(path)
            if len(item) < len(names):
                raise s_exc.StormVarListError(names=names, vals=item)

            for name, valu in zip(names, item):
                runt.setVar(name, valu)
                path.setVar(name, valu)

            yield node, path

        if vkid.isRuntSafe(runt):

            item = await vkid.runtval(runt)
            if len(item) < len(names):
                raise s_exc.StormVarListError(names=names, vals=item)

            for name, valu in zip(names, item):
                runt.setVar(name, valu)

            async for item in genr:
                yield item

            return

    def getRuntVars(self, runt):

        if not self.kids[1].isRuntSafe(runt):
            return

        for name in self.kids[0].value():
            yield name

class VarEvalOper(Oper):
    '''
    Facilitate a stand-alone operator that evaluates a var.
    $foo.bar("baz")
    '''
    async def run(self, runt, genr):

        if self.isRuntSafe(runt):

            async for item in genr:
                yield item

            await self.kids[0].runtval(runt)

        else:
            async for node, path in genr:
                await self.kids[0].compute(path)
                yield node, path

class SwitchCase(Oper):

    def prepare(self):
        self.cases = {}
        self.defcase = None

        for cent in self.kids[1:]:

            # if they only have one kid, it's a default case.
            if len(cent.kids) == 1:
                self.defcase = cent.kids[0]
                continue

            valu = cent.kids[0].value()
            self.cases[valu] = cent.kids[1]

    async def run(self, runt, genr):

        varv = await self.kids[0].runtval(runt)
        if varv is None:
            raise s_exc.NoSuchVar()

        subq = self.cases.get(varv)
        if subq is None and self.defcase is not None:
            subq = self.defcase

        if subq is None:
            async for item in genr:
                yield item
            return

        async for item in subq.inline(runt, genr):
            yield item

class CaseEntry(AstNode):
    pass

class LiftOper(Oper):

    async def run(self, runt, genr):

        if self.isRuntSafe(runt):

            # runtime safe lift operation
            async for item in genr:
                yield item

            async for node in self.lift(runt):
                yield node, runt.initPath(node)

            return

        # TODO unify runtval() / compute() methods
        async for node, path in genr:

            yield node, path

            async for subn in self.lift(path):
                yield subn, path.fork(subn)

class LiftTag(LiftOper):

    async def lift(self, runt):
        cmpr = '='
        valu = None
        tag = await self.kids[0].compute(runt)
        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt)
            valu = await self.kids[2].compute(runt)
        async for node in runt.snap._getNodesByTag(tag, valu=valu, cmpr=cmpr):
            yield node

class LiftTagTag(LiftOper):
    '''
    ##foo.bar
    '''

    async def lift(self, runt):

        todo = collections.deque()
        cmpr = '='
        valu = None

        tag = await self.kids[0].compute(runt)
        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt)
            valu = await self.kids[2].compute(runt)

        node = await runt.snap.getNodeByNdef(('syn:tag', tag))
        if node is None:
            return

        # only apply the lift valu to the top level tag of tags, not to the sub tags
        # or non-tag nodes
        todo.append((node, valu, cmpr))

        done = set()
        while todo:

            node, valu, cmpr = todo.popleft()

            tagname = node.ndef[1]
            if tagname in done:
                continue

            done.add(tagname)
            async for node in runt.snap._getNodesByTag(tagname, valu=valu, cmpr=cmpr):
                if node.form.name == 'syn:tag':
                    todo.append((node, None, '='))
                    continue

                yield node

class LiftFormTag(LiftOper):

    async def lift(self, runt):

        form = self.kids[0].value()
        tag = await self.kids[1].compute(runt)

        cmpr = None
        valu = None

        if len(self.kids) == 4:
            cmpr = self.kids[2].value()
            valu = await self.kids[3].compute(runt)

        async for node in runt.snap._getNodesByFormTag(form, tag, valu=valu, cmpr=cmpr):
            yield node

class LiftProp(LiftOper):

    async def lift(self, runt):

        name = self.kids[0].value()

        cmpr = None
        valu = None

        if len(self.kids) == 3:
            cmpr = self.kids[1].value()
            valu = await self.kids[2].compute(runt)

        # If its a secondary prop, there's no optimization
        if runt.snap.model.forms.get(name) is None:
            async for node in runt.snap.getNodesBy(name, valu=valu, cmpr=cmpr):
                yield node
            return

        if cmpr is not None:
            async for node in runt.snap.getNodesBy(name, valu=valu, cmpr=cmpr):
                yield node
            return

        # lifting by a form only is pretty bad, maybe
        # we can pick up a near by filter based hint...
        for oper in self.iterright():

            if isinstance(oper, FiltOper):

                for hint in oper.getLiftHints():

                    if hint[0] == 'tag':
                        tagname = hint[1].get('name')
                        async for node in runt.snap._getNodesByFormTag(name, tagname):
                            yield node
                        return

            # we can skip other lifts but that's it...
            if isinstance(oper, LiftOper):
                continue

            break

        async for node in runt.snap.getNodesBy(name, valu=valu, cmpr=cmpr):
            yield node

class LiftPropBy(LiftOper):

    async def lift(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        valu = await self.kids[2].compute(runt)

        async for node in runt.snap.getNodesBy(name, valu, cmpr=cmpr):
            yield node

class PivotOper(Oper):

    def __init__(self, kids=(), isjoin=False):
        Oper.__init__(self, kids=kids)
        self.isjoin = isjoin

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}, isjoin={self.isjoin}'

    def __repr__(self):
        return self.repr()

class PivotOut(PivotOper):
    '''
    -> *
    '''
    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            # <syn:tag> -> * is "from tags to nodes with tags"
            if node.form.name == 'syn:tag':

                async for pivo in runt.snap._getNodesByTag(node.ndef[1]):
                    yield pivo, path.fork(pivo)

                continue

            if isinstance(node.form.type, s_types.Edge):
                n2def = node.get('n2')
                pivo = await runt.snap.getNodeByNdef(n2def)
                if pivo is None:
                    logger.warning(f'Missing node corresponding to ndef {n2def} on edge')
                    continue
                yield pivo, path.fork(pivo)
                continue

            for name, prop in node.form.props.items():

                valu = node.get(name)
                if valu is None:
                    continue

                # if the outbound prop is an ndef...
                if isinstance(prop.type, s_types.Ndef):
                    pivo = await runt.snap.getNodeByNdef(valu)
                    if pivo is None:
                        continue

                    yield pivo, path.fork(pivo)
                    continue

                form = runt.snap.model.forms.get(prop.type.name)
                if form is None:
                    continue

                pivo = await runt.snap.getNodeByNdef((form.name, valu))
                if pivo is None:
                    continue

                # avoid self references
                if pivo.buid == node.buid:
                    continue

                yield pivo, path.fork(pivo)

class PivotToTags(PivotOper):
    '''
    -> #                pivot to all leaf tag nodes
    -> #*               pivot to all tag nodes
    -> #cno.*           pivot to all tag nodes which match cno.*
    -> #foo.bar         pivot to the tag node foo.bar if present
    '''
    async def run(self, runt, genr):

        leaf = False
        mval = self.kids[0].value()

        if not mval:

            leaf = True

            def filter(x):
                return True

        elif mval.find('*') != -1:

            # glob matcher...
            def filter(x):
                return fnmatch.fnmatch(x, mval)

        else:

            def filter(x):
                return x == mval

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            for name, valu in node.getTags(leaf=leaf):

                if not filter(name):
                    continue

                pivo = await runt.snap.getNodeByNdef(('syn:tag', name))
                if pivo is None:
                    continue

                yield pivo, path.fork(pivo)

class PivotIn(PivotOper):
    '''
    <- *
    '''

    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            # if it's a graph edge, use :n2
            if isinstance(node.form.type, s_types.Edge):

                ndef = node.get('n1')

                pivo = await runt.snap.getNodeByNdef(ndef)
                if pivo is None:
                    continue

                yield pivo, path.fork(pivo)

                continue

            name, valu = node.ndef

            for prop in runt.snap.model.propsbytype.get(name, ()):
                async for pivo in runt.snap.getNodesBy(prop.full, valu):
                    yield pivo, path.fork(pivo)

class PivotInFrom(PivotOper):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        form = runt.snap.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        # <- edge
        if isinstance(form.type, s_types.Edge):

            full = form.name + ':n2'

            async for node, path in genr:

                if self.isjoin:
                    yield node, path

                async for pivo in runt.snap.getNodesBy(full, node.ndef):
                    yield pivo, path.fork(pivo)

            return

        # edge <- form
        async for node, path in genr:

            if self.isjoin:
                yield node, path

            if not isinstance(node.form.type, s_types.Edge):
                continue

            # dont bother traversing edges to the wrong form
            if node.get('n1:form') != form.name:
                continue

            n1def = node.get('n1')

            pivo = await runt.snap.getNodeByNdef(n1def)
            if pivo is None:
                continue

            yield pivo, path.fork(pivo)

class FormPivot(PivotOper):

    async def run(self, runt, genr):
        warned = False
        name = self.kids[0].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        # -> baz:ndef
        if isinstance(prop.type, s_types.Ndef):

            async for node, path in genr:

                if self.isjoin:
                    yield node, path

                async for pivo in runt.snap.getNodesBy(prop.full, node.ndef):
                    yield pivo, path.fork(pivo)

            return

        if not prop.isform:

            # plain old pivot...
            async for node, path in genr:

                if self.isjoin:
                    yield node, path

                valu = node.ndef[1]

                # TODO cache/bypass normalization in loop!
                try:
                    async for pivo in runt.snap.getNodesBy(prop.full, valu):
                        yield pivo, path.fork(pivo)
                except (s_exc.BadTypeValu, s_exc.BadLiftValu) as e:
                    if not warned:
                        logger.warning(f'Caught error during pivot: {e.items()}')
                        warned = True
                    items = e.items()
                    mesg = items.pop('mesg', '')
                    mesg = ': '.join((f'{e.__class__.__qualname__} [{repr(valu)}] during pivot', mesg))
                    await runt.snap.fire('warn', mesg=mesg, **items)

        # form -> form pivot is nonsensical. Lets help out...

        # if dest form is a subtype of a graph "edge", use N1 automatically
        if isinstance(prop.type, s_types.Edge):

            full = prop.name + ':n1'

            async for node, path in genr:

                if self.isjoin:
                    yield node, path

                async for pivo in runt.snap.getNodesBy(full, node.ndef):
                    yield pivo, path.fork(pivo)

            return

        # form name and type name match
        formprop = prop
        destform = prop.name

        # TODO: both of these should be precomputed in the model

        @s_cache.memoize()
        def getsrc(form):
            names = []
            for name, prop in form.props.items():
                if prop.type.name == destform:
                    names.append(name)
            return names

        @s_cache.memoize()
        def getdst(form):
            # formprop is really a form here...
            names = []
            for name, prop in formprop.props.items():
                if prop.type.name == form.type.name:
                    names.append(prop.full)
            return names

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            # <syn:tag> -> <form> is "from tags to nodes" pivot
            if node.form.name == 'syn:tag' and prop.isform:
                async for pivo in runt.snap.getNodesBy(f'{prop.name}#{node.ndef[1]}'):
                    yield pivo, path.fork(pivo)

                continue

            # if the source node is a graph edge, use n2
            if isinstance(node.form.type, s_types.Edge):

                n2def = node.get('n2')
                if n2def[0] != destform:
                    continue

                pivo = await runt.snap.getNodeByNdef(node.get('n2'))
                if pivo:
                    yield pivo, path.fork(pivo)

                continue

            names = getsrc(node.form)
            if names:
                for name in names:

                    valu = node.get(name)
                    if valu is None:
                        continue

                    async for pivo in runt.snap.getNodesBy(prop.name, valu):
                        yield pivo, path.fork(pivo)

                continue

            names = getdst(node.form)
            if names:
                for name in names:
                    valu = node.ndef[1]
                    async for pivo in runt.snap.getNodesBy(name, valu):
                        yield pivo, path.fork(pivo)

                continue

            raise s_exc.NoSuchPivot(n1=node.form.name, n2=destform)

class PropPivotOut(PivotOper):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        warned = False
        async for node, path in genr:

            prop = node.form.props.get(name)
            if prop is None:
                continue

            valu = node.get(name)
            if valu is None:
                continue

            # ndef pivot out syntax...
            # :ndef -> *
            if isinstance(prop.type, s_types.Ndef):
                pivo = await runt.snap.getNodeByNdef(valu)
                if pivo is None:
                    logger.warning(f'Missing node corresponding to ndef {valu}')
                    continue
                yield pivo, path.fork(pivo)
                continue

            # :prop -> *
            fname = prop.type.name
            if prop.modl.form(fname) is None:
                if warned is False:
                    await runt.snap.warn(f'The source property "{name}" type "{fname}" is not a form. Cannot pivot.')
                    warned = True
                continue

            ndef = (fname, valu)
            pivo = await runt.snap.getNodeByNdef(ndef)
            # A node explicitly deleted in the graph or missing from a underlying layer
            # could cause this lift to return None.
            if pivo:
                yield pivo, path.fork(pivo)


class PropPivot(PivotOper):

    async def run(self, runt, genr):
        warned = False
        name = self.kids[1].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        # TODO if we are pivoting to a form, use ndef!

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            valu = await self.kids[0].compute(path)
            if valu is None:
                continue

            # TODO cache/bypass normalization in loop!
            try:
                async for pivo in runt.snap.getNodesBy(prop.full, valu):
                    yield pivo, path.fork(pivo)
            except (s_exc.BadTypeValu, s_exc.BadLiftValu) as e:
                if not warned:
                    logger.warning(f'Caught error during pivot: {e.items()}')
                    warned = True
                items = e.items()
                mesg = items.pop('mesg', '')
                mesg = ': '.join((f'{e.__class__.__qualname__} [{repr(valu)}] during pivot', mesg))
                await runt.snap.fire('warn', mesg=mesg, **items)

class Cond(AstNode):

    def getLiftHints(self):
        return ()

    async def getCondEval(self, runt): # pragma: no cover
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.evaluate()')

class SubqCond(Cond):

    def __init__(self, kids=()):
        Cond.__init__(self, kids=kids)
        self.funcs = {
            '=': self._subqCondEq,
            '>': self._subqCondGt,
            '<': self._subqCondLt,
            '>=': self._subqCondGe,
            '<=': self._subqCondLe,
            '!=': self._subqCondNe,
        }

    async def _runSubQuery(self, runt, node, path):
        size = 1
        genr = agen((node, path))
        async for item in self.kids[0].run(runt, genr):
            yield size, item
            size += 1

    def _subqCondEq(self, runt):

        async def cond(node, path):

            size = 0
            valu = int(await self.kids[2].compute(path))

            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return False

            return size == valu

        return cond

    def _subqCondGt(self, runt):

        async def cond(node, path):

            valu = int(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return True

            return False

        return cond

    def _subqCondLt(self, runt):

        async def cond(node, path):

            valu = int(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    return False

            return True

        return cond

    def _subqCondGe(self, runt):

        async def cond(node, path):

            valu = int(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    return True

            return False

        return cond

    def _subqCondLe(self, runt):

        async def cond(node, path):

            valu = int(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return False

            return True

        return cond

    def _subqCondNe(self, runt):

        async def cond(node, path):

            size = 0
            valu = int(await self.kids[2].compute(path))

            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return True

            return size != valu

        return cond

    async def getCondEval(self, runt):

        if len(self.kids) == 3:
            cmpr = self.kids[1].value()
            ctor = self.funcs.get(cmpr)
            if ctor is None:
                raise s_exc.NoSuchCmpr(cmpr=cmpr, type='subquery')

            return ctor(runt)

        subq = self.kids[0]

        async def cond(node, path):
            genr = agen((node, path))
            async for _ in subq.run(runt, genr):
                return True
            return False

        return cond

class OrCond(Cond):
    '''
    <cond> or <cond>
    '''
    async def getCondEval(self, runt):

        cond0 = await self.kids[0].getCondEval(runt)
        cond1 = await self.kids[1].getCondEval(runt)

        async def cond(node, path):

            if await cond0(node, path):
                return True

            return await cond1(node, path)

        return cond

class AndCond(Cond):
    '''
    <cond> and <cond>
    '''
    def getLiftHints(self):
        h0 = self.kids[0].getLiftHints()
        h1 = self.kids[1].getLiftHints()
        return h0 + h1

    async def getCondEval(self, runt):

        cond0 = await self.kids[0].getCondEval(runt)
        cond1 = await self.kids[1].getCondEval(runt)

        async def cond(node, path):

            if not await cond0(node, path):
                return False

            return await cond1(node, path)

        return cond

class NotCond(Cond):
    '''
    not <cond>
    '''

    async def getCondEval(self, runt):

        kidcond = await self.kids[0].getCondEval(runt)

        async def cond(node, path):
            return not await kidcond(node, path)

        return cond

class TagCond(Cond):
    '''
    #foo.bar
    '''
    def getLiftHints(self):

        kid = self.kids[0]

        if not isinstance(kid, TagMatch):
            # TODO:  we might hint based on variable value
            return ()

        name = kid.value()
        if '*' in name:
            return ()
        return (
            ('tag', {'name': name}),
        )

    async def getCondEval(self, runt):

        assert len(self.kids) == 1
        kid = self.kids[0]
        if isinstance(kid, TagMatch):
            name = self.kids[0].value()
        else:
            # TODO:  enable runtval calc here (variable nodes haven't been evaluated yet)
            # if kid.isRuntSafe(runt):
            #     name = await kid.runtval(runt)
            name = None

        if name is not None:

            # Allow for a user to ask for #* to signify "any tags on this node"
            if name == '*':
                async def cond(node, path):
                    # Check if the tags dictionary has any members
                    return bool(node.tags)
                return cond

            # Allow a user to use tag globbing to do regex matching of a node.
            if '*' in name:
                reobj = s_cache.getTagGlobRegx(name)

                def getIsHit(tag):
                    return reobj.fullmatch(tag)

                # This cache persists per-query
                cache = s_cache.FixedCache(getIsHit)

                async def cond(node, path):
                    return any((cache.get(p) for p in node.tags))

                return cond

            # Default exact match
            async def cond(node, path):
                return node.tags.get(name) is not None

            return cond

        # kid is a non-runtsafe VarValue: dynamically evaluate value of variable for each node
        async def cond(node, path):
            name = await kid.compute(path)

            if name == '*':
                return bool(node.tags)

            if '*' in name:
                reobj = s_cache.getTagGlobRegx(name)
                return any(reobj.fullmatch(p) for p in node.tags)

            return node.tags.get(name) is not None

        return cond

class HasRelPropCond(Cond):

    async def getCondEval(self, runt):

        name = self.kids[0].value()

        async def cond(node, path):
            return node.has(name)

        return cond

class HasAbsPropCond(Cond):

    async def getCondEval(self, runt):

        name = self.kids[0].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        if prop.isform:

            async def cond(node, path):
                return node.form.name == prop.name

            return cond

        async def cond(node, path):

            if node.form.name != prop.form.name:
                return False

            return node.has(prop.name)

        return cond

class AbsPropCond(Cond):

    async def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        ctor = prop.type.getCmprCtor(cmpr)
        if ctor is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr, name=prop.type.name)

        if prop.isform:

            async def cond(node, path):

                if node.ndef[0] != name:
                    return False

                val1 = node.ndef[1]
                val2 = await self.kids[2].compute(path)

                return ctor(val2)(val1)

            return cond

        async def cond(node, path):
            val1 = node.get(prop.name)
            if val1 is None:
                return False

            val2 = await self.kids[2].compute(path)
            return ctor(val2)(val1)

        return cond

class TagValuCond(Cond):

    async def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        ival = runt.snap.model.type('ival')

        cmprctor = ival.getCmprCtor(cmpr)
        if cmprctor is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr, name=ival.name)

        if isinstance(self.kids[2], Const):

            valu = self.kids[2].value()

            cmpr = cmprctor(valu)

            async def cond(node, path):
                return cmpr(node.tags.get(name))

            return cond

        # it's a runtime value...
        async def cond(node, path):
            valu = await self.kids[2].compute(path)
            return cmprctor(valu)(node.tags.get(name))

        return cond

class RelPropCond(Cond):
    '''
    :foo:bar <cmpr> <value>
    '''
    async def getCondEval(self, runt):

        cmpr = self.kids[1].value()

        async def cond(node, path):

            prop, valu = await self.kids[0].getPropAndValu(path)
            if valu is None:
                return False

            xval = await self.kids[2].compute(path)
            ctor = prop.type.getCmprCtor(cmpr)
            if ctor is None:
                raise s_exc.NoSuchCmpr(cmpr=cmpr, name=prop.type.name)
            func = ctor(xval)

            return func(valu)

        return cond

class FiltOper(Oper):

    def getLiftHints(self):

        if self.kids[0].value() != '+':
            return ()

        return self.kids[1].getLiftHints()

    async def run(self, runt, genr):

        must = self.kids[0].value() == '+'
        cond = await self.kids[1].getCondEval(runt)

        async for node, path in genr:
            answ = await cond(node, path)
            if (must and answ) or (not must and not answ):
                yield node, path

class CompValue(AstNode):
    '''
    A computed value which requires a runtime, node, and path.
    '''
    async def compute(self, path): # pragma: no cover
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.compute()')

    def isRuntSafe(self, runt):
        return False

class RunValue(CompValue):
    '''
    A computed value that requires a runtime.
    '''

    async def runtval(self, runt):
        return self.value()

    async def compute(self, path):
        return await self.runtval(path.runt)

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

class Value(RunValue):

    '''
    A fixed/constant value.
    '''
    def __init__(self, valu, kids=()):
        RunValue.__init__(self, kids=kids)
        self.valu = valu

    def repr(self):
        if self.kids:
            return f'{self.__class__.__name__}: {self.valu}, kids={self.kids}'
        else:
            return f'{self.__class__.__name__}: {self.valu}'

    def __repr__(self):
        return self.repr()

    async def runtval(self, runt):
        return self.value()

    async def compute(self, path):
        return self.value()

    def value(self):
        return self.valu

class PropValue(CompValue):

    def prepare(self):
        self.name = self.kids[0].value()
        self.ispiv = self.name.find('::') != -1

    async def getPropAndValu(self, path):

        if not self.ispiv:

            prop = path.node.form.props.get(self.name)
            if prop is None:
                raise s_exc.NoSuchProp(name=self.name)

            valu = path.node.get(self.name)
            return prop, valu

        # handle implicit pivot properties
        names = self.name.split('::')

        node = path.node

        imax = len(names) - 1
        for i, name in enumerate(names):

            valu = node.get(name)
            if valu is None:
                return None, None

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name)

            if i >= imax:
                return prop, valu

            form = path.runt.snap.model.forms.get(prop.type.name)
            if form is None:
                raise s_exc.NoSuchForm(name=prop.type.name)

            node = await path.runt.snap.getNodeByNdef((form.name, valu))
            if node is None:
                return None, None

    async def compute(self, path):
        prop, valu = await self.getPropAndValu(path)
        return valu

class RelPropValue(PropValue): pass
class UnivPropValue(PropValue): pass

class TagPropValue(CompValue):

    async def compute(self, path):
        valu = await self.kids[0].compute(path)
        return path.node.getTag(valu)

class CallArgs(RunValue):

    async def compute(self, path):
        return [await k.compute(path) for k in self.kids]

    async def runtval(self, runt):
        return [await k.runtval(runt) for k in self.kids]

class CallKwarg(CallArgs): pass
class CallKwargs(CallArgs): pass

class VarValue(RunValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def isRuntSafe(self, runt):
        return runt.isRuntVar(self.name)

    async def runtval(self, runt):

        valu = runt.getVar(self.name, defv=s_common.novalu)
        if valu is s_common.novalu:
            raise s_exc.NoSuchVar(name=self.name)

        return valu

    async def compute(self, path):

        valu = path.getVar(self.name, defv=s_common.novalu)
        if valu is s_common.novalu:
            raise s_exc.NoSuchVar(name=self.name)

        return valu

class VarDeref(RunValue):

    async def compute(self, path):
        valu = await self.kids[0].compute(path)
        name = await self.kids[1].compute(path)
        valu = s_stormtypes.fromprim(valu, path=path)
        return valu.deref(name)

    async def runtval(self, runt):
        valu = await self.kids[0].runtval(runt)
        name = await self.kids[1].runtval(runt)
        valu = s_stormtypes.fromprim(valu)
        return valu.deref(name)

class FuncCall(RunValue):

    async def compute(self, path):
        func = await self.kids[0].compute(path)
        argv = await self.kids[1].compute(path)
        kwlist = await self.kids[2].compute(path)
        kwargs = dict(kwlist)
        return await func(*argv, **kwargs)

    async def runtval(self, runt):
        func = await self.kids[0].runtval(runt)
        argv = await self.kids[1].runtval(runt)
        kwlist = await self.kids[2].compute(runt)
        kwargs = dict(kwlist)
        return await func(*argv, **kwargs)

class DollarExpr(RunValue):
    '''
    Top level node for $(...) expressions
    '''
    async def compute(self, path):
        assert len(self.kids) == 1
        return await self.kids[0].compute(path)

    async def runtval(self, runt):
        assert len(self.kids) == 1
        return await self.kids[0].runtval(runt)

_ExprFuncMap = {
    '*': lambda x, y: int(x) * int(y),
    '/': lambda x, y: int(x) // int(y),
    '+': lambda x, y: int(x) + int(y),
    '-': lambda x, y: int(x) - int(y),
    '>': lambda x, y: int(int(x) > int(y)),
    '<': lambda x, y: int(int(x) < int(y)),
    '>=': lambda x, y: int(int(x) >= int(y)),
    '<=': lambda x, y: int(int(x) <= int(y)),
    '==': lambda x, y: int(x == y),
    '!=': lambda x, y: int(x != y),
}

class ExprNode(RunValue):

    def prepare(self):
        # TODO: constant folding
        assert len(self.kids) == 3
        assert isinstance(self.kids[1], Const)
        oper = self.kids[1].value()
        self._operfunc = _ExprFuncMap[oper]

    async def compute(self, path):
        return self._operfunc(await self.kids[0].compute(path), await self.kids[2].compute(path))

    async def runtval(self, runt):
        return self._operfunc(await self.kids[0].runtval(runt), await self.kids[2].runtval(runt))

class VarList(Value):
    pass

class TagName(Value):
    pass

class TagMatch(Value):
    pass

class Cmpr(Value):
    pass

class Const(Value):
    pass

class List(Value):

    def repr(self):
        return 'List: %s' % self.kids

    async def runtval(self, runt):
        return [await k.runtval(runt) for k in self.kids]

    async def compute(self, path):
        return [await k.compute(path) for k in self.kids]

    def value(self):
        return [k.value() for k in self.kids]

class RelProp(Value):
    pass

class UnivProp(Value):
    pass

class AbsProp(Value):
    pass

class Edit(Oper):
    pass

class EditNodeAdd(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        form = runt.snap.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        # the behavior here is a bit complicated...

        # single value add (runtime computed per node )
        # In the cases below, $hehe is input to the storm runtime vars.
        # case 1: [ foo:bar="lols" ]
        # case 2: [ foo:bar=$hehe ]
        # case 2: [ foo:bar=$lib.func(20, $hehe) ]
        # case 3: ($foo, $bar) = $hehe [ foo:bar=($foo, $bar) ]

        # iterative add ( node add is executed once per inbound node )
        # case 1: <query> [ foo:bar=(:baz, 20) ]
        # case 2: <query> [ foo:bar=($node, 20) ]
        # case 2: <query> $blah=:baz [ foo:bar=($blah, 20) ]

        if not self.kids[1].isRuntSafe(runt):

            first = True
            async for node, path in genr:

                # must reach back first to trigger sudo / etc
                if first:
                    runt.allowed('node:add', name)
                    first = False

                yield node, path

                valu = await self.kids[1].compute(path)

                for valu in form.type.getTypeVals(valu):
                    newn = await runt.snap.addNode(name, valu)
                    yield newn, runt.initPath(newn)

        else:

            async for node, path in genr:
                yield node, path

            runt.allowed('node:add', name)

            valu = await self.kids[1].runtval(runt)

            for valu in form.type.getTypeVals(valu):
                node = await runt.snap.addNode(name, valu)
                yield node, runt.initPath(node)

class EditPropSet(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        async for node, path in genr:

            valu = await self.kids[1].compute(path)

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            runt.allowed('prop:set', prop.full)

            await node.set(name, valu)

            yield node, path

class EditPropDel(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        async for node, path in genr:

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            runt.allowed('prop:del', prop.full)

            await node.pop(name)

            yield node, path

class EditUnivDel(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        univ = runt.snap.model.props.get(name)
        if univ is None:
            raise s_exc.NoSuchProp(name=name)

        async for node, path in genr:

            runt.allowed('prop:del', name)

            await node.pop(name)
            yield node, path

class EditTagAdd(Edit):

    async def run(self, runt, genr):

        hasval = len(self.kids) > 1

        valu = (None, None)

        async for node, path in genr:

            name = await self.kids[0].compute(path)
            parts = name.split('.')

            runt.allowed('tag:add', *parts)

            if hasval:
                valu = await self.kids[1].compute(path)

            await node.addTag(name, valu=valu)

            yield node, path

class EditTagDel(Edit):

    async def run(self, runt, genr):

        async for node, path in genr:

            name = await self.kids[0].compute(path)
            parts = name.split('.')

            runt.allowed('tag:del', *parts)

            await node.delTag(name)

            yield node, path

class BreakOper(AstNode):

    async def run(self, runt, genr):

        # we must be a genr...
        for _ in ():
            yield _

        async for node, path in genr:
            raise StormBreak(item=(node, path))

        raise StormBreak()

class ContinueOper(AstNode):

    async def run(self, runt, genr):

        # we must be a genr...
        for _ in ():
            yield _

        async for node, path in genr:
            raise StormContinue(item=(node, path))

        raise StormContinue()
