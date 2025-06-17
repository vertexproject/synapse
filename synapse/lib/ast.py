import types
import asyncio
import decimal
import fnmatch
import hashlib
import logging
import binascii
import itertools
import contextlib
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope
import synapse.lib.types as s_types
import synapse.lib.scrape as s_scrape
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

from synapse.lib.stormtypes import tobool, toint, toprim, tostr, tonumber, tocmprvalu, undef

SET_ALWAYS = 0
SET_UNSET = 1
SET_NEVER = 2

COND_EDIT_SET = {
    'always': SET_ALWAYS,
    'unset': SET_UNSET,
    'never': SET_NEVER,
}

logger = logging.getLogger(__name__)

def parseNumber(x):
    return s_stormtypes.Number(x) if '.' in x else s_stormtypes.intify(x)

class AstNode:
    '''
    Base class for all nodes in the Storm abstract syntax tree.
    '''
    # set to True if recursive runt-safety checks should *not* recurse
    # into children of this node.
    runtopaque = False

    def __init__(self, astinfo, kids=()):
        self.kids = []
        self.astinfo = astinfo
        self.hasast = {}
        [self.addKid(k) for k in kids]

    def getAstText(self):
        return self.astinfo.text[self.astinfo.soff:self.astinfo.eoff]

    def getPosInfo(self):
        return {
            'hash': s_common.queryhash(self.astinfo.text),
            'lines': (self.astinfo.sline, self.astinfo.eline),
            'columns': (self.astinfo.scol, self.astinfo.ecol),
            'offsets': (self.astinfo.soff, self.astinfo.eoff),
        }

    def addExcInfo(self, exc):
        if 'highlight' not in exc.errinfo:
            exc.set('highlight', self.getPosInfo())
        return exc

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
        [k.init(core) for k in self.kids]
        self.prepare()

    def validate(self, runt):
        [k.validate(runt) for k in self.kids]

    def prepare(self):
        pass

    def hasAstClass(self, clss):
        if (hasast := self.hasast.get(clss)) is not None:
            return hasast

        retn = self._hasAstClass(clss)
        self.hasast[clss] = retn
        return retn

    def _hasAstClass(self, clss):

        for kid in self.kids:

            if isinstance(kid, clss):
                return True

            if isinstance(kid, (Edit, Function, CmdOper, SetVarOper, SetItemOper, VarListSetOper, Value, N1Walk, LiftOper)):
                continue

            if kid.hasAstClass(clss):
                return True

        return False

    def optimize(self):
        [k.optimize() for k in self.kids]

    def __iter__(self):
        for kid in self.kids:
            yield kid

    def getRuntVars(self, runt):
        for kid in self.kids:
            yield from kid.getRuntVars(runt)

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

    def isRuntSafeAtom(self, runt):
        return True

    def reqRuntSafe(self, runt, mesg):

        todo = collections.deque([self])

        # depth first search for an non-runtsafe atom.
        while todo:

            nkid = todo.popleft()
            if not nkid.isRuntSafeAtom(runt):
                raise nkid.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            if nkid.runtopaque:
                continue

            todo.extend(nkid.kids)

    def reqNotReadOnly(self, runt, mesg=None):
        if runt.readonly:
            if mesg is None:
                mesg = 'Storm runtime is in readonly mode, cannot create or edit nodes and other graph data.'
            raise self.addExcInfo(s_exc.IsReadOnly(mesg=mesg))

    def hasVarName(self, name):
        return any(k.hasVarName(name) for k in self.kids)

class LookList(AstNode): pass

class Query(AstNode):

    def __init__(self, astinfo, kids=()):

        AstNode.__init__(self, astinfo, kids=kids)

        # for options parsed from the query itself
        self.opts = {}
        self.text = self.getAstText()

    async def run(self, runt, genr):

        with s_scope.enter({'runt': runt}):
            async with contextlib.AsyncExitStack() as stack:
                for oper in self.kids:
                    genr = await stack.enter_async_context(contextlib.aclosing(oper.run(runt, genr)))

                async for node, path in genr:
                    yield node, path

    async def iterNodePaths(self, runt, genr=None):

        self.optimize()
        self.validate(runt)

        # turtles all the way down...
        if genr is None:
            genr = runt.getInput()

        count = 0
        limit = runt.getOpt('limit')

        async with contextlib.aclosing(self.run(runt, genr)) as agen:
            async for node, path in agen:

                yield node, path

                if limit is not None:
                    count += 1
                    if count >= limit:
                        break

class Lookup(Query):
    '''
    When storm input mode is "lookup"
    '''
    def __init__(self, astinfo, kids, autoadd=False):
        Query.__init__(self, astinfo, kids=kids)
        self.autoadd = autoadd

    async def run(self, runt, genr):

        if self.autoadd:
            self.reqNotReadOnly(runt)

        async def getnode(form, valu):
            try:
                if self.autoadd:
                    runt.layerConfirm(('node', 'add', form))
                    return await runt.view.addNode(form, valu)
                else:
                    norm, info = runt.model.form(form).type.norm(valu)
                    node = await runt.view.getNodeByNdef((form, norm))
                    if node is None:
                        await runt.bus.fire('look:miss', ndef=(form, norm))
                    return node
            except s_exc.BadTypeValu:
                return None

        async def lookgenr():

            async for item in genr:
                yield item

            tokns = [await kid.compute(runt, None) for kid in self.kids[0]]
            if not tokns:
                return

            for tokn in tokns:
                async for form, valu in s_scrape.scrapeAsync(tokn, first=True):
                    node = await getnode(form, valu)
                    if node is not None:
                        yield node, runt.initPath(node)

        realgenr = lookgenr()
        if len(self.kids) > 1:
            realgenr = self.kids[1].run(runt, realgenr)

        with s_scope.enter({'runt': runt}):
            async for node, path in realgenr:
                yield node, path

class Search(Query):

    async def run(self, runt, genr):

        view = runt.view

        if not view.core.stormiface_search:
            await runt.warn('Storm search interface is not enabled!', log=False)
            return

        async def searchgenr():

            async for item in genr:
                yield item

            tokns = [await kid.compute(runt, None) for kid in self.kids[0]]
            if not tokns:
                return

            async with await s_spooled.Set.anit(dirn=runt.view.core.dirn, cell=runt.view.core) as buidset:

                todo = s_common.todo('search', tokns)
                async for (prio, buid) in view.mergeStormIface('search', todo):
                    if buid in buidset:
                        await asyncio.sleep(0)
                        continue

                    await buidset.add(buid)
                    node = await runt.view.getNodeByBuid(buid)
                    if node is not None:
                        yield node, runt.initPath(node)

        realgenr = searchgenr()
        if len(self.kids) > 1:
            realgenr = self.kids[1].run(runt, realgenr)

        with s_scope.enter({'runt': runt}):
            async for node, path in realgenr:
                yield node, path

class SubGraph:
    '''
    An Oper like object which generates a subgraph.

    Notes:

        The rules format for the subgraph is shaped like the following::

                rules = {

                    'degrees': 1,

                    'edges': True,
                    'edgelimit': 3000,
                    'filterinput': True,
                    'yieldfiltered': False,

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

        All nodes have path.meta('edges') which is a list of (nid, info) tuples.

    '''

    def __init__(self, rules):

        self.omits = {}
        self.rules = rules

        self.graphnodes = set([s_common.uhex(b) for b in rules.get('graphnodes', ())])
        self.maxsize = min(rules.get('maxsize', 100000), 100000)

        self.rules.setdefault('forms', {})
        self.rules.setdefault('pivots', ())
        self.rules.setdefault('filters', ())
        self.rules.setdefault('existing', ())

        self.rules.setdefault('refs', True)
        self.rules.setdefault('edges', True)
        self.rules.setdefault('degrees', 1)
        self.rules.setdefault('maxsize', 100000)
        self.rules.setdefault('edgelimit', 3000)

        self.rules.setdefault('filterinput', True)
        self.rules.setdefault('yieldfiltered', False)

    async def omit(self, runt, node):

        answ = self.omits.get(node.nid)
        if answ is not None:
            return answ

        for filt in self.rules.get('filters'):
            if await node.filter(runt, filt):
                self.omits[node.nid] = True
                return True

        rules = self.rules['forms'].get(node.form.name)
        if rules is None:
            rules = self.rules['forms'].get('*')

        if rules is None:
            self.omits[node.nid] = False
            return False

        for filt in rules.get('filters', ()):
            if await node.filter(runt, filt):
                self.omits[node.nid] = True
                return True

        self.omits[node.nid] = False
        return False

    async def pivots(self, runt, node, path, existing):

        if self.rules.get('refs'):

            for formname, (cmpr, func) in node.form.type.pivs.items():
                valu = func(node.ndef[1])
                link = {'type': 'type'}
                async for pivonode in node.view.nodesByPropValu(formname, cmpr, valu, norm=False):
                    yield pivonode, path.fork(pivonode, link), link

            for propname, ndef in node.getNodeRefs():
                pivonode = await node.view.getNodeByNdef(ndef)
                if pivonode is None:  # pragma: no cover
                    await asyncio.sleep(0)
                    continue

                link = {'type': 'prop', 'prop': propname}
                yield (pivonode, path.fork(pivonode, link), link)

            for nid in existing:
                othr = await node.view.getNodeByNid(s_common.int64en(nid))
                for propname, ndef in othr.getNodeRefs():
                    if ndef == node.ndef:
                        yield (othr, path, {'type': 'prop', 'prop': propname, 'reverse': True})

        for pivq in self.rules.get('pivots'):
            indx = 0
            async for node, path in node.storm(runt, pivq):
                yield node, path, {'type': 'rules', 'scope': 'global', 'index': indx}
                indx += 1

        scope = node.form.name

        rules = self.rules['forms'].get(scope)
        if rules is None:
            scope = '*'
            rules = self.rules['forms'].get(scope)

        if rules is None:
            return

        for pivq in rules.get('pivots', ()):
            indx = 0
            async for n, p in node.storm(runt, pivq):
                yield (n, p, {'type': 'rules', 'scope': scope, 'index': indx})
                indx += 1

    async def _edgefallback(self, runt, results, node):
        async for nid1 in results:
            await asyncio.sleep(0)
            intnid1 = s_common.int64un(nid1)

            async for verb in node.iterEdgeVerbs(nid1):
                await asyncio.sleep(0)
                yield (intnid1, {'type': 'edge', 'verb': verb})

            # for existing nodes, we need to add n2 -> n1 edges in reverse
            async for verb in runt.view.iterEdgeVerbs(nid1, node.nid):
                await asyncio.sleep(0)
                yield (intnid1, {'type': 'edge', 'verb': verb, 'reverse': True})

    async def run(self, runt, genr):

        # NOTE: this function must agressively yield the ioloop

        edgelimit = self.rules.get('edgelimit')
        doedges = self.rules.get('edges')
        degrees = self.rules.get('degrees')
        maxsize = self.rules.get('maxsize')
        existing = self.rules.get('existing')
        filterinput = self.rules.get('filterinput')
        yieldfiltered = self.rules.get('yieldfiltered')

        self.user = runt.user

        todo = collections.deque()

        async with contextlib.AsyncExitStack() as stack:
            core = runt.view.core

            done = await stack.enter_async_context(await s_spooled.Set.anit(dirn=core.dirn, cell=core))
            intodo = await stack.enter_async_context(await s_spooled.Set.anit(dirn=core.dirn, cell=core))
            results = await stack.enter_async_context(await s_spooled.Set.anit(dirn=core.dirn, cell=core))
            revpivs = await stack.enter_async_context(await s_spooled.Dict.anit(dirn=core.dirn, cell=core))

            revedge = await stack.enter_async_context(await s_spooled.Dict.anit(dirn=core.dirn, cell=core))
            n1delayed = await stack.enter_async_context(await s_spooled.Set.anit(dirn=core.dirn, cell=core))

            # load the existing graph as already done
            for nid in existing:
                nid = s_common.int64en(nid)
                await results.add(nid)

                if doedges:
                    if runt.view.getEdgeCount(nid) > edgelimit:
                        # We've hit a potential death star and need to deal with it specially
                        await n1delayed.add(nid)
                        continue

                    async for verb, n2nid in runt.view.iterNodeEdgesN1(nid):
                        await asyncio.sleep(0)

                        if n2nid in results:
                            continue

                        if (re := revedge.get(n2nid)) is None:
                            re = {nid: [verb]}
                        elif nid not in re:
                            re[nid] = [verb]
                        else:
                            re[nid].append(verb)

                        await revedge.set(n2nid, re)

            async def todogenr():

                async for node, path in genr:
                    path.meta('graph:seed', True)
                    yield node, path, 0

                while todo:
                    yield todo.popleft()

            count = 0
            async for node, path, dist in todogenr():

                await asyncio.sleep(0)

                nid = node.nid
                if nid in done:
                    continue

                count += 1

                if count > maxsize:
                    await runt.warn(f'Graph projection hit max size {maxsize}. Truncating results.')
                    break

                await done.add(nid)
                intodo.discard(nid)

                omitted = False
                if dist > 0 or filterinput:
                    omitted = await self.omit(runt, node)

                    if omitted and not yieldfiltered:
                        continue

                # we must traverse the pivots for the node *regardless* of degrees
                # due to needing to tie any leaf nodes to nodes that were already yielded

                intnid = s_common.int64un(node.nid)
                edges = list(revpivs.get(nid, defv=()))
                async for pivn, pivp, pinfo in self.pivots(runt, node, path, existing):

                    await asyncio.sleep(0)

                    if results.has(pivn.nid):
                        edges.append((s_common.int64un(pivn.nid), pinfo))
                    else:
                        pinfo['reverse'] = True
                        pivedges = revpivs.get(pivn.nid, defv=())
                        await revpivs.set(pivn.nid, pivedges + ((intnid, pinfo),))

                    # we dont pivot from omitted nodes
                    if omitted:
                        continue

                    # no need to pivot to nodes we already did
                    if pivn.nid in done:
                        continue

                    # no need to queue up todos that are already in todo
                    if pivn.nid in intodo:
                        continue

                    # no need to pivot to existing nodes
                    if s_common.int64un(pivn.nid) in existing:
                        continue

                    # do we have room to go another degree out?
                    if degrees is None or dist < degrees:
                        todo.append((pivn, pivp, dist + 1))
                        await intodo.add(pivn.nid)

                if doedges:
                    await results.add(nid)

                    if runt.view.getEdgeCount(nid) > edgelimit:
                        # The current node in the pipeline has too many edges from it, so it's
                        # less prohibitive to just check against the graph
                        await n1delayed.add(nid)
                        async for e in self._edgefallback(runt, results, node):
                            edges.append(e)

                    else:
                        # Try to lift and cache the potential edges for a node so that if we end up
                        # seeing n2 later, we won't have to go back and check for it
                        async for verb, n2nid in runt.view.iterNodeEdgesN1(nid):
                            await asyncio.sleep(0)

                            if (re := revedge.get(n2nid)) is None:
                                re = {nid: [verb]}
                            elif nid not in re:
                                re[nid] = [verb]
                            else:
                                re[nid].append(verb)

                            await revedge.set(n2nid, re)

                            if n2nid in results:
                                edges.append((s_common.int64un(n2nid), {'type': 'edge', 'verb': verb}))

                        if revedge.has(nid):
                            for n2nid, verbs in revedge.get(nid).items():
                                n2intnid = s_common.int64un(n2nid)

                                for verb in verbs:
                                    await asyncio.sleep(0)
                                    edges.append((n2intnid, {'type': 'edge', 'verb': verb, 'reverse': True}))

                        async for n1nid in n1delayed:
                            n1intnid = s_common.int64un(n1nid)

                            async for verb in runt.view.iterEdgeVerbs(n1nid, nid):
                                await asyncio.sleep(0)
                                edges.append((n1intnid, {'type': 'edge', 'verb': verb, 'reverse': True}))

                path.metadata['edges'] = edges
                yield node, path

class Oper(AstNode):

    async def yieldFromValu(self, runt, valu, vkid):

        viewiden = runt.view.iden

        # there is nothing in None... ;)
        if valu is None:
            return

        # a little DWIM on what we get back...
        # ( most common case will be stormtypes libs agenr -> nid )
        # nid -> node
        if isinstance(valu, int):
            if (node := await runt.view.getNodeByNid(s_common.int64en(valu))) is not None:
                yield node

            return

        # buid list -> nodes
        if isinstance(valu, bytes):
            if (node := await runt.view.getNodeByBuid(valu)) is not None:
                yield node

            return

        # iden list -> nodes
        if isinstance(valu, str):
            try:
                buid = s_common.uhex(valu)
            except binascii.Error:
                mesg = 'Yield string must be iden in hexdecimal. Got: %r' % (valu,)
                raise vkid.addExcInfo(s_exc.BadLiftValu(mesg=mesg))

            node = await runt.view.getNodeByBuid(buid)
            if node is not None:
                yield node

            return

        if isinstance(valu, types.AsyncGeneratorType):
            try:
                async for item in valu:
                    async for node in self.yieldFromValu(runt, item, vkid):
                        yield node
            finally:
                await valu.aclose()
            return

        if isinstance(valu, types.GeneratorType):
            try:
                for item in valu:
                    async for node in self.yieldFromValu(runt, item, vkid):
                        yield node
            finally:
                valu.close()
            return

        if isinstance(valu, (list, tuple, set)):
            for item in valu:
                async for node in self.yieldFromValu(runt, item, vkid):
                    yield node
            return

        if isinstance(valu, s_stormtypes.Node):
            valu = valu.valu
            if valu.view.iden != viewiden:
                mesg = f'Node is not from the current view. Node {valu.iden()} is from {valu.view.iden} expected {viewiden}'
                raise vkid.addExcInfo(s_exc.BadLiftValu(mesg=mesg))
            yield valu
            return

        if isinstance(valu, s_node.Node):
            if valu.view.iden != viewiden:
                mesg = f'Node is not from the current view. Node {valu.iden()} is from {valu.view.iden} expected {viewiden}'
                raise vkid.addExcInfo(s_exc.BadLiftValu(mesg=mesg))
            yield valu
            return

        if isinstance(valu, (s_stormtypes.List, s_stormtypes.Set)):
            for item in valu.valu:
                async for node in self.yieldFromValu(runt, item, vkid):
                    yield node
            return

        if isinstance(valu, s_stormtypes.Prim):
            async with contextlib.aclosing(valu.nodes()) as genr:
                async for node in genr:
                    if node.view.iden != viewiden:
                        mesg = f'Node is not from the current view. Node {node.iden()} is from {node.view.iden} expected {viewiden}'
                        raise vkid.addExcInfo(s_exc.BadLiftValu(mesg=mesg))
                    yield node
                return

