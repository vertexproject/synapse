import re

from synapse.common import gentask

import synapse.swarm.opers.common as s_opers_common

class OptsOper(s_opers_common.Oper):

    def _oper_lift(self):
        for name,valu in self.kwlist:
            self.query.setOpt(name,valu)

class EqOper(s_opers_common.CmpOper):

    def getCmpFunc(self):

        if len(self.args) != 1:
            raise Exception('%s requires a property argument' % (self.__class__.__name__,))

        prop = self.args[0]
        valu = self.kwargs.get('valu')

        if valu == None:
            def hasprop(tufo):
                return tufo[1].get(prop) != None
            return hasprop

        def cmpvalu(tufo):
            return tufo[1].get(prop) == valu

        return cmpvalu

    def _oper_lift(self):
        prop = self.args[0]

        kwargs = {
            'valu':self.kwargs.get('valu'),
            'limit':self.kwargs.get('limit'),
            'fromtag':self.kwargs.get('from',s_opers_common.deftag),
            'mintime':self.kwargs.get('mintime'),
            'maxtime':self.kwargs.get('maxtime'),
        }

        for tufo in self.query.getTufosByPropFrom(prop, **kwargs):
            self.query.add(tufo)

class OrOper(s_opers_common.CmpOper):

    def getCmpFunc(self):
        opers = self.query.initInstOpers(self.args)
        funcs = [ oper.getCmpFunc() for oper in opers ]

        def cmptufo(tufo):
            return any([ f(tufo) for f in funcs ])

        return cmptufo

class AndOper(s_opers_common.CmpOper):

    def getCmpFunc(self):

        opers = self.query.initInstOpers(self.args)
        funcs = [ oper.getCmpFunc() for oper in opers ]

        def cmptufo(tufo):
            return all([ f(tufo) for f in funcs ])

        return cmptufo

class ByMix:

    def getByPropValu(self):

        name = None
        valu = None

        argc = len(self.args)
        if argc > 3 or argc < 1:
            raise SyntaxError(args=self.args,mesg='by() takes from 1 to 3 args')

        prop = self.args[0]

        if argc == 3:
            name,prop,valu = self.args

        elif argc == 2:
            name,prop = self.args[:2]

        if name == None:
            name = self.kwargs.get('by')

        if valu == None:
            valu = self.kwargs.get('valu')

        return name,prop,valu

    def _oper_lift(self):

        name,prop,valu = self.getByPropValu()

        limt = self.kwargs.get('limit')
        ftag = self.kwargs.get('from', s_opers_common.deftag)

        dyntask = gentask('getTufosBy', name, prop, valu, limit=limt)

        # TODO: timeouts
        for svcfo,tufos in self.query.callByTag(ftag, dyntask):
            for tufo in tufos:
                tufo[1]['.from'] = svcfo[0]
                self.query.add(tufo)

class ByOper(s_opers_common.Oper,ByMix):
    pass

class RangeOper(s_opers_common.CmpOper,ByMix):

    def getByPropValu(self):
        return 'range',self.args[0],self.args[1]

    def _oper_lift(self):

        rtup = self.getLiftRange()

        prop = self.args[0]
        rtup = self.getLiftRange()
        limt = self.kwargs.get('limit')
        ftag = self.kwargs.get('from', s_opers_common.deftag)

        dyntask = gentask('getTufosBy','range', prop, rtup, limit=limt)

        # TODO: timeouts
        for svcfo,tufos in self.query.callByTag(ftag, dyntask):
            for tufo in tufos:
                tufo[1]['.from'] = svcfo[0]
                self.query.add(tufo)

    def getLiftRange(self):
        pass

class LtOper(s_opers_common.CmpOper,ByMix):

    def getByPropValu(self):
        valu = self.kwargs.get('valu')
        return 'le',self.args[0],valu - 1

    def getCmpFunc(self):

        prop = self.args[0]
        valu = self.kwargs.get('valu')

        def cmptufo(tufo):
            return tufo[1].get(prop) < valu

        return cmptufo

