
import logging
import time

import synapse.eventbus as s_eventbus
import synapse.lib.service as s_service
import synapse.swarm.syntax as s_syntax
import synapse.lib.userauth as s_userauth

import synapse.swarm.opers.basic as s_opers_basic

from synapse.exc import *
from synapse.common import gentask, msgenpack

logger = logging.getLogger(__name__)

class QueryKilled(Exception):pass
class QueryCancelled(QueryKilled):pass
class QueryLimitTime(QueryKilled):pass
class QueryLimitTouch(QueryKilled):pass

# TODO: implement per-form perms
# TODO: implement per-instruction perms
# TODO: runtime data model awareness
# TODO: instr to pull rest/json info and flatten to tufo form
# TODO: plugin/event based macro last-ditch parser
# TODO: objectify syntax parser to allow events/plugins
# TODO: def bytag(query,inst):
# TODO: support by queries via a different instr?
# TODO: syntax error exception classes
# TODO: optimize core selection by form
# TODO: sync/monitor data model for Cortex instances
# TODO: implement/expose unified data model

deftag = 'class.synapse.cores.common.Cortex'

class Query(s_eventbus.EventBus):

    def __init__(self, runt, insts, user=None, data=()):

        s_eventbus.EventBus.__init__(self)
        self.runt = runt
        #self.info = info
        self.canc = False

        self.user = user
        #self.user = info.get('user')

        self.formallow = {}

        self.uniq = {}
        self.saved = {}
        self.insts = insts

        # enforce operator perms
        for inst in insts:
            perm = 'swarm:oper:%s' % (inst[0],)
            if not self.allow(perm):
                raise NoSuchRule(user=self.user,perm=perm)

        self.opers = self.initInstOpers(insts)

        self.touched = 0
        self.recache = {}

        self.maxtime = None
        self.maxtouch = None

        self.results = {

            'debug': {
                'count': 0,
                'insts': [],
                'size': 0,
                'time': 0.0,
            },

            'options':{
                'uniq':True,
            },

            'limits':{
                'lift':None,
                'time':None,
                'touch':None,
            },

            'data':list(data),
        }

    def allow(self, perm):
        if self.user == None:
            return True

        return self.runt.allow(self.user,perm)

    def setSaveData(self, name, data):
        self.saved[name] = data

    def getSaveData(self, name):
        return self.saved.get(name,())

    def initInstOpers(self, insts):
        return [ self.initInstOper(inst) for inst in insts ]

    def initInstOper(self, inst):
        ctor = self.runt.getOperCtor(inst[0])
        return ctor(self,inst)

    def allowForm(self, form):
        if self.user == None:
            return True

        ret = self.formallow.get(form)
        if ret == None:
            ret = self.runt.allow(self.user,'swarm:form:' + form)
            self.formallow[form] = ret

        return ret

    def add(self, tufo):
        '''
        Add a tufo to the current query result set.
        '''
        self.tick()

        if self.opt('debug:count'):
            self.incDebug('count')

        if self.opt('debug:size'):
            prop = tufo[1].pop('.from')
            self.incDebug('size', len(msgenpack(tufo)))
            tufo[1]['.from'] = prop

        form = tufo[1].get('tufo:form')

        if not self.allowForm(form):
            return False

        if self.results['options'].get('uniq'):
            if self.uniq.get( tufo[0] ):
                return False

            self.uniq[ tufo[0] ] = True

        self.results['data'].append(tufo)

        return True

    def getTufosByPropFrom(self, prop, valu=None, limit=None, mintime=None, maxtime=None, fromtag=deftag):

        dyntask = gentask('getTufosByFrob',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)

        for svcfo,retval in self.callByTag(fromtag,dyntask):
            for tufo in retval:
                tufo[1]['.from'] = svcfo[0]
                yield tufo

    def callByTag(self, *args, **kwargs):
        # provide direct access to the callByTag API to prevent object reaching
        return self.runt.svcprox.callByTag(*args,**kwargs)

    def setOpt(self, name, valu):
        '''
        Set a query option to the given value.
        '''
        self.results['options'][name] = valu
        if name == 'debug':
            self.setOpt('debug:count', valu)
            self.setOpt('debug:size', valu)
            self.setOpt('debug:time', valu)

    def opt(self,name):
        '''
        Return the current value of a query option.
        '''
        return self.results['options'].get(name)

    def getDebug(self, name):
        '''
        Get debug info for the given value.
        '''
        return self.results['debug'].get(name, 0)

    def setDebug(self, name, valu):
        '''
        Set debug info to the given value.
        '''
        self.results['debug'][name] = valu

    def incDebug(self, name, valu=1):
        '''
        Increment debug info with the given value.
        '''
        valu = self.getDebug(name) + valu
        self.setDebug(name, valu)

    def addInstDebug(self, valu):
        '''
        Append the given instruction debug info.
        '''
        self.results['debug']['insts'].append(valu)

    def sumInstDebug(self, name):
        '''
        Sum the instruction debug info of the given name.
        '''
        return sum(inst.get(name, 0) for inst in self.results['debug']['insts'])

    def data(self):
        return self.results.get('data')

    def take(self):
        '''
        Return and clear the current result set.
        ( used by filtration operators )
        '''
        data = self.results.get('data')

        self.uniq.clear()
        # no list.clear() in py27
        self.results['data'] = []

        return data
        # FIXME reset any uniq stuff here!

    def run(self, oper):
        '''
        Run the given operation. Collect debug profiling per query options.
        '''
        debug = {}
        start = time.time()

        # HACK: Using top level debug for temporary storage since it will be overwritten later.
        if self.opt('debug:size'):
            self.setDebug('size', 0)

        if self.opt('debug:count'):
            self.setDebug('count', 0)

        oper.run()

        if self.opt('debug:time'):
            debug['time'] = int((time.time() - start) * 1000)

        if self.opt('debug:size'):
            debug['size'] = self.getDebug('size')

        if self.opt('debug:count'):
            debug['count'] = self.getDebug('count')

        if debug:
            self.addInstDebug(debug)

    def execute(self):
        '''
        Execute the parsed swarm query instructions.
        '''
        start = time.time()

        # FIXME setup user limits
        for oper in self.opers:
            self.run(oper)

        if self.opt('debug:count'):
            self.setDebug('count', self.sumInstDebug('count'))

        if self.opt('debug:time'):
            duration_ms = int((time.time() - start) * 1000)
            self.setDebug('time', duration_ms)

        if self.opt('debug:size'):
            self.setDebug('size', self.sumInstDebug('size'))

        return self.results

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

        if self.maxtime != None and time.time() > self.maxtime:
            raise QueryLimitTime()

        self.touched += touch
        if self.maxtouch != None and self.touched > self.maxtouch:
            raise QueryLimitTouch()

