import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.cache as s_cache

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

            sibl = self.siblink(offs)
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

        self._init(snap)

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

        self.opts = {}

        self.tick = None
        self.canceled = False

    def setUser(self, user):
        self.user = user

    def isWrite(self):
        return any(o.iswrite for o in self.kids)

    def cancel(self):
        self.canceled = True

    def execute(self):

        chan = s_queue.Queue()

        self._runQueryThread(chan)

        return chan

    def getInput(self, snap):
        for ndef in self.opts.get('ndefs', ()):
            node = snap.getNodeByNdef(ndef)
            if node is not None:
                yield node

    def evaluate(self):
        with self._getQuerySnap() as snap:
            for node in self._runQueryLoop(snap):
                yield node

    def _runQueryLoop(self, snap):

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

        for node in genr:

            yield node
            count += 1

            limit = self.opts.get('limit')
            if limit is not None and count >= limit:
                snap.printf('limit reached: %d' % (limit,))
                break

            if self.canceled:
                raise s_exc.Canceled()

    def _getQuerySnap(self):
        write = self.isWrite()
        snap = self.view.snap(write=write)
        snap.setUser(self.user)
        return snap

    @s_glob.inpool
    def _runQueryThread(self, chan):

        #for depth, text in self.format():
            #print(' ' * depth + text)

        try:

            count = 0
            with self._getQuerySnap() as snap:

                tick = s_common.now()
                chan.put(('init', {'tick': tick}))

                snap.link(chan.put)

                for node in self._runQueryLoop(snap):
                    chan.put(('node', node.pack()))
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

class LiftOper(Oper):

    def run(self, genr):
        yield from genr
        yield from self.lift()

class LiftTag(LiftOper):

    def lift(self):
        tag = self.kids[0].value()
        yield from self.snap._getNodesByTag(tag)

#class LiftTagTime():

class LiftProp(LiftOper):

    def lift(self):
        name = self.kids[0].value()
        for node in self.snap.getNodesBy(name):
            yield node

class LiftPropBy(LiftOper):

    def lift(self):

        name = self.kids[0].value()
        cmpr = self.kids[1].value()
        valu = self.kids[2].value()

        for node in self.snap.getNodesBy(name, valu, cmpr=cmpr):
            yield node

class PivotOper(Oper):

    def __init__(self, kids=(), isjoin=False):
        Oper.__init__(self, kids=kids)
        self.isjoin = isjoin

class PivotOut(PivotOper):

    def prepare(self):
        pass

    def run(self, nodes):

        for node in nodes:

            if self.isjoin:
                yield node

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

                yield pivo

class PivotIn(PivotOper):

    def prepare(self):
        pass

    def run(self, nodes):

        for node in nodes:

            if self.isjoin:
                yield node

            name, valu = node.ndef

            for prop in self.snap.model.propsbytype.get(name, ()):
                for node in self.snap.getNodesBy(prop.full, valu):
                    yield node

class FormPivot(PivotOper):

    def prepare(self):

        name = self.kids[0].value()

        self.prop = self.snap.model.props.get(name)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=name)

    def run(self, nodes):

        if not self.prop.isform:

            # plain old pivot...
            for node in nodes:

                if self.isjoin:
                    yield node

                valu = node.ndef[1]

                # TODO cache/bypass normalization in loop!
                for pivo in self.snap.getNodesBy(self.prop.full, valu):
                    yield pivo

        # form -> form pivot is nonsensical. Lets help out...

        # form name and type name match
        desttype = self.prop.name

        @s_cache.memoize()
        def getsrc(form):
            for name, prop in form.props.items():
                if prop.type.name == desttype:
                    return name

        for node in nodes:

            if self.isjoin:
                yield node

            name = getsrc(node.form)
            if name is None:
                continue

            # TODO: bypass normalization
            valu = node.get(name)

            for pivo in self.snap.getNodesBy(self.prop.name, valu):
                yield pivo