class SubQuery(Oper):

    def __init__(self, astinfo, kids=()):
        Oper.__init__(self, astinfo, kids)
        self.hasyield = False
        self.hasretn = self.hasAstClass(Return)

        self.text = ''
        if len(kids):
            self.text = kids[0].getAstText()

    def isRuntSafe(self, runt):
        return True

    async def run(self, runt, genr):

        subq = self.kids[0]

        async for item in genr:

            subp = None

            async for subp in subq.run(runt, s_common.agen(item)):
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

    async def _compute(self, runt, path, limit):

        retn = []

        async with runt.getSubRuntime(self.kids[0]) as runt:
            async for valunode, valupath in runt.execute():

                retn.append(valunode)

                if len(retn) > limit:
                    query = self.kids[0].text
                    mesg = f'Subquery used as a value yielded too many (>{limit}) nodes. {s_common.trimText(query)}'
                    raise self.addExcInfo(s_exc.BadTypeValu(mesg=mesg, text=query))

        return retn

    async def compute(self, runt, path):
        '''
        Use subquery as a value.  It is error if the subquery used in this way doesn't yield exactly one node or has a
        return statement.

        Its value is the primary property of the node yielded, or the returned value.
        '''
        try:
            retn = await self._compute(runt, path, 1)

        except s_stormctrl.StormReturn as e:
            # a subquery assignment with a return; just use the returned value
            return e.item

        if retn == []:
            return None

        return retn[0]

    async def compute_array(self, runt, path):
        '''
        Use subquery as an array.
        '''
        try:
            return await self._compute(runt, path, 128)
        except s_stormctrl.StormReturn as e:
            # a subquery assignment with a return; just use the returned value
            return e.item


class InitBlock(AstNode):
    '''
    An AST node that runs only once before yielding nodes.

    Example:

        Using a init block::

            init {
                // stuff here runs *once* before the first node yield (even if there are no nodes)
            }

    '''

    async def run(self, runt, genr):

        subq = self.kids[0]
        self.reqRuntSafe(runt, 'Init block query must be runtsafe')

        once = False
        async for item in genr:

            if not once:
                async for innr in subq.run(runt, s_common.agen()):
                    yield innr

                once = True

            yield item

        if not once:
            async for innr in subq.run(runt, s_common.agen()):
                yield innr

class EmptyBlock(AstNode):
    '''
    An AST node that only runs if there are not inbound nodes in the pipeline. It is
    capable of yielding nodes into the pipeline.

    Example:

        Using an empty block::

            empty {
                // the pipeline is empty so this block will execute
            }

            [foo:bar=*]
            empty {
                // there is a node in the pipeline so this block will not run
            }
    '''
    async def run(self, runt, genr):

        subq = self.kids[0]
        self.reqRuntSafe(runt, 'Empty block query must be runtsafe')

        empty = True
        async for item in genr:
            empty = False
            yield item

        if empty:
            async for subn in subq.run(runt, s_common.agen()):
                yield subn

class FiniBlock(AstNode):
    '''
    An AST node that runs only once after all nodes have been consumed.

    Example:

        Using a fini block::

            fini {
               // stuff here runs *once* after the last node yield (even if there are no nodes)
            }

    Notes:
        A fini block must be runtsafe.

    '''

    async def run(self, runt, genr):

        subq = self.kids[0]

        self.reqRuntSafe(runt, 'Fini block query must be runtsafe')

        async for item in genr:
            yield item

        async for innr in subq.run(runt, s_common.agen()):
            yield innr

class TryCatch(AstNode):

    async def run(self, runt, genr):

        count = 0
        async for item in genr:
            count += 1
            try:
                agen = s_common.agen(item)
                async for subi in self.kids[0].run(runt, agen):
                    yield subi

            except s_exc.SynErr as e:
                block = await self.getCatchBlock(e.errname, runt, path=item[1])
                if block is None:
                    raise

                await item[1].setVar(block.errvar(), await self.getErrValu(e))

                agen = s_common.agen(item)
                async for subi in block.run(runt, agen):
                    yield subi

        if count == 0:
            try:
                async for item in self.kids[0].run(runt, genr):
                    yield item

            except s_exc.SynErr as e:
                block = await self.getCatchBlock(e.errname, runt)
                if block is None:
                    raise

                await runt.setVar(block.errvar(), await self.getErrValu(e))
                async for item in block.run(runt, s_common.agen()):
                    yield item

    async def getErrValu(self, e):
        mesg = e.errinfo.pop('mesg', 'No message given.')
        info = await s_stormtypes.toprim(e.errinfo)
        return {'name': e.errname, 'mesg': mesg, 'info': info}

    async def getCatchBlock(self, name, runt, path=None):
        for catchblock in self.kids[1:]:
            if await catchblock.catches(name, runt, path=path):
                return catchblock

class CatchBlock(AstNode):

    def _hasAstClass(self, clss):
        return self.kids[1].hasAstClass(clss)

    async def run(self, runt, genr):
        async for item in self.kids[2].run(runt, genr):
            yield item

    def getRuntVars(self, runt):
        yield (self.errvar(), True)
        yield from self.kids[2].getRuntVars(runt)

    def errvar(self):
        return self.kids[1].value()

    async def catches(self, name, runt, path=None):

        catchvalu = await self.kids[0].compute(runt, path)
        catchvalu = await s_stormtypes.toprim(catchvalu)

        if isinstance(catchvalu, str):
            if catchvalu == '*':
                return True
            return catchvalu == name

        if isinstance(catchvalu, (list, tuple)):
            for catchname in catchvalu:
                if catchname == name:
                    return True
            return False

        etyp = catchvalu.__class__.__name__
        mesg = f'catch block must be a str or list object. {etyp} not allowed.'
        raise self.kids[0].addExcInfo(s_exc.StormRuntimeError(mesg=mesg, type=etyp))

class ForLoop(Oper):

    def _hasAstClass(self, clss):
        return self.kids[2].hasAstClass(clss)

    def getRuntVars(self, runt):

        runtsafe = self.kids[1].isRuntSafe(runt)

        if isinstance(self.kids[0], VarList):
            for name in self.kids[0].value():
                yield name, runtsafe

        else:
            yield self.kids[0].value(), runtsafe

        yield from self.kids[2].getRuntVars(runt)

    async def run(self, runt, genr):

        subq = self.kids[2]
        name = self.kids[0].value()
        node = None

        async for node, path in genr:

            # TODO: remove when storm is all objects
            valu = await self.kids[1].compute(runt, path)

            if isinstance(valu, s_stormtypes.Prim):
                # returns an async genr instance...
                valu = valu.iter()

            if isinstance(valu, dict):
                valu = list(valu.items())

            if valu is None:
                valu = ()

            async with contextlib.aclosing(s_coro.agen(valu)) as agen:

                try:
                    agen, _ = await pullone(agen)
                except TypeError:
                    styp = await s_stormtypes.totype(valu, basetypes=True)
                    mesg = f"'{styp}' object is not iterable: {s_common.trimText(repr(valu))}"
                    raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg, type=styp)) from None

                async for item in agen:

                    if isinstance(name, (list, tuple)):

                        try:
                            numitems = len(item)
                        except TypeError:
                            mesg = f'Number of items to unpack does not match the number of variables: {s_common.trimText(repr(item))}'
                            exc = s_exc.StormVarListError(mesg=mesg, names=name)
                            raise self.kids[1].addExcInfo(exc)

                        if len(name) != numitems:
                            mesg = f'Number of items to unpack does not match the number of variables: {s_common.trimText(repr(item))}'
                            exc = s_exc.StormVarListError(mesg=mesg, names=name, numitems=numitems)
                            raise self.kids[1].addExcInfo(exc)

                        if isinstance(item, s_stormtypes.Prim):
                            item = await item.value()

                        for x, y in itertools.zip_longest(name, item):
                            await path.setVar(x, y)
                            await runt.setVar(x, y)

                    else:
                        # set both so inner subqueries have it in their runtime
                        await path.setVar(name, item)
                        await runt.setVar(name, item)

                    try:

                        # since it's possible to "multiply" the (node, path)
                        # we must make a clone of the path to prevent yield-then-use.
                        newg = s_common.agen((node, path.clone()))
                        async for item in subq.inline(runt, newg):
                            yield item

                    except s_stormctrl.StormBreak as e:
                        if (eitem := e.get('item')) is not None:
                            yield eitem
                        break

                    except s_stormctrl.StormContinue as e:
                        if (eitem := e.get('item')) is not None:
                            yield eitem
                        continue

                    finally:
                        # for loops must yield per item they iterate over
                        await asyncio.sleep(0)

        # no nodes and a runt safe value should execute once
        if node is None and self.kids[1].isRuntSafe(runt):

            valu = await self.kids[1].compute(runt, None)

            if isinstance(valu, s_stormtypes.Prim):
                # returns an async genr instance...
                valu = valu.iter()

            if isinstance(valu, dict):
                valu = list(valu.items())

            if valu is None:
                valu = ()

            async with contextlib.aclosing(s_coro.agen(valu)) as agen:
                try:
                    agen, _ = await pullone(agen)
                except TypeError:
                    styp = await s_stormtypes.totype(valu, basetypes=True)
                    mesg = f"'{styp}' object is not iterable: {s_common.trimText(repr(valu))}"
                    raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg, type=styp)) from None

                async for item in agen:

                    if isinstance(name, (list, tuple)):

                        try:
                            numitems = len(item)
                        except TypeError:
                            mesg = f'Number of items to unpack does not match the number of variables: {s_common.trimText(repr(item))}'
                            exc = s_exc.StormVarListError(mesg=mesg, names=name)
                            raise self.kids[1].addExcInfo(exc)

                        if len(name) != numitems:
                            mesg = f'Number of items to unpack does not match the number of variables: {s_common.trimText(repr(item))}'
                            exc = s_exc.StormVarListError(mesg=mesg, names=name, numitems=numitems)
                            raise self.kids[1].addExcInfo(exc)

                        if isinstance(item, s_stormtypes.Prim):
                            item = await item.value()

                        for x, y in itertools.zip_longest(name, item):
                            await runt.setVar(x, y)

                    else:
                        await runt.setVar(name, item)

                    try:
                        async for jtem in subq.inline(runt, s_common.agen()):
                            yield jtem

                    except s_stormctrl.StormBreak as e:
                        if (eitem := e.get('item')) is not None:
                            yield eitem
                        break

                    except s_stormctrl.StormContinue as e:
                        if (eitem := e.get('item')) is not None:
                            yield eitem
                        continue

                    finally:
                        # for loops must yield per item they iterate over
                        await asyncio.sleep(0)

class WhileLoop(Oper):

    def _hasAstClass(self, clss):
        return self.kids[1].hasAstClass(clss)

    async def run(self, runt, genr):
        subq = self.kids[1]
        node = None

        async for node, path in genr:

            while await tobool(await self.kids[0].compute(runt, path)):
                try:

                    newg = s_common.agen((node, path))
                    async for item in subq.inline(runt, newg):
                        yield item
                        await asyncio.sleep(0)

                except s_stormctrl.StormBreak as e:
                    if (eitem := e.get('item')) is not None:
                        yield eitem
                    break

                except s_stormctrl.StormContinue as e:
                    if (eitem := e.get('item')) is not None:
                        yield eitem
                    continue

                finally:
                    # while loops must yield each time they loop
                    await asyncio.sleep(0)

        # no nodes and a runt safe value should execute once
        if node is None and self.kids[0].isRuntSafe(runt):

            while await tobool(await self.kids[0].compute(runt, None)):

                try:
                    async for jtem in subq.inline(runt, s_common.agen()):
                        yield jtem
                        await asyncio.sleep(0)

                except s_stormctrl.StormBreak as e:
                    if (eitem := e.get('item')) is not None:
                        yield eitem
                    break

                except s_stormctrl.StormContinue as e:
                    if (eitem := e.get('item')) is not None:
                        yield eitem
                    continue

                finally:
                    # while loops must yield each time they loop
                    await asyncio.sleep(0)

async def pullone(genr):
    empty = False
    try:
        gotone = await genr.__anext__()
    except StopAsyncIteration:
        empty = True

    async def pullgenr():
        if empty:
            return

        yield gotone
        async for item in genr:
            yield item

    return pullgenr(), empty

class CmdOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        ctor = runt.view.core.getStormCmd(name)
        if ctor is None:
            mesg = f'Storm command ({name}) not found.'
            exc = s_exc.NoSuchName(name=name, mesg=mesg)
            raise self.kids[0].addExcInfo(exc)

        runtsafe = self.kids[1].isRuntSafe(runt)

        scmd = ctor(runt, runtsafe)

        if runt.readonly and not scmd.isReadOnly():
            mesg = f'Command ({name}) is not marked safe for readonly use.'
            raise self.addExcInfo(s_exc.IsReadOnly(mesg=mesg))

        async def genx():

            async for node, path in genr:
                argv = await self.kids[1].compute(runt, path)
                if not await scmd.setArgv(argv):
                    raise s_stormctrl.StormExit()

                yield node, path

        # must pull through the genr to get opts set
        # ( many commands expect self.opts is set at run() )
        genr, empty = await pullone(genx())

        try:
            if runtsafe:
                argv = await self.kids[1].compute(runt, None)
                if not await scmd.setArgv(argv):
                    raise s_stormctrl.StormExit()

            if runtsafe or not empty:
                async with contextlib.aclosing(scmd.execStormCmd(runt, genr)) as agen:
                    async for item in agen:
                        yield item

        finally:
            await genr.aclose()

class SetVarOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        vkid = self.kids[1]

        count = 0

        async for node, path in genr:
            count += 1

            valu = await vkid.compute(runt, path)
            if valu is undef:
                await runt.popVar(name)
                # TODO detect which to update here
                await path.popVar(name)

            else:
                await runt.setVar(name, valu)
                # TODO detect which to update here
                await path.setVar(name, valu)

            yield node, path

        if count == 0 and vkid.isRuntSafe(runt):
            valu = await vkid.compute(runt, None)
            if valu is undef:
                await runt.popVar(name)
            else:
                await runt.setVar(name, valu)

    def getRuntVars(self, runt):

        name = self.kids[0].value()
        if runt.runtvars.get(name) is None and self.kids[1].hasVarName(name):
            exc = s_exc.NoSuchVar(mesg=f'Missing variable: {name}', name=name)
            raise self.kids[0].addExcInfo(exc)

        yield name, self.kids[1].isRuntSafe(runt)
        for k in self.kids:
            yield from k.getRuntVars(runt)

class SetItemOper(Oper):
    '''
    $foo.bar = baz
    $foo."bar baz" = faz
    $foo.$bar = baz
    '''
    async def run(self, runt, genr):

        count = 0
        async for node, path in genr:

            count += 1

            item = s_stormtypes.fromprim(await self.kids[0].compute(runt, path), basetypes=False)

            if runt.readonly and not getattr(item.setitem, '_storm_readonly', False):
                self.kids[0].reqNotReadOnly(runt)

            name = await self.kids[1].compute(runt, path)
            valu = await self.kids[2].compute(runt, path)

            # TODO: ditch this when storm goes full heavy object
            with s_scope.enter({'runt': runt}):
                try:
                    await item.setitem(name, valu)
                except s_exc.SynErr as e:
                    raise self.kids[0].addExcInfo(e)

            yield node, path

        if count == 0 and self.isRuntSafe(runt):

            item = s_stormtypes.fromprim(await self.kids[0].compute(runt, None), basetypes=False)

            name = await self.kids[1].compute(runt, None)
            valu = await self.kids[2].compute(runt, None)

            if runt.readonly and not getattr(item.setitem, '_storm_readonly', False):
                self.kids[0].reqNotReadOnly(runt)

            # TODO: ditch this when storm goes full heavy object
            with s_scope.enter({'runt': runt}):
                try:
                    await item.setitem(name, valu)
                except s_exc.SynErr as e:
                    raise self.kids[0].addExcInfo(e)

class VarListSetOper(Oper):

    async def run(self, runt, genr):

        names = self.kids[0].value()
        vkid = self.kids[1]

        anynodes = False
        async for node, path in genr:
            anynodes = True
            item = await vkid.compute(runt, path)
            item = [i async for i in s_stormtypes.toiter(item)]

            if len(item) < len(names):
                mesg = f'Attempting to assign more items than we have variables to assign to: {s_common.trimText(repr(item))}'
                exc = s_exc.StormVarListError(mesg=mesg, names=names, numitems=len(item))
                raise self.kids[0].addExcInfo(exc)

            for name, valu in zip(names, item):
                await runt.setVar(name, valu)
                await path.setVar(name, valu)

            yield node, path

        if not anynodes and vkid.isRuntSafe(runt):

            item = await vkid.compute(runt, None)
            item = [i async for i in s_stormtypes.toiter(item)]

            if len(item) < len(names):
                mesg = f'Attempting to assign more items than we have variables to assign to: {s_common.trimText(repr(item))}'
                exc = s_exc.StormVarListError(mesg=mesg, names=names, numitems=len(item))
                raise self.kids[0].addExcInfo(exc)

            for name, valu in zip(names, item):
                await runt.setVar(name, valu)

            async for item in genr:
                yield item

            return

    def getRuntVars(self, runt):
        runtsafe = self.kids[1].isRuntSafe(runt)
        for name in self.kids[0].value():
            yield name, runtsafe

class VarEvalOper(Oper):
    '''
    Facilitate a stand-alone operator that evaluates a var.
    $foo.bar("baz")
    '''
    async def run(self, runt, genr):

        anynodes = False
        async for node, path in genr:
            anynodes = True
            valu = await self.kids[0].compute(runt, path)

            if isinstance(valu, types.AsyncGeneratorType):
                mesg = 'Standalone evaluation of a generator does not do anything, they must be yielded or iterated.'
                raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            yield node, path

        if not anynodes and self.isRuntSafe(runt):
            valu = await self.kids[0].compute(runt, None)

            if isinstance(valu, types.AsyncGeneratorType):
                mesg = 'Standalone evaluation of a generator does not do anything, they must be yielded or iterated.'
                raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

