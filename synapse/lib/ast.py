import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.queue as s_queue

class AstNode:

    def __init__(self, kids=()):
        self.xact = None
        self.kids = list(kids)
        if None in self.kids:
            raise Exception('')

    def add(self, astnode):
        self.kids.append(astnode)

    def format(self, depth=0):

        yield (depth, self.repr())

        for kid in self.kids:
            for item in kid.format(depth=depth + 1):
                yield item

    def repr(self):
        return self.__class__.__name__

    def prepare(self, xact):
        self.xact = xact
        [k.prepare(xact) for k in self.kids]

    def optimize(self):
        [k.optimize() for k in self.kids]

class Query(AstNode):

    def __init__(self, view):
        AstNode.__init__(self)

        #self.core = core
        #self.text = text

        self.view = view

        self.tick = None
        self.canceled = False

    def isWrite(self):
        return any(o.iswrite for o in self.kids)

    def cancel(self):
        pass

    def execute(self, view):

        chan = s_queue.Queue()

        self._runQueryThread(view, chan)

        return chan

    def stream(self, view, tx):
        self._runQueryThread(view, tx)

    @s_glob.inpool
    def _runQueryThread(self, view, chan):

        write = self.isWrite()

        for depth, repr in self.format():
            print(' ' * depth + repr)

        try:

            with self.view.xact(write=write) as xact:

                self.prepare(xact)
                self.optimize()

                xact.link(chan.put)

                xact.printf('oh hai')

                genr = ()
                for oper in self.kids:
                    genr = oper.run(genr)

                for node, info in genr:
                    pack = node.pack()
                    chan.put(('node', {'node': pack}))

        except Exception as e:
            tx(s_common.geterr(e))

        finally:
            chan.done()

    #def onLog(
    #def onErr(
    #def onOut(

class Oper(AstNode):
    iswrite = False

class SubQuery(Oper):
    pass

class LiftOper(Oper):
    pass

class LiftTag(LiftOper):
    pass

class LiftProp(LiftOper):
    pass

class LiftPropBy(LiftOper):

    def run(self, genr):

        for item in genr:
            yield item

        name = self.kids[0].value()
        cmpr = self.kids[1].value()
        valu = self.kids[2].value()

        for node in self.xact.getNodesBy(name, valu, cmpr=cmpr):
            yield (node, {'vars': {}})

class PivotOper(Oper):
    pass

class FormPivotOper(PivotOper):
    pass

class Cond(AstNode):

    def evaluate(self, result):
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
    def evaluate(self, result):
        if self.kid[0].evaluate(result):
            return True
        return self.kid[1].evaluate(result)

class AndCond(Cond):
    '''
    <cond> and <cond>
    '''
    def evaluate(self, result):
        if not self.kid[0].evaluate(result):
            return False
        return self.kid[1].evaluate(result)

class RelPropCond(Cond):
    '''
    :foo:bar <cmpr> <value>
    '''

    def prepare(self, xact):

        self.constval = None

        self.propname = self.kids[0].text
        self.cmprname = self.kids[1].value()

        self.isconst = isinstance(self.kids[2], Const)
        if self.isconst:
            self.constval = self.kids[2].value()

        self.cmprcache = {}

    def _getCmprFunc(self, prop, result):

        if self.isconst:

            name = prop.type.name

            func = self.cmprcache.get(name)
            if func is not None:
                return func

            ctor = prop.type.getCmprCtor(self.cmprname)
            func = ctor(self.constval)
            self.cmprcache[name] = func
            return func

        # dynamic vs dynamic comparison... no cacheing...
        valu = self.kid[2].value(result=result)

        ctor = prop.type.getCmprCtor(self.cmprname)
        if ctor is None:
            raise FIXME

        return ctor(valu)

    def evaluate(self, result):

        node, info = result
        prop = node.form.props.get(self.propname)

        # TODO: make this behavior optional
        if prop is None:
            raise FIXME_or_log
            return False

        valu = node.get(prop.name)
        if valu is None:
            return False

        cmpr = self._getCmprFunc(prop, result)
        return cmpr(valu)

class TagTimeCond(Cond):
    pass

class FiltOper(Oper):

    def prepare(self, xact):
        self.ismust = self.kids[0].value() == '+'
        return Oper.prepare(self, xact)

    def run(self, genr):
        for item in genr:
            if self.allow(item):
                yield item

    def allow(self, result):
        answ = self.kids[1].evaluate(result)
        if self.ismust:
            return answ

        return not answ

class AssignOper(Oper):
    pass

class Cmpr(AstNode):

    def __init__(self, text, kids=()):
        AstNode.__init__(self, kids=kids)
        self.text = text

    def value(self, result=None):
        return self.text

    def repr(self):
        return 'Cmpr: %r' % (self.text,)

#class Variable(AstNode):

class Value(AstNode):

    def __init__(self, text, kids=()):
        AstNode.__init__(self, kids=kids)
        self.text = text

    def value(self, result=None):
        return self.text

class Const(Value):

    def repr(self):
        return 'Const: %s' % (self.text,)

class RelProp(Value):

    def prepare(self, xact):
        self.propname = self.text.lower().strip(':')
        return Value.prepare(self, xact)

    def value(self, result=None):

        if result is None:
            raise FIXME

        node, info = result

        valu = result[0].get(self.propname)
        if valu is None:

            prop = node.props.get(self.propname)

            if prop is None:
                formname, formvalu = node.ndef
                self.xact.warning('%s form has no prop named %s' % (formname, self.propname))

        return valu

    def repr(self):
        return 'RelProp: %r' % (self.text,)

        # get the relative property value

class CallOper(Oper):
    pass

if __name__ == '__main__':

    import synapse.cortex as s_cortex
    import synapse.lib.syntax as s_syntax

    with s_cortex.Cortex('shit', {}) as core:

        with core.xact(write=True) as xact:
            node = xact.addNode('inet:user', 'visi')

        for mesg in core.storm('inet:user = visi'):
            print('yield: %r' % (mesg,))
