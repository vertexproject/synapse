import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

import synapse.lib.queue as s_queue

class AstNode:
    '''
    Base class for all nodes in the STORM abstract syntax tree.
    '''

    def __init__(self, kids=()):
        self.snap = None

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

        if self.snap:
            astn.init(self.snap)

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

    def init(self, snap):
        self.snap = snap
        [k.init(snap) for k in self.kids]
        self.prepare()

    def prepare(self):
        pass

    def optimize(self):
        [k.optimize() for k in self.kids]

class Query(AstNode):

    def __init__(self, view, kids=()):

        AstNode.__init__(self, kids=kids)

        self.user = None
        self.view = view
        self.text = ''

        self.opts = {}

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

    def execute(self):

        chan = s_queue.Queue()

        self._runQueryThread(chan)

        return chan

    def getInput(self, snap):
        for ndef in self.opts.get('ndefs', ()):
            node = snap.getNodeByNdef(ndef)
            if node is not None:
                path = s_node.Path(self.snap.vars)
                yield node, path

    def evaluate(self):

        with self._getQuerySnap() as snap:
            yield from self._runQueryLoop(snap)

    def _runQueryLoop(self, snap):

        snap.core._logStormQuery(self.text, self.user)

        count = 0

        # all snap events go into the output queue...
        snap.runt['storm:opts'] = self.opts

        self.init(snap)

        varz = self.opts.get('vars')
        if varz is not None:
            snap.vars.update(varz)

        self.optimize()

        # turtles all the way down...
        genr = self.getInput(snap)

        for oper in self.kids:
            genr = oper.run(genr)

        for item in genr:

            yield item

            count += 1

            limit = self.opts.get('limit')
            if limit is not None and count >= limit:
                snap.printf('limit reached: %d' % (limit,))
                break

            if self.canceled:
                raise s_exc.Canceled()

    def _getQuerySnap(self):
        write = self.isWrite()
        snap = self.view.snap()
        snap.setUser(self.user)
        return snap

    @s_glob.inpool
    def _runQueryThread(self, chan):

        #for depth, text in self.format():
            #print(' ' * depth + text)

        try:

            count = 0

            dopath = self.opts.get('path')
            dorepr = self.opts.get('repr')

            with self._getQuerySnap() as snap:

                tick = s_common.now()
                chan.put(('init', {'tick': tick}))

                snap.link(chan.put)

                for node, path in self._runQueryLoop(snap):
                    pode = node.pack(dorepr=dorepr)
                    chan.put(('node', pode))
                    count += 1

        except Exception as e:
            logger.exception('error in storm execution')
            chan.put(('err', s_common.err(e)))

        finally:
            tock = s_common.now()
            took = tock - tick
            chan.put(('fini', {'tock': tock, 'took': took, 'count': count}))
            chan.done()

class Oper(AstNode):
    iswrite = False

class SubQuery(Oper):
    pass

class CmdOper(Oper):

    def prepare(self):

        name = self.kids[0].value()
        text = self.kids[1].value()

        ctor = self.snap.core.getStormCmd(name)

        if ctor is None:
            mesg = 'Storm command not found.'
            raise s_exc.NoSuchName(name=name, mesg=mesg)

        self.scmd = ctor(text)
        self.scmd.reqValidOpts(self.snap)

    def run(self, genr):
        # we only actually run or do anything if parser was ok
        if not self.scmd.pars.exited:
            yield from self.scmd.runStormCmd(self.snap, genr)

class VarSetOper(Oper):

    def run(self, genr):

        name = self.kids[0].value()

        vkid = self.kids[1]
        if isinstance(vkid, Value):
            self.snap.vars[name] = vkid.value()

        for node, path in genr:
            valu = self.kids[1].compute(node, path)
            path.set(name, valu)
            self.snap.vars[name] = valu
            yield node, path

class LiftOper(Oper):

    def run(self, genr):

        yield from genr

        for node in self.lift():
            path = s_node.Path(self.snap.vars)
            yield node, path

class LiftTag(LiftOper):

    def lift(self):
        tag = self.kids[0].value()
        yield from self.snap._getNodesByTag(tag)

class LiftFormTag(LiftOper):

    def prepare(self):

        self.form = self.kids[0].value()
        self.tag = self.kids[1].value()

        self.cmpr = None
        self.valu = None

        if len(self.kids) == 4:
            self.cmpr = self.kids[2].value()
            self.valu = self.kids[3].value()

    def lift(self):
        yield from self.snap._getNodesByFormTag(self.form, self.tag, valu=self.valu, cmpr=self.cmpr)

