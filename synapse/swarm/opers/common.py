from synapse.exc import *

# TODO: in-band help (as result)

deftag = 'class.synapse.cores.common.Cortex'

class Oper:

    def __init__(self, query, inst, prev=None):
        self.inst = inst
        self.prev = prev
        self.query = query

        self.args = inst[1].get('args',())
        self.kwlist = inst[1].get('kwlist',())

        self.kwargs = dict(self.kwlist)

        self.runSyntaxCheck()

    def runSyntaxCheck(self):
        # hook point for subclass syntax validation
        pass

    def run(self):
        # do we have a filter mode?
        mode = self.inst[1].get('mode','lift')
        meth = getattr(self,'_oper_%s' % mode, None)
        if meth == None:
            raise NoSuchImpl('%s does not implement %s' % (self.__class__.__name__,mode))

        return meth()

class CmpOper(Oper):
    '''
    Base class for simple comparison based operators.
    '''
    def __init__(self, query, inst):
        Oper.__init__(self, query, inst)
        self.cmpfunc = self.getCmpFunc()

    def _oper_must(self):
        [ self.query.add(t) for t in self.query.take() if self.cmpfunc(t) ]

    def _oper_cant(self):
        [ self.query.add(t) for t in self.query.take() if not self.cmpfunc(t) ]

    def getCmpFunc(self):
        '''
        Return a comparitor function for use in one query run.
        ( allows multi-eval optimization and cachinng )

        Example:

            class MyOper(CmpOper):

                def getCmpFunc(self):

                    if len(self.args) != 1:
                        raise Exception('myoper requires 1 argument!')

                    myval = self.args[0]

                    def cmptufo(tufo):
                        return tufo[1].get('foo:bar:baz') == myval

                    return cmptufo

        '''
        raise NoSuchImpl('%s: getCmpFunc' % (self.__class__.__name__,))

    def getFiltFunc(self):
        '''
        Return a tufo filter function based on the cmp func and mode.
        '''
        if self.inst[1].get('mode') == 'must':
            return self.cmpfunc

        def notfunc(tufo):
            return not self.cmpfunc(tufo)

        return notfunc
