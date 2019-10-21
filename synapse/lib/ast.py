import asyncio
import fnmatch
import logging
import itertools
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.types as s_types
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

def parseNumber(x):
    return float(x) if '.' in x else s_stormtypes.intify(x)

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

    async def iterNodePaths(self, runt, genr=None):

        count = 0
        subgraph = None

        rules = runt.getOpt('graph')

        if rules not in (False, None):
            if rules is True:
                rules = {'degrees': None, 'pivots': ('-> *',)}

            subgraph = SubGraph(rules)

        self.optimize()

        # turtles all the way down...
        if genr is None:
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

    def __init__(self, kids=()):
        Oper.__init__(self, kids)
        self.hasyield = False

    async def run(self, runt, genr):

        subq = self.kids[0]

        async for item in genr:

            subp = None

            async for subp in subq.run(runt, agen(item)):
                if self.hasyield:
                    yield subp

            # dup any path variables from the last yielded
            if subp is not None:
                item[1].vars.update(subp[1].vars)

            yield item

    async def inline(self, runt, genr):
        '''
        Operate subquery as if it were inlined
        '''
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
        node = None

        async for node, path in genr:

            async for item in s_coro.agen(await self.kids[1].compute(path)):

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
                    async for item in subq.inline(runt, newg):
                        yield item

                except StormBreak as e:
                    if e.item is not None:
                        yield e.item
                    break

                except StormContinue as e:
                    if e.item is not None:
                        yield e.item
                    continue

        # no nodes and a runt safe value should execute once
        if node is None and self.kids[1].isRuntSafe(runt):

            async for item in s_coro.agen(await self.kids[1].runtval(runt)):

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

                except StormBreak as e:
                    if e.item is not None:
                        yield e.item
                    break

                except StormContinue as e:
                    if e.item is not None:
                        yield e.item
                    continue

class WhileLoop(Oper):

    async def run(self, runt, genr):
        subq = self.kids[1]
        node = None

        async for node, path in genr:

            while await self.kids[0].compute(path):
                try:

                    newg = agen((node, path))
                    async for item in subq.inline(runt, newg):
                        yield item

                except StormBreak as e:
                    if e.item is not None:
                        yield e.item
                    break

                except StormContinue as e:
                    if e.item is not None:
                        yield e.item
                    continue

        # no nodes and a runt safe value should execute once
        if node is None and self.kids[0].isRuntSafe(runt):

            while await self.kids[0].runtval(runt):

                try:
                    async for jtem in subq.inline(runt, agen()):
                        yield jtem

                except StormBreak as e:
                    if e.item is not None:
                        yield e.item
                    break

                except StormContinue as e:
                    if e.item is not None:
                        yield e.item
                    continue

                await asyncio.sleep(0)  # give other tasks some CPU

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

        count = 0
        async for node, path in genr:
            count += 1
            valu = await vkid.compute(path)
            path.setVar(name, valu)
            runt.setVar(name, valu)
            yield node, path

        if count == 0 and vkid.isRuntSafe(runt):
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

        anynodes = False
        async for node, path in genr:
            anynodes = True
            await self.kids[0].compute(path)
            yield node, path

        if not anynodes and self.isRuntSafe(runt):
            await self.kids[0].runtval(runt)

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
        count = 0
        async for node, path in genr:
            count += 1

            varv = await self.kids[0].compute(path)

            # TODO:  when we have var type system, do type-aware comparison
            subq = self.cases.get(str(varv))
            if subq is None and self.defcase is not None:
                subq = self.defcase

            if subq is None:
                yield (node, path)
            else:
                async for item in subq.inline(runt, agen((node, path))):
                    yield item

        if count == 0 and self.kids[0].isRuntSafe(runt):
            # no nodes and a runt safe value should execute
            varv = await self.kids[0].runtval(runt)

            subq = self.cases.get(str(varv))
            if subq is None and self.defcase is not None:
                subq = self.defcase

            if subq is None:
                return

            async for item in subq.inline(runt, agen()):
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