class LeOper(s_opers_common.CmpOper,ByMix):

    def getByPropValu(self):
        valu = self.kwargs.get('valu')
        return 'le',self.args[0],valu

    def getCmpFunc(self):

        prop = self.args[0]
        valu = self.kwargs.get('valu')

        def cmptufo(tufo):
            return tufo[1].get(prop) <= valu

        return cmptufo

class GtOper(s_opers_common.CmpOper,ByMix):

    def getByPropValu(self):
        valu = self.kwargs.get('valu')
        return 'ge',self.args[0],valu + 1

    def getCmpFunc(self):

        prop = self.args[0]
        valu = self.kwargs.get('valu')

        def cmptufo(tufo):
            return tufo[1].get(prop) > valu

        return cmptufo

class GeOper(s_opers_common.CmpOper,ByMix):

    def getByPropValu(self):
        valu = self.kwargs.get('valu')
        return 'ge',self.args[0],valu

    def getCmpFunc(self):

        prop = self.args[0]
        valu = self.kwargs.get('valu')

        def cmptufo(tufo):
            return tufo[1].get(prop) >= valu

        return cmptufo


class JoinOper(s_opers_common.Oper):

    def runSyntaxCheck(self):
        argc = len(self.args)
        if argc not in (1,2):
            raise Exception('join() syntax error: %d args (needs 1 or 2)' % len)

    def _oper_lift(self):
        
        ftag = self.kwargs.get('from',s_opers_common.deftag)

        newprop = self.args[0]
        curprop = self.args[-1]

        tufos = self.query.data()

        vals = set()
        for tufo in self.query.data():
            valu = tufo[1].get(curprop)
            if valu == None:
                continue

            vals.add(valu)

        for valu in vals:
            for tufo in self.query.getTufosByPropFrom(newprop,valu=valu,fromtag=ftag):
                self.query.add(tufo)

class PivotOper(s_opers_common.Oper):

    def _oper_lift(self):

        ftag = self.kwargs.get('from',s_opers_common.deftag)

        newprop = self.args[0]
        curprop = self.args[-1]

        vals = set()
        for tufo in self.query.take():
            valu = tufo[1].get(curprop)
            if valu == None:
                continue

            vals.add(valu)

        for valu in vals:
            for tufo in self.query.getTufosByPropFrom(newprop,valu=valu,fromtag=ftag):
                self.query.add(tufo)

class HasOper(s_opers_common.CmpOper):

    def runSyntaxCheck(self):
        if len(self.args) != 1:
            raise Exception('has() operator requires prop name: has(name)')

    def getCmpFunc(self):
        prop = self.args[0]
        def cmptufo(tufo):
            return tufo[1].get(prop) != None
        return cmptufo

    def _oper_lift(self):
        prop = self.args[0]

        kwargs = {
            'limit':self.kwargs.get('limit'),
            'fromtag':self.kwargs.get('from',s_opers_common.deftag),
            'mintime':self.kwargs.get('mintime'),
            'maxtime':self.kwargs.get('maxtime'),
        }

        for tufo in self.query.getTufosByPropFrom(prop, **kwargs):
            self.query.add(tufo)

class ReOper(s_opers_common.CmpOper):

    def getCmpFunc(self):

        prop = self.args[0]
        reobj = re.compile(self.kwargs.get('valu'))

        def cmptufo(tufo):
            return reobj.search(tufo[1].get(prop)) != None

        return cmptufo

class SaveOper(s_opers_common.Oper):

    def runSyntaxCheck(self):
        if len(self.args) != 1:
            raise Exception('save() oper requires a single argument: save(name)')

    def _oper_lift(self):
        self.query.setSaveData(self.args[0], self.query.data())

class LoadOper(s_opers_common.Oper):

    def runSyntaxCheck(self):
        if not self.args:
            raise Exception('load() requires name arguments: load("foo")')

    def _oper_lift(self):
        for name in self.args:
            [ self.query.add(t) for t in self.query.getSaveData(name) ]

class ClearOper(s_opers_common.Oper):
    def _oper_lift(self):
        self.query.take()

