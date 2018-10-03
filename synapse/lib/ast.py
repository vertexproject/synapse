import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)


class AstNode:
    '''
    Base class for all nodes in the STORM abstract syntax tree.
    '''

    def __init__(self, kids=()):
        self.kids = []
        [self.addKid(k) for k in kids]

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

    def repr(self):
        return self.__class__.__name__

    def init(self, core):
        self.core = core
        [k.init(core) for k in self.kids]
        self.prepare()

    def prepare(self):
        pass

    def optimize(self):
        [k.optimize() for k in self.kids]

class Query(AstNode):

    def __init__(self, core, kids=()):

        AstNode.__init__(self, kids=kids)

        self.core = core
        self.text = ''

        # for options parsed from the query itself
        self.opts = {}

        # used by the di-graph projection logic
        self._graph_done = {}
        self._graph_want = collections.deque()

        self.tick = None
        self.canceled = False

    def setUser(self, user):
        self.user = user

    def isWrite(self):
        return any(o.iswrite for o in self.kids)

    def cancel(self):

        if self.snap is not None:
            self.snap.cancel()

        self.canceled = True

    async def execute(self):

        chan = asyncio.Queue(maxsize=10)

        coro = self._runQueryThread(chan)

        s_glob.plex.coroLoopTask(coro)

        while not self.canceled:

            item = await chan.get()
            if item is None:
                return

            yield item

    async def getInput(self, snap):
        for ndef in self.opts.get('ndefs', ()):
            node = await snap.getNodeByNdef(ndef)
            if node is not None:
                yield node, node.initPath()
        for iden in self.opts.get('idens', ()):
            buid = s_common.uhex(iden)
            node = await snap.getNodeByBuid(buid)
            if node is not None:
                yield node, node.initPath()

    async def _finiGraph(self, runt):

        # gather up any remaining todo nodes
        while runt._graph_want:

            ndef = runt._graph_want.popleft()

            if runt._graph_done.get(ndef):
                continue

            node = await runt.snap.getNodeByNdef(ndef)
            if node is None:
                continue

            path = runt.initPath(node)

            await self._iterGraph(runt, node, path)

            yield node, path

    async def _iterGraph(self, runt, node, path):

        runt._graph_done[node.ndef] = True

        done = {}
        edges = []

        for name, ndef in node.getNodeRefs():

            if done.get(ndef):
                continue

            done[ndef] = True

            iden = s_common.ehex(s_common.buid(ndef))

            edges.append((iden, {}))

            if not runt._graph_done.get(ndef):
                runt._graph_want.append(ndef)

        path.meta('edges', edges)

    async def iterNodePaths(self, runt):

        self.core._logStormQuery(self.text, runt.user)

        count = 0

        graph = runt.getOpt('graph')

        self.optimize()

        # turtles all the way down...
        genr = runt.getInput()

        for oper in self.kids:
            genr = oper.run(runt, genr)

        async for node, path in genr:

            runt.tick()

            if graph:
                await self._iterGraph(runt, node, path)

            yield node, path

            count += 1

            limit = runt.getOpt('limit')
            if limit is not None and count >= limit:
                await runt.printf('limit reached: %d' % (limit,))
                break

        if graph:
            async for item in self._finiGraph(runt):
                yield item

class Oper(AstNode):
    pass

class SubQuery(Oper):
    pass

class CmdOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        text = self.kids[1].value()

        ctor = runt.snap.core.getStormCmd(name)
        if ctor is None:
            mesg = 'Storm command not found.'
            raise s_exc.NoSuchName(name=name, mesg=mesg)

        scmd = ctor(text)

        if not await scmd.hasValidOpts(runt.snap):
            return

        async for item in scmd.execStormCmd(runt, genr):
            yield item

class VarSetOper(Oper):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        if isinstance(self.kids[1], Value):
            valu = self.kids[1].value()
            runt.vars[name] = valu

        async for node, path in genr:
            valu = self.kids[1].compute(runt, node, path)
            path.set(name, valu)
            runt.vars[name] = valu
            yield node, path

class LiftOper(Oper):

    async def run(self, runt, genr):

        async for x in genr:
            yield x

        async for node in self.lift(runt):
            yield node, runt.initPath(node)

class LiftTag(LiftOper):

    async def lift(self, runt):
        tag = self.kids[0].value()
        async for node in runt.snap._getNodesByTag(tag):
            yield node

class LiftFormTag(LiftOper):

    async def lift(self, runt):

        form = self.kids[0].value()
        tag = self.kids[1].value()

        cmpr = None
        valu = None

        if len(self.kids) == 4:
            cmpr = self.kids[2].value()
            valu = self.kids[3].runtval(runt)

        async for node in runt.snap._getNodesByFormTag(form, tag, valu=valu, cmpr=cmpr):
            yield node