class PropPivot(PivotOper):

    def prepare(self):

        name = self.kids[1].value()

        #self.isform = snap.model.forms.get(name) is not None

        self.prop = self.snap.model.props.get(name)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=name)

    def run(self, nodes):

        # TODO if we are pivoting to a form, use ndef!

        for node in nodes:

            if self.isjoin:
                yield node

            valu = self.kids[0].value(node=node)
            if valu is None:
                continue

            # TODO cache/bypass normalization in loop!
            for pivo in self.snap.getNodesBy(self.prop.full, valu):
                yield pivo

class Cond(AstNode):

    def evaluate(self, node):
        raise FIXME

class MultiCond(Cond):
    '''
    ( <cond> , ... )
    '''
    pass

class OrCond(Cond):
    '''
    <cond> or <cond>
    '''
    def evaluate(self, node):
        if self.kids[0].evaluate(node):
            return True
        return self.kids[1].evaluate(node)

class AndCond(Cond):
    '''
    <cond> and <cond>
    '''
    def evaluate(self, node):
        if not self.kids[0].evaluate(node):
            return False
        return self.kids[1].evaluate(node)

class NotCond(Cond):
    '''
    not <cond>
    '''
    def evaluate(self, node):
        return not self.kids[0].evaluate(node)

class TagCond(Cond):
    '''
    #foo.bar
    '''
    def prepare(self):
        self.tagname = self.kids[0].value()

    def evaluate(self, node):
        return node.tags.get(self.tagname) is not None

class HasRelPropCond(Cond):

    def prepare(self):
        self.propname = self.kids[0].value()

    def evaluate(self, node):
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

    def evaluate(self, node):

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

    def _getCmprFunc(self, prop, node):

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
        valu = self.kids[2].value(node=node)

        ctor = prop.type.getCmprCtor(self.cmprname)
        if ctor is None:
            raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

        return ctor(valu)

    def evaluate(self, node):

        if node.form.name != self.formname:
            return False

        if self.prop.isform:
            valu = node.ndef[1]

        else:
            valu = node.get(self.propname)
            if valu is None:
                return False

        cmpr = self._getCmprFunc(self.prop, node)
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

    def _getCmprFunc(self, prop, node):

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
        valu = self.kids[2].value(node=node)

        ctor = prop.type.getCmprCtor(self.cmprname)
        if ctor is None:
            raise s_exc.NoSuchCmpr(name=self.cmprname, type=prop.type.name)

        return ctor(valu)

    def evaluate(self, node):

        prop = node.form.props.get(self.propname)

        if prop is None:
            return False

        valu = node.get(prop.name)
        if valu is None:
            return False

        cmpr = self._getCmprFunc(prop, node)
        return cmpr(valu)

class TagTimeCond(Cond):
    pass

class FiltOper(Oper):

    def prepare(self):
        self.ismust = self.kids[0].value() == '+'

    def run(self, genr):
        for node in genr:
            if self.allow(node):
                yield node

    def allow(self, node):
        answ = self.kids[1].evaluate(node)
        if self.ismust:
            return answ

        return not answ

class AssignOper(Oper):
    pass

class Cmpr(AstNode):

    def __init__(self, text, kids=()):
        AstNode.__init__(self, kids=kids)
        self.text = text

    def value(self, node=None):
        return self.text

    def repr(self):
        return 'Cmpr: %r' % (self.text,)

class Value(AstNode):

    def __init__(self, valu, kids=()):
        AstNode.__init__(self, kids=kids)
        self.valu = valu

    def value(self, node=None):
        return self.valu

class Const(Value):

    def repr(self):
        return 'Const: %s' % (self.valu,)

class List(Value):

    def repr(self):
        return 'List: %s' % (self.valu,)

    def value(self, node=None):
        return [k.value(node=node) for k in self.kids]

class Tag(Value):

    def repr(self):
        return 'Tag: #%s' % (self.valu,)

class RelProp(Value):

    def repr(self):
        return 'RelProp: %r' % (self.valu,)

class RelPropValue(Value):

    def prepare(self):
        self.propname = self.kids[0].value()

    def value(self, node=None):
        return node.get(self.propname)