class SwitchCase(Oper):

    def _hasAstClass(self, clss):

        for kid in self.kids[1:]:
            if kid.hasAstClass(clss):
                return True

        return False

    def prepare(self):
        self.cases = {}
        self.defcase = None

        for cent in self.kids[1:]:
            *vals, subq = cent.kids

            if cent.defcase:
                self.defcase = subq
                continue

            for valu in vals:
                self.cases[valu.value()] = subq

    async def run(self, runt, genr):
        count = 0
        async for node, path in genr:
            count += 1

            varv = await self.kids[0].compute(runt, path)

            # TODO:  when we have var type system, do type-aware comparison
            subq = self.cases.get(await s_stormtypes.tostr(varv))
            if subq is None and self.defcase is not None:
                subq = self.defcase

            if subq is None:
                yield (node, path)
            else:
                async for item in subq.inline(runt, s_common.agen((node, path))):
                    yield item

        if count == 0 and self.kids[0].isRuntSafe(runt):
            # no nodes and a runt safe value should execute
            varv = await self.kids[0].compute(runt, None)

            subq = self.cases.get(await s_stormtypes.tostr(varv))
            if subq is None and self.defcase is not None:
                subq = self.defcase

            if subq is None:
                return

            async for item in subq.inline(runt, s_common.agen()):
                yield item

class CaseEntry(AstNode):
    def __init__(self, astinfo, kids=(), defcase=False):
        AstNode.__init__(self, astinfo, kids=kids)
        self.defcase = defcase

class LiftOper(Oper):

    def __init__(self, astinfo, kids=()):
        Oper.__init__(self, astinfo, kids=kids)
        self.reverse = False

    def reverseLift(self, astinfo):
        self.astinfo = astinfo
        self.reverse = True

    def getPivLifts(self, runt, props, pivs):
        plist = props
        virts = []
        pivlifts = []

        ptyp = props[0].type

        for piv in pivs:
            if (virt := ptyp.virts.get(piv)) is not None:
                ptyp = virt[0]
                virts.append(piv)
                continue

            pivlifts.append((plist, virts))

            pivprop = runt.model.reqProp(f'{ptyp.name}:{piv}', extra=self.kids[0].addExcInfo)
            plist = (pivprop,)
            virts = []

            ptyp = pivprop.type

        pivlifts.append((plist, virts))

        return pivlifts, ptyp

    async def pivlift(self, runt, pivlifts, genr):

        async def pivvals(props, virts, pivgenr):
            if len(props) == 1:
                prop = props[0].full
                async for node in pivgenr:
                    async for pivo in runt.view.nodesByPropValu(prop, '=', node.ndef[1], reverse=self.reverse, virts=virts):
                        yield pivo
                return

            names = [prop.full for prop in props]
            async for node in pivgenr:
                valu = node.ndef[1]
                for prop in names:
                    async for pivo in runt.view.nodesByPropValu(prop, '=', valu, reverse=self.reverse, virts=virts):
                        yield pivo

        for names, virts in pivlifts[-2::-1]:
            genr = pivvals(names, virts, genr)

        async for node in genr:
            yield node

    async def run(self, runt, genr):

        if self.isRuntSafe(runt):

            # runtime safe lift operation
            async for item in genr:
                yield item

            async for node in self.lift(runt, None):
                yield node, runt.initPath(node)

            return

        link = {'type': 'runtime'}
        async for node, path in genr:

            yield node, path

            async for subn in self.lift(runt, path):
                yield subn, path.fork(subn, link)

    async def lift(self, runt, path):  # pragma: no cover
        raise NotImplementedError('Must define lift(runt, path)')

class YieldValu(Oper):

    async def run(self, runt, genr):

        node = None
        vkid = self.kids[0]

        async for node, path in genr:
            valu = await vkid.compute(runt, path)
            async with contextlib.aclosing(self.yieldFromValu(runt, valu, vkid)) as agen:
                async for subn in agen:
                    yield subn, runt.initPath(subn)
            yield node, path

        if node is None and self.kids[0].isRuntSafe(runt):
            valu = await vkid.compute(runt, None)
            async with contextlib.aclosing(self.yieldFromValu(runt, valu, vkid)) as agen:
                async for subn in agen:
                    yield subn, runt.initPath(subn)

class LiftTag(LiftOper):

    async def lift(self, runt, path):
        tag = await self.kids[0].compute(runt, path)

        async for node in runt.view.nodesByTag(tag, reverse=self.reverse):
            yield node

class LiftTagValu(LiftOper):

    async def lift(self, runt, path):
        tag = await self.kids[0].compute(runt, path)
        cmpr = await self.kids[1].compute(runt, path)
        valu = await toprim(await self.kids[2].compute(runt, path))

        async for node in runt.view.nodesByTagValu(tag, cmpr, valu, reverse=self.reverse):
            yield node

class LiftTagVirt(LiftOper):

    async def lift(self, runt, path):
        tag = await self.kids[0].compute(runt, path)
        virt = (await self.kids[1].compute(runt, path))[0]

        async for node in runt.view.nodesByTag(tag, reverse=self.reverse, virt=virt):
            yield node

class LiftTagVirtValu(LiftOper):

    async def lift(self, runt, path):
        tag = await self.kids[0].compute(runt, path)
        virt = (await self.kids[1].compute(runt, path))[0]
        cmpr = await self.kids[2].compute(runt, path)
        valu = await toprim(await self.kids[3].compute(runt, path))

        async for node in runt.view.nodesByTagValu(tag, f'{virt}{cmpr}', valu, reverse=self.reverse):
            yield node

class LiftByArray(LiftOper):
    '''
    :prop*[range=(200, 400)]
    '''
    async def lift(self, runt, path):

        name = await self.kids[0].compute(runt, path)
        cmpr = self.kids[1].value()
        valu = await s_stormtypes.tostor(await self.kids[2].compute(runt, path))

        pivs = None
        if name.find('::') != -1:
            parts = name.split('::')
            name, pivs = parts[0], parts[1:]

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        try:
            if pivs is not None:
                pivlifts, ptyp = self.getPivLifts(runt, props, pivs)
                (plift, virts) = pivlifts[-1]

                if not virts:
                    virts = None

                prop = plift[0]
                genr = runt.view.nodesByPropArray(prop.full, cmpr, valu, reverse=self.reverse, virts=virts)

                async for node in self.pivlift(runt, pivlifts, genr):
                    yield node
                return

            if not props[0].type.isarray:
                mesg = f'Array syntax is invalid on non array type: {props[0].type.name}.'
                raise s_exc.BadTypeValu(mesg=mesg)

            genrs = []
            for prop in props:
                genrs.append(runt.view.nodesByPropArray(prop.full, cmpr, valu, reverse=self.reverse))

            if len(genrs) == 1:
                async for node in genrs[0]:
                    yield node
                return

            relname = props[0].name

            def cmprkey(node):
                return node.get(relname)

            async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
                yield node

        except s_exc.BadTypeValu as e:
            raise self.kids[2].addExcInfo(e)

        except s_exc.SynErr as e:
            raise self.addExcInfo(e)

class LiftByArrayVirt(LiftOper):
    '''
    :prop*[.min*range=(200, 400)]
    '''
    async def lift(self, runt, path):

        name = await self.kids[0].compute(runt, path)
        vnames = await self.kids[1].compute(runt, path)
        cmpr = self.kids[2].value()
        valu = await s_stormtypes.tostor(await self.kids[3].compute(runt, path))

        pivs = None
        if name.find('::') != -1:
            parts = name.split('::')
            name, pivs = parts[0], parts[1:]

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        try:
            if pivs is not None:
                pivlifts, ptyp = self.getPivLifts(runt, props, pivs)
                (plift, virts) = pivlifts[-1]

                virts += vnames

                prop = plift[0]
                genr = runt.view.nodesByPropArray(prop.full, cmpr, valu, reverse=self.reverse, virts=virts)

                async for node in self.pivlift(runt, pivlifts, genr):
                    yield node
                return

            if not props[0].type.isarray:
                mesg = f'Array syntax is invalid on non array type: {props[0].type.name}.'
                raise s_exc.BadTypeValu(mesg=mesg)

            genrs = []
            for prop in props:
                genrs.append(runt.view.nodesByPropArray(prop.full, cmpr, valu, reverse=self.reverse, virts=vnames))

            if len(genrs) == 1:
                async for node in genrs[0]:
                    yield node
                return

            relname = props[0].name
            getr = props[0].type.arraytype.getVirtGetr(vnames)

            def cmprkey(node):
                return node.get(relname, virts=getr)

            async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
                yield node

        except s_exc.BadTypeValu as e:
            raise self.kids[2].addExcInfo(e)

        except s_exc.SynErr as e:
            raise self.addExcInfo(e)

class LiftTagProp(LiftOper):
    '''
    #foo.bar:baz [ = x ]
    '''
    async def lift(self, runt, path):

        tag, prop = await self.kids[0].compute(runt, path)

        if len(self.kids) == 3:

            cmpr = await self.kids[1].compute(runt, path)
            valu = await s_stormtypes.tostor(await self.kids[2].compute(runt, path))

            async for node in runt.view.nodesByTagPropValu(None, tag, prop, cmpr, valu, reverse=self.reverse):
                yield node

            return

        virt = None
        if len(self.kids) == 2:
            virt = await self.kids[1].compute(runt, path)

        async for node in runt.view.nodesByTagProp(None, tag, prop, reverse=self.reverse, virt=virt):
            yield node

class LiftFormTagProp(LiftOper):
    '''
    hehe:haha#foo.bar:baz [ = x ]
    '''

    async def lift(self, runt, path):

        formname, tag, prop = await self.kids[0].compute(runt, path)

        forms = runt.model.reqFormsByLook(formname, self.kids[0].addExcInfo)

        def cmprkey(node):
            return node.getTagProp(tag, prop)

        genrs = []

        if len(self.kids) == 3:

            cmpr = await self.kids[1].compute(runt, path)
            valu = await s_stormtypes.tostor(await self.kids[2].compute(runt, path))

            for form in forms:
                genrs.append(runt.view.nodesByTagPropValu(form, tag, prop, cmpr, valu, reverse=self.reverse))

        elif len(self.kids) == 2:
            virt = await self.kids[1].compute(runt, path)

            for form in forms:
                genrs.append(runt.view.nodesByTagProp(form, tag, prop, reverse=self.reverse, virt=virt))

        else:
            for form in forms:
                genrs.append(runt.view.nodesByTagProp(form, tag, prop, reverse=self.reverse))

        async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
            yield node

class LiftTagTag(LiftOper):
    '''
    ##foo.bar
    '''

    async def lift(self, runt, path):

        tagname = await self.kids[0].compute(runt, path)

        node = await runt.view.getNodeByNdef(('syn:tag', tagname))
        if node is None:
            return

        # only apply the lift valu to the top level tag of tags, not to the sub tags
        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt, path)
            valu = await toprim(await self.kids[2].compute(runt, path))
            genr = runt.view.nodesByTagValu(tagname, cmpr, valu, reverse=self.reverse)

        else:

            genr = runt.view.nodesByTag(tagname, reverse=self.reverse)

        done = set([tagname])
        todo = collections.deque([genr])

        while todo:

            genr = todo.popleft()

            async for node in genr:

                if node.form.name == 'syn:tag':

                    tagname = node.ndef[1]
                    if tagname not in done:
                        done.add(tagname)
                        todo.append(runt.view.nodesByTag(tagname, reverse=self.reverse))

                    continue

                yield node

class LiftFormTag(LiftOper):

    async def lift(self, runt, path):

        formname = await self.kids[0].compute(runt, path)
        forms = runt.model.reqFormsByLook(formname, self.kids[0].addExcInfo)

        tag = await self.kids[1].compute(runt, path)

        genrs = []
        for form in forms:
            genrs.append(runt.view.nodesByTag(tag, form=form, reverse=self.reverse))

        def cmprkey(node):
            return node.getTag(tag, defval=(0, 0))

        async for node in s_common.merggenr2(genrs, cmprkey=cmprkey, reverse=self.reverse):
            yield node

class LiftFormTagValu(LiftOper):

    async def lift(self, runt, path):

        formname = await self.kids[0].compute(runt, path)
        forms = runt.model.reqFormsByLook(formname, self.kids[0].addExcInfo)

        tag = await self.kids[1].compute(runt, path)
        cmpr = await self.kids[2].compute(runt, path)
        valu = await toprim(await self.kids[3].compute(runt, path))

        genrs = []
        for form in forms:
            genrs.append(runt.view.nodesByTagValu(tag, cmpr, valu, form=form, reverse=self.reverse))

        def cmprkey(node):
            return node.getTag(tag, defval=(0, 0))

        async for node in s_common.merggenr2(genrs, cmprkey=cmprkey, reverse=self.reverse):
            yield node

class LiftFormTagVirt(LiftOper):

    async def lift(self, runt, path):

        formname = await self.kids[0].compute(runt, path)
        forms = runt.model.reqFormsByLook(formname, self.kids[0].addExcInfo)

        tag = await self.kids[1].compute(runt, path)
        virts = await self.kids[2].compute(runt, path)
        getr = runt.model.type('ival').getVirtGetr(virts)

        genrs = []
        for form in forms:
            genrs.append(runt.view.nodesByTag(tag, form=form, reverse=self.reverse, virt=virts[0]))

        def cmprkey(node):
            tagv = node.getTag(tag, defval=(0, 0))
            for func in getr:
                tagv = func(tagv)
            return tagv

        async for node in s_common.merggenr2(genrs, cmprkey=cmprkey, reverse=self.reverse):
            yield node

class LiftFormTagVirtValu(LiftOper):

    async def lift(self, runt, path):

        formname = await self.kids[0].compute(runt, path)
        forms = runt.model.reqFormsByLook(formname, self.kids[0].addExcInfo)

        tag = await self.kids[1].compute(runt, path)
        virts = await self.kids[2].compute(runt, path)
        getr = runt.model.type('ival').getVirtGetr(virts)

        cmpr = await self.kids[3].compute(runt, path)
        valu = await toprim(await self.kids[4].compute(runt, path))

        cmpr = f'{virts[0]}{cmpr}'

        genrs = []
        for form in forms:
            genrs.append(runt.view.nodesByTagValu(tag, cmpr, valu, form=form, reverse=self.reverse))

        def cmprkey(node):
            tagv = node.getTag(tag, defval=(0, 0))
            for func in getr:
                tagv = func(tagv)
            return tagv

        async for node in s_common.merggenr2(genrs, cmprkey=cmprkey, reverse=self.reverse):
            yield node

class LiftMeta(LiftOper):

    async def lift(self, runt, path):

        names = await self.kids[0].compute(runt, path)
        name = await tostr(names[0])

        mtyp = runt.model.reqMetaType(name, extra=self.kids[0].addExcInfo)

        if len(self.kids) == 1:
            async for node in runt.view.nodesByMeta(name, reverse=self.reverse):
                yield node
        else:
            cmpr = self.kids[1].value()
            valu = await self.kids[2].compute(runt, path)

            async for node in runt.view.nodesByMetaValu(name, cmpr, valu, reverse=self.reverse):
                yield node

class LiftProp(LiftOper):

    async def lift(self, runt, path):

        name = await tostr(await self.kids[0].compute(runt, path))

        if (prop := runt.model.props.get(name)) is not None:
            async for node in self.proplift(prop, runt, path):
                yield node
            return

        proplist = runt.model.reqPropsByLook(name, self.kids[0].addExcInfo)
        props = [runt.model.props.get(propname) for propname in proplist]

        relname = props[0].name

        if len(props) == 1 or props[0].isform:
            for prop in props:
                async for node in self.proplift(prop, runt, path):
                    yield node
            return

        def cmprkey(node):
            return node.get(relname)

        genrs = []
        for prop in props:
            genrs.append(self.proplift(prop, runt, path))

        async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
            yield node

    async def proplift(self, prop, runt, path):

        # check if we can optimize a form lift
        if prop.isform:

            async for hint in self.getRightHints(runt, path):
                if hint[0] == 'tag':
                    tagname = hint[1].get('name')
                    async for node in runt.view.nodesByTag(tagname, form=prop.full, reverse=self.reverse):
                        yield node
                    return

                if hint[0] == 'relprop':
                    relpropname = hint[1].get('name')
                    fullname = ':'.join([prop.full, relpropname])

                    prop = runt.model.prop(fullname)
                    if prop is None:
                        return

                    cmpr = hint[1].get('cmpr')
                    valu = hint[1].get('valu')

                    if cmpr is not None and valu is not None:
                        try:
                            # try lifting by valu but no guarantee a cmpr is available
                            async for node in runt.view.nodesByPropValu(fullname, cmpr, valu, reverse=self.reverse):
                                yield node
                            return
                        except asyncio.CancelledError:  # pragma: no cover
                            raise
                        except:
                            pass

                    async for node in runt.view.nodesByProp(fullname, reverse=self.reverse):
                        yield node
                    return

        async for node in runt.view.nodesByProp(prop.full, reverse=self.reverse):
            yield node

    async def getRightHints(self, runt, path):

        for oper in self.iterright():

            # we can skip other lifts but that's it...
            if isinstance(oper, LiftOper):
                continue

            if isinstance(oper, FiltOper):
                for hint in await oper.getLiftHints(runt, path):
                    yield hint
                continue

            return

class LiftPropVirt(LiftProp):

    async def lift(self, runt, path):

        name = await tostr(await self.kids[0].compute(runt, path))
        virts = await self.kids[1].compute(runt, path)

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        if len(props) == 1:
            async for node in runt.view.nodesByProp(props[0].full, reverse=self.reverse, virts=virts):
                yield node
            return

        relname = props[0].name
        vgetr = props[0].type.getVirtGetr(virts)

        def cmprkey(node):
            return node.get(relname, virts=vgetr)

        genrs = []
        for prop in props:
            genrs.append(runt.view.nodesByProp(prop.full, reverse=self.reverse, virts=virts))

        async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
            yield node

