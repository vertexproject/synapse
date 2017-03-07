import re
import time
import logging

import synapse.eventbus as s_eventbus

import synapse.lib.scope as s_scope
import synapse.lib.syntax as s_syntax
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.lib.config import Configable

logger = logging.getLogger(__name__)

class OperWith:

    def __init__(self, query, oper):
        self.oper = oper
        self.query = query
        self.stime = None

    def __enter__(self):
        self.stime = now()
        self.query.added = 0
        self.query.subed = 0
        return self

    def __exit__(self, exc, cls, tb):

        info = {
            'sub':self.query.subed,
            'add':self.query.added,
            'took':now() - self.stime
        }

        if exc != None:
            info.update( excinfo(exc) )
            self.query.clear()

        self.query.log(**info)

class Query:

    def __init__(self, data=(), maxtime=None):

        self.canc = False

        self.uniq = {}
        self.saved = {}
        self.touched = 0

        self.added = 0
        self.subed = 0

        self.maxtime = maxtime
        self.maxtouch = None

        self.results = {

            'options':{
                'uniq':1,
            },

            'limits':{
                'lift':None,
                'time':None,
                'touch':None,
            },

            'oplog':[], # [ <dict>, ... ] ( one dict for each oper )

            'data':list(data),
        }

    def log(self, **info):
        '''
        Log execution metadata for the current oper.
        '''
        self.results['oplog'][-1].update(info)

    def result(self):
        return self.results

    def retn(self):
        '''
        Return the results data or raise exception.
        '''

    def save(self, name, data):
        self.saved[name] = data

    def load(self, name):
        return self.saved.get(name,())

    def add(self, tufo):
        '''
        Add a tufo to the current query result set.
        '''
        self.tick()
        self.added += 1

        data = self.results.get('data')

        form = tufo[1].get('tufo:form')

        if tufo[0] != None and self.results['options'].get('uniq'):
            if self.uniq.get( tufo[0] ):
                return False

            self.uniq[ tufo[0] ] = True

        self.results['data'].append(tufo)

        return True

    def setOpt(self, name, valu):
        '''
        Set a query option to the given value.
        '''
        self.results['options'][name] = valu

    def opt(self,name):
        '''
        Return the current value of a query option.
        '''
        return self.results['options'].get(name)

    def data(self):
        return list(self.results.get('data'))

    def take(self):
        '''
        Return and clear the current result set.
        ( used by filtration operators )
        '''
        data = self.results.get('data')
        self.subed += len(data)

        self.uniq.clear()
        # no list.clear() in py27
        self.results['data'] = []

        return data

    def clear(self):
        self.take()

    def withop(self, oper):
        self.results['oplog'].append({'mnem':oper[0]})
        return OperWith(self,oper)

    def cancel(self):
        '''
        Cancel the current query ( occurs at next tick() call ).
        '''
        self.canc = True

    def tick(self, touch=1):
        '''
        '''
        if self.canc:
            raise QueryCancelled()

        nowtime = time.time()
        if self.maxtime != None and nowtime >= self.maxtime:
            raise HitStormLimit(name='maxtime', limit=self.maxtime, valu=nowtime)

        self.touched += touch
        if self.maxtouch != None and self.touched > self.maxtouch:
            raise HitStormLimit(name='maxtouch', limit=self.maxtouch, valu=self.touched)

class QueryKilled(Exception):pass
class QueryCancelled(QueryKilled):pass
class QueryLimitTime(QueryKilled):pass
class QueryLimitTouch(QueryKilled):pass

def invert(func):
    def invfunc(*args,**kwargs):
        return not func(*args,**kwargs)
    return invfunc