class LiftByArray(LiftOper):
    '''
    :prop*[range=(200, 400)]
    '''
    async def lift(self, runt):

        name = await self.kids[0].compute(runt)
        cmpr = await self.kids[1].compute(runt)
        valu = await self.kids[2].compute(runt)

        async for node in runt.snap.getNodesByArray(name, valu, cmpr=cmpr):
            yield node

class LiftTagProp(LiftOper):
    '''
    #foo.bar:baz [ = x ]
    '''
    async def lift(self, runt):

        cmpr = None
        valu = None
        tag, prop = await self.kids[0].compute(runt)

        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt)
            valu = await self.kids[2].compute(runt)

        async for node in runt.snap._getNodesByTagProp(prop, tag=tag, valu=valu, cmpr=cmpr):
            yield node

class LiftFormTagProp(LiftOper):
    '''
    hehe:haha#foo.bar:baz [ = x ]
    '''

    async def lift(self, runt):

        cmpr = None
        valu = None
        form, tag, prop = await self.kids[0].compute(runt)

        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt)
            valu = await self.kids[2].compute(runt)

        async for node in runt.snap._getNodesByTagProp(prop, form=form, tag=tag, valu=valu, cmpr=cmpr):
            yield node

class LiftOnlyTagProp(LiftOper):
    '''
    #:baz [ = x ]
    '''

    async def lift(self, runt):

        cmpr = None
        valu = None
        prop = await self.kids[0].compute(runt)

        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt)
            valu = await self.kids[2].compute(runt)

        async for node in runt.snap._getNodesByTagProp(prop, valu=valu, cmpr=cmpr):
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

        cmpr = '='
        valu = None
        name = await self.kids[0].compute(runt)

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

        cmpr = self.kids[1].value()
        name = await self.kids[0].compute(runt)
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

                if isinstance(prop.type, s_types.Array):
                    typename = prop.type.opts.get('type')
                    if runt.snap.model.forms.get(typename) is not None:
                        for item in valu:
                            async for pivo in runt.snap.getNodesBy(typename, item):
                                yield pivo, path.fork(pivo)

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

        assert len(self.kids) == 1
        kid = self.kids[0]
        assert isinstance(kid, TagMatch)

        if kid.isconst:

            mval = kid.value()

            if not mval:

                leaf = True

                async def filter(x, path):
                    return True

            elif kid.hasglob():

                # glob matcher...
                async def filter(x, path):
                    return fnmatch.fnmatch(x, mval)

            else:

                async def filter(x, path):
                    return x == mval
        else:  # We have a $var as a segment

            if kid.hasglob():

                async def filter(x, path):
                    valu = await kid.compute(path)
                    return fnmatch.fnmatch(x, valu)

            else:

                async def filter(x, path):
                    valu = await kid.compute(path)
                    return x == valu

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            for name, valu in node.getTags(leaf=leaf):

                if not await filter(name, path):
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

            # if it's a graph edge, use :n1
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

            for prop in runt.snap.model.arraysbytype.get(name, ()):
                async for pivo in runt.snap.getNodesByArray(prop.full, valu):
                    yield pivo, path.fork(pivo)