class LiftPropBy(LiftOper):

    async def lift(self, runt, path):
        name = await self.kids[0].compute(runt, path)
        cmpr = await self.kids[1].compute(runt, path)
        valu = await self.kids[2].compute(runt, path)

        if not isinstance(valu, s_node.Node):
            valu = await s_stormtypes.tostor(valu)

        pivs = None
        if name.find('::') != -1:
            parts = name.split('::')
            name, pivs = parts[0], parts[1:]

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        try:
            if pivs is not None:
                pivlifts, ptyp = self.getPivLifts(runt, props, pivs)
                (plift, virts) = pivlifts[-1]

                if not virts:
                    virts = None

                prop = plift[0]
                genr = runt.view.nodesByPropValu(prop.full, cmpr, valu, reverse=self.reverse, virts=virts)

                async for node in self.pivlift(runt, pivlifts, genr):
                    yield node
                return

            genrs = []
            for prop in props:
                genrs.append(runt.view.nodesByPropValu(prop.full, cmpr, valu, reverse=self.reverse))

            if len(genrs) == 1:
                async for node in genrs[0]:
                    yield node
                return

            relname = props[0].name

            def cmprkey(node):
                return node.get(relname)

            async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
                yield node

        except s_exc.BadTypeValu as e:
            raise self.kids[2].addExcInfo(e)

        except s_exc.SynErr as e:
            raise self.addExcInfo(e)

class LiftPropVirtBy(LiftOper):

    async def lift(self, runt, path):
        name = await self.kids[0].compute(runt, path)
        vnames = await self.kids[1].compute(runt, path)
        cmpr = await self.kids[2].compute(runt, path)
        valu = await self.kids[3].compute(runt, path)

        if not isinstance(valu, s_node.Node):
            valu = await s_stormtypes.tostor(valu)

        pivs = None
        if name.find('::') != -1:
            parts = name.split('::')
            name, pivs = parts[0], parts[1:]

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        try:
            if pivs is not None:
                pivlifts, ptyp = self.getPivLifts(runt, props, pivs)
                (plift, virts) = pivlifts[-1]

                virts += vnames

                prop = plift[0]
                genr = runt.view.nodesByPropValu(prop.full, cmpr, valu, reverse=self.reverse, virts=virts)

                async for node in self.pivlift(runt, pivlifts, genr):
                    yield node
                return

            genrs = []
            for prop in props:
                genrs.append(runt.view.nodesByPropValu(prop.full, cmpr, valu, reverse=self.reverse, virts=vnames))

            if len(genrs) == 1:
                async for node in genrs[0]:
                    yield node
                return

            relname = props[0].name
            vgetr = props[0].type.getVirtGetr(vnames)

            def cmprkey(node):
                return node.get(relname, virts=vgetr)

            async for node in s_common.merggenr2(genrs, cmprkey, reverse=self.reverse):
                yield node

        except s_exc.BadTypeValu as e:
            raise self.kids[2].addExcInfo(e)

        except s_exc.SynErr as e:
            raise self.addExcInfo(e)

class PivotOper(Oper):

    def __init__(self, astinfo, kids=(), isjoin=False):
        Oper.__init__(self, astinfo, kids=kids)
        self.isjoin = isjoin

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}, isjoin={self.isjoin}'

    def __repr__(self):
        return self.repr()

class RawPivot(PivotOper):
    '''
    -> { <varsfrompath> }
    '''
    async def run(self, runt, genr):
        query = self.kids[0]
        async for node, path in genr:
            async with runt.getSubRuntime(query) as subr:
                async for node, path in subr.execute():
                    yield node, path

class PivotOut(PivotOper):
    '''
    -> *
    '''
    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            async for item in self.getPivsOut(runt, node, path):
                yield item

    async def getPivsOut(self, runt, node, path):

        # <syn:tag> -> * is "from tags to nodes with tags"
        if node.form.name == 'syn:tag':

            link = {'type': 'tag', 'tag': node.ndef[1], 'reverse': True}
            async for pivo in runt.view.nodesByTag(node.ndef[1]):
                yield pivo, path.fork(pivo, link)

            return

        for formname, (cmpr, func) in node.form.type.pivs.items():
            valu = func(node.ndef[1])
            link = {'type': 'type'}
            async for pivo in runt.view.nodesByPropValu(formname, cmpr, valu, norm=False):
                yield pivo, path.fork(pivo, link)

        refs = node.form.getRefsOut()
        for name, form in refs['prop']:
            if (valu := node.get(name)) is None:
                continue

            prop = node.form.prop(name)
            if prop.isrunt:
                link = {'type': 'prop', 'prop': name}
                async for pivo in runt.view.nodesByPropValu(form, '=', valu):
                    yield pivo, path.fork(pivo, link)
                continue

            pivo = await runt.view.getNodeByNdef((form, valu))
            if pivo is None:  # pragma: no cover
                continue

            # avoid self references
            if pivo.nid == node.nid:
                continue

            yield pivo, path.fork(pivo, {'type': 'prop', 'prop': name})

        for name, form in refs['array']:
            if (valu := node.get(name)) is not None:
                link = {'type': 'prop', 'prop': name}
                for aval in valu:
                    async for pivo in runt.view.nodesByPropValu(form, '=', aval, norm=False):
                        yield pivo, path.fork(pivo, link)

        for name in refs['ndef']:
            if (valu := node.get(name)) is not None:
                if (pivo := await runt.view.getNodeByNdef(valu)) is not None:
                    yield pivo, path.fork(pivo, {'type': 'prop', 'prop': name})

        for name in refs['ndefarray']:
            if (valu := node.get(name)) is not None:
                link = {'type': 'prop', 'prop': name}
                for aval in valu:
                    if (pivo := await runt.view.getNodeByNdef(aval)) is not None:
                        yield pivo, path.fork(pivo, link)

class N1WalkNPivo(PivotOut):

    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            async for item in self.getPivsOut(runt, node, path):
                yield item

            async for (verb, n2nid) in node.iterEdgesN1():
                wnode = await runt.view.getNodeByNid(n2nid)
                if wnode is not None:
                    yield wnode, path.fork(wnode, {'type': 'edge', 'verb': verb})

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

            mval = kid.constval

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
                    valu = await kid.compute(runt, path)
                    return fnmatch.fnmatch(x, valu)

            else:

                async def filter(x, path):
                    valu = await kid.compute(runt, path)
                    return x == valu

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            for name, _ in node.getTags(leaf=leaf):

                if not await filter(name, path):
                    await asyncio.sleep(0)
                    continue

                pivo = await runt.view.getNodeByNdef(('syn:tag', name))
                if pivo is None:
                    continue

                yield pivo, path.fork(pivo, {'type': 'tag', 'tag': name})

class PivotIn(PivotOper):
    '''
    <- *
    '''

    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            async for item in self.getPivsIn(runt, node, path):
                yield item

    async def getPivsIn(self, runt, node, path):

        name, valu = node.ndef

        for prop in runt.model.getPropsByType(name):
            link = {'type': 'prop', 'prop': prop.name, 'reverse': True}
            norm = node.form.typehash is not prop.typehash
            async for pivo in runt.view.nodesByPropValu(prop.full, '=', valu, norm=norm):
                yield pivo, path.fork(pivo, link)

        for prop in runt.model.getArrayPropsByType(name):
            norm = node.form.typehash is not prop.arraytypehash
            link = {'type': 'prop', 'prop': prop.name, 'reverse': True}
            async for pivo in runt.view.nodesByPropArray(prop.full, '=', valu, norm=norm):
                yield pivo, path.fork(pivo, link)

        async for refsnid, prop in runt.view.getNdefRefs(node.buid, props=True):
            pivo = await runt.view.getNodeByNid(refsnid)
            yield pivo, path.fork(pivo, {'type': 'prop', 'prop': prop, 'reverse': True})

class N2WalkNPivo(PivotIn):

    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            async for item in self.getPivsIn(runt, node, path):
                yield item

            async for (verb, n1nid) in node.iterEdgesN2():
                wnode = await runt.view.getNodeByNid(n1nid)
                if wnode is not None:
                    yield wnode, path.fork(wnode, {'type': 'edge', 'verb': verb, 'reverse': True})

class FormPivot(PivotOper):
    '''
    -> foo:bar
    '''

    def pivogenr(self, runt, prop, virts=None):

        # -> baz:ndef
        if isinstance(prop.type, s_types.Ndef):

            async def pgenr(node, strict=True):
                link = {'type': 'prop', 'prop': prop.name, 'reverse': True}
                async for pivo in runt.view.nodesByPropValu(prop.full, '=', node.ndef, norm=False, virts=virts):
                    yield pivo, link

        elif not prop.isform or virts is not None:

            # plain old pivot...
            async def pgenr(node, strict=True):
                if prop.type.isarray:
                    if isinstance(prop.type.arraytype, s_types.Ndef):
                        ngenr = runt.view.nodesByPropArray(prop.full, '=', node.ndef, norm=False, virts=virts)
                    else:
                        norm = prop.arraytypehash is not node.form.typehash
                        ngenr = runt.view.nodesByPropArray(prop.full, '=', node.ndef[1], norm=norm, virts=virts)
                else:
                    norm = prop.typehash is not node.form.typehash
                    ngenr = runt.view.nodesByPropValu(prop.full, '=', node.ndef[1], norm=norm, virts=virts)

                link = {'type': 'prop', 'prop': prop.name, 'reverse': True}
                async for pivo in ngenr:
                    yield pivo, link

        else:
            # form -> form pivot is nonsensical. Lets help out...

            # form name and type name match
            destform = prop

            async def pgenr(node, strict=True):

                # <syn:tag> -> <form> is "from tags to nodes" pivot
                if node.form.name == 'syn:tag' and prop.isform:
                    link = {'type': 'tag', 'tag': node.ndef[1], 'reverse': True}
                    async for pivo in runt.view.nodesByTag(node.ndef[1], form=prop.name):
                        yield pivo, link

                    return

                #########################################################################
                # regular "-> form" pivot (ie inet:dns:a -> inet:fqdn)

                found = False   # have we found a ref/pivot?

                if (tpiv := node.form.type.pivs.get(destform.type.name)) is not None:

                    found = True
                    cmpr, func = tpiv
                    valu = func(node.ndef[1])

                    link = {'type': 'type'}
                    async for pivo in runt.view.nodesByPropValu(destform.name, cmpr, valu, norm=False):
                        yield pivo, link

                refs = node.form.getRefsOut()
                for refsname, refsform in refs.get('prop'):

                    if refsform != destform.name:
                        continue

                    found = True

                    refsvalu = node.get(refsname)
                    if refsvalu is not None:
                        link = {'type': 'prop', 'prop': refsname}
                        async for pivo in runt.view.nodesByPropValu(refsform, '=', refsvalu, norm=False):
                            yield pivo, link

                for refsname, refsform in refs.get('array'):

                    if refsform != destform.name:
                        continue

                    found = True

                    refsvalu = node.get(refsname)
                    if refsvalu is not None:
                        link = {'type': 'prop', 'prop': refsname}
                        for refselem in refsvalu:
                            async for pivo in runt.view.nodesByPropValu(destform.name, '=', refselem, norm=False):
                                yield pivo, link

                for refsname in refs.get('ndef'):

                    found = True

                    refsvalu = node.get(refsname)
                    if refsvalu is not None and refsvalu[0] == destform.name:
                        pivo = await runt.view.getNodeByNdef(refsvalu)
                        if pivo is not None:
                            yield pivo, {'type': 'prop', 'prop': refsname}

                for refsname in refs.get('ndefarray'):

                    found = True

                    if (refsvalu := node.get(refsname)) is not None:
                        link = {'type': 'prop', 'prop': refsname}
                        for aval in refsvalu:
                            if aval[0] == destform.name:
                                if (pivo := await runt.view.getNodeByNdef(aval)) is not None:
                                    yield pivo, link

                #########################################################################
                # reverse "-> form" pivots (ie inet:fqdn -> inet:dns:a)
                refs = destform.getRefsOut()

                # "reverse" property references...
                for refsname, refsform in refs.get('prop'):

                    if refsform != node.form.name:
                        continue

                    found = True

                    refsprop = destform.props.get(refsname)
                    link = {'type': 'prop', 'prop': refsname, 'reverse': True}
                    async for pivo in runt.view.nodesByPropValu(refsprop.full, '=', node.ndef[1], norm=False):
                        yield pivo, link

                # "reverse" array references...
                for refsname, refsform in refs.get('array'):

                    if refsform != node.form.name:
                        continue

                    found = True

                    destprop = destform.props.get(refsname)
                    link = {'type': 'prop', 'prop': refsname, 'reverse': True}
                    async for pivo in runt.view.nodesByPropArray(destprop.full, '=', node.ndef[1], norm=False):
                        yield pivo, link

                # "reverse" ndef references...
                for refsname in refs.get('ndef'):

                    found = True

                    refsprop = destform.props.get(refsname)
                    link = {'type': 'prop', 'prop': refsname, 'reverse': True}
                    async for pivo in runt.view.nodesByPropValu(refsprop.full, '=', node.ndef, norm=False):
                        yield pivo, link

                for refsname in refs.get('ndefarray'):

                    found = True

                    refsprop = destform.props.get(refsname)
                    link = {'type': 'prop', 'prop': refsname, 'reverse': True}
                    async for pivo in runt.view.nodesByPropArray(refsprop.full, '=', node.ndef, norm=False):
                        yield pivo, link

                if strict and not found:
                    mesg = f'No pivot found for {node.form.name} -> {destform.name}.'
                    raise self.addExcInfo(s_exc.NoSuchPivot(n1=node.form.name, n2=destform.name, mesg=mesg))

        return pgenr

    def buildgenr(self, runt, targets):

        if len(targets) == 1:
            prop, virts = targets[0]
            return self.pivogenr(runt, prop, virts=virts)

        pgenrs = []
        for (prop, virts) in targets:
            pgenrs.append(self.pivogenr(runt, prop, virts=virts))

        async def listpivot(node):
            for pgenr in pgenrs:
                async for item in pgenr(node, strict=False):
                    yield item

        return listpivot

    async def run(self, runt, genr):

        pgenr = None
        warned = False

        async for node, path in genr:

            if pgenr is None or self.kids[0].constval is None:
                targets = await self.kids[0].compute(runt, None)
                pgenr = self.buildgenr(runt, targets)

            if self.isjoin:
                yield node, path

            try:
                async for pivo, link in pgenr(node):
                    yield pivo, path.fork(pivo, link)
            except (s_exc.BadTypeValu, s_exc.BadLiftValu) as e:
                if not warned:
                    logger.warning(f'Caught error during pivot: {e.items()}')
                    warned = True
                items = e.items()
                mesg = items.pop('mesg', '')
                mesg = ': '.join((f'{e.__class__.__qualname__} [{repr(node.ndef[1])}] during pivot', mesg))
                await runt.warn(mesg, log=False, **items)

class PropPivotOut(PivotOper):
    '''
    :prop -> *
    '''
    async def run(self, runt, genr):

        warned = False
        async for node, path in genr:

            if self.isjoin:
                yield node, path

            srctype, valu, srcname = await self.kids[0].getTypeValuProp(runt, path, strict=False)
            if valu is None:
                # all filters must sleep
                await asyncio.sleep(0)
                continue

            link = {'type': 'prop', 'prop': srcname}
            for typename, (cmpr, func) in srctype.pivs.items():
                pivvalu = func(valu)
                async for pivo in runt.view.nodesByPropValu(typename, cmpr, pivvalu, norm=False):
                    yield pivo, path.fork(pivo, link)

            if srctype.isarray:
                if isinstance(srctype.arraytype, s_types.Ndef):
                    for item in valu:
                        if (pivo := await runt.view.getNodeByNdef(item)) is not None:
                            yield pivo, path.fork(pivo, link)
                    continue

                fname = srctype.arraytype.name
                if runt.model.forms.get(fname) is None:
                    if not warned:
                        mesg = f'The source property "{srcname}" array type "{fname}" is not a form. Cannot pivot.'
                        await runt.warn(mesg, log=False)
                        warned = True
                    continue

                for item in valu:
                    async for pivo in runt.view.nodesByPropValu(fname, '=', item, norm=False):
                        yield pivo, path.fork(pivo, link)

                continue

            # ndef pivot out syntax...
            # :ndef -> *
            if isinstance(srctype, s_types.Ndef):
                pivo = await runt.view.getNodeByNdef(valu)
                if pivo is None:
                    logger.warning(f'Missing node corresponding to ndef {valu}')
                    continue
                yield pivo, path.fork(pivo, link)
                continue

            # :prop -> *
            fname = srctype.name
            if runt.model.form(fname) is None:
                if warned is False:
                    await runt.warn(f'The source property "{srcname}" type "{fname}" is not a form. Cannot pivot.', log=False)
                    warned = True
                continue

            ndef = (fname, valu)
            pivo = await runt.view.getNodeByNdef(ndef)
            # A node explicitly deleted in the graph or missing from a underlying layer
            # could cause this lift to return None.
            if pivo:
                yield pivo, path.fork(pivo, link)