class LiftProp(LiftOper):

    def prepare(self):
        self.name = self.kids[0].value()
        # TODO generalize by morphing AST
        self.taghint = None

    def optimize(self):

        if self.snap.model.forms.get(self.name) is None:
            return

        # lifting by a form only is pretty bad, maybe
        # we can pick up a near by filter based hint...
        for oper in self.iterright():

            if isinstance(oper, FiltOper):

                for hint in oper.getLiftHints():

                    if hint[0] == 'tag':
                        self.taghint = hint[1].get('name')
                        return

            # we can skip other lifts but that's it...
            if isinstance(oper, LiftOper):
                continue

            break

    def lift(self):

        if self.taghint:
            yield from self.snap._getNodesByFormTag(self.name, self.taghint)
            return

        yield from self.snap.getNodesBy(self.name)

class LiftPropBy(LiftOper):

    def lift(self):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()
        valu = self.kids[2].value()

        yield from self.snap.getNodesBy(name, valu, cmpr=cmpr)

class PivotOper(Oper):

    def __init__(self, kids=(), isjoin=False):
        Oper.__init__(self, kids=kids)
        self.isjoin = isjoin

class PivotOut(PivotOper):
    '''
    -> *
    '''

    def prepare(self):
        pass

    def run(self, genr):

        for node, path in genr:

            if self.isjoin:
                yield node, path

            if isinstance(node.form.type, s_types.Edge):
                n2def = node.get('n2')
                pivo = self.snap.getNodeByNdef(n2def)
                yield pivo, path.fork()
                continue

            for name, valu in node.props.items():

                prop = node.form.props.get(name)

                if prop is None:
                    # this should be impossible
                    logger.warning(f'node prop is not form prop: {node.form.name} {name}')
                    continue

                form = self.snap.model.forms.get(prop.type.name)
                if form is None:
                    continue

                pivo = self.snap.getNodeByNdef((form.name, valu))
                if pivo is None:
                    continue

                yield pivo, path.fork()

class PivotIn(PivotOper):
    '''
    <- *
    '''

    def prepare(self):
        pass

    def run(self, genr):

        for node, path in genr:

            if self.isjoin:
                yield node, path

            # if it's a digraph edge, use :n2
            if isinstance(node.form.type, s_types.Edge):

                ndef = node.get('n1')

                pivo = self.snap.getNodeByNdef(ndef)
                if pivo is None:
                    continue

                yield pivo, path.fork()

                continue

            name, valu = node.ndef

            for prop in self.snap.model.propsbytype.get(name, ()):
                for pivo in self.snap.getNodesBy(prop.full, valu):
                    yield pivo, path.fork()

class PivotInFrom(PivotOper):

    def prepare(self):

        name = self.kids[0].value()
        self.form = self.snap.model.forms.get(name)

        if self.form is None:
            raise s_exc.NoSuchForm(name=name)

    def run(self, genr):

        # <- edge
        if isinstance(self.form.type, s_types.Edge):

            full = self.form.name + ':n2'

            for node, path in genr:
                for pivo in self.snap.getNodesBy(full, node.ndef):
                    yield pivo, path.fork()

            return

        # edge <- form
        for node, path in genr:

            if not isinstance(node.form.type, s_types.Edge):
                continue

            # dont bother traversing edges to the wrong form
            if node.get('n1:form') != self.form.name:
                continue

            n1def = node.get('n1')

            pivo = self.snap.getNodeByNdef(n1def)
            if pivo is None:
                continue

            yield pivo, path.fork()

class FormPivot(PivotOper):

    def prepare(self):

        name = self.kids[0].value()

        self.prop = self.snap.model.props.get(name)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=name)

    def run(self, genr):

        if not self.prop.isform:

            # plain old pivot...
            for node, path in genr:

                if self.isjoin:
                    yield node, path

                valu = node.ndef[1]

                # TODO cache/bypass normalization in loop!
                for pivo in self.snap.getNodesBy(self.prop.full, valu):
                    yield pivo, path.fork()

        # form -> form pivot is nonsensical. Lets help out...

        # if dest form is a subtype of a digraph "edge", use N1 automatically
        if isinstance(self.prop.type, s_types.Edge):

            full = self.prop.name + ':n1'

            for node, path in genr:
                for pivo in self.snap.getNodesBy(full, node.ndef):
                    yield pivo, path.fork()

            return

        # form name and type name match
        destform = self.prop.name

        @s_cache.memoize()
        def getsrc(form):
            for name, prop in form.props.items():
                if prop.type.name == destform:
                    return name

        for node, path in genr:

            if self.isjoin:
                yield node, path

            # if the source node is a digraph edge, use n2
            if isinstance(node.form.type, s_types.Edge):

                n2def = node.get('n2')
                if n2def[0] != destform:
                    continue

                pivo = self.snap.getNodeByNdef(node.get('n2'))
                yield pivo, path.fork()

                continue

            name = getsrc(node.form)
            if name is None:
                continue

            # TODO: bypass normalization
            valu = node.get(name)

            for pivo in self.snap.getNodesBy(self.prop.name, valu):
                yield pivo, path.fork()