class PivotInFrom(PivotOper):
    '''
    <- foo:edge
    '''

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
    '''
    -> foo:bar
    '''

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

            return

        # if dest form is a subtype of a graph "edge", use N1 automatically
        if isinstance(prop.type, s_types.Edge):

            full = prop.name + ':n1'

            async for node, path in genr:

                if self.isjoin:
                    yield node, path

                async for pivo in runt.snap.getNodesBy(full, node.ndef):
                    yield pivo, path.fork(pivo)

            return

        # form -> form pivot is nonsensical. Lets help out...

        # form name and type name match
        destform = prop

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
                if n2def[0] != destform.name:
                    continue

                pivo = await runt.snap.getNodeByNdef(node.get('n2'))
                if pivo:
                    yield pivo, path.fork(pivo)

                continue

            #########################################################################
            # regular "-> form" pivot (ie inet:dns:a -> inet:fqdn)

            found = False   # have we found a ref/pivot?
            refs = node.form.getRefsOut()
            for refsname, refsform in refs.get('prop'):

                if refsform != destform.name:
                    continue

                found = True

                refsvalu = node.get(refsname)
                if refsvalu is not None:
                    pivo = await runt.snap.getNodeByNdef((refsform, refsvalu))
                    if pivo is not None:
                        yield pivo, path.fork(pivo)

            for refsname, refsform in refs.get('array'):

                if refsform != destform.name:
                    continue

                found = True

                refsvalu = node.get(refsname)
                if refsvalu is not None:
                    for refselem in refsvalu:
                        async for pivo in runt.snap.getNodesBy(destform.name, refselem):
                            yield pivo, path.fork(pivo)

            for refsname in refs.get('ndef'):

                found = True

                refsvalu = node.get(refsname)
                if refsvalu is not None and refsvalu[0] == destform.name:
                    pivo = await runt.snap.getNodeByNdef(refsvalu)
                    if pivo is not None:
                        yield pivo, path.fork(pivo)

            #########################################################################
            # reverse "-> form" pivots (ie inet:fqdn -> inet:dns:a)
            refs = destform.getRefsOut()

            # "reverse" property references...
            for refsname, refsform in refs.get('prop'):

                if refsform != node.form.name:
                    continue

                found = True

                refsprop = destform.props.get(refsname)
                async for pivo in runt.snap.getNodesBy(refsprop.full, node.ndef[1]):
                    yield pivo, path.fork(pivo)

            # "reverse" array references...
            for refsname, refsform in refs.get('array'):

                if refsform != node.form.name:
                    continue

                found = True

                destprop = destform.props.get(refsname)
                async for pivo in runt.snap.getNodesByArray(destprop.full, node.ndef[1]):
                    yield pivo, path.fork(pivo)

            # "reverse" ndef references...
            for refsname in refs.get('ndef'):

                found = True

                refsprop = destform.props.get(refsname)
                async for pivo in runt.snap.getNodesBy(refsprop.full, node.ndef):
                    yield pivo, path.fork(pivo)

            if not found:
                mesg = f'No pivot found for {node.form.name} -> {destform.name}.'
                raise s_exc.NoSuchPivot(n1=node.form.name, n2=destform.name, mesg=mesg)