class PropPivot(PivotOper):
    '''
    :foo -> bar:foo
    '''

    def pivogenr(self, runt, prop, virts=None):

        async def pgenr(node, srcname, srctype, valu):

            link = {'type': 'prop', 'prop': srcname}
            if not prop.isform:
                link['dest'] = prop.full

            ptyp = prop.type
            if virts is not None:
                ptyp = ptyp.getVirtType(virts)

            if (tpiv := srctype.pivs.get(ptyp.name)) is not None:
                cmpr, func = tpiv
                pivvalu = func(valu)
                async for pivo in runt.view.nodesByPropValu(prop.full, cmpr, pivvalu, norm=False, virts=virts):
                    yield pivo, link

                return

            # pivoting from an array prop to a non-array prop needs an extra loop
            if srctype.isarray and not prop.type.isarray:
                if isinstance(srctype.arraytype, s_types.Ndef) and prop.isform:
                    for aval in valu:
                        if aval[0] != prop.form.name:
                            continue

                        if (pivo := await runt.view.getNodeByNdef(aval)) is not None:
                            yield pivo, link
                    return

                norm = srctype.arraytype.typehash is not ptyp.typehash
                for arrayval in valu:
                    async for pivo in runt.view.nodesByPropValu(prop.full, '=', arrayval, norm=norm, virts=virts):
                        yield pivo, link

                return

            if isinstance(srctype, s_types.Ndef) and prop.isform:
                if valu[0] != prop.form.name:
                    return

                pivo = await runt.view.getNodeByNdef(valu)
                if pivo is None:
                    await runt.warn(f'Missing node corresponding to ndef {valu}', log=False, ndef=valu)
                    return
                yield pivo, link

                return

            if prop.type.isarray and not srctype.isarray:
                norm = ptyp.arraytypehash is not srctype.typehash
                genr = runt.view.nodesByPropArray(prop.full, '=', valu, norm=norm, virts=virts)
            else:
                norm = ptyp.typehash is not srctype.typehash
                genr = runt.view.nodesByPropValu(prop.full, '=', valu, norm=norm, virts=virts)

            async for pivo in genr:
                yield pivo, link

        return pgenr

    def buildgenr(self, runt, targets):

        if not isinstance(targets, list):
            prop, virts = targets
            return self.pivogenr(runt, prop, virts=virts)

        pgenrs = []
        for (prop, virts) in targets:
            pgenrs.append(self.pivogenr(runt, prop, virts=virts))

        async def listpivot(node, srcname, srctype, valu):
            for pgenr in pgenrs:
                async for pivo in pgenr(node, srcname, srctype, valu):
                    yield pivo

        return listpivot

    async def run(self, runt, genr):

        pgenr = None
        warned = False

        async for node, path in genr:

            if pgenr is None or self.kids[1].constval is None:
                targets = await self.kids[1].compute(runt, None)
                pgenr = self.buildgenr(runt, targets)

            if self.isjoin:
                yield node, path

            srctype, valu, srcname = await self.kids[0].getTypeValuProp(runt, path)
            if valu is None:
                # all filters must sleep
                await asyncio.sleep(0)
                continue

            try:
                async for pivo, link in pgenr(node, srcname, srctype, valu):
                    yield pivo, path.fork(pivo, link)

            except (s_exc.BadTypeValu, s_exc.BadLiftValu) as e:
                if not warned:
                    logger.warning(f'Caught error during pivot: {e.items()}')
                    warned = True
                items = e.items()
                mesg = items.pop('mesg', '')
                mesg = ': '.join((f'{e.__class__.__qualname__} [{repr(valu)}] during pivot', mesg))
                await runt.warn(mesg, log=False, **items)

class Value(AstNode):
    '''
    The base class for all values and value expressions.
    '''

    def __init__(self, astinfo, kids=()):
        AstNode.__init__(self, astinfo, kids=kids)

    def __repr__(self):
        return self.repr()

    def isRuntSafe(self, runt):
        return all(k.isRuntSafe(runt) for k in self.kids)

    async def compute(self, runt, path):  # pragma: no cover
        raise self.addExcInfo(s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.compute()'))

    async def getLiftHints(self, runt, path):
        return []

    async def getCondEval(self, runt):
        '''
        Return a function that may be used to evaluate the boolean truth
        of the value expression using a runtime and optional node path.
        '''
        async def cond(node, path):
            return await tobool(await self.compute(runt, path))

        return cond

class Cond(Value):
    '''
    A condition that is evaluated to filter nodes.
    '''
    # Keeping the distinction of Cond as a subclass of Value
    # due to the fact that Cond instances may always presume
    # they are being evaluated per node.

class SubqCond(Cond):

    def __init__(self, astinfo, kids=()):
        Cond.__init__(self, astinfo, kids=kids)
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
        genr = s_common.agen((node, path))
        async for item in self.kids[0].run(runt, genr):
            yield size, item
            size += 1

    def _subqCondEq(self, runt):

        async def cond(node, path):

            size = 0
            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))

            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    path.vars.update(item[1].vars)
                    return False

            if item:
                path.vars.update(item[1].vars)
            return size == valu

        return cond

    def _subqCondGt(self, runt):

        async def cond(node, path):

            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    path.vars.update(item[1].vars)
                    return True

            if item:
                path.vars.update(item[1].vars)
            return False

        return cond

    def _subqCondLt(self, runt):

        async def cond(node, path):

            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    path.vars.update(item[1].vars)
                    return False

            if item:
                path.vars.update(item[1].vars)
            return True

        return cond

    def _subqCondGe(self, runt):

        async def cond(node, path):

            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size >= valu:
                    path.vars.update(item[1].vars)
                    return True

            if item:
                path.vars.update(item[1].vars)
            return False

        return cond

    def _subqCondLe(self, runt):

        async def cond(node, path):

            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))
            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    path.vars.update(item[1].vars)
                    return False

            if item:
                path.vars.update(item[1].vars)
            return True

        return cond

    def _subqCondNe(self, runt):

        async def cond(node, path):

            size = 0
            item = None
            valu = s_stormtypes.intify(await self.kids[2].compute(runt, path))

            async for size, item in self._runSubQuery(runt, node, path):
                if size > valu:
                    path.vars.update(item[1].vars)
                    return True

            if item:
                path.vars.update(item[1].vars)
            return size != valu

        return cond

    async def getCondEval(self, runt):

        if len(self.kids) == 3:
            cmpr = await self.kids[1].compute(runt, None)
            ctor = self.funcs.get(cmpr)
            if ctor is None:
                raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, type='subquery'))

            return ctor(runt)

        subq = self.kids[0]

        async def cond(node, path):
            genr = s_common.agen((node, path))
            async for _, subp in subq.run(runt, genr):
                path.vars.update(subp.vars)
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
    async def getLiftHints(self, runt, path):
        h0 = await self.kids[0].getLiftHints(runt, path)
        h1 = await self.kids[0].getLiftHints(runt, path)
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
    async def getLiftHints(self, runt, path):

        kid = self.kids[0]

        if not isinstance(kid, TagMatch):
            return []

        if kid.hasglob():
            return []

        if kid.isconst:
            return (
                ('tag', {'name': await kid.compute(None, None)}),
            )

        if kid.isRuntSafe(runt):
            name = await kid.compute(runt, path)
            if name and '*' not in name:
                return (
                    ('tag', {'name': name}),
                )

        return []

    async def getCondEval(self, runt):

        assert len(self.kids) == 1

        # kid is a non-runtsafe VarValue: dynamically evaluate value of variable for each node
        async def cond(node, path):
            name = await self.kids[0].compute(runt, path)
            if name == '*':
                return bool(node.getTagNames())

            if '*' in name:
                reobj = s_cache.getTagGlobRegx(name)
                return any(reobj.fullmatch(p) for p in node.getTagNames())

            return node.getTag(name) is not None

        return cond

class HasRelPropCond(Cond):

    async def getCondEval(self, runt):

        assert isinstance(self.kids[0], RelProp)

        virts = None
        if len(self.kids) == 2:
            virts = await self.kids[1].compute(runt, None)

        async def cond(node, path):
            return await self.hasProp(node, runt, path, virts=virts)

        return cond

    async def hasProp(self, node, runt, path, virts=None):

        realnode, name, _ = await self.kids[0].resolvePivs(node, runt, path)
        if realnode is None:
            return False

        if (prop := realnode.form.props.get(name)) is None:
            return False

        if virts is None:
            return realnode.has(name)

        try:
            vgetr = prop.type.getVirtGetr(virts)
        except s_exc.NoSuchVirt:
            return False

        return realnode.has(name, virts=vgetr)

    async def getLiftHints(self, runt, path):

        relprop = self.kids[0]

        name = await relprop.compute(runt, path)
        ispiv = name.find('::') != -1
        if ispiv:
            return (
                ('relprop', {'name': name.split('::')[0]}),
            )

        hint = {
            'name': name,
        }

        return (
            ('relprop', hint),
        )

class HasTagPropCond(Cond):

    async def getCondEval(self, runt):

        async def cond(node, path):
            tag = await self.kids[0].compute(runt, path)
            name = await self.kids[1].compute(runt, path)

            if tag == '*':
                tagprops = node._getTagPropsDict()
                return any(name in props for props in tagprops.values())

            if '*' in tag:
                reobj = s_cache.getTagGlobRegx(tag)
                tagprops = node._getTagPropsDict()
                for tagname, props in tagprops.items():
                    if reobj.fullmatch(tagname) and name in props:
                        return True

            return node.hasTagProp(tag, name)

        return cond

class HasAbsPropCond(Cond):

    async def getCondEval(self, runt):

        name = await self.kids[0].compute(runt, None)

        virts = None
        if len(self.kids) == 2:
            virts = await self.kids[1].compute(runt, None)

        prop = runt.model.props.get(name)
        if prop is not None:

            vgetr = None
            if virts:
                vgetr = prop.type.getVirtGetr(virts)

            if prop.isform:
                if virts is None:
                    async def cond(node, path):
                        return node.form.name == prop.name
                else:
                    async def cond(node, path):
                        if node.form.name != prop.name:
                            return False
                        return node.valu(virts=vgetr) is not None

                return cond

            async def cond(node, path):
                if node.form.name != prop.form.name:
                    return False

                return node.has(prop.name, virts=vgetr)

            return cond

        if name.endswith('*'):
            formlist = runt.model.reqFormsByPrefix(name[:-1], extra=self.kids[0].addExcInfo)

            async def cond(node, path):
                return node.form.name in formlist

            return cond

        if (formlist := runt.model.formsbyiface.get(name)) is not None:

            async def cond(node, path):
                return node.form.name in formlist

            return cond

        if (proplist := runt.model.ifaceprops.get(name)) is not None:

            formlist = []
            for propname in proplist:
                prop = runt.model.props.get(propname)
                formlist.append(prop.form.name)
                relname = prop.name

            vgetr = None
            if virts:
                vgetr = prop.type.getVirtGetr(virts)

            async def cond(node, path):
                if node.form.name not in formlist:
                    return False

                return node.has(relname, virts=vgetr)

            return cond

        raise self.kids[0].addExcInfo(s_exc.NoSuchProp.init(name))

class HasVirtPropCond(Cond):

    async def getCondEval(self, runt):

        async def cond(node, path):
            virts = await self.kids[0].compute(runt, path)
            if len(virts) == 1 and virts[0] in runt.model.metatypes:
                return node.getMeta(virts[0]) is not None

            getr = node.form.type.getVirtGetr(virts)
            return node.valu(virts=getr) is not None

        return cond

class VirtPropCond(Cond):

    async def getCondEval(self, runt):

        cmpr = self.kids[1].value()

        async def cond(node, path):

            (ptyp, val1) = await self.kids[0].getTypeValu(runt, path)
            if val1 is None:
                return False

            if (ctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            val2 = await self.kids[2].compute(runt, path)
            return ctor(val2)(val1)

        return cond

class ArrayCond(Cond):

    async def getCondEval(self, runt):

        offs = 0
        virts = None
        if len(self.kids) == 4:
            offs = 1
            virts = self.kids[1]

        relprop = self.kids[0]
        cmpr = self.kids[offs + 1].value()
        valukid = self.kids[offs + 2]

        async def cond(node, path):

            realnode, realprop, _ = await relprop.resolvePivs(node, runt, path)
            if realnode is None:
                return False

            if (prop := realnode.form.props.get(realprop)) is None:
                raise self.kids[0].addExcInfo(s_exc.NoSuchProp.init(realprop))

            if not prop.type.isarray:
                mesg = f'Array filter syntax is invalid for non-array prop {realprop}.'
                raise self.kids[offs + 1].addExcInfo(s_exc.BadCmprType(mesg=mesg))

            ptyp = prop.type.arraytype
            getr = None
            if virts is not None:
                vnames = await virts.compute(runt, path)
                (ptyp, getr) = ptyp.getVirtInfo(vnames)

            if (ctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            if (items := realnode.get(realprop, virts=getr)) is None:
                return False

            val2 = await valukid.compute(runt, path)

            for item in items:
                if ctor(val2)(item):
                    return True

            return False

        return cond

class AbsPropCond(Cond):

    async def getCondEval(self, runt):

        name = await self.kids[0].compute(runt, None)
        iface = False

        if (prop := runt.model.props.get(name)) is None:
            if (proplist := runt.model.ifaceprops.get(name)) is not None:
                iface = True
                prop = runt.model.props.get(proplist[0])
            else:
                raise self.kids[0].addExcInfo(s_exc.NoSuchProp.init(name))

        cmpr = await self.kids[1].compute(runt, None)

        if (ctor := prop.type.getCmprCtor(cmpr)) is None:
            raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=prop.type.name))

        if prop.isform:
            async def cond(node, path):
                if node.ndef[0] != name:
                    return False

                val1 = node.ndef[1]
                val2 = await self.kids[2].compute(runt, path)
                return ctor(val2)(val1)

            return cond

        async def cond(node, path):
            if not iface and node.ndef[0] != prop.form.name:
                return False

            if (val1 := node.get(prop.name)) is None:
                return False

            val2 = await self.kids[2].compute(runt, path)
            return ctor(val2)(val1)

        return cond

class AbsVirtPropCond(Cond):

    async def getCondEval(self, runt):

        name = await self.kids[0].compute(runt, None)
        virts = await self.kids[1].compute(runt, None)
        cmpr = await self.kids[2].compute(runt, None)

        props = runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)
        prop = props[0]

        if prop.isform and len(virts) == 1 and (ptyp := runt.model.metatypes.get(virts[0])) is not None:
            if (ctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            metaname = virts[0]

            async def cond(node, path):
                if node.ndef[0] != name:
                    return False

                val1 = node.getMeta(metaname)
                val2 = await self.kids[3].compute(runt, path)
                return ctor(val2)(val1)

            return cond

        (ptyp, getr) = prop.type.getVirtInfo(virts)

        if (ctor := ptyp.getCmprCtor(cmpr)) is None:
            raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

        if prop.isform:
            async def cond(node, path):
                if node.ndef[0] != name:
                    return False

                if (val1 := node.valu(virts=getr)) is None:
                    return False

                val2 = await self.kids[3].compute(runt, path)
                return ctor(val2)(val1)

            return cond

        forms = set([prop.form.name for prop in props])

        async def cond(node, path):
            if node.ndef[0] not in forms:
                return False

            if (val1 := node.get(prop.name, virts=getr)) is None:
                return False

            val2 = await self.kids[3].compute(runt, path)
            return ctor(val2)(val1)

        return cond

class TagValuCond(Cond):

    async def getCondEval(self, runt):

        lval = self.kids[0]
        cmpr = await self.kids[1].compute(runt, None)
        rval = self.kids[2]

        ival = runt.model.type('ival')
        if (cmprctor := ival.getCmprCtor(cmpr)) is None:
            raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ival.name))

        if isinstance(lval, VarValue) or not lval.isconst:
            async def cond(node, path):
                name = await lval.compute(runt, path)
                if '*' in name:
                    mesg = f'Wildcard tag names may not be used in conjunction with tag value comparison: {name}'
                    raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, name=name))

                valu = await rval.compute(runt, path)
                return cmprctor(valu)(node.getTag(name))

            return cond

        name = await lval.compute(runt, None)

        if isinstance(rval, Const):
            valu = await rval.compute(runt, None)
            cmpr = cmprctor(valu)

            async def cond(node, path):
                return cmpr(node.getTag(name))

            return cond

        # it's a runtime value...
        async def cond(node, path):
            valu = await rval.compute(runt, path)
            return cmprctor(valu)(node.getTag(name))

        return cond