class LiftProp(LiftOper):

    async def lift(self, runt):

        name = self.kids[0].value()

        cmpr = None
        valu = None

        if len(self.kids) == 3:
            cmpr = self.kids[1].value()
            valu = self.kids[2].runtval(runt)

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

        valu = self.kids[2].runtval(runt)

        async for node in runt.snap.getNodesBy(name, valu, cmpr=cmpr):
            yield node

class PivotOper(Oper):

    def __init__(self, kids=(), isjoin=False):
        Oper.__init__(self, kids=kids)
        self.isjoin = isjoin

class PivotOut(PivotOper):
    '''
    -> *
    '''
    async def run(self, runt, genr):

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            if isinstance(node.form.type, s_types.Edge):
                n2def = node.get('n2')
                pivo = await runt.snap.getNodeByNdef(n2def)
                yield pivo, path.fork(pivo)
                continue

            for name, valu in node.props.items():

                prop = node.form.props.get(name)

                if prop is None:
                    # this should be impossible
                    logger.warning(f'node prop is not form prop: {node.form.name} {name}')
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
                async for pivo in runt.snap.getNodesBy(prop.full, valu):
                    yield pivo, path.fork(pivo)

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
        destform = prop.name

        @s_cache.memoize()
        def getsrc(form):
            for name, prop in form.props.items():
                if prop.type.name == destform:
                    return name

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            # if the source node is a graph edge, use n2
            if isinstance(node.form.type, s_types.Edge):

                n2def = node.get('n2')
                if n2def[0] != destform:
                    continue

                pivo = await runt.snap.getNodeByNdef(node.get('n2'))
                yield pivo, path.fork(pivo)

                continue

            name = getsrc(node.form)
            if name is None:
                continue

            # TODO: bypass normalization
            valu = node.get(name)

            async for pivo in runt.snap.getNodesBy(prop.name, valu):
                yield pivo, path.fork(pivo)

class PropPivotOut(PivotOper):

    async def run(self, runt, genr):

        name = self.kids[0].value()

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
                yield pivo, path.fork(pivo)
                continue

            # :ipv4 -> *
            ndef = (prop.type.name, valu)
            pivo = await runt.snap.getNodeByNdef(ndef)
            yield pivo, path.fork(pivo)

class PropPivot(PivotOper):

    async def run(self, runt, genr):

        name = self.kids[1].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        # TODO if we are pivoting to a form, use ndef!

        async for node, path in genr:

            if self.isjoin:
                yield node, path

            valu = self.kids[0].compute(runt, node, path)
            if valu is None:
                continue

            # TODO cache/bypass normalization in loop!
            try:
                async for pivo in runt.snap.getNodesBy(prop.full, valu):
                    yield pivo, path.fork(pivo)
            except (s_exc.BadTypeValu, s_exc.BadLiftValu) as e:
                logger.warning('Caught error during pivot', exc_info=e)
                items = e.items()
                mesg = items.pop('mesg', '')
                mesg = ': '.join((f'{e.__class__.__qualname__} [{repr(valu)}] during pivot', mesg))
                await runt.snap.warn(mesg, **items)

class Cond(AstNode):

    def getLiftHints(self):
        return ()

    def getCondEval(self, runt):
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.evaluate()')

class OrCond(Cond):
    '''
    <cond> or <cond>
    '''
    def getCondEval(self, runt):

        cond0 = self.kids[0].getCondEval(runt)
        cond1 = self.kids[1].getCondEval(runt)

        def cond(node, path):

            if cond0(node, path):
                return True

            return cond1(node, path)

        return cond

class AndCond(Cond):
    '''
    <cond> and <cond>
    '''
    def getLiftHints(self):
        h0 = self.kids[0].getLiftHints()
        h1 = self.kids[1].getLiftHints()
        return h0 + h1

    def getCondEval(self, runt):

        cond0 = self.kids[0].getCondEval(runt)
        cond1 = self.kids[1].getCondEval(runt)

        def cond(node, path):

            if not cond0(node, path):
                return False

            return cond1(node, path)

        return cond

class NotCond(Cond):
    '''
    not <cond>
    '''

    def getCondEval(self, runt):

        kidcond = self.kids[0].getCondEval(runt)

        def cond(node, path):
            return not kidcond(node, path)

        return cond

class TagCond(Cond):
    '''
    #foo.bar
    '''
    def getLiftHints(self):
        name = self.kids[0].value()
        return (
            ('tag', {'name': name}),
        )

    def getCondEval(self, runt):

        name = self.kids[0].value()

        def cond(node, path):
            return node.tags.get(name) is not None

        return cond

class HasRelPropCond(Cond):

    def getCondEval(self, runt):

        name = self.kids[0].value()

        def cond(node, path):
            return node.has(name)

        return cond

class HasAbsPropCond(Cond):

    def getCondEval(self, runt):

        name = self.kids[0].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        if prop.isform:

            def cond(node, path):
                return node.form.name == prop.name

            return cond

        def cond(node, path):

            if node.form.name != prop.form.name:
                return False

            return node.has(prop.name)

        return cond