class PropPivotOut(PivotOper):
    '''
    :prop -> *
    '''
    async def run(self, runt, genr):

        warned = False
        async for node, path in genr:
            name = await self.kids[0].compute(path)

            prop = node.form.props.get(name)
            if prop is None:
                continue

            valu = node.get(name)
            if valu is None:
                continue

            if isinstance(prop.type, s_types.Array):
                fname = prop.type.arraytype.name
                if runt.snap.model.forms.get(fname) is None:
                    if not warned:
                        await runt.snap.warn(f'The source property "{name}" array type "{fname}" is not a form. Cannot pivot.')
                        warned = True
                    continue

                for item in valu:

                    pivo = await runt.snap.getNodeByNdef((fname, item))
                    if pivo is not None:
                        yield pivo, path.fork(pivo)

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
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.getCondEval()')

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
            valu = s_stormtypes.intify(await self.kids[2].compute(path))

            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return False

            return size == valu

        return cond

    def _subqCondGt(self, runt):

        async def cond(node, path):

            valu = s_stormtypes.intify(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return True

            return False

        return cond

    def _subqCondLt(self, runt):

        async def cond(node, path):

            valu = s_stormtypes.intify(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    return False

            return True

        return cond

    def _subqCondGe(self, runt):

        async def cond(node, path):

            valu = s_stormtypes.intify(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    return True

            return False

        return cond

    def _subqCondLe(self, runt):

        async def cond(node, path):

            valu = s_stormtypes.intify(await self.kids[2].compute(path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    return False

            return True

        return cond

    def _subqCondNe(self, runt):

        async def cond(node, path):

            size = 0
            valu = s_stormtypes.intify(await self.kids[2].compute(path))

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

        if not kid.isconst or kid.hasglob():
            return ()

        return (
            ('tag', {'name': kid.value()}),
        )

    async def getCondEval(self, runt):

        assert len(self.kids) == 1
        kid = self.kids[0]

        if isinstance(kid, TagMatch) and kid.isconst:
            name = self.kids[0].value()
        else:
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

        relprop = self.kids[0]
        assert isinstance(relprop, RelProp)

        if relprop.isconst:
            name = relprop.value()

            async def cond(node, path):
                return node.has(name)

            return cond

        # relprop name itself is variable, so dynamically compute

        async def cond(node, path):
            name = await relprop.compute(path)
            return node.has(name)

        return cond

class HasTagPropCond(Cond):

    async def getCondEval(self, runt):

        async def cond(node, path):
            tag, name = await self.kids[0].compute(path)
            return node.hasTagProp(tag, name)

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

class ArrayCond(Cond):

    async def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        async def cond(node, path):

            prop = node.form.props.get(name)
            if prop is None:
                mesg = f'No property named {name}.'
                raise s_exc.NoSuchProp(name=name)

            if not isinstance(prop.type, s_types.Array):
                mesg = f'Array filter syntax is invalid for non-array prop {name}.'
                raise s_exc.BadCmprType(mesg=mesg)

            ctor = prop.type.arraytype.getCmprCtor(cmpr)

            items = node.get(name)
            if items is None:
                return False

            val2 = await self.kids[2].compute(path)
            for item in items:
                if ctor(val2)(item):
                    return True

            return False

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

        lnode, cnode, rnode = self.kids

        ival = runt.snap.model.type('ival')

        cmpr = cnode.value()
        cmprctor = ival.getCmprCtor(cmpr)
        if cmprctor is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr, name=ival.name)

        if isinstance(lnode, VarValue) or not lnode.isconst:
            async def cond(node, path):
                name = await lnode.compute(path)
                valu = await rnode.compute(path)
                return cmprctor(valu)(node.tags.get(name))

            return cond

        name = lnode.value()

        if isinstance(rnode, Const):

            valu = rnode.value()

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

class TagPropCond(Cond):

    async def getCondEval(self, runt):

        cmpr = self.kids[1].value()

        async def cond(node, path):

            tag, name = await self.kids[0].compute(path)

            prop = path.runt.snap.model.getTagProp(name)
            if prop is None:
                mesg = f'No such tag property: {name}'
                raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

            # TODO cache on (cmpr, valu) for perf?
            valu = await self.kids[2].compute(path)

            ctor = prop.type.getCmprCtor(cmpr)
            if ctor is None:
                raise s_exc.NoSuchCmpr(cmpr=cmpr, name=prop.type.name)

            curv = node.getTagProp(tag, name)
            if curv is None:
                return False
            return ctor(valu)(curv)

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

class FiltByArray(FiltOper):
    '''
    +:foo*[^=visi]
    '''

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

    def value(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.value()')

    async def runtval(self, runt):
        return self.value()

    async def compute(self, path):
        return await self.runtval(path.runt)

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

class EmbedQuery(RunValue):

    def __init__(self, text, kids=()):
        AstNode.__init__(self, kids=kids)
        self.text = text

    def isRuntSafe(self, runt):
        return True

    async def runtval(self, runt):
        opts = {'vars': dict(runt.vars)}
        return s_stormtypes.Query(self.text, opts)

    async def compute(self, path):
        opts = {'vars': dict(path.vars)}
        return s_stormtypes.Query(self.text, opts)

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

    async def compute(self, path):
        return self.value()

    def value(self):
        return self.valu

class PropValue(CompValue):

    async def getPropAndValu(self, path):
        name = await self.kids[0].compute(path)

        ispiv = name.find('::') != -1
        if not ispiv:

            prop = path.node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=path.node.form.name)

            valu = path.node.get(name)
            return prop, valu

        # handle implicit pivot properties
        names = name.split('::')

        node = path.node

        imax = len(names) - 1
        for i, name in enumerate(names):

            valu = node.get(name)
            if valu is None:
                return None, None

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

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

class RelPropValue(PropValue):
    pass

class UnivPropValue(PropValue):
    pass

class TagValue(CompValue):

    async def compute(self, path):
        valu = await self.kids[0].compute(path)
        return path.node.getTag(valu)

class TagProp(CompValue):

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

    async def compute(self, path):
        tag = await self.kids[0].compute(path)
        prop = await self.kids[1].compute(path)
        return (tag, prop)

class FormTagProp(CompValue):

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

    async def compute(self, path):
        form = await self.kids[0].compute(path)
        tag = await self.kids[1].compute(path)
        prop = await self.kids[2].compute(path)
        return (form, tag, prop)

class OnlyTagProp(CompValue):

    def isRuntSafe(self, runt):
        return self.kids[0].isRuntSafe(runt)

    async def compute(self, path):
        return await self.kids[0].compute(path)

class TagPropValue(CompValue):
    async def compute(self, path):
        tag, prop = await self.kids[0].compute(path)
        return path.node.getTagProp(tag, prop)

class CallArgs(RunValue):

    async def compute(self, path):
        return [await k.compute(path) for k in self.kids]

    async def runtval(self, runt):
        return [await k.runtval(runt) for k in self.kids]

class CallKwarg(CallArgs):
    pass

class CallKwargs(CallArgs):
    pass

class VarValue(RunValue, Cond):

    async def getCondEval(self, runt):

        async def cond(node, path):
            return await self.compute(path)

        return cond

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
        return await valu.deref(name)

    async def runtval(self, runt):
        valu = await self.kids[0].runtval(runt)
        name = await self.kids[1].runtval(runt)
        valu = s_stormtypes.fromprim(valu)
        return await valu.deref(name)

class FuncCall(RunValue):

    async def compute(self, path):
        func = await self.kids[0].compute(path)
        argv = await self.kids[1].compute(path)
        kwlist = await self.kids[2].compute(path)
        kwargs = dict(kwlist)
        return await s_coro.ornot(func, *argv, **kwargs)

    async def runtval(self, runt):
        func = await self.kids[0].runtval(runt)
        argv = await self.kids[1].runtval(runt)
        kwlist = await self.kids[2].compute(runt)
        kwargs = dict(kwlist)
        return await s_coro.ornot(func, *argv, **kwargs)

class DollarExpr(RunValue, Cond):
    '''
    Top level node for $(...) expressions
    '''
    async def compute(self, path):
        assert len(self.kids) == 1
        return s_stormtypes.intify(await self.kids[0].compute(path))

    async def runtval(self, runt):
        assert len(self.kids) == 1
        return s_stormtypes.intify(await self.kids[0].runtval(runt))

    async def getCondEval(self, runt):

        async def cond(node, path):
            return await self.compute(path)

        return cond

_ExprFuncMap = {
    '*': lambda x, y: x * y,
    '/': lambda x, y: x // y,
    '+': lambda x, y: x + y,
    '-': lambda x, y: x - y,
    '>': lambda x, y: int(x > y),
    '<': lambda x, y: int(x < y),
    '>=': lambda x, y: int(x >= y),
    '<=': lambda x, y: int(x <= y),
    'and': lambda x, y: x and y,
    'or': lambda x, y: x or y,
    '=': lambda x, y: int(x == y),
    '!=': lambda x, y: int(x != y),
}

_UnaryExprFuncMap = {
    'not': lambda x: int(not x),
}

class UnaryExprNode(RunValue):
    '''
    A unary (i.e. single-argument) expression node
    '''
    def prepare(self):
        assert len(self.kids) == 2
        assert isinstance(self.kids[0], Const)
        oper = self.kids[0].value()
        self._operfunc = _UnaryExprFuncMap[oper]

    async def compute(self, path):
        return self._operfunc(await self.kids[1].compute(path))

    async def runtval(self, runt):
        return self._operfunc(await self.kids[1].runtval(runt))

class ExprNode(RunValue):
    '''
    A binary (i.e. two argument) expression node
    '''
    def prepare(self):
        # TODO: constant folding
        assert len(self.kids) == 3
        assert isinstance(self.kids[1], Const)
        oper = self.kids[1].value()
        self._operfunc = _ExprFuncMap[oper]

    def _coerce(self, parm1, parm2):
        '''
        If one parameter is a string and the other is a number, convert the string parameter to a number
        '''
        if isinstance(parm1, str):
            if isinstance(parm2, str):
                return parm1, parm2
            if not isinstance(parm2, (int, float)):
                raise s_exc.BadCmprType(type1=type(parm1).__name__, type2=type(parm2).__name__)

            return parseNumber(parm1), parm2

        if isinstance(parm2, str):
            assert not isinstance(parm1, str)
            if not isinstance(parm1, (int, float)):
                raise s_exc.BadCmprType(type1=type(parm1).__name__, type2=type(parm2).__name__)
            return parm1, parseNumber(parm2)

        return parm1, parm2

    async def compute(self, path):
        parm1 = await self.kids[0].compute(path)
        parm2 = await self.kids[2].compute(path)
        return self._operfunc(*self._coerce(parm1, parm2))

    async def runtval(self, runt):
        parm1 = await self.kids[0].runtval(runt)
        parm2 = await self.kids[2].runtval(runt)
        return self._operfunc(*self._coerce(parm1, parm2))

class VarList(Value):
    pass

class TagName(RunValue):
    def __init__(self, kids=()):
        RunValue.__init__(self, kids)
        self.isconst = not kids or (len(kids) == 1 and isinstance(self.kids[0], Const))

    def value(self):
        assert self.isconst
        return self.kids[0].valu if self.kids else ''

    async def compute(self, path):
        if self.isconst:
            return self.value()
        vals = [(await kid.compute(path)) for kid in self.kids]
        return '.'.join(vals)

class TagMatch(TagName):
    '''
    Like TagName, but can have asterisks
    '''
    def hasglob(self):
        assert self.kids

        return any('*' in kid.valu for kid in self.kids if isinstance(kid, Const))

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

class RelProp(RunValue):

    def __init__(self, kids=()):
        RunValue.__init__(self, kids=kids)
        assert len(kids) == 1
        kid = kids[0]

        if isinstance(kid, Const):
            self.isconst = True
            valu = kid.value()
            self.valu = valu[1:]
            return

        assert isinstance(kid, VarValue)
        self.isconst = False
        self.valu = s_common.novalu

    def value(self):
        assert self.isconst
        return self.valu

    async def runtval(self, runt):
        if self.isconst:
            return self.value()
        return await self.kids[0].runtval(runt)

class UnivProp(RelProp):
    async def runtval(self, runt):
        if self.isconst:
            return self.value()
        return '.' + await self.kids[0].runtval(runt)

    def value(self):
        assert self.isconst
        return '.' + self.valu

class AbsProp(Value):
    pass

class Edit(Oper):
    pass

class EditParens(Edit):
    async def run(self, runt, genr):

        nodeadd = self.kids[0]
        assert isinstance(nodeadd, EditNodeAdd)

        if not nodeadd.isruntsafe(runt):
            mesg = 'First node add in edit parentheses must not be dependent on incoming nodes'
            raise s_exc.StormRuntimeError(mesg=mesg)

        # Luke, let the nodes flow through you
        async for item in genr:
            yield item

        # Run the opers once with no incoming nodes
        genr = agen()

        for oper in self.kids:
            genr = oper.run(runt, genr)

        async for item in genr:
            yield item

class EditNodeAdd(Edit):

    def isruntsafe(self, runt):
        return self.kids[2].isRuntSafe(runt)

    async def run(self, runt, genr):

        name = self.kids[0].value()
        oper = self.kids[1].value()
        excignore = (s_exc.BadTypeValu, s_exc.BadPropValu) if oper == '?=' else ()

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

        if not self.isruntsafe(runt):

            first = True
            async for node, path in genr:

                # must reach back first to trigger sudo / etc
                if first:
                    runt.allowed('node:add', name)
                    first = False

                yield node, path

                valu = await self.kids[2].compute(path)

                for valu in form.type.getTypeVals(valu):
                    try:
                        newn = await runt.snap.addNode(name, valu)
                    except excignore:
                        pass
                    else:
                        yield newn, runt.initPath(newn)

        else:
            async for node, path in genr:
                yield node, path

            runt.allowed('node:add', name)

            valu = await self.kids[2].runtval(runt)

            for valu in form.type.getTypeVals(valu):
                try:
                    node = await runt.snap.addNode(name, valu)
                except excignore:
                    continue
                yield node, runt.initPath(node)

class EditPropSet(Edit):

    async def run(self, runt, genr):

        oper = self.kids[1].value()
        excignore = (s_exc.BadTypeValu, s_exc.BadPropValu) if oper == '?=' else ()

        async for node, path in genr:
            name = await self.kids[0].compute(path)
            valu = await self.kids[2].compute(path)

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            # runt node property permissions are enforced by the callback
            if not node.isrunt:
                runt.allowed('prop:set', prop.full)

            try:
                await node.set(name, valu)
            except excignore:
                pass

            yield node, path

class EditPropDel(Edit):

    async def run(self, runt, genr):

        async for node, path in genr:
            name = await self.kids[0].compute(path)

            prop = node.form.props.get(name)
            if prop is None:
                raise s_exc.NoSuchProp(name=name, form=node.form.name)

            runt.allowed('prop:del', prop.full)

            await node.pop(name)

            yield node, path

class EditUnivDel(Edit):

    async def run(self, runt, genr):

        univprop = self.kids[0]
        assert isinstance(univprop, UnivProp)
        if univprop.isconst:
            name = self.kids[0].value()

            univ = runt.snap.model.props.get(name)
            if univ is None:
                raise s_exc.NoSuchProp(name=name)

        async for node, path in genr:
            if not univprop.isconst:
                name = await univprop.compute(path)

                univ = runt.snap.model.props.get(name)
                if univ is None:
                    raise s_exc.NoSuchProp(name=name)

            runt.allowed('prop:del', name)

            await node.pop(name)
            yield node, path

class EditTagAdd(Edit):

    async def run(self, runt, genr):

        hasval = len(self.kids) > 1

        valu = (None, None)

        async for node, path in genr:

            names = await self.kids[0].compute(path)
            if not isinstance(names, list):
                names = [names]

            for name in names:
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

class EditTagPropSet(Edit):
    '''
    [ #foo.bar:baz=10 ]
    '''
    async def run(self, runt, genr):

        oper = self.kids[1].value()
        excignore = (s_exc.BadTypeValu, s_exc.BadPropValu) if oper == '?=' else ()

        async for node, path in genr:

            tag, prop = await self.kids[0].compute(path)
            valu = await self.kids[2].compute(path)

            tagparts = tag.split('.')

            # for now, use the tag add perms
            runt.allowed('tag:add', *tagparts)

            try:
                await node.setTagProp(tag, prop, valu)
            except asyncio.CancelledError: # pragma: no cover
                raise
            except excignore:
                pass

            yield node, path

class EditTagPropDel(Edit):
    '''
    [ -#foo.bar:baz ]
    '''
    async def run(self, runt, genr):

        async for node, path in genr:

            tag, prop = await self.kids[0].compute(path)

            tagparts = tag.split('.')

            # for now, use the tag add perms
            runt.allowed('tag:del', *tagparts)

            await node.delTagProp(tag, prop)

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

class IfClause(AstNode):
    pass

class IfStmt(Oper):

    def prepare(self):
        if isinstance(self.kids[-1], IfClause):
            self.elsequery = None
            self.clauses = self.kids
        else:
            self.elsequery = self.kids[-1]
            self.clauses = self.kids[:-1]

    async def _runtsafe_calc(self, runt):
        '''
        All conditions are runtsafe: figure out which clause wins
        '''
        for clause in self.clauses:
            expr, subq = clause.kids

            exprvalu = await expr.runtval(runt)
            if exprvalu:
                return subq
        else:
            return self.elsequery

    async def run(self, runt, genr):
        count = 0

        allcondsafe = all(clause.kids[0].isRuntSafe(runt) for clause in self.clauses)

        async for node, path in genr:
            count += 1

            if allcondsafe:
                if count == 1:
                    subq = await self._runtsafe_calc(runt)
            else:

                for clause in self.clauses:
                    expr, subq = clause.kids

                    exprvalu = await expr.compute(path)
                    if exprvalu:
                        break
                else:
                    subq = self.elsequery

            if subq:
                assert isinstance(subq, SubQuery)

                async for item in subq.inline(runt, agen((node, path))):
                    yield item
            else:
                # If none of the if branches were executed and no else present, pass the stream through unaltered
                yield node, path

        if count != 0 or not allcondsafe:
            return
        # no nodes and a runt safe value should execute the winning clause once
        subq = await self._runtsafe_calc(runt)

        if subq:
            async for item in subq.inline(runt, agen()):
                yield item