class TagVirtCond(Cond):

    async def getCondEval(self, runt):

        lval = self.kids[0]
        vkid = self.kids[1]
        cmpr = await self.kids[2].compute(runt, None)
        rval = self.kids[3]

        ival = runt.model.type('ival')

        if isinstance(lval, VarValue) or not lval.isconst:
            async def cond(node, path):
                name = await lval.compute(runt, path)
                if '*' in name:
                    mesg = f'Wildcard tag names may not be used in conjunction with tag value comparison: {name}'
                    raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, name=name))

                valu = await rval.compute(runt, path)
                virts = await vkid.compute(runt, path)

                (ptyp, getr) = ival.getVirtInfo(virts)

                if (cmprctor := ptyp.getCmprCtor(cmpr)) is None:
                    raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

                tval = node.getTag(name)
                for func in getr:
                    tval = func(tval)

                return cmprctor(valu)(tval)

            return cond

        name = await lval.compute(runt, None)

        if isinstance(rval, Const):
            valu = await rval.compute(runt, None)
            virts = await vkid.compute(runt, None)

            (ptyp, getr) = ival.getVirtInfo(virts)

            if (cmprctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            cmpr = cmprctor(valu)

            async def cond(node, path):
                tval = node.getTag(name)
                for func in getr:
                    tval = func(tval)
                return cmpr(tval)

            return cond

        # it's a runtime value...
        async def cond(node, path):
            valu = await rval.compute(runt, path)
            virts = await vkid.compute(runt, path)

            (ptyp, getr) = ival.getVirtInfo(virts)

            if (cmprctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            tval = node.getTag(name)
            for func in getr:
                tval = func(tval)

            return cmprctor(valu)(tval)

        return cond

class RelPropCond(Cond):
    '''
    :foo:bar <cmpr> <value>
    '''
    async def getCondEval(self, runt):

        cmpr = self.kids[1].value()
        valukid = self.kids[2]

        async def cond(node, path):
            ptyp, valu, _ = await self.kids[0].getTypeValuProp(runt, path)

            xval = await valukid.compute(runt, path)
            if not isinstance(xval, s_node.Node):
                xval = await s_stormtypes.tostor(xval)

            if xval is None or valu is None:
                return False

            if (ctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[1].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            return ctor(xval)(valu)

        return cond

    async def getLiftHints(self, runt, path):

        relprop = self.kids[0].kids[0]

        name = await relprop.compute(runt, path)
        ispiv = name.find('::') != -1
        if ispiv:
            return (
                ('relprop', {'name': name.split('::')[0]}),
            )

        hint = {
            'name': name,
            'cmpr': await self.kids[1].compute(runt, path),
            'valu': await self.kids[2].compute(runt, path),
        }

        return (
            ('relprop', hint),
        )

class TagPropCond(Cond):

    async def getCondEval(self, runt):

        offs = 0
        virts = None
        if len(self.kids) == 5:
            offs = 1
            virts = await self.kids[2].compute(runt, None)

        cmpr = self.kids[offs + 2].value()
        rval = self.kids[offs + 3]

        async def cond(node, path):

            tag = await self.kids[0].compute(runt, path)
            name = await self.kids[1].compute(runt, path)

            if '*' in tag:
                mesg = f'Wildcard tag names may not be used in conjunction with tagprop value comparison: {tag}'
                raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, name=tag))

            prop = runt.model.getTagProp(name)
            if prop is None:
                mesg = f'No such tag property: {name}'
                raise self.kids[0].addExcInfo(s_exc.NoSuchTagProp(name=name, mesg=mesg))

            curv = node.getTagProp(tag, name)
            if curv is None:
                return False

            # TODO cache on (cmpr, valu) for perf?
            valu = await rval.compute(runt, path)

            getr = ()
            ptyp = prop.type
            if virts is not None:
                (ptyp, getr) = ptyp.getVirtInfo(virts)

            if (ctor := ptyp.getCmprCtor(cmpr)) is None:
                raise self.kids[2].addExcInfo(s_exc.NoSuchCmpr(cmpr=cmpr, name=ptyp.name))

            for func in getr:
                curv = func(curv)

            return ctor(valu)(curv)

        return cond

class FiltOper(Oper):

    async def getLiftHints(self, runt, path):

        if await self.kids[0].compute(None, None) != '+':
            return []

        return await self.kids[1].getLiftHints(runt, path)

    async def run(self, runt, genr):

        must = await self.kids[0].compute(None, None) == '+'
        cond = await self.kids[1].getCondEval(runt)

        async for node, path in genr:
            answ = await cond(node, path)
            if (must and answ) or (not must and not answ):
                yield node, path
            else:
                # all filters must sleep
                await asyncio.sleep(0)

class ArgvQuery(Value):

    runtopaque = True

    def isRuntSafe(self, runt):
        # an argv query is really just a string, so it's runtsafe.
        return True

    def validate(self, runt):
        # validation is done by the sub-runtime
        pass

    async def compute(self, runt, path):
        return self.kids[0].text

class PropValue(Value):

    def prepare(self):
        self.isconst = isinstance(self.kids[0], Const)

        self.virts = None
        self.constvirts = None

        if len(self.kids) > 1:
            self.virts = self.kids[1]
            if all(isinstance(k, Const) for k in self.virts.kids):
                self.constvirts = [k.value() for k in self.virts.kids]

    def isRuntSafe(self, runt):
        return False

    def isRuntSafeAtom(self, runt):
        return False

    async def getTypeValuProp(self, runt, path, strict=True):
        if not path:
            return None, None, None

        node, realprop, fullname = await self.kids[0].resolvePivs(path.node, runt, path)
        if node is None:
            return None, None, None

        if (prop := node.form.props.get(realprop)) is None:
            propname = await self.kids[0].compute(runt, path)
            if (exc := await s_stormtypes.typeerr(propname, str)) is None:
                if not strict:
                    return None, None, None

                mesg = f'No property named {propname}.'
                exc = s_exc.NoSuchProp(mesg=mesg, name=propname, form=path.node.form.name)

            raise self.kids[0].addExcInfo(exc)

        getr = None
        ptyp = prop.type

        if self.virts is not None:
            if (virts := self.constvirts) is None:
                virts = await self.virts.compute(runt, path)

            (ptyp, getr) = ptyp.getVirtInfo(virts)
            fullname += f".{'.'.join(virts)}"

        if (valu := node.get(realprop, virts=getr)) is None:
            return None, None, None

        if isinstance(valu, (dict, list, tuple)):
            # these get special cased because changing them affects the node
            # while it's in the pipeline but the modification doesn't get stored
            valu = s_msgpack.deepcopy(valu)

        return ptyp, valu, fullname

    async def compute(self, runt, path):
        return (await self.getTypeValuProp(runt, path))[1]

class RelPropValue(PropValue):
    pass

class VirtPropValue(PropValue):

    def prepare(self):
        self.const = self.kids[0].const

    async def getTypeValu(self, runt, path):

        node = path.node

        if (virts := self.const) is None:
            virts = await self.kids[0].compute(runt, path)

        if len(virts) == 1 and (mtyp := runt.model.metatypes.get(virts[0])) is not None:
            return mtyp, node.getMeta(virts[0])

        (ptyp, getr) = node.form.type.getVirtInfo(virts)

        if (valu := node.valu(virts=getr)) is None:
            return ptyp, None

        if isinstance(valu, (dict, list, tuple)):
            # these get special cased because changing them affects the node
            # while it's in the pipeline but the modification doesn't get stored
            valu = s_msgpack.deepcopy(valu)

        return ptyp, valu

    async def compute(self, runt, path):
        return (await self.getTypeValu(runt, path))[1]

class TagValue(Value):

    def isRuntSafe(self, runt):
        return False

    def isRuntSafeAtom(self, runt):
        return False

    async def compute(self, runt, path):
        name = await self.kids[0].compute(runt, path)
        return path.node.getTag(name)

class TagVirtValue(Value):

    def isRuntSafe(self, runt):
        return False

    def isRuntSafeAtom(self, runt):
        return False

    async def compute(self, runt, path):
        name = await self.kids[0].compute(runt, path)
        virts = await self.kids[1].compute(runt, path)

        valu = path.node.getTag(name)
        for getr in runt.model.type('ival').getVirtGetr(virts):
            valu = getr(valu)

        return valu

class TagProp(Value):

    async def compute(self, runt, path):
        tag = await self.kids[0].compute(runt, path)
        prop = await self.kids[1].compute(runt, path)
        return (tag, prop)

class FormTagProp(Value):

    async def compute(self, runt, path):
        form = await self.kids[0].compute(runt, path)
        tag = await self.kids[1].compute(runt, path)
        prop = await self.kids[2].compute(runt, path)
        return (form, tag, prop)

class TagPropValue(Value):
    async def compute(self, runt, path):
        tag, prop = await self.kids[0].compute(runt, path)

        tprop = runt.model.getTagProp(prop)
        if tprop is None:
            mesg = f'No such tag property: {prop}'
            raise self.kids[0].addExcInfo(s_exc.NoSuchTagProp(name=prop, mesg=mesg))

        valu = path.node.getTagProp(tag, prop)

        if len(self.kids) > 1:
            virts = await self.kids[1].compute(runt, path)
            for getr in tprop.type.getVirtGetr(virts):
                valu = getr(valu)

        return valu

class CallArgs(Value):

    async def compute(self, runt, path):
        return [await k.compute(runt, path) for k in self.kids]

class CallKwarg(CallArgs):
    pass

class CallKwargs(CallArgs):
    pass

class VirtProps(Value):
    def prepare(self):
        self.const = None
        if all(isinstance(k, Const) for k in self.kids):
            self.const = [k.value() for k in self.kids]

    async def compute(self, runt, path):
        if self.const is not None:
            return self.const
        return [await v.compute(runt, path) for v in self.kids]

class VarValue(Value):

    def validate(self, runt):

        if runt.runtvars.get(self.name) is None:
            exc = s_exc.NoSuchVar(mesg=f'Missing variable: {self.name}', name=self.name)
            raise self.addExcInfo(exc)

    def prepare(self):
        assert isinstance(self.kids[0], Const)
        self.name = self.kids[0].value()
        self.isconst = False

    def isRuntSafe(self, runt):
        return runt.isRuntVar(self.name)

    def isRuntSafeAtom(self, runt):
        return runt.isRuntVar(self.name)

    def hasVarName(self, name):
        return self.kids[0].value() == name

    async def compute(self, runt, path):

        if path is not None:
            valu = path.getVar(self.name, defv=s_common.novalu)
            if valu is not s_common.novalu:
                return valu

        valu = runt.getVar(self.name, defv=s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        if runt.isRuntVar(self.name):
            exc = s_exc.NoSuchVar(mesg=f'Runtsafe variable used before assignment: {self.name}',
                                  name=self.name, runtsafe=True)
        else:
            exc = s_exc.NoSuchVar(mesg=f'Non-runtsafe variable used before assignment: {self.name}',
                                  name=self.name, runtsafe=False)

        raise self.addExcInfo(exc)

class VarDeref(Value):

    async def compute(self, runt, path):

        base = await self.kids[0].compute(runt, path)
        # the deref of None is always None
        if base is None:
            return None

        name = await self.kids[1].compute(runt, path)

        valu = s_stormtypes.fromprim(base, path=path)
        with s_scope.enter({'runt': runt}):
            try:
                return await valu.deref(name)
            except s_exc.SynErr as e:
                raise self.kids[1].addExcInfo(e)

class FuncCall(Value):

    async def compute(self, runt, path):

        func = await self.kids[0].compute(runt, path)
        if not callable(func):
            text = self.getAstText()
            styp = await s_stormtypes.totype(func, basetypes=True)
            mesg = f"'{styp}' object is not callable: {text}"
            raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

        if runt.readonly and not getattr(func, '_storm_readonly', False):
            funcname = getattr(func, '_storm_funcpath', func.__name__)
            mesg = f'{funcname}() is not marked readonly safe.'
            raise self.kids[0].addExcInfo(s_exc.IsReadOnly(mesg=mesg))

        argv = await self.kids[1].compute(runt, path)
        kwargs = {k: v for (k, v) in await self.kids[2].compute(runt, path)}

        with s_scope.enter({'runt': runt}):
            try:
                retn = func(*argv, **kwargs)
                if s_coro.iscoro(retn):
                    return await retn
                return retn

            except TypeError as e:
                mesg = str(e)
                if (funcpath := getattr(func, '_storm_funcpath', None)) is not None:
                    mesg = f"{funcpath}(){mesg.split(')', 1)[1]}"

                raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            except s_exc.SynErr as e:
                if getattr(func, '_storm_runtime_lib_func', None) is not None:
                    e.errinfo.pop('highlight', None)
                raise self.addExcInfo(e)

class DollarExpr(Value):
    '''
    Top level node for $(...) expressions
    '''
    async def compute(self, runt, path):
        return await self.kids[0].compute(runt, path)

async def expr_add(x, y):
    return await tonumber(x) + await tonumber(y)

async def expr_sub(x, y):
    return await tonumber(x) - await tonumber(y)

async def expr_mod(x, y):
    return await tonumber(x) % await tonumber(y)

async def expr_mul(x, y):
    return await tonumber(x) * await tonumber(y)

async def expr_div(x, y):
    x = await tonumber(x)
    y = await tonumber(y)
    if isinstance(x, int) and isinstance(y, int):
        return x // y
    return x / y

async def expr_pow(x, y):
    return await tonumber(x) ** await tonumber(y)

async def expr_eq(x, y):
    return await tocmprvalu(x) == await tocmprvalu(y)

async def expr_ne(x, y):
    return await tocmprvalu(x) != await tocmprvalu(y)

async def expr_gt(x, y):
    return await tonumber(x) > await tonumber(y)

async def expr_lt(x, y):
    return await tonumber(x) < await tonumber(y)

async def expr_ge(x, y):
    return await tonumber(x) >= await tonumber(y)

async def expr_le(x, y):
    return await tonumber(x) <= await tonumber(y)

async def expr_prefix(x, y):
    x, y = await tostr(x), await tostr(y)
    return x.startswith(y)

async def expr_re(x, y):
    if regex.search(await tostr(y), await tostr(x), flags=regex.I):
        return True
    return False

async def expr_in(x, y):
    x = await toprim(x)
    if hasattr(y, '_storm_contains'):
        return await y._storm_contains(x)

    return x in await toprim(y)

async def expr_notin(x, y):
    x = await toprim(x)
    if hasattr(y, '_storm_contains'):
        return not (await y._storm_contains(x))

    return x not in await toprim(y)

_ExprFuncMap = {
    '+': expr_add,
    '-': expr_sub,
    '%': expr_mod,
    '*': expr_mul,
    '/': expr_div,
    '**': expr_pow,
    '=': expr_eq,
    '!=': expr_ne,
    '~=': expr_re,
    '>': expr_gt,
    '<': expr_lt,
    '>=': expr_ge,
    '<=': expr_le,
    '^=': expr_prefix,
    'in': expr_in,
    'not in': expr_notin,
}

async def expr_not(x):
    return not await tobool(x)

async def expr_neg(x):
    return await tonumber(x) * -1

_UnaryExprFuncMap = {
    '-': expr_neg,
    'not': expr_not,
}

class UnaryExprNode(Value):
    '''
    A unary (i.e. single-argument) expression node
    '''
    def prepare(self):
        assert len(self.kids) == 2
        assert isinstance(self.kids[0], Const)

        oper = self.kids[0].value()
        self._operfunc = _UnaryExprFuncMap[oper]

    async def compute(self, runt, path):
        return await self._operfunc(await self.kids[1].compute(runt, path))

class ExprNode(Value):
    '''
    A binary (i.e. two argument) expression node
    '''
    def prepare(self):

        assert len(self.kids) == 3
        assert isinstance(self.kids[1], Const)

        self.oper = self.kids[1].value()
        self._operfunc = _ExprFuncMap[self.oper]

    async def compute(self, runt, path):
        parm1 = await self.kids[0].compute(runt, path)
        parm2 = await self.kids[2].compute(runt, path)
        try:
            return await self._operfunc(parm1, parm2)
        except ZeroDivisionError:
            exc = s_exc.StormRuntimeError(mesg='Cannot divide by zero')
            raise self.kids[2].addExcInfo(exc)
        except decimal.InvalidOperation:
            exc = s_exc.StormRuntimeError(mesg='Invalid operation on a Number')
            raise self.addExcInfo(exc)
        except TypeError as e:
            exc = s_exc.StormRuntimeError(mesg=f'Error evaluating "{self.oper}" operator: {str(e)}')
            raise self.addExcInfo(exc)

class ExprOrNode(Value):
    async def compute(self, runt, path):
        parm1 = await self.kids[0].compute(runt, path)
        if await tobool(parm1):
            return True
        parm2 = await self.kids[2].compute(runt, path)
        return await tobool(parm2)

class ExprAndNode(Value):
    async def compute(self, runt, path):
        parm1 = await self.kids[0].compute(runt, path)
        if not await tobool(parm1):
            return False
        parm2 = await self.kids[2].compute(runt, path)
        return await tobool(parm2)

class TagName(Value):

    def prepare(self):
        self.isconst = not self.kids or all(isinstance(k, Const) for k in self.kids)
        if self.isconst and self.kids:
            self.constval = '.'.join([k.value() for k in self.kids])
        else:
            self.constval = None

    async def compute(self, runt, path):

        if self.isconst:
            return self.constval

        if not isinstance(self.kids[0], Const):
            valu = await self.kids[0].compute(runt, path)
            valu = await s_stormtypes.toprim(valu)

            if not isinstance(valu, str):
                mesg = 'Invalid value type for tag name, tag names must be strings.'
                raise s_exc.BadTypeValu(mesg=mesg)

            normtupl = runt.view.core.getTagNorm(valu)
            return normtupl[0]

        vals = []
        for kid in self.kids:
            part = await kid.compute(runt, path)
            if part is None:
                mesg = f'Null value from var ${kid.name} is not allowed in tag names.'
                raise kid.addExcInfo(s_exc.BadTypeValu(mesg=mesg))

            part = await tostr(part)
            partnorm = runt.view.core.getTagNorm(part)
            vals.append(partnorm[0])

        return '.'.join(vals)

    async def computeTagArray(self, runt, path, excignore=()):

        if self.isconst:
            return (self.constval,)

        if not isinstance(self.kids[0], (Const, FormatString)):
            tags = []
            vals = await self.kids[0].compute(runt, path)
            vals = await s_stormtypes.toprim(vals)

            if not isinstance(vals, (tuple, list, set)):
                vals = (vals,)

            for valu in vals:
                try:
                    if not isinstance(valu, str):
                        mesg = 'Invalid value type for tag name, tag names must be strings.'
                        raise s_exc.BadTypeValu(mesg=mesg)

                    normtupl = runt.view.core.getTagNorm(valu)
                    if normtupl is None:
                        continue

                    tags.append(normtupl[0])
                except excignore:
                    pass
            return tags

        vals = []
        for kid in self.kids:
            part = await kid.compute(runt, path)
            if part is None:
                mesg = f'Null value from var ${kid.name} is not allowed in tag names.'
                raise kid.addExcInfo(s_exc.BadTypeValu(mesg=mesg))

            part = await tostr(part)
            partnorm = runt.view.core.getTagNorm(part)
            vals.append(partnorm[0])

        return ('.'.join(vals),)

class TagMatch(TagName):
    '''
    Like TagName, but can have asterisks
    '''
    def hasglob(self):
        assert self.kids
        # TODO support vars with asterisks?
        return any('*' in kid.valu for kid in self.kids if isinstance(kid, Const))

    async def compute(self, runt, path):

        if self.isconst:
            return self.constval

        if not isinstance(self.kids[0], Const):
            valu = await self.kids[0].compute(runt, path)
            valu = await s_stormtypes.toprim(valu)

            if not isinstance(valu, str):
                mesg = 'Invalid value type for tag name, tag names must be strings.'
                raise s_exc.BadTypeValu(mesg=mesg)

            return valu

        vals = []
        for kid in self.kids:
            part = await kid.compute(runt, path)
            if part is None:
                mesg = f'Null value from var ${kid.name} is not allowed in tag names.'
                raise s_exc.BadTypeValu(mesg=mesg)

            vals.append(await tostr(part))

        return '.'.join(vals)

class Const(Value):

    def __init__(self, astinfo, valu, kids=()):
        Value.__init__(self, astinfo, kids=kids)
        self.isconst = True
        self.valu = valu

    def repr(self):
        return f'{self.__class__.__name__}: {self.valu}'

    def isRuntSafe(self, runt):
        return True

    def value(self):
        return self.valu

    async def compute(self, runt, path):
        return self.valu

class ExprDict(Value):

    def prepare(self):
        self.const = None
        if all(isinstance(k, Const) and not isinstance(k, EmbedQuery) for k in self.kids):
            valu = {}
            for i in range(0, len(self.kids), 2):
                valu[self.kids[i].value()] = self.kids[i + 1].value()
            self.const = s_msgpack.en(valu)

    async def compute(self, runt, path):

        if self.const is not None:
            return s_stormtypes.Dict(s_msgpack.un(self.const))

        valu = {}
        for i in range(0, len(self.kids), 2):

            key = await self.kids[i].compute(runt, path)

            if s_stormtypes.ismutable(key):
                key = await s_stormtypes.torepr(key)
                raise s_exc.BadArg(mesg='Mutable values are not allowed as dictionary keys', name=key)

            key = await toprim(key)

            valu[key] = await self.kids[i + 1].compute(runt, path)

        return s_stormtypes.Dict(valu)

class ExprList(Value):

    def prepare(self):
        self.const = None
        if all(isinstance(k, Const) and not isinstance(k, EmbedQuery) for k in self.kids):
            self.const = s_msgpack.en([k.value() for k in self.kids])

    async def compute(self, runt, path):
        if self.const is not None:
            return s_stormtypes.List(list(s_msgpack.un(self.const)))
        return s_stormtypes.List([await v.compute(runt, path) for v in self.kids])

class FormatString(Value):

    def prepare(self):
        self.isconst = not self.kids or (len(self.kids) == 1 and isinstance(self.kids[0], Const))
        self.constval = self.kids[0].value() if self.isconst and self.kids else ''

    async def compute(self, runt, path):
        if self.isconst:
            return self.constval
        reprs = [await s_stormtypes.torepr(await k.compute(runt, path), usestr=True) for k in self.kids]
        return ''.join(reprs)

class VarList(Const):
    pass

class Bool(Const):
    pass

class EmbedQuery(Const):
    runtopaque = True

    def validate(self, runt):
        # var scope validation occurs in the sub-runtime
        pass

    def hasVarName(self, name):
        # similar to above, the sub-runtime handles var scoping
        return False

    def getRuntVars(self, runt):
        if 0:
            yield

    async def compute(self, runt, path):

        varz = {}
        varz.update(runt.getScopeVars())

        if path is not None:
            varz.update(path.vars)

        return s_stormtypes.Query(self.valu, varz, runt, path=path)

class List(Value):

    def prepare(self):
        self.isconst = all(isinstance(k, Const) for k in self.kids)

    def repr(self):
        return 'List: %s' % self.kids

    async def compute(self, runt, path):
        return [await k.compute(runt, path) for k in self.kids]

class PropName(Value):

    def prepare(self):
        self.isconst = isinstance(self.kids[0], Const)
        if self.isconst:
            self.name = self.kids[0].value()
            self.pivs = self.name.split('::')

    async def compute(self, runt, path):
        return await self.kids[0].compute(runt, path)

    async def resolvePivs(self, node, runt, path):
        if self.isconst:
            pivs = self.pivs
            name = self.name
        else:
            propname = await self.compute(runt, path)
            name = await tostr(propname)
            pivs = name.split('::')

        realprop = pivs[-1]

        for name in pivs[:-1]:
            if (prop := node.form.props.get(name)) is None:
                return None, None, None

            if (valu := node.get(name)) is None:
                return None, None, None

            if (typename := prop.type.name) == 'ndef':
                ndef = valu
            elif (form := runt.model.forms.get(typename)) is not None:
                ndef = (form.name, valu)
            else:
                raise self.addExcInfo(s_exc.NoSuchForm.init(typename))

            if (node := await runt.view.getNodeByNdef(ndef)) is None:
                return None, None, None

        return node, realprop, name

class FormName(Value):

    async def compute(self, runt, path):
        return await self.kids[0].compute(runt, path)

class PivotTarget(Value):

    def init(self, core):
        [k.init(core) for k in self.kids]

        self.constval = None
        self.constprops = None
        if isinstance(self.kids[0], Const):
            self.constprops = self.getPropList(self.kids[0].value(), core.model)
            self.constval = [(prop, None) for prop in self.constprops]

    def getPropList(self, name, model):
        if (prop := model.props.get(name)) is not None:
            return (prop,)

        proplist = model.reqPropsByLook(name, extra=self.kids[0].addExcInfo)
        return [model.props.get(prop) for prop in proplist]

    async def compute(self, runt, path):
        if self.constval is not None:
            return self.constval

        valu = await self.kids[0].compute(runt, path)
        if not isinstance(valu, list):
            props = self.getPropList(valu, runt.model)
        else:
            props = []
            for name in valu:
                props += self.getPropList(name, runt.model)

        return [(prop, None) for prop in props]

class PivotTargetVirt(Value):

    def init(self, core):
        [k.init(core) for k in self.kids]

        self.virts = self.kids[1]
        self.constvirts = None
        if all(isinstance(k, Const) for k in self.virts.kids):
            self.constvirts = [k.value() for k in self.virts.kids]

        self.constprops = None
        if isinstance(self.kids[0], Const):
            self.constprops = core.model.reqPropList(self.kids[0].value(), extra=self.kids[0].addExcInfo)

        self.constval = None
        if self.constprops and self.constvirts:
            self.constval = [(prop, self.constvirts) for prop in self.constprops]

    async def compute(self, runt, path):
        if self.constval is not None:
            return self.constval

        if (virts := self.constvirts) is None:
            virts = await self.virts.compute(runt, path)

        if (props := self.constprops) is None:
            valu = await self.kids[0].compute(runt, path)
            if not isinstance(valu, list):
                props = runt.model.reqPropList(valu, extra=self.kids[0].addExcInfo)
            else:
                props = []
                for name in valu:
                    props += runt.model.reqPropList(name, extra=self.kids[0].addExcInfo)

        return [(prop, virts) for prop in props]

class PivotTargetList(List):

    def prepare(self):
        self.constval = None
        if all(k.constval is not None for k in self.kids):
            self.constval = []
            for kid in self.kids:
                self.constval += kid.constval

    async def compute(self, runt, path):
        if self.constval is not None:
            return self.constval

        targets = []
        for kid in self.kids:
            targets += await kid.compute(runt, path)

        return targets

class RelProp(PropName):
    pass

class Edit(Oper):
    pass

class EditParens(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        nodeadd = self.kids[0]
        assert isinstance(nodeadd, EditNodeAdd)

        formname = await nodeadd.kids[0].compute(runt, None)

        runt.layerConfirm(('node', 'add', formname))

        # create an isolated generator for the add vs edit
        if nodeadd.isRuntSafe(runt):

            # Luke, let the (node,path) tuples flow through you
            async for item in genr:
                yield item

            # isolated runtime stack...
            genr = s_common.agen()
            for oper in self.kids:
                genr = oper.run(runt, genr)

            async for item in genr:
                yield item

        else:

            # do a little genr-jig.
            async for node, path in genr:

                formname = await nodeadd.kids[0].compute(runt, path)
                form = runt.model.form(formname)

                yield node, path

                async def editgenr():
                    async for item in nodeadd.addFromPath(form, runt, path):
                        yield item

                fullgenr = editgenr()
                for oper in self.kids[1:]:
                    fullgenr = oper.run(runt, fullgenr)

                async for item in fullgenr:
                    yield item

class EditNodeAdd(Edit):

    def prepare(self):

        assert isinstance(self.kids[0], FormName)
        assert isinstance(self.kids[1], Const)

        self.oper = self.kids[1].value()
        self.excignore = (s_exc.BadTypeValu, ) if self.oper == '?=' else ()

    async def addFromPath(self, form, runt, path):
        '''
        Add a node using the context from path.

        NOTE: CALLER MUST CHECK PERMS
        '''
        vals = await self.kids[2].compute(runt, path)

        try:
            if isinstance(form.type, s_types.Guid):
                vals = await s_stormtypes.toprim(vals)

            for valu in form.type.getTypeVals(vals):
                try:
                    newn = await runt.view.addNode(form.name, valu)
                except self.excignore:
                    pass
                else:
                    if newn is not None:
                        yield newn, runt.initPath(newn)
        except self.excignore:
            await asyncio.sleep(0)

    async def run(self, runt, genr):

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

        self.reqNotReadOnly(runt)

        runtsafe = self.isRuntSafe(runt)

        async def feedfunc():

            if not runtsafe:

                async for node, path in genr:

                    # must reach back first to trigger sudo / etc
                    name = await self.kids[0].compute(runt, path)
                    formname = await tostr(name)
                    runt.layerConfirm(('node', 'add', formname))

                    form = runt.model.form(formname)
                    if form is None:
                        if (exc := await s_stormtypes.typeerr(name, str)) is None:
                            exc = s_exc.NoSuchForm.init(formname)

                        raise self.kids[0].addExcInfo(exc)

                    # must use/resolve all variables from path before yield
                    async for item in self.addFromPath(form, runt, path):
                        yield item

                    yield node, path
                    await asyncio.sleep(0)

            else:

                name = await self.kids[0].compute(runt, None)
                formname = await tostr(name)
                runt.layerConfirm(('node', 'add', formname))

                form = runt.model.form(formname)
                if form is None:
                    if (exc := await s_stormtypes.typeerr(name, str)) is None:
                        exc = s_exc.NoSuchForm.init(formname)

                    raise self.kids[0].addExcInfo(exc)

                valu = await self.kids[2].compute(runt, None)
                valu = await s_stormtypes.tostor(valu)

                try:
                    for valu in form.type.getTypeVals(valu):
                        try:
                            node = await runt.view.addNode(formname, valu)
                        except self.excignore:
                            continue

                        if node is not None:
                            yield node, runt.initPath(node)
                        await asyncio.sleep(0)
                except self.excignore:
                    await asyncio.sleep(0)

        if runtsafe:
            async for node, path in genr:
                yield node, path

        async with contextlib.aclosing(s_base.schedGenr(feedfunc())) as agen:
            async for item in agen:
                yield item

class CondSetOper(Oper):
    def __init__(self, astinfo, kids, errok=False):
        Value.__init__(self, astinfo, kids=kids)
        self.errok = errok

    def prepare(self):
        self.isconst = False
        if isinstance(self.kids[0], Const):
            self.isconst = True
            kidv = self.kids[0].value()
            self.valu = COND_EDIT_SET.get(kidv, kidv)

    async def compute(self, runt, path):
        if self.isconst:
            return self.valu

        valu = await self.kids[0].compute(runt, path)
        return COND_EDIT_SET.get(valu, valu)

class EditCondPropSet(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        excignore = (s_exc.BadTypeValu,) if self.kids[1].errok else ()
        rval = self.kids[2]

        async for node, path in genr:

            propname = await self.kids[0].compute(runt, path)
            name = await tostr(propname)

            prop = node.form.reqProp(name, extra=self.kids[0].addExcInfo)

            oper = await self.kids[1].compute(runt, path)
            if oper == SET_NEVER or (oper == SET_UNSET and (oldv := node.get(name)) is not None):
                yield node, path
                await asyncio.sleep(0)
                continue

            if not node.form.isrunt:
                # runt node property permissions are enforced by the callback
                runt.confirmPropSet(prop)

            if oper not in (SET_UNSET, SET_ALWAYS):
                try:
                    oldv = node.get(name)
                    valu = await rval.compute(runt, path)
                    newv, norminfo = prop.type.normVirt(oper, oldv, valu)

                    await node.set(name, newv, norminfo=norminfo)
                except excignore:
                    pass

                yield node, path
                await asyncio.sleep(0)
                continue

            isndef = isinstance(prop.type, s_types.Ndef)

            try:
                valu = await rval.compute(runt, path)
                valu = await s_stormtypes.tostor(valu, isndef=isndef)

                if isinstance(prop.type, s_types.Ival) and oldv is not None:
                    valu, _ = prop.type.norm(valu)
                    valu = prop.type.merge(oldv, valu)

                await node.set(name, valu)

            except excignore:
                pass

            yield node, path

            await asyncio.sleep(0)

class EditVirtPropSet(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        oper = await self.kids[2].compute(runt, None)
        excignore = (s_exc.BadTypeValu,) if oper in ('?=', '?+=', '?-=') else ()

        rval = self.kids[3]

        async for node, path in genr:

            propname = await self.kids[0].compute(runt, path)
            name = await tostr(propname)

            prop = node.form.reqProp(name, extra=self.kids[0].addExcInfo)

            if not node.form.isrunt:
                # runt node property permissions are enforced by the callback
                runt.confirmPropSet(prop)

            virts = await self.kids[1].compute(runt, path)

            try:
                oldv = node.get(name)
                valu = await rval.compute(runt, path)
                newv, norminfo = prop.type.normVirt(virts[0], oldv, valu)

                await node.set(name, newv, norminfo=norminfo)
            except excignore:
                pass

            yield node, path
            await asyncio.sleep(0)

class EditPropSet(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        oper = await self.kids[1].compute(runt, None)
        excignore = (s_exc.BadTypeValu,) if oper in ('?=', '?+=', '?-=') else ()

        isadd = oper in ('+=', '?+=')
        issub = oper in ('-=', '?-=')
        rval = self.kids[2]
        expand = True

        async for node, path in genr:

            propname = await self.kids[0].compute(runt, path)
            name = await tostr(propname)

            prop = node.form.props.get(name)
            if prop is None:
                if (exc := await s_stormtypes.typeerr(propname, str)) is None:
                    mesg = f'No property named {name} on form {node.form.name}.'
                    exc = s_exc.NoSuchProp(mesg=mesg, name=name, form=node.form.name)

                raise self.kids[0].addExcInfo(exc)

            if not node.form.isrunt:
                # runt node property permissions are enforced by the callback
                runt.confirmPropSet(prop)

            isndef = isinstance(prop.type, s_types.Ndef)
            isarray = prop.type.isarray
            if isarray and isinstance(prop.type.arraytype, s_types.Ndef):
                isndef = True

            try:

                if isarray and isinstance(rval, SubQuery):
                    valu = await rval.compute_array(runt, path)
                    expand = False

                else:
                    valu = await rval.compute(runt, path)

                valu = await s_stormtypes.tostor(valu, isndef=isndef)

                if isadd or issub:

                    if not isarray:
                        mesg = f'Property set using ({oper}) is only valid on arrays.'
                        exc = s_exc.StormRuntimeError(mesg=mesg)
                        raise self.kids[0].addExcInfo(exc)

                    arry = node.get(name)
                    if arry is None:
                        arry = ()

                    # make arry mutable
                    arry = list(arry)

                    if expand:
                        valu = (valu,)

                    if isadd:
                        arry.extend(valu)

                    else:
                        assert issub
                        # we cant remove something we cant norm...
                        # but that also means it can't be in the array so...
                        for v in valu:
                            norm, info = prop.type.arraytype.norm(v)
                            try:
                                arry.remove(norm)
                            except ValueError:
                                pass

                    valu = arry

                if isinstance(prop.type, s_types.Ival):
                    oldv = node.get(name)
                    if oldv is not None:
                        valu, _ = prop.type.norm(valu)
                        valu = prop.type.merge(oldv, valu)

                if node.form.isrunt:
                    await node.set(name, valu)
                else:
                    async with runt.view.getNodeEditor(node, runt=runt) as protonode:
                        await protonode.set(name, valu)

            except excignore:
                pass

            yield node, path

            await asyncio.sleep(0)

class EditPropSetMulti(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        rval = self.kids[2]
        oper = await self.kids[1].compute(runt, None)

        isadd = '+' in oper
        excignore = (s_exc.BadTypeValu,) if '?' in oper else ()

        async for node, path in genr:

            propname = await self.kids[0].compute(runt, path)
            name = await tostr(propname)

            prop = node.form.props.get(name)
            if prop is None:
                if (exc := await s_stormtypes.typeerr(propname, str)) is None:
                    exc = s_exc.NoSuchProp.init(f'{node.form.name}:{name}')

                raise self.kids[0].addExcInfo(exc)

            runt.confirmPropSet(prop)

            if not prop.type.isarray:
                mesg = f'Property set using ({oper}) is only valid on arrays.'
                exc = s_exc.StormRuntimeError(mesg=mesg)
                raise self.kids[0].addExcInfo(exc)

            if isinstance(rval, SubQuery):
                valu = await rval.compute_array(runt, path)
            else:
                valu = await rval.compute(runt, path)

            if valu is None:
                yield node, path
                await asyncio.sleep(0)
                continue

            atyp = prop.type.arraytype
            isndef = isinstance(atyp, s_types.Ndef)
            valu = await s_stormtypes.tostor(valu, isndef=isndef)

            if (arry := node.get(name)) is None:
                arry = ()

            arry = list(arry)

            try:
                for item in valu:
                    await asyncio.sleep(0)

                    try:
                        norm, info = atyp.norm(item)
                    except excignore:
                        continue

                    if isadd:
                        arry.append(norm)
                    else:
                        try:
                            arry.remove(norm)
                        except ValueError:
                            pass

            except TypeError:
                styp = await s_stormtypes.totype(valu, basetypes=True)
                mesg = f"'{styp}' object is not iterable: {s_common.trimText(repr(valu))}"
                raise rval.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, type=styp)) from None

            await node.set(name, arry)

            yield node, path
            await asyncio.sleep(0)

class EditPropDel(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        async for node, path in genr:
            propname = await self.kids[0].compute(runt, path)
            name = await tostr(propname)

            prop = node.form.props.get(name)
            if prop is None:
                if (exc := await s_stormtypes.typeerr(propname, str)) is None:
                    mesg = f'No property named {name}.'
                    exc = s_exc.NoSuchProp(mesg=mesg, name=name, form=node.form.name)

                raise self.kids[0].addExcInfo(exc)

            runt.confirmPropDel(prop)

            await node.pop(name)

            yield node, path

            await asyncio.sleep(0)

class N1Walk(Oper):

    def __init__(self, astinfo, kids=(), isjoin=False, reverse=False):
        Oper.__init__(self, astinfo, kids=kids)
        self.isjoin = isjoin
        self.reverse = reverse

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}, isjoin={self.isjoin}'

    async def walkNodeEdges(self, runt, node, verb=None):
        async for verb, nid in node.iterEdgesN1(verb=verb):
            walknode = await runt.view.getNodeByNid(nid)
            if walknode is not None:
                yield verb, walknode

    def buildfilter(self, runt, destforms, cmpr):

        if not isinstance(destforms, (tuple, list)):
            destforms = (destforms,)

        if '*' in destforms:
            if cmpr is not None:
                mesg = 'Wild card walk operations do not support comparison.'
                raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            return False

        forms = set()
        formprops = collections.defaultdict(dict)

        for destform in destforms:
            prop = runt.model.prop(destform)
            if prop is not None:
                if prop.isform:
                    forms.add(destform)
                else:
                    formprops[prop.form.name][prop.name] = prop
                continue

            formlist = runt.model.reqFormsByLook(destform, extra=self.kids[0].addExcInfo)
            forms.update(formlist)

        if cmpr is None:
            async def destfilt(node, path, cmprvalu):
                if node.form.full in forms:
                    return True

                props = formprops.get(node.form.full)
                if props is not None:
                    for prop in props:
                        if node.get(prop) is not None:
                            return True

                return False

            return destfilt

        async def destfilt(node, path, cmprvalu):

            if node.form.full in forms:
                return node.form.type.cmpr(node.ndef[1], cmpr, cmprvalu)

            props = formprops.get(node.form.full)
            if props is not None:
                for name, prop in props.items():
                    if (propvalu := node.get(name)) is not None:
                        if prop.type.cmpr(propvalu, cmpr, cmprvalu):
                            return True

            return False

        return destfilt

    async def run(self, runt, genr):

        cmpr = None
        cmprvalu = None
        destfilt = None

        if len(self.kids) == 4:
            cmpr = await self.kids[2].compute(runt, None)

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            verbs = await self.kids[0].compute(runt, path)
            verbs = await s_stormtypes.toprim(verbs)

            if not isinstance(verbs, (str, list, tuple)):
                mesg = f'walk operation expected a string or list.  got: {verbs!r}.'
                raise self.kids[0].addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            if isinstance(verbs, str):
                verbs = (verbs,)

            if cmpr is not None:
                cmprvalu = await self.kids[3].compute(runt, path)

            if destfilt is None or not self.kids[1].isconst:
                dest = await self.kids[1].compute(runt, path)
                dest = await s_stormtypes.toprim(dest)

                destfilt = self.buildfilter(runt, dest, cmpr)

            for verb in verbs:

                verb = await s_stormtypes.tostr(verb)

                if verb == '*':
                    verb = None

                async for verbname, walknode in self.walkNodeEdges(runt, node, verb=verb):

                    if destfilt and not await destfilt(walknode, path, cmprvalu):
                        continue

                    link = {'type': 'edge', 'verb': verbname}
                    if self.reverse:
                        link['reverse'] = True

                    yield walknode, path.fork(walknode, link)

class N2Walk(N1Walk):

    def __init__(self, astinfo, kids=(), isjoin=False):
        N1Walk.__init__(self, astinfo, kids=kids, isjoin=isjoin, reverse=True)

    async def walkNodeEdges(self, runt, node, verb=None):
        async for verb, nid in node.iterEdgesN2(verb=verb):
            walknode = await runt.view.getNodeByNid(nid)
            if walknode is not None:
                yield verb, walknode

class EditEdgeAdd(Edit):

    def __init__(self, astinfo, kids=(), n2=False):
        Edit.__init__(self, astinfo, kids=kids)
        self.n2 = n2

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        constverb = False
        if self.kids[0].isconst:
            constverb = True
            verb = await tostr(await self.kids[0].compute(runt, None))
            runt.layerConfirm(('node', 'edge', 'add', verb))
        else:
            hits = set()
            def allowed(x):
                if x in hits:
                    return

                runt.layerConfirm(('node', 'edge', 'add', x))
                hits.add(x)

        isvar = False
        vkid = self.kids[1]

        if not isinstance(vkid, SubQuery):
            isvar = True
        else:
            query = vkid.kids[0]

        async for node, path in genr:

            if node.form.isrunt:
                mesg = f'Edges cannot be used with runt nodes: {node.form.full}'
                raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=node.form.full))

            if not constverb:
                verb = await tostr(await self.kids[0].compute(runt, path))
                allowed(verb)

            if isvar:
                valu = await vkid.compute(runt, path)
                async with contextlib.aclosing(self.yieldFromValu(runt, valu, vkid)) as agen:
                    if self.n2:
                        nid = node.nid
                        form = node.form.name
                        async for subn in agen:
                            await subn.addEdge(verb, nid, n2form=form, extra=self.addExcInfo)
                    else:
                        async with node.view.getEditor() as editor:
                            proto = editor.loadNode(node)
                            async for subn in agen:
                                if subn.form.isrunt:
                                    mesg = f'Edges cannot be used with runt nodes: {subn.form.full}'
                                    raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=subn.form.full))

                                await proto.addEdge(verb, subn.nid, n2form=subn.form.name)
                                await asyncio.sleep(0)

            else:
                async with runt.getSubRuntime(query) as subr:
                    if self.n2:
                        nid = node.nid
                        form = node.form.name
                        async for subn, subp in subr.execute():
                            await subn.addEdge(verb, nid, n2form=form, extra=self.addExcInfo)
                    else:
                        async with node.view.getEditor() as editor:
                            proto = editor.loadNode(node)
                            async for subn, subp in subr.execute():
                                if subn.form.isrunt:
                                    mesg = f'Edges cannot be used with runt nodes: {subn.form.full}'
                                    raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=subn.form.full))

                                await proto.addEdge(verb, subn.nid, n2form=subn.form.name)
                                await asyncio.sleep(0)

            yield node, path