class AbsPropCond(Cond):

    def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        prop = runt.snap.model.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(name=name)

        ctor = prop.type.getCmprCtor(cmpr)
        if ctor is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr, name=prop.type.name)

        if prop.isform:

            def cond(node, path):

                if node.ndef[0] != name:
                    return False

                val1 = node.ndef[1]
                val2 = self.kids[2].compute(runt, node, path)

                return ctor(val2)(val1)

            return cond

        def cond(node, path):
            val1 = node.get(prop.name)
            if val1 is None:
                return False

            val2 = self.kids[2].compute(runt, node, path)
            return ctor(val2)(val1)

        return cond

class TagValuCond(Cond):

    def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        ival = runt.snap.model.type('ival')

        cmprctor = ival.getCmprCtor(cmpr)
        if cmprctor is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr, name=ival.name)

        if isinstance(self.kids[2], Const):

            valu = self.kids[2].value()

            cmpr = cmprctor(valu)

            def cond(node, path):
                return cmpr(node.tags.get(name))

            return cond

        # it's a runtime value...
        def cond(node, path):
            valu = self.kids[2].compute(runt, node, path)
            return cmprctor(valu)(node.tags.get(name))

        return cond

class RelPropCond(Cond):
    '''
    :foo:bar <cmpr> <value>
    '''
    def getCondEval(self, runt):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()

        def cond(node, path):

            prop = node.form.props.get(name)
            if prop is None:
                return False

            valu = node.get(prop.name)
            if valu is None:
                return False

            xval = self.kids[2].compute(runt, node, path)
            func = prop.type.getCmprCtor(cmpr)(xval)

            return func(valu)

        return cond

class FiltOper(Oper):

    def getLiftHints(self):

        if self.kids[0].value() != '+':
            return ()

        return self.kids[1].getLiftHints()

    async def run(self, runt, genr):

        must = self.kids[0].value() == '+'
        func = self.kids[1].getCondEval(runt)

        async for node, path in genr:
            answ = func(node, path)
            if (must and answ) or (not must and not answ):
                yield node, path

class CompValue(AstNode):

    def compute(self, runt, node, path):
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.compute()')

class RunValue(AstNode):

    def runtval(self, runt):
        return self.value()

    def compute(self, runt, node, path):
        return self.runtval(runt)

class RelPropValue(CompValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def compute(self, runt, node, path):
        return node.get(self.name)

class TagPropValue(CompValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def compute(self, runt, node, path):
        return node.getTag(self.name)

class VarValue(RunValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def runtval(self, runt):
        return runt.vars.get(self.name)

    def compute(self, runt, node, path):
        valu = path.get(self.name, s_common.novalu)
        if valu is s_common.novalu:
            raise s_exc.NoSuchVar(name=self.name)
        return valu

class Value(RunValue):

    def __init__(self, valu, kids=()):
        RunValue.__init__(self, kids=kids)
        self.valu = valu

    def runtval(self, runt):
        return self.value()

    def compute(self, runt, node, path):
        return self.value()

    def value(self):
        return self.valu

class Cmpr(Value):

    def repr(self):
        return 'Cmpr: %r' % (self.text,)

class Const(Value):

    def repr(self):
        return 'Const: %s' % (self.valu,)

class List(Value):

    def repr(self):
        return 'List: %s' % (self.valu,)

    def runtval(self, runt):
        return [k.runtval(runt) for k in self.kids]

    def compute(self, runt, node, path):
        return [k.compute(runt, node, path) for k in self.kids]

    def value(self):
        return [k.value() for k in self.kids]

class Tag(Value):

    def repr(self):
        return 'Tag: #%s' % (self.valu,)

class RelProp(Value):

    def repr(self):
        return 'RelProp: %r' % (self.valu,)

class AbsProp(Value):

    def repr(self):
        return f'AbsProp: {self.valu}'

class Edit(Oper):
    pass

class EditNodeAdd(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        formtype = runt.snap.model.types.get(name)

        async for x in genr:
            yield x

        runt.allowed('node:add', name)

        kval = self.kids[1].runtval(runt)

        for valu in formtype.getTypeVals(kval):
            node = await runt.snap.addNode(name, valu)
            yield node, runt.initPath(node)

class EditPropSet(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()

        async for node, path in genr:

            valu = self.kids[1].compute(runt, node, path)

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

        runt.allowed('prop:del', name)

        async for node, path in genr:
            await node.pop(name)
            yield node, path

class EditTagAdd(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        hasval = len(self.kids) > 1

        valu = (None, None)

        parts = name.split('.')

        async for node, path in genr:

            runt.allowed('tag:add', *parts)

            if hasval:
                valu = self.kids[1].compute(runt, node, path)

            await node.addTag(name, valu=valu)

            yield node, path

class EditTagDel(Edit):

    async def run(self, runt, genr):

        name = self.kids[0].value()
        parts = name.split('.')

        async for node, path in genr:

            runt.allowed('tag:del', *parts)

            await node.delTag(name)

            yield node, path
