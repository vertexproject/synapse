import re
import time
import logging
import collections

import synapse.eventbus as s_eventbus

import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope
import synapse.lib.syntax as s_syntax
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.lib.config import Configable

logger = logging.getLogger(__name__)

class LimitHelp:

    def __init__(self, limit):
        self.limit = limit

    def get(self):
        return self.limit

    def reached(self):
        return self.limit != None and self.limit == 0

    def dec(self, size=1):

        if self.limit == None:
            return False

        if size < 0:
            size = 0

        self.limit = max(self.limit-size,0)
        return self.limit == 0

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
            info['excinfo'] = excinfo(exc)
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

    def __len__(self):
        return len(self.results['data'])

    def size(self):
        '''
        Get the number of tufos currently in the query.
        '''
        return len(self)

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
        self.setCmprCtor('seen', self._cmprCtorSeen)
        self.setCmprCtor('range', self._cmprCtorRange)

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
        self.setOperFunc('refs', self._stormOperRefs)
        self.setOperFunc('pivot', self._stormOperPivot)
        self.setOperFunc('alltag', self._stormOperAllTag)
        self.setOperFunc('addtag', self._stormOperAddTag)
        self.setOperFunc('deltag', self._stormOperDelTag)
        self.setOperFunc('totags', self._stormOperToTags)
        self.setOperFunc('nexttag', self._stormOperNextSeq)
        self.setOperFunc('setprop', self._stormOperSetProp)
        self.setOperFunc('addxref', self._stormOperAddXref)
        self.setOperFunc('fromtags', self._stormOperFromTags)
        self.setOperFunc('jointags', self._stormOperJoinTags)

        # Cache compiled regex objects.
        self._rt_regexcache = s_cache.FixedCache(1024, re.compile)

    def getStormCore(self, name=None):
        '''
        Return the (optionally named) cortex for use in direct storm
        operators.
        '''
        return self._getStormCore(name=name)

    def _getStormCore(self, name=None):
        raise NoSuchImpl(name='getStormCore')

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

        NOTE: Under the hood, this API dynamically generates a
              cmpr ctor add adds it using addCmprCtor.

        '''
        # TODO make ourselves a model that is local...
        # ( in most instances it is anyway, but for swarm... )
        core = self.getStormCore()

        def cmprctor(oper):

            prop = oper[1].get('prop')
            valu = oper[1].get('valu')

            isrel = prop.startswith(':')

            # generate a slightly different function for rel / non-rel
            if not isrel:

                valu,subs = core.getPropNorm(prop,valu)
                def cmpr(tufo):
                    return func(tufo[1].get(prop),valu)

                return cmpr

            # we are processing a relative property filter....
            fulls = {}
            norms = {}

            def _get_full_norm(f,p,v):
                retfull = fulls.get(f)
                if retfull == None:
                    retfull = fulls[f] = (f+p)

                retnorm,_ = core.getPropNorm(retfull,v)
                return retfull,retnorm

            def cmpr(tufo):
                form = tufo[1].get('tufo:form')
                full,norm = _get_full_norm(form,prop,valu)
                return func(tufo[1].get(full),norm)

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

        isrel = prop.startswith(':')
        reobj = self._rt_regexcache.get(oper[1].get('valu'))

        def cmpr(tufo):

            full = prop
            if isrel:
                full = tufo[1].get('tufo:form') + prop

            valu = tufo[1].get(full)
            if valu == None:
                return False

            return reobj.search(valu) != None

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
        reg_props = {}

        # Glob helpers
        glob_smark = '*'
        glob_mmark = '**'
        glob_sre = '[^\.]+?'
        glob_mre = '.+'

        def _cmpGlobParts(s, sep='.'):
            parts = s.split(sep)
            parts = [p.replace(glob_mmark, glob_mre) for p in parts]
            parts = [p.replace(glob_smark, glob_sre) for p in parts]
            regex = '\{}'.format(sep).join(parts)
            return regex + '$'

        if glob_smark in tag:
            tag_regex = _cmpGlobParts(tag)
            reobj = self._rt_regexcache.get(tag_regex)

            def getIsHit(prop):
                _tag = prop.split('|', 2)[2]
                return reobj.search(_tag)

            glob_props = s_cache.KeyCache(getIsHit)

            def glob_cmpr(tufo):
                return any((glob_props.get(p) for p in tufo[1] if p.startswith('*|')))

            return glob_cmpr

        def reg_cmpr(tufo):
            form = tufo[1].get('tufo:form')

            prop = reg_props.get(form)
            if prop == None:
                prop = reg_props[form] = '*|%s|%s' % (form,tag)

            return tufo[1].get(prop) != None

        return reg_cmpr

    def _cmprCtorSeen(self, oper):

        args = [ str(v) for v in oper[1].get('args') ]

        core = self.getStormCore()

        vals = [ core.getTypeNorm('time',t)[0] for t in args ]

        seenprops = {}
        def getseen(form):
            stup = seenprops.get(form)
            if stup == None:
                stup = seenprops[form] = (form+':seen:min',form+':seen:max')
            return stup

        def cmpr(tufo):

            form = tufo[1].get('tufo:form')

            minprop,maxprop = getseen(form)

            smin = tufo[1].get(minprop)
            smax = tufo[1].get(maxprop)

            if smin == None or smax == None:
                return False

            for valu in vals:
                if valu >= smin and valu <= smax:
                    return True

        return cmpr

    def _cmprCtorRange(self, oper):

        prop = self._reqOperArg(oper,'prop')
        valu = self._reqOperArg(oper,'valu')

        #TODO unified syntax plumbing with in-band help

        core = self.getStormCore()
        isrel = prop.startswith(':')

        def initMinMax(key):
            xmin,_ = core.getPropNorm(key,valu[0])
            xmax,_ = core.getPropNorm(key,valu[1])
            return int(xmin),int(xmax)

        norms = s_cache.KeyCache( initMinMax )

        def cmpr(tufo):

            full = prop
            if isrel:
                form = tufo[1].get('tufo:form')
                full = form + prop

            valu = tufo[1].get(full)
            if valu == None:
                return False

            minval,maxval = norms.get(full)

            return valu >= minval and valu <= maxval

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

        [query.add(tufo) for tufo in self.stormTufosBy(by, prop, valu, limit=limit)]

    def _stormOperPivot(self, query, oper):
        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        srcp = None
        dstp = args[0]

        if len(args) > 1:
            srcp = args[1]

        # do we have a relative source property?
        relsrc = srcp != None and srcp.startswith(':')

        vals = set()
        tufs = query.take()

        if srcp != None and not relsrc:

            for tufo in tufs:
                valu = tufo[1].get(srcp)
                if valu != None:
                    vals.add(valu)

        elif not relsrc:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form)
                if valu != None:
                    vals.add(valu)

        else:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form+srcp)
                if valu != None:
                    vals.add(valu)

        [query.add(t)for t in self.stormTufosBy('in', dstp, list(vals), limit=opts.get('limit'))]

    def _stormOperNextSeq(self, query, oper):
        name = None

        args = oper[1].get('args')
        kwargs = dict( oper[1].get('kwlist') )

        doc = kwargs.get('doc')
        name = kwargs.get('core')

        if len(args) != 1:
            raise SyntaxError('nexttag(<tagname>,doc=<doc>)')

        tag = args[0]

        core = self.getStormCore(name=name)
        valu = core.nextSeqValu(tag)

        node = core.formTufoByProp('syn:tag',valu,doc=doc)

        query.add(node)

    def _stormOperJoin(self, query, oper):

        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        dstp = args[0]
        srcp = args[0]

        if len(args) > 1:
            srcp = args[1]

        # use the more optimal "in" mechanism once we have the pivot vals
        vals = list({ t[1].get(srcp) for t in query.data() if t != None })
        [query.add(tufo) for tufo in self.stormTufosBy('in', dstp, vals, limit=opts.get('limit'))]

    def _stormOperAddXref(self, query, oper):

        args = oper[1].get('args')
        if len(args) != 3:
            raise SyntaxError('addxref(<type>,<form>,<valu>)')

        xref,form,valu = args

        core = self.getStormCore()

        # TODO clearer error handling
        for node in query.take():
            sorc = node[1].get( node[1].get('tufo:form') )
            node = core.formTufoByProp(xref,(sorc,form,valu))
            query.add(node)

    def _stormOperRefs(self, query, oper):
        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        #TODO opts.get('degrees')
        limt = LimitHelp( opts.get('limit') )

        core = self.getStormCore()

        nodes = query.data()

        #NOTE: we only actually want refs where type is form

        done = set()
        if not args or 'in' in args:

            for node in nodes:

                if limt.reached():
                    break

                form = node[1].get('tufo:form')
                valu = node[1].get(form)

                dkey = (form,valu)
                if dkey in done:
                    continue

                done.add(dkey)

                for prop,info in core.getPropsByType(form):

                    pkey = (prop,valu)
                    if pkey in done:
                        continue

                    done.add(pkey)

                    news = core.getTufosByProp(prop,valu=valu, limit=limt.get())

                    [ query.add(n) for n in news ]

                    if limt.dec(len(news)):
                        break

        if not args or 'out' in args:

            for node in nodes:

                if limt.reached():
                    break

                form = node[1].get('tufo:form')
                for prop,info in core.getSubProps(form):

                    valu = node[1].get(prop)
                    if valu == None:
                        continue

                    # ensure that the prop's type is also a form
                    name = core.getPropTypeName(prop)
                    if not core.isTufoForm(name):
                        continue

                    pkey = (prop,valu)
                    if pkey in done:
                        continue

                    done.add(pkey)

                    news = core.getTufosByProp(name,valu=valu,limit=limt.get())

                    [ query.add(n) for n in news ]

                    if limt.dec(len(news)):
                        break

    def _stormOperSetProp(self, query, oper):
        args = oper[1].get('args')
        props = dict( oper[1].get('kwlist') )

        core = self.getStormCore()

        [ core.setTufoProps(node,**props) for node in query.data() ]

    def _iterPropTags(self, props, tags):
        for prop in props:
            for tag in tags:
                yield prop,tag

    def _stormOperAllTag(self, query, oper):

        tags = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        limit = opts.get('limit')

        core = self.getStormCore()

        for tag in tags:
            nodes = core.getTufosByDark('tag', tag, limit=limit)

            [query.add(node) for node in nodes]

            if limit != None:
                limit -= len(nodes)
                if limit <= 0:
                    break

    def _stormOperAddTag(self, query, oper):
        tags = oper[1].get('args')

        core = self.getStormCore()

        nodes = query.data()

        for tag in tags:
            [ core.addTufoTag(node,tag) for node in nodes ]

    def _stormOperDelTag(self, query, oper):
        tags = oper[1].get('args')

        core = self.getStormCore()

        nodes = query.data()

        for tag in tags:
            [ core.delTufoTag(node,tag) for node in nodes ]

    def _stormOperJoinTags(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))
        core = self.getStormCore()

        forms = {arg for arg in args}
        keep_nodes = opts.get('keep_nodes', False)
        limt = LimitHelp(opts.get('limit'))

        nodes = query.data()
        if not keep_nodes:
            query.clear()

        tags = {tag for node in nodes for tag in s_tufo.tags(node, leaf=True)}

        if not forms:
            forms = set(core.getModelDict().get('forms'))

        for tag in tags:
            lqs = query.size()
            tufos = core.getTufosByDark('tag', tag, limit=limt.get())
            [query.add(tufo) for tufo in tufos if tufo[1].get('tufo:form') in forms]
            if tufos:
                lq = query.size()
                nnewnodes = lq - lqs
                if limt.dec(nnewnodes):
                    break

    def _stormOperToTags(self, query, oper):
        opts = dict(oper[1].get('kwlist'))
        nodes = query.take()
        core = self.getStormCore()

        leaf = opts.get('leaf', True)
        tags = {tag for node in nodes for tag in s_tufo.tags(node, leaf=leaf)}
        [query.add(tufo) for tufo in core.getTufosBy('in', 'syn:tag', list(tags))]

    def _stormOperFromTags(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        nodes = query.take()

        forms = {arg for arg in args}
        limt = LimitHelp(opts.get('limit'))

        tags = {node[1].get('syn:tag') for node in nodes if node[1].get('tufo:form') == 'syn:tag'}

        core = self.getStormCore()

        if not forms:
            forms = set(core.getModelDict().get('forms'))

        for tag in tags:
            lqs = query.size()
            tufos = core.getTufosByDark('tag', tag, limit=limt.get())
            [query.add(tufo) for tufo in tufos if tufo[1].get('tufo:form') in forms]
            if tufos:
                lq = query.size()
                nnewnodes = lq - lqs
                if limt.dec(nnewnodes):
                    break