class EditEdgeDel(Edit):

    def __init__(self, astinfo, kids=(), n2=False):
        Edit.__init__(self, astinfo, kids=kids)
        self.n2 = n2

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        isvar = False
        vkid = self.kids[1]

        if not isinstance(vkid, SubQuery):
            isvar = True
        else:
            query = vkid.kids[0]

        constverb = False
        if self.kids[0].isconst:
            constverb = True
            verb = await tostr(await self.kids[0].compute(runt, None))
            runt.layerConfirm(('node', 'edge', 'del', verb))
        else:
            hits = set()
            def allowed(x):
                if x in hits:
                    return

                runt.layerConfirm(('node', 'edge', 'del', x))
                hits.add(x)

        async for node, path in genr:

            if node.form.isrunt:
                mesg = f'Edges cannot be used with runt nodes: {node.form.full}'
                raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=node.form.full))

            if not constverb:
                verb = await tostr(await self.kids[0].compute(runt, path))
                allowed(verb)

            if isvar:
                valu = await vkid.compute(runt, path)
                async with contextlib.aclosing(self.yieldFromValu(runt, valu, vkid)) as agen:
                    if self.n2:
                        nid = node.nid
                        async for subn in agen:
                            await subn.delEdge(verb, nid, extra=self.addExcInfo)
                    else:
                        async with node.view.getEditor() as editor:
                            proto = editor.loadNode(node)
                            async for subn in agen:
                                if subn.form.isrunt:
                                    mesg = f'Edges cannot be used with runt nodes: {subn.form.full}'
                                    raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=subn.form.full))

                                await proto.delEdge(verb, subn.nid)
                                await asyncio.sleep(0)

            else:
                async with runt.getSubRuntime(query) as subr:
                    if self.n2:
                        nid = node.nid
                        async for subn, subp in subr.execute():
                            await subn.delEdge(verb, nid, extra=self.addExcInfo)
                    else:
                        async with node.view.getEditor() as editor:
                            proto = editor.loadNode(node)
                            async for subn, subp in subr.execute():
                                if subn.form.isrunt:
                                    mesg = f'Edges cannot be used with runt nodes: {subn.form.full}'
                                    raise self.addExcInfo(s_exc.IsRuntForm(mesg=mesg, form=subn.form.full))

                                await proto.delEdge(verb, subn.nid)
                                await asyncio.sleep(0)

            yield node, path