class VarValue(Value):

    def prepare(self):
        self.name = self.kids[0].value()

    def value(self, node=None):

        # if we have a node, use his vars...
        if node is not None:
            valu = node.vars.get(self.name, s_common.novalu)
            if valu is not s_common.novalu:
                return valu

        # if not, try for storm query vars...
        valu = self.snap.vars.get(self.name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        raise s_exc.NoSuchVar(name=self.name)

class AbsProp(Value):

    def prepare(self):
        self.prop = self.snap.model.props.get(self.valu)
        if self.prop is None:
            raise s_exc.NoSuchProp(name=name)

    def value(self, node=None):
        return self.prop.full

    def repr(self):
        return f'AbsProp: {self.valu}'

class Edit(Oper):
    iswrite = True

class EditNodeAdd(Edit):

    def prepare(self):
        self.formname = self.kids[0].value()
        self.formvalu = self.kids[1].value()

    # TODO: optmize and pick up sibling prop sets

    def run(self, nodes):
        yield from nodes
        yield self.snap.addNode(self.formname, self.formvalu)

class EditNodeDel(Edit):

    def prepare(self):
        self.formname = self.kids[0].value()

    def run(self, nodes):

        for node in nodes:

            if node.ndef[0] != self.formname:
                continue

            print('FIXME NODE DEL')

class EditPropSet(Edit):

    def prepare(self):
        self.propname = self.kids[0].value()

    def run(self, nodes):
        for node in nodes:
            valu = self.kids[1].value(node=node)
            node.set(self.propname, valu)
            yield node

class EditPropDel(Edit):

    def prepare(self):
        self.propname = self.kids[0].value()

    def run(self, nodes):
        for node in nodes:
            node.pop(self.propname)
            yield node

class EditTagAdd(Edit):

    def prepare(self):
        self.tagname = self.kids[0].value()

    def run(self, nodes):
        for node in nodes:
            node.addTag(self.tagname)
            yield node

class EditTagDel(Edit):

    def prepare(self):
        self.tagname = self.kids[0].value()

    def run(self, nodes):
        for node in nodes:
            node.delTag(self.tagname)
            yield node

class CallOper(Oper):
    pass

if __name__ == '__main__':

    import synapse.cortex as s_cortex
    import synapse.lib.syntax as s_syntax

    with s_cortex.Cortex('shit') as core:

        with core.snap(write=True) as snap:
            node = snap.addNode('inet:email', 'visi@vertex.link')
            node.addTag('foo')
            #node = snap.addNode('inet:ipv4', '1.2.3.4')

        #for mesg in core.storm('inet:user = visi +#foo.bar'):
        #for mesg in core.storm('inet:user = visi -(#foo.bar or #faz)'):
        #for mesg in core.storm('inet:ipv4'):
        #for mesg in core.storm('inet:user'):
        #for mesg in core.storm('inet:user = visi -#foo.bar'):
        #for mesg in core.storm('inet:user=visi -> inet:email:user'):
        #for mesg in core.storm('inet:email=visi@vertex.link :user -> inet:user'):
        #for mesg in core.storm('inet:email=visi@vertex.link -> inet:user'):
        #for mesg in core.storm('inet:email=visi@vertex.link :user <- inet:user'):
        #for mesg in core.storm('inet:email=visi@vertex.link +:user^=vi'):
        #for mesg in core.storm('inet:email=visi@vertex.link -:user^=vi'):
        #for mesg in core.storm('inet:email=visi@vertex.link -:user~=is'):
        #for mesg in core.storm('[ inet:ipv4=1.2.3.4 :loc=us.va ]'):
        #for mesg in core.storm('[ inet:ipv4=1.2.3.4 :loc=us.va #foo.bar ]'):
        #for mesg in core.storm('[ inet:ipv4=1.2.3.4 :loc=us.va -#foo.bar ]'):
        for mesg in core.storm('inet:email=visi@vertex.link [:user=hehe]'):
        #for mesg in core.storm('inet:email=visi@vertex.link +:user~=is'):
        #for mesg in core.storm('.created'):
        #for mesg in core.storm('.created'):
            print('yield: %r' % (mesg,))

        print(repr(mesg))