class Runtime(s_eventbus.EventBus):

    def __init__(self, svcbus, **info):
        s_eventbus.EventBus.__init__(self)

        self.info = info
        self.auth = info.get('auth')

        self.svcbus = svcbus
        self.svcprox = s_service.SvcProxy(svcbus)

        self.rules = {}

        self.operctors = {}

        # add the basic operators
        self.setOperCtor('by', s_opers_basic.ByOper)
        self.setOperCtor('eq', s_opers_basic.EqOper)

        self.setOperCtor('gt', s_opers_basic.GtOper)
        self.setOperCtor('lt', s_opers_basic.LtOper)
        self.setOperCtor('ge', s_opers_basic.GeOper)
        self.setOperCtor('le', s_opers_basic.LeOper)

        self.setOperCtor('re', s_opers_basic.ReOper)

        self.setOperCtor('or', s_opers_basic.OrOper)
        self.setOperCtor('and', s_opers_basic.AndOper)

        self.setOperCtor('has', s_opers_basic.HasOper)

        self.setOperCtor('join', s_opers_basic.JoinOper)
        self.setOperCtor('opts', s_opers_basic.OptsOper)

        self.setOperCtor('load', s_opers_basic.LoadOper)
        self.setOperCtor('save', s_opers_basic.SaveOper)
        self.setOperCtor('clear', s_opers_basic.ClearOper)

        self.setOperCtor('pivot', s_opers_basic.PivotOper)

    def setOperCtor(self, name, func):
        '''
        Add a constructor for an operator by name.

        Example:

            runt.setOperInit('foo',FooOper)

        '''
        self.operctors[name] = func

    def getOperCtor(self, name):
        '''
        Return a constructor function for an operator by name.
        '''
        ctor = self.operctors.get(name)
        if ctor == None:
            raise NoSuchOper(name=name)
        return ctor

    def setUserAuth(self, auth):
        self.auth = auth
        self.rules.clear()

    def allow(self, user, perm):
        '''
        Check if a user is allowed a given permission.
        '''
        if self.auth == None:
            return True

        rules = self._getUserRules(user)
        return rules.allow(perm)

    def allowForm(self, user, form):
        '''
        Check if a user is allowed access to a data form.

        Example:

            if runt.allowForm('visi','foo:bar'):
                stuff()

        '''
        return self.allow(user,'swarm:form:' + form)

    def _getUserRules(self, user):
        rules = self.rules.get(user)
        if rules == None:
            rules = s_userauth.Rules(self.auth,user)
            self.rules[user] = rules
        return rules

    def ask(self, text, user=None, data=(), maxtime=None):
        '''
        Run a swarm query and return the query result dict.
        user= stdin=
        '''
        #info['text'] = text
        insts = s_syntax.parse(text)

        # TODO user query auditing
        # TODO enforce oper perms here ( before run )

        query = Query(self, insts, user=user, data=data)
        query.maxtime = maxtime

        return query.execute()

    def eval(self, text, user=None, data=()):
        '''
        Run a swarm query and return only the result data.
        '''
        return self.ask(text,user=user,data=data).get('data')

class SwarmApi:
    '''
    The SwarmApi is meant for "less trusted" exposure via telepath/svcbus.
    '''
    def __init__(self, runt):
        self.runt = runt

    def ask(self, *args, **kwargs):
        return self.runt.ask(*args,**kwargs)