class EditTagAdd(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        if len(self.kids) > 1 and isinstance(self.kids[0], Const) and (await self.kids[0].compute(runt, None)) == '?':
            oper_offset = 1
        else:
            oper_offset = 0

        excignore = (s_exc.BadTypeValu,) if oper_offset == 1 else ()

        hasval = len(self.kids) > 2 + oper_offset

        valu = (None, None)

        async for node, path in genr:

            try:
                names = await self.kids[oper_offset].computeTagArray(runt, path, excignore=excignore)
            except excignore:
                yield node, path
                await asyncio.sleep(0)
                continue

            for name in names:

                try:
                    parts = name.split('.')

                    runt.layerConfirm(('node', 'tag', 'add', *parts))

                    if hasval:
                        valu = await self.kids[2 + oper_offset].compute(runt, path)
                        valu = await s_stormtypes.toprim(valu)
                    await node.addTag(name, valu=valu)
                except excignore:
                    pass

            yield node, path

            await asyncio.sleep(0)

class EditTagDel(Edit):

    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        async for node, path in genr:

            names = await self.kids[0].computeTagArray(runt, path, excignore=(s_exc.BadTypeValu, s_exc.BadTag))

            for name in names:

                parts = name.split('.')

                runt.layerConfirm(('node', 'tag', 'del', *parts))

                await node.delTag(name)

            yield node, path

            await asyncio.sleep(0)

class EditTagPropSet(Edit):
    '''
    [ #foo.bar:baz=10 ]
    '''
    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        oper = await self.kids[1].compute(runt, None)
        excignore = s_exc.BadTypeValu if oper == '?=' else ()

        async for node, path in genr:

            tag, prop = await self.kids[0].compute(runt, path)

            valu = await self.kids[2].compute(runt, path)
            valu = await s_stormtypes.tostor(valu)

            tagparts = tag.split('.')

            # for now, use the tag add perms
            runt.layerConfirm(('node', 'tag', 'add', *tagparts))

            try:
                await node.setTagProp(tag, prop, valu)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except excignore:
                pass

            yield node, path

            await asyncio.sleep(0)

class EditTagPropDel(Edit):
    '''
    [ -#foo.bar:baz ]
    '''
    async def run(self, runt, genr):

        self.reqNotReadOnly(runt)

        async for node, path in genr:

            tag, prop = await self.kids[0].compute(runt, path)
            tagparts = tag.split('.')

            # for now, use the tag add perms
            runt.layerConfirm(('node', 'tag', 'del', *tagparts))

            await node.delTagProp(tag, prop)

            yield node, path

            await asyncio.sleep(0)

class BreakOper(AstNode):

    async def run(self, runt, genr):

        # we must be a genr...
        for _ in ():
            yield _

        async for node, path in genr:
            raise self.addExcInfo(s_stormctrl.StormBreak(item=(node, path)))

        raise self.addExcInfo(s_stormctrl.StormBreak())

class ContinueOper(AstNode):

    async def run(self, runt, genr):

        # we must be a genr...
        for _ in ():
            yield _

        async for node, path in genr:
            raise self.addExcInfo(s_stormctrl.StormContinue(item=(node, path)))

        raise self.addExcInfo(s_stormctrl.StormContinue())

class IfClause(AstNode):
    pass

class IfStmt(Oper):

    def _hasAstClass(self, clss):

        clauses = self.kids

        if not isinstance(clauses[-1], IfClause):
            if clauses[-1].hasAstClass(clss):
                return True

            clauses = clauses[:-1]

        for clause in clauses:
            if clause.kids[1].hasAstClass(clss):
                return True

        return False

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

            exprvalu = await expr.compute(runt, None)
            if await tobool(exprvalu):
                return subq
        else:
            return self.elsequery

    async def run(self, runt, genr):
        count = 0

        allcondsafe = all(clause.kids[0].isRuntSafe(runt) for clause in self.clauses)

        async for node, path in genr:
            count += 1

            for clause in self.clauses:
                expr, subq = clause.kids

                exprvalu = await expr.compute(runt, path)
                if await tobool(exprvalu):
                    break
            else:
                subq = self.elsequery

            if subq:
                assert isinstance(subq, SubQuery)

                async for item in subq.inline(runt, s_common.agen((node, path))):
                    yield item
            else:
                # If none of the if branches were executed and no else present, pass the stream through unaltered
                yield node, path

        if count != 0 or not allcondsafe:
            return

        # no nodes and a runt safe value should execute the winning clause once
        subq = await self._runtsafe_calc(runt)
        if subq:
            async for item in subq.inline(runt, s_common.agen()):
                yield item

class Return(Oper):

    async def run(self, runt, genr):

        # fake out a generator...
        for item in ():
            yield item  # pragma: no cover

        valu = None
        async for node, path in genr:
            if self.kids:
                valu = await self.kids[0].compute(runt, path)

            raise s_stormctrl.StormReturn(valu)

        # no items in pipeline... execute
        if self.isRuntSafe(runt):
            if self.kids:
                valu = await self.kids[0].compute(runt, None)
            raise s_stormctrl.StormReturn(valu)

class Emit(Oper):

    async def run(self, runt, genr):

        count = 0
        async for node, path in genr:
            count += 1
            try:
                await runt.emit(await self.kids[0].compute(runt, path))
            except s_exc.StormRuntimeError as e:
                raise self.addExcInfo(e)
            yield node, path

        # no items in pipeline and runtsafe. execute once.
        if count == 0 and self.isRuntSafe(runt):
            try:
                await runt.emit(await self.kids[0].compute(runt, None))
            except s_exc.StormRuntimeError as e:
                raise self.addExcInfo(e)

class Stop(Oper):

    async def run(self, runt, genr):
        for _ in (): yield _
        async for node, path in genr:
            raise self.addExcInfo(s_stormctrl.StormStop())
        raise self.addExcInfo(s_stormctrl.StormStop())

class FuncArgs(AstNode):
    '''
    Represents the function arguments in a function definition
    '''

    async def compute(self, runt, path):
        retn = []

        for kid in self.kids:
            valu = await kid.compute(runt, path)
            if isinstance(kid, CallKwarg):
                if s_stormtypes.ismutable(valu[1]):
                    exc = s_exc.StormRuntimeError(mesg='Mutable default parameter value not allowed')
                    raise kid.addExcInfo(exc)
            else:
                valu = (valu, s_common.novalu)
            retn.append(valu)

        return retn

class Function(AstNode):
    '''
    ( name, args, body )

    // use args/kwargs syntax
    function bar(x, v=$(30)) {
    }

    # we auto-detect the behavior of the target function

    # return a value
    function bar(x, y) { return ($(x + y)) }

    # a function that produces nodes
    function bar(x, y) { [ baz:faz=(x, y) ] }

    $foo = $bar(10, v=20)
    '''
    runtopaque = True
    def prepare(self):
        assert isinstance(self.kids[0], Const)
        self.name = self.kids[0].value()
        self.hasemit = self.hasAstClass(Emit)
        self.hasretn = self.hasAstClass(Return)

    def isRuntSafe(self, runt):
        return True

    async def run(self, runt, genr):
        argskid = self.kids[1]
        if not argskid.isRuntSafe(runt):
            exc = s_exc.StormRuntimeError(mesg='Non-runtsafe default parameter value not allowed')
            raise argskid.addExcInfo(exc)

        async def once():
            argdefs = await argskid.compute(runt, None)

            @s_stormtypes.stormfunc(readonly=True)
            async def realfunc(*args, **kwargs):
                return await self.callfunc(runt, argdefs, args, kwargs, realfunc._storm_funcpath)

            realfunc._storm_funcpath = self.name
            await runt.setVar(self.name, realfunc)

        count = 0

        async for node, path in genr:
            count += 1
            if count == 1:
                await once()

            yield node, path

        if count == 0:
            await once()

    def getRuntVars(self, runt):
        yield (self.kids[0].value(), True)

    def validate(self, runt):
        # var scope validation occurs in the sub-runtime
        pass

    async def callfunc(self, runt, argdefs, args, kwargs, funcpath):
        '''
        Execute a function call using the given runtime.

        This function may return a value / generator / async generator
        '''
        mergargs = {}
        posnames = set()  # Positional argument names

        argcount = len(args) + len(kwargs)
        if argcount > len(argdefs):
            mesg = f'{funcpath}() takes {len(argdefs)} arguments but {argcount} were provided'
            raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

        # Fill in the positional arguments
        for pos, argv in enumerate(args):
            name = argdefs[pos][0]
            mergargs[name] = argv
            posnames.add(name)

        # Merge in the rest from kwargs or the default values set at function definition
        for name, defv in argdefs[len(args):]:
            valu = kwargs.pop(name, s_common.novalu)
            if valu is s_common.novalu:
                if defv is s_common.novalu:
                    mesg = f'{funcpath}() missing required argument {name}'
                    raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg))
                valu = defv

            mergargs[name] = valu

        if kwargs:
            # Repeated kwargs are caught at parse time, so query either repeated a positional parameter, or
            # used a kwarg not defined.
            kwkeys = list(kwargs.keys())
            if kwkeys[0] in posnames:
                mesg = f'{funcpath}() got multiple values for parameter {kwkeys[0]}'
                raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

            plural = 's' if len(kwargs) > 1 else ''
            mesg = f'{funcpath}() got unexpected keyword argument{plural}: {",".join(kwkeys)}'
            raise self.kids[1].addExcInfo(s_exc.StormRuntimeError(mesg=mesg))

        assert len(mergargs) == len(argdefs)

        opts = {'vars': mergargs}

        if (self.hasretn and not self.hasemit):
            async with runt.getSubRuntime(self.kids[2], opts=opts) as subr:

                # inform the sub runtime to use function scope rules
                subr.funcscope = True

                try:
                    await asyncio.sleep(0)
                    async for item in subr.execute():
                        await asyncio.sleep(0)

                    return None
                except s_stormctrl.StormReturn as e:
                    return e.item
                except s_stormctrl.StormLoopCtrl as e:
                    mesg = f'function {self.name} - Loop control statement "{e.statement}" used outside of a loop.'
                    raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, function=self.name,
                                                                  statement=e.statement)) from e
                except s_stormctrl.StormGenrCtrl as e:
                    mesg = f'function {self.name} - Generator control statement "{e.statement}" used outside of a generator function.'
                    raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, function=self.name,
                                                                  statement=e.statement)) from e

        async def genr():
            async with runt.getSubRuntime(self.kids[2], opts=opts) as subr:
                # inform the sub runtime to use function scope rules
                subr.funcscope = True
                try:
                    if self.hasemit:
                        await asyncio.sleep(0)
                        async with contextlib.aclosing(await subr.emitter()) as agen:
                            async for item in agen:
                                yield item
                                await asyncio.sleep(0)
                    else:
                        await asyncio.sleep(0)
                        async with contextlib.aclosing(subr.execute()) as agen:
                            async for node, path in agen:
                                yield node, path
                except s_stormctrl.StormStop:
                    return
                except s_stormctrl.StormLoopCtrl as e:
                    mesg = f'function {self.name} - Loop control statement "{e.statement}" used outside of a loop.'
                    raise self.addExcInfo(s_exc.StormRuntimeError(mesg=mesg, function=self.name,
                                                                  statement=e.statement)) from e

        return genr()