class PropPivot(PivotOper):

    def prepare(self):

        name = self.kids[1].value()

        #self.isform = snap.model.forms.get(name) is not None

        self.prop = self.snap.model.props.get(name)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=name)

    def run(self, genr):

        # TODO if we are pivoting to a form, use ndef!

        for node, path in genr:

            if self.isjoin:
                yield node, path

            valu = self.kids[0].compute(node, path)
            if valu is None:
                continue

            # TODO cache/bypass normalization in loop!
            try:
                for pivo in self.snap.getNodesBy(self.prop.full, valu):
                    yield pivo, path.fork()
            except s_exc.BadTypeValu as e:
                logger.warning('Caught error during pivot', exc_info=e)
                items = e.items()
                mesg = items.pop('mesg', '')
                mesg = ': '.join((f'BadTypeValu [{repr(valu)}] during pivot', mesg))
                self.snap.warn(mesg, **items)

class Cond(AstNode):

    def getLiftHints(self):
        return ()

    def evaluate(self, node, path):
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.evaluate()')

class OrCond(Cond):
    '''
    <cond> or <cond>
    '''
    def evaluate(self, node, path):
        if self.kids[0].evaluate(node, path):
            return True
        return self.kids[1].evaluate(node, path)

class AndCond(Cond):
    '''
    <cond> and <cond>
    '''
    def getLiftHints(self):
        h0 = self.kids[0].getLiftHints()
        h1 = self.kids[1].getLiftHints()
        return h0 + h1

    def evaluate(self, node, path):
        if not self.kids[0].evaluate(node, path):
            return False
        return self.kids[1].evaluate(node, path)

class NotCond(Cond):
    '''
    not <cond>
    '''
    def evaluate(self, node, path):
        return not self.kids[0].evaluate(node, path)

class TagCond(Cond):
    '''
    #foo.bar
    '''
    def getLiftHints(self):
        return (
            ('tag', {'name': self.tagname}),
        )

    def prepare(self):
        self.tagname = self.kids[0].value()

    def evaluate(self, node, path):
        return node.tags.get(self.tagname) is not None

class HasRelPropCond(Cond):

    def prepare(self):
        self.propname = self.kids[0].value()

    def evaluate(self, node, path):
        return node.has(self.propname)

class HasAbsPropCond(Cond):

    def prepare(self):

        propfull = self.kids[0].value()

        # our AbsProp kid would raise if NoSuchProp.
        self.prop = self.snap.model.props.get(propfull)

        if self.prop.isform:
            self.propname = None
            self.formname = self.prop.name
        else:
            self.propname = self.prop.name
            self.formname = self.prop.form.name

    def evaluate(self, node, path):

        if node.form.name != self.formname:
            return False

        if self.propname is None:
            return True

        return node.has(self.propname)

class AbsPropCond(Cond):

    def prepare(self):

        self.constval = None

        propfull = self.kids[0].value()
        self.prop = self.snap.model.props.get(propfull)

        if self.prop.isform:
            self.propname = None
            self.formname = self.prop.name
        else:
            self.propname = self.prop.name
            self.formname = self.prop.form.name

        self.cmprname = self.kids[1].value()

        self.isconst = isinstance(self.kids[2], Const)

        if self.isconst:
            self.constval = self.kids[2].value()

        self.cmprcache = {}

    def _getCmprFunc(self, prop, node, path):

        if self.isconst:

            name = prop.type.name

            func = self.cmprcache.get(name)
            if func is not None:
                return func

            ctor = prop.type.getCmprCtor(self.cmprname)
            if ctor is None:
                raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

            func = ctor(self.constval)
            self.cmprcache[name] = func
            return func

        # dynamic vs dynamic comparison... no cacheing...
        valu = self.kids[2].compute(node, path)

        ctor = prop.type.getCmprCtor(self.cmprname)
        if ctor is None:
            raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

        return ctor(valu)

    def evaluate(self, node, path):

        if node.form.name != self.formname:
            return False

        if self.prop.isform:
            valu = node.ndef[1]

        else:
            valu = node.get(self.propname)
            if valu is None:
                return False

        cmpr = self._getCmprFunc(self.prop, node, path)
        return cmpr(valu)