class Runtime(Configable):

    def __init__(self, **opts):
        Configable.__init__(self)

        self.addConfDef('storm:limit:lift', asloc='limlift', defval=None, doc='Global lift limit')

        self.setConfOpts(opts)

        self.operfuncs = {}
        self.cmprctors = {}

        self.setCmprFunc('eq', lambda x,y: x == y )
        self.setCmprFunc('lt', lambda x,y: x < y )
        self.setCmprFunc('gt', lambda x,y: x > y )
        self.setCmprFunc('le', lambda x,y: x <= y )
        self.setCmprFunc('ge', lambda x,y: x >= y )

        self.setCmprCtor('or', self._cmprCtorOr )
        self.setCmprCtor('and', self._cmprCtorAnd )
        self.setCmprCtor('tag', self._cmprCtorTag )

        self.setCmprCtor('in', self._cmprCtorIn )
        self.setCmprCtor('re', self._cmprCtorRe )
        self.setCmprCtor('has', self._cmprCtorHas )

        self.setOperFunc('filt', self._stormOperFilt)
        self.setOperFunc('opts', self._stormOperOpts)

        self.setOperFunc('save', self._stormOperSave )
        self.setOperFunc('load', self._stormOperLoad )
        self.setOperFunc('clear', self._stormOperClear )

        self.setOperFunc('join', self._stormOperJoin)
        self.setOperFunc('lift', self._stormOperLift)
        self.setOperFunc('pivot', self._stormOperPivot)

    def getLiftLimit(self, limit):
        userlim = s_scope.get('storm:limit:lift')
        if userlim != None:
            if limit == None:
                return userlim

            return min(userlim,limit)

        if self.limlift != None:
            if limit == None:
                return self.limlift
            return min(self.limlift,limit)

        return limit

    def stormTufosBy(self, by, prop, valu=None, limit=None):
        '''
        A STORM runtime specific version of the cortex function getTufosBy
        which allows sub-classes to override the default behavior for
        operators like lift/join/pivot.
        '''
        limit = self.getLiftLimit(limit)
        return self._stormTufosBy(by,prop,valu=valu,limit=limit)

    def _stormTufosBy(self, by, prop, valu=None, limit=None):
        raise NoSuchImpl(name='_stormTufosBy')

    def setCmprCtor(self, name, func):
        '''
        Add a comparitor constructor function for use in the
        "filt" operator.

        Example:

            def substr(oper):

                prop = oper[1].get('prop')
                valu = oper[1].get('valu')

                def cmpr(tufo):
                    tufo[1].get(prop).find(valu) != -1

                return cmpr

            runt.setCmprCtor('substr',substr)

            # storm syntax now suports
            # +foo:bar*substring="baz" and -foo:bar*substring="baz"

        '''
        self.cmprctors[name] = func

    def setCmprFunc(self, name, func):
        '''
        Helper function for adding simple comparitors.

        Example:

            def substr(x,y):
                return x.find(y) != -1

            runt.setCmprFunc('substr', substr)

        '''
        def cmprctor(oper):
            prop = oper[1].get('prop')
            valu = oper[1].get('valu')
            def cmpr(tufo):
                return func(tufo[1].get(prop),valu)
            return cmpr

        self.setCmprCtor(name,cmprctor)

    def getCmprFunc(self, oper):
        '''
        Return a comparison function for the given operator.
        '''
        name = oper[1].get('cmp','eq')
        ctor = self.cmprctors.get(name)
        if ctor == None:
            raise NoSuchCmpr(name=name)
        return ctor(oper)

    def setOperFunc(self, name, func):
        '''
        Add a handler function for a given operator.  The function
        must implement the convention:

        def func(query,oper):
            args = oper[1].get('args')
            opts = dict(oper[1].get('kwlist'))
            dostuff()

        Where query is a synapse.lib.storm.Query instance and oper
        is a (<oper>,<info>) tufo.
        '''
        self.operfuncs[name] = func

    def ask(self, text, data=(), timeout=None):
        '''
        Run a storm query and return the query result dict.
        user= stdin=
        '''
        opers = s_syntax.parse(text)
        return self.run(opers, data=data, timeout=timeout)

    def run(self, opers, data=(), timeout=None):
        '''
        Execute a pre-parsed set of opers.

        Example:

            opers = runt.parse('foo:bar=20 +foo:baz | foo:faz=30')
            # ... some time later...
            res0 = runt.run(opers)

        '''
        maxtime = None
        if timeout != None:
            maxtime = time.time() + timeout

        # FIXME overall time per user goes here

        query = Query(data=data,maxtime=maxtime)

        try:

            self._runOperFuncs(query,opers)

        except Exception as e:
            logger.exception(e)

        return query.result()

    def parse(self, text):
        return s_syntax.parse(text)

    def eval(self, text, data=(), timeout=None):
        '''
        Run a storm query and return only the result data.

        Example:

            for tufo in runt.eval('foo:bar=10 +foo:baz<30'):
                dostuff(tufo)

        '''
        answ = self.ask(text,data=data,timeout=timeout)

        excinfo = answ['oplog'][-1].get('excinfo')
        #if excinfo.get('errinfo') != None:
        if excinfo != None:
            errname = excinfo.get('err')
            errinfo = excinfo.get('errinfo',{})
            errinfo['errfile'] = excinfo.get('errfile')
            errinfo['errline'] = excinfo.get('errline')
            raise synerr(errname,**errinfo)

        return answ.get('data')

    def _reqOperArg(self, oper, name):
        valu = oper[1].get(name)
        if valu == None:
            raise BadOperArg(oper=oper, name=name, mesg='not found')
        return valu

    def _cmprCtorHas(self, oper):
        prop = self._reqOperArg(oper,'prop')
        def cmpr(tufo):
            return tufo[1].get(prop) != None
        return cmpr

    def _cmprCtorIn(self, oper):
        prop = self._reqOperArg(oper,'prop')
        valus = self._reqOperArg(oper,'valu')
        if len(valus) > 12: # TODO opt value?
            valus = set(valus)

        def cmpr(tufo):
            return tufo[1].get(prop) in valus

        return cmpr

    def _cmprCtorRe(self, oper):
        prop = oper[1].get('prop')
        reobj = re.compile( oper[1].get('valu') )

        def cmpr(tufo):
            return reobj.search(tufo[1].get(prop)) != None

        return cmpr

    def _stormOperFilt(self, query, oper):
        cmpr = self.getCmprFunc(oper)
        if oper[1].get('mode') == 'cant':
            cmpr = invert(cmpr)

        [ query.add(t) for t in query.take() if cmpr(t) ]

    def _stormOperOr(self, query, oper):
        funcs = [ self.getCmprFunc(op) for op in oper[1].get('args') ]
        for tufo in query.take():
            if any([ func(tufo) for func in funcs ]):
                query.add(tufo)

    def _cmprCtorOr(self, oper):
        args = self._reqOperArg(oper,'args')
        funcs = [ self.getCmprFunc(op) for op in args ]
        def cmpr(tufo):
            return any([ func(tufo) for func in funcs ])
        return cmpr

    def _cmprCtorAnd(self, oper):
        args = self._reqOperArg(oper,'args')
        funcs = [ self.getCmprFunc(op) for op in args ]
        def cmpr(tufo):
            return all([ func(tufo) for func in funcs ])
        return cmpr

    def _cmprCtorTag(self, oper):
        tag = self._reqOperArg(oper,'valu')

        props = {}
        def cmpr(tufo):
            form = tufo[1].get('tufo:form')

            prop = props.get(form)
            if prop == None:
                props[form] = prop = '*|%s|%s' % (form,tag)

            return tufo[1].get(prop) != None

        return cmpr

    def _stormOperAnd(self, query, oper):
        funcs = [ self.getCmprFunc(op) for op in oper[1].get('args') ]
        for tufo in query.take():
            if any([ func(tufo) for func in funcs ]):
                query.add(tufo)

    def _stormOperSave(self, query, oper):
        data = query.data()
        for name in oper[1].get('args'):
            query.save(name,data)

    def _stormOperLoad(self, query, oper):
        names = oper[1].get('args')
        for name in names:
            [ query.add(t) for t in query.load(name) ]

    def _stormOperClear(self, query, oper):
        query.take()

    def _stormOperOpts(self, query, oper):
        for name,valu in oper[1].get('kwlist'):
            query.setOpt(name,valu)

    def _runOperFunc(self, query, oper):

        with query.withop(oper):

            query.tick()

            func = self.operfuncs.get( oper[0] )
            if func == None:
                raise NoSuchOper(name=oper[0])

            func(query,oper)

    def _runOperFuncs(self, query, opers):
        '''
        Run the given oper funcs within the query.
        '''
        try:

            [ self._runOperFunc(query,oper) for oper in opers ]

        except Exception as e:
            query.clear()
            query.log( excinfo=excinfo(e) )

    def _stormOperLift(self, query, oper):
        by = oper[1].get('cmp')
        prop = oper[1].get('prop')
        valu = oper[1].get('valu')
        limit = oper[1].get('limit')

        for tufo in self.stormTufosBy(by, prop, valu, limit=limit):
            query.add(tufo)

    def _stormOperPivot(self, query, oper):
        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        dstp = args[0]
        srcp = args[0]

        if len(args) > 1:
            srcp = args[1]

        # use the more optimal "in" mechanism once we have the pivot vals
        vals = list({ t[1].get(srcp) for t in query.take() if t != None })
        for tufo in self.stormTufosBy('in', dstp, vals, limit=opts.get('limit') ):
            query.add(tufo)

    def _stormOperJoin(self, query, oper):

        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        dstp = args[0]
        srcp = args[0]

        if len(args) > 1:
            srcp = args[1]

        # use the more optimal "in" mechanism once we have the pivot vals
        vals = list({ t[1].get(srcp) for t in query.data() if t != None })
        for tufo in self.stormTufosBy('in', dstp, vals, limit=opts.get('limit') ):
            query.add(tufo)