class RelPropCond(Cond):
    '''
    :foo:bar <cmpr> <value>
    '''

    def prepare(self):

        self.constval = None

        self.propname = self.kids[0].value()
        self.cmprname = self.kids[1].value()

        self.isconst = isinstance(self.kids[2], Const)

        if self.isconst:
            self.constval = self.kids[2].value()

        self.cmprcache = {}

    def _getCmprFunc(self, prop, node, path):

        if self.isconst:

            name = prop.type.name

            func = self.cmprcache.get(name)
            if func is not None:
                return func

            ctor = prop.type.getCmprCtor(self.cmprname)
            if ctor is None:
                raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

            func = ctor(self.constval)
            self.cmprcache[name] = func
            return func

        # dynamic vs dynamic comparison... no cacheing...
        valu = self.kids[2].compute(node, path)

        ctor = prop.type.getCmprCtor(self.cmprname)
        if ctor is None:
            raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

        return ctor(valu)

    def evaluate(self, node, path):

        prop = node.form.props.get(self.propname)

        if prop is None:
            return False

        valu = node.get(prop.name)
        if valu is None:
            return False

        cmpr = self._getCmprFunc(prop, node, path)
        return cmpr(valu)

class TagTimeCond(Cond):
    pass

class FiltOper(Oper):

    def getLiftHints(self):

        if not self.ismust:
            return ()

        return self.kids[1].getLiftHints()

    def prepare(self):
        self.ismust = self.kids[0].value() == '+'

    def run(self, genr):
        for node, path in genr:
            if self.allow(node, path):
                yield node, path

    def allow(self, node, path):
        answ = self.kids[1].evaluate(node, path)
        if self.ismust:
            return answ

        return not answ

class AssignOper(Oper):
    pass

class RunValue(AstNode):

    def compute(self, node, path):
        raise s_exc.NoSuchImpl(name=f'{self.__class__.__name__}.compute()')

class RelPropValue(RunValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def compute(self, node, path):
        return node.get(self.name)

class TagPropValue(RunValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def compute(self, node, path):
        return node.getTag(self.name)

class VarValue(RunValue):

    def prepare(self):
        self.name = self.kids[0].value()

    def value(self):
        valu = self.snap.vars.get(self.name, s_common.novalu)
        if valu is s_common.novalu:
            raise s_exc.NoSuchVar(name=self.name)
        return valu

    def compute(self, node, path):
        valu = path.get(self.name, s_common.novalu)
        if valu is s_common.novalu:
            raise s_exc.NoSuchVar(name=self.name)
        return valu

class Value(RunValue):

    def __init__(self, valu, kids=()):
        RunValue.__init__(self, kids=kids)
        self.valu = valu

    def compute(self, node, path):
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

    def compute(self, node, path):
        return [k.compute(node, path) for k in self.kids]

    def value(self):
        return [k.value() for k in self.kids]

class Tag(Value):

    def repr(self):
        return 'Tag: #%s' % (self.valu,)

class RelProp(Value):

    def repr(self):
        return 'RelProp: %r' % (self.valu,)

class AbsProp(Value):

    def prepare(self):
        self.prop = self.snap.model.props.get(self.valu)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=self.valu)

    def value(self):
        return self.prop.full

    def repr(self):
        return f'AbsProp: {self.valu}'

class Edit(Oper):
    iswrite = True

class EditNodeAdd(Edit):

    def prepare(self):
        self.formname = self.kids[0].value()
        self.formtype = self.snap.model.types.get(self.formname)

    def run(self, genr):

        yield from genr

        kval = self.kids[1].value()

        for valu in self.formtype.getTypeVals(kval):
            node = self.snap.addNode(self.formname, valu)
            yield node, s_node.Path(self.snap.vars)

class EditPropSet(Edit):

    def prepare(self):
        self.propname = self.kids[0].value()

    def run(self, genr):
        for node, path in genr:
            valu = self.kids[1].compute(node, path)
            node.set(self.propname, valu)
            yield node, path

class EditPropDel(Edit):

    def prepare(self):
        self.propname = self.kids[0].value()

    def run(self, genr):
        for node, path in genr:
            node.pop(self.propname)
            yield node, path

class EditTagAdd(Edit):

    def prepare(self):
        self.tagname = self.kids[0].value()
        self.hasvalu = len(self.kids) > 1

    def getTagValue(self, node, path):

        if not self.hasvalu:
            return (None, None)

        return self.kids[1].compute(node, path)

    def run(self, genr):
        for node, path in genr:
            valu = self.getTagValue(node, path)
            node.addTag(self.tagname, valu=valu)
            yield node, path

class EditTagDel(Edit):

    def prepare(self):
        self.tagname = self.kids[0].value()

    def run(self, genr):
        for node, path in genr:
            node.delTag(self.tagname)
            yield node, path
