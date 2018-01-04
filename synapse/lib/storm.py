import time
import fnmatch
import logging
import collections

import regex

import synapse.common as s_common

import synapse.lib.auth as s_auth
import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.syntax as s_syntax
import synapse.lib.interval as s_interval

from synapse.lib.config import Configable, confdef

logger = logging.getLogger(__name__)

class LimitHelp:

    def __init__(self, limit):
        self.limit = limit

    def get(self):
        return self.limit

    def reached(self):
        return self.limit is not None and self.limit == 0

    def dec(self, size=1):

        if self.limit is None:
            return False

        if size < 0:
            size = 0

        self.limit = max(self.limit - size, 0)
        return self.limit == 0

class ShowHelp:
    '''
    The ShowHelp class implements routines for formatting storm
    query output based on the embedded "show" directive within
    the query results.
    '''
    def __init__(self, core, show):
        self.core = core
        self.show = show

    def _relPropFunc(self, prop):

        def get(node):

            form = node[1].get('tufo:form')
            full = form + prop

            valu = node[1].get(full)
            if valu is None:
                return ''

            return self.core.getPropRepr(full, valu)

        return get

    def _tagGlobFunc(self, ptrn):

        # do they want all tags?
        if ptrn == '#':

            def alltags(node):
                tags = ['#' + t for t in sorted(s_tufo.tags(node, leaf=True))]
                return ' '.join(tags)

            return alltags

        ptrn = ptrn[1:]

        def get(node):

            tags = []

            for tag in list(sorted(s_tufo.tags(node, leaf=True))):

                if not fnmatch.fnmatch(tag, ptrn):
                    continue

                tags.append('#' + tag)

            return ' '.join(tags)

        return get

    def _fullPropFunc(self, prop):

        def get(node):

            valu = node[1].get(prop)
            if valu is None:
                return ''

            return self.core.getPropRepr(prop, valu)

        return get

    def _getShowFunc(self, col):

        col = col.strip()

        if col.startswith('#'):
            return self._tagGlobFunc(col)

        if col.startswith(':'):
            return self._relPropFunc(col)

        return self._fullPropFunc(col)

    def _getShowFuncs(self):
        cols = self.show.get('columns')
        return [self._getShowFunc(c) for c in cols]

    def rows(self, nodes):
        '''
        Return a list of display columns for the given nodes.

        Args:
            nodes (((str,dict),...)):   A list of nodes in tuple form.

        Returns:
            ( [(str,...), ...] ): A list of column lists containing strings

        '''
        funcs = self._getShowFuncs()

        ordr = self.show.get('order')
        if ordr is not None:
            nodes.sort(key=lambda x: x[1].get(ordr))

        rows = []
        for node in nodes:
            rows.append([func(node) for func in funcs])

        return rows

    def pad(self, rows):
        '''
        Pad a series of column values for aligned display.
        '''
        widths = []
        for i in range(len(rows[0])):
            widths.append(max([len(r[i]) for r in rows]))

        retn = []
        for row in rows:
            retn.append([r.rjust(size) for r, size in s_common.iterzip(row, widths)])

        return retn

class OperWith:

    def __init__(self, query, oper):
        self.oper = oper
        self.query = query
        self.stime = None

    def __enter__(self):
        self.stime = s_common.now()
        self.query.added = 0
        self.query.subed = 0
        return self

    def __exit__(self, exc, cls, tb):

        info = {
            'sub': self.query.subed,
            'add': self.query.added,
            'took': s_common.now() - self.stime
        }

        if exc is not None:
            info['excinfo'] = s_common.excinfo(exc)
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

            'options': {
                'uniq': 1,
                'limit': None,
            },

            'limits': {
                'lift': None,
                'time': None,
                'touch': None,
            },

            'oplog': [], # [ <dict>, ... ] ( one dict for each oper )

            'data': list(data),
            'show': {},

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
        return self.saved.get(name, ())

    def add(self, tufo):
        '''
        Add a tufo to the current query result set.
        '''
        self.tick()
        self.added += 1

        data = self.results.get('data')

        form = tufo[1].get('tufo:form')

        if tufo[0] is not None and self.results['options'].get('uniq'):
            if self.uniq.get(tufo[0]):
                return False

            self.uniq[tufo[0]] = True

        self.results['data'].append(tufo)

        return True

    def setOpt(self, name, valu):
        '''
        Set a query option to the given value.
        '''
        self.results['options'][name] = valu

    def opt(self, name):
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

        self.uniq = {}
        self.results['data'] = []

        return data

    def clear(self):
        self.take()

    def withop(self, oper):
        self.results['oplog'].append({'mnem': oper[0]})
        return OperWith(self, oper)

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
        if self.maxtime is not None and nowtime >= self.maxtime:
            raise s_common.HitStormLimit(name='maxtime', limit=self.maxtime, valu=nowtime)

        self.touched += touch
        if self.maxtouch is not None and self.touched > self.maxtouch:
            raise s_common.HitStormLimit(name='maxtouch', limit=self.maxtouch, valu=self.touched)

class QueryKilled(Exception): pass
class QueryCancelled(QueryKilled): pass
class QueryLimitTime(QueryKilled): pass
class QueryLimitTouch(QueryKilled): pass

def invert(func):
    def invfunc(*args, **kwargs):
        return not func(*args, **kwargs)
    return invfunc

def eq(x, y):
    if x is None or y is None:
        return False
    return x == y

def lt(x, y):
    if x is None or y is None:
        return False
    return x < y

def gt(x, y):
    if x is None or y is None:
        return False
    return x > y

def le(x, y):
    if x is None or y is None:
        return False
    return x <= y

def ge(x, y):
    if x is None or y is None:
        return False
    return x >= y

def setkw(oper, name, valu):
    '''
    Set a keyword argument in a given operator.

    Args:
        oper ((str,dict)): A storm operator tufo
        name (str): A kwarg name
        valu (obj): A kwarg value

    Returns:
        (None)
    '''
    kwlist = oper[1].get('kwlist')
    if kwlist is None:
        kwlist = []

    kwlist = [(k, v) for (k, v) in kwlist if k != name]
    kwlist.append((name, valu))
    oper[1]['kwlist'] = kwlist

class Runtime(Configable):

    def __init__(self, **opts):
        Configable.__init__(self)

        self.setConfOpts(opts)

        self.operfuncs = {}
        self.cmprctors = {}

        self.setCmprFunc('eq', eq)
        self.setCmprFunc('lt', lt)
        self.setCmprFunc('gt', gt)
        self.setCmprFunc('le', le)
        self.setCmprFunc('ge', ge)

        self.setCmprCtor('or', self._cmprCtorOr)
        self.setCmprCtor('and', self._cmprCtorAnd)
        self.setCmprCtor('tag', self._cmprCtorTag)
        self.setCmprCtor('seen', self._cmprCtorSeen)
        self.setCmprCtor('range', self._cmprCtorRange)

        # interval and interval-interval comparisons
        self.setCmprCtor('ival', self._cmprCtorIval)
        self.setCmprCtor('ivalival', self._cmprCtorIvalIval)

        self.setCmprCtor('in', self._cmprCtorIn)
        self.setCmprCtor('re', self._cmprCtorRe)
        self.setCmprCtor('has', self._cmprCtorHas)

        self.setOperFunc('filt', self._stormOperFilt)
        self.setOperFunc('opts', self._stormOperOpts)

        self.setOperFunc('save', self._stormOperSave)
        self.setOperFunc('load', self._stormOperLoad)
        self.setOperFunc('clear', self._stormOperClear)

        self.setOperFunc('guid', self._stormOperGuid)
        self.setOperFunc('join', self._stormOperJoin)
        self.setOperFunc('task', self._stormOperTask)
        self.setOperFunc('lift', self._stormOperLift)
        self.setOperFunc('refs', self._stormOperRefs)
        self.setOperFunc('tree', self._stormOperTree)
        self.setOperFunc('limit', self._stormOperLimit)
        self.setOperFunc('pivot', self._stormOperPivot)
        self.setOperFunc('alltag', self._stormOperAllTag)
        self.setOperFunc('addtag', self._stormOperAddTag)
        self.setOperFunc('deltag', self._stormOperDelTag)
        self.setOperFunc('totags', self._stormOperToTags)

        self.setOperFunc('addnode', self._stormOperAddNode)
        self.setOperFunc('delnode', self._stormOperDelNode)
        self.setOperFunc('delprop', self._stormOperDelProp)

        self.setOperFunc('nexttag', self._stormOperNextTag)
        self.setOperFunc('setprop', self._stormOperSetProp)
        self.setOperFunc('addxref', self._stormOperAddXref)
        self.setOperFunc('fromtags', self._stormOperFromTags)
        self.setOperFunc('jointags', self._stormOperJoinTags)

        self.setOperFunc('get:tasks', self._stormOperGetTasks)

        self.setOperFunc('show:cols', self._stormOperShowCols)

        # Cache compiled regex objects.
        self._rt_regexcache = s_cache.FixedCache(1024, regex.compile)

    @staticmethod
    @confdef(name='storm')
    def _storm_runtime_confdefs():
        confdefs = (
            ('storm:limit:lift', {'asloc': 'limlift', 'defval': None, 'doc': 'Global lift limit'}),
            ('storm:query:log:en', {'asloc': 'querylog', 'defval': 0, 'ptype': 'bool',
                                    'doc': 'words'}),
            ('storm:query:log:level', {'asloc': 'queryloglevel', 'defval': logging.DEBUG, 'ptype': 'int',
                                       'doc': 'Logging level to fire query log messages at.'}),
        )
        return confdefs

    def getStormCore(self, name=None):
        '''
        Return the (optionally named) cortex for use in direct storm
        operators.
        '''
        return self._getStormCore(name=name)

    def _getStormCore(self, name=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='getStormCore')

    def getLiftLimit(self, *limits):
        '''
        Return the lift() result limit for the current user/runtime.

        Args:
            *limits:    Optional list of requested int limit values

        Returns:
            (int): The lift limit value or None

        '''
        limits = [l for l in limits if l is not None]

        # If they made no requests, return the default
        if not limits:
            return self.limlift

        # TODO: plumb user auth based limit here...
        return max(limits)

    def stormTufosBy(self, by, prop, valu=None, limit=None):
        '''
        A STORM runtime specific version of the cortex function getTufosBy
        which allows sub-classes to override the default behavior for
        operators like lift/join/pivot.
        '''
        limit = self.getLiftLimit(limit)
        return self._stormTufosBy(by, prop, valu=valu, limit=limit)

    def _stormTufosBy(self, by, prop, valu=None, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_stormTufosBy')

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

                valu, subs = core.getPropNorm(prop, valu)
                def cmpr(tufo):
                    return func(tufo[1].get(prop), valu)

                return cmpr

            # we are processing a relative property filter....
            fulls = {}
            norms = {}

            def _get_full_norm(f, p, v):
                retfull = fulls.get(f)
                if retfull is None:
                    retfull = fulls[f] = (f + p)

                retnorm, _ = core.getPropNorm(retfull, v)
                return retfull, retnorm

            def cmpr(tufo):
                form = tufo[1].get('tufo:form')
                full, norm = _get_full_norm(form, prop, valu)
                return func(tufo[1].get(full), norm)

            return cmpr

        self.setCmprCtor(name, cmprctor)

    def getCmprFunc(self, oper):
        '''
        Return a comparison function for the given operator.
        '''
        name = oper[1].get('cmp', 'eq')
        ctor = self.cmprctors.get(name)
        if ctor is None:
            raise s_common.NoSuchCmpr(name=name)
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
        if self.querylog:
            user = s_auth.whoami()
            logger.log(self.queryloglevel, 'Executing storm query [%s] as [%s]', text, user)
        opers = s_syntax.parse(text)
        return self.run(opers, data=data, timeout=timeout)

    def plan(self, opers):
        '''
        Review a list of opers and return a potentially optimized list.

        Args:
            opers ([(str,dict),]):  List of opers in tufo form

        Returns:
            ([(str,dict),]): Optimized list

        '''
        retn = []

        for oper in opers:

            # specify a limit backward from limit oper...
            if oper[0] == 'limit' and retn:
                args = oper[1].get('args', ())
                if args:
                    limt = s_common.intify(args[0])
                    if limt is not None:
                        setkw(retn[-1], 'limit', limt)

            # TODO look for a form lift + tag filter and optimize

            retn.append(oper)

        return retn

    def run(self, opers, data=(), timeout=None):
        '''
        Execute a pre-parsed set of opers.

        Example:

            opers = runt.parse('foo:bar=20 +foo:baz | foo:faz=30')
            # ... some time later...
            res0 = runt.run(opers)

        '''
        opers = self.plan(opers)

        maxtime = None
        if timeout is not None:
            maxtime = time.time() + timeout

        # TODO overall time per user goes here

        query = Query(data=data, maxtime=maxtime)

        try:

            self._runOperFuncs(query, opers)

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
        answ = self.ask(text, data=data, timeout=timeout)

        oplog = answ.get('oplog')
        if oplog:
            excinfo = oplog[-1].get('excinfo')
            if excinfo is not None:
                errname = excinfo.get('err')
                errinfo = excinfo.get('errinfo', {})
                errinfo['errfile'] = excinfo.get('errfile')
                errinfo['errline'] = excinfo.get('errline')
                raise s_common.synerr(errname, **errinfo)

        return answ.get('data')

    def _reqOperArg(self, oper, name):
        valu = oper[1].get(name)
        if valu is None:
            raise s_common.BadOperArg(oper=oper, name=name, mesg='not found')
        return valu

    def _cmprCtorHas(self, oper):
        prop = self._reqOperArg(oper, 'prop')

        def cmpr(tufo):
            return tufo[1].get(prop) is not None

        return cmpr

    def _cmprCtorIn(self, oper):
        prop, valu = oper[1].get('args')

        if len(valu) > 12:
            valu = set(valu)

        def cmpr(tufo):
            return tufo[1].get(prop) in valu

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
            if valu is None:
                return False

            return reobj.search(valu) is not None

        return cmpr

    def _cmprCtorOr(self, oper):
        args = self._reqOperArg(oper, 'args')
        funcs = [self.getCmprFunc(op) for op in args]
        def cmpr(tufo):
            return any([func(tufo) for func in funcs])
        return cmpr

    def _cmprCtorAnd(self, oper):
        args = self._reqOperArg(oper, 'args')
        funcs = [self.getCmprFunc(op) for op in args]
        def cmpr(tufo):
            return all([func(tufo) for func in funcs])
        return cmpr

    def _cmprCtorTag(self, oper):
        tag = self._reqOperArg(oper, 'valu')
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
                #_tag = prop.split('|', 2)[2]
                #_tag = prop.split('|', 2)[2]
                # prop will be like "#foo.bar"
                return reobj.search(prop[1:])

            glob_props = s_cache.KeyCache(getIsHit)

            def glob_cmpr(tufo):
                return any((glob_props.get(p) for p in tufo[1] if p[0] == '#'))

            return glob_cmpr

        def reg_cmpr(tufo):
            return tufo[1].get('#' + tag) is not None

        return reg_cmpr

    def _cmprCtorSeen(self, oper):

        args = [str(v) for v in oper[1].get('args')]

        core = self.getStormCore()

        vals = [core.getTypeNorm('time', t)[0] for t in args]

        seenprops = {}
        def getseen(form):
            stup = seenprops.get(form)
            if stup is None:
                stup = seenprops[form] = (form + ':seen:min', form + ':seen:max')
            return stup

        def cmpr(tufo):

            form = tufo[1].get('tufo:form')

            minprop, maxprop = getseen(form)

            smin = tufo[1].get(minprop)
            smax = tufo[1].get(maxprop)

            if smin is None or smax is None:
                return False

            for valu in vals:
                if valu >= smin and valu <= smax:
                    return True

        return cmpr

    def _cmprCtorRange(self, oper):
        prop, valu = oper[1].get('args')

        core = self.getStormCore()
        isrel = prop.startswith(':')

        def initMinMax(key):
            xmin, _ = core.getPropNorm(key, valu[0])
            xmax, _ = core.getPropNorm(key, valu[1])
            return int(xmin), int(xmax)

        norms = s_cache.KeyCache(initMinMax)

        def cmpr(tufo):

            full = prop
            if isrel:
                form = tufo[1].get('tufo:form')
                full = form + prop

            valu = tufo[1].get(full)
            if valu is None:
                return False

            minval, maxval = norms.get(full)

            return valu >= minval and valu <= maxval

        return cmpr

    def _cmprCtorIval(self, oper):

        name, tick = oper[1].get('valu')

        minp = '>' + name
        maxp = '<' + name

        def cmpr(tufo):

            minv = tufo[1].get(minp)
            maxv = tufo[1].get(maxp)

            if minv is None or minv > tick or maxv is None or maxv <= tick:
                return False

            return True

        return cmpr

    def _cmprCtorIvalIval(self, oper):

        name, ival = oper[1].get('valu')

        minp = '>' + name
        maxp = '<' + name

        def cmpr(tufo):

            minv = tufo[1].get(minp)
            maxv = tufo[1].get(maxp)

            if minv is None or maxv is None:
                return False

            return s_interval.overlap(ival, (minv, maxv))

        return cmpr

    def _stormOperShowCols(self, query, oper):

        opts = dict(oper[1].get('kwlist'))

        order = opts.get('order')
        if order is not None:
            query.results['show']['order'] = order

        query.results['show']['columns'] = oper[1].get('args')

    def _stormOperFilt(self, query, oper):
        cmpr = self.getCmprFunc(oper)
        if oper[1].get('mode') == 'cant':
            cmpr = invert(cmpr)

        [query.add(t) for t in query.take() if cmpr(t)]

    def _stormOperSave(self, query, oper):
        data = query.data()
        for name in oper[1].get('args'):
            query.save(name, data)

    def _stormOperLoad(self, query, oper):
        names = oper[1].get('args')
        for name in names:
            [query.add(t) for t in query.load(name)]

    def _stormOperClear(self, query, oper):
        query.take()

    def _stormOperOpts(self, query, oper):
        for name, valu in oper[1].get('kwlist'):
            query.setOpt(name, valu)

    def _runOperFunc(self, query, oper):

        with query.withop(oper):

            query.tick()

            func = self.operfuncs.get(oper[0])
            if func is None:
                raise s_common.NoSuchOper(name=oper[0])

            try:

                func(query, oper)

            except Exception as e:
                logger.exception(e)
                raise

    def _runOperFuncs(self, query, opers):
        '''
        Run the given oper funcs within the query.
        '''
        try:

            [self._runOperFunc(query, oper) for oper in opers]

        except Exception as e:
            query.clear()
            query.log(excinfo=s_common.excinfo(e))

    def _stormOperLift(self, query, oper):

        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        if len(args) not in (1, 2):
            raise s_common.BadSyntaxError(mesg='lift(<prop> [,<valu>, by=<by>, limit=<limit>])')

        valu = None
        prop = args[0]
        if len(args) == 2:
            valu = args[1]

        by = opts.get('by', 'has')
        if by == 'has' and valu is not None:
            by = 'eq'

        limt0 = opts.get('limit')
        limt1 = query.opt('limit')

        limit = self.getLiftLimit(limt0, limt1)

        [query.add(tufo) for tufo in self.stormTufosBy(by, prop, valu, limit=limit)]

    def _stormOperLimit(self, query, oper):
        args = oper[1].get('args', ())
        if len(args) != 1:
            raise s_common.BadSyntaxError(mesg='limit(<size>)')

        size = s_common.intify(args[0])
        if size is None:
            raise s_common.BadSyntaxError(mesg='limit(<size>)')

        if query.size() > size:
            [query.add(node) for node in query.take()[:size]]

    def _stormOperPivot(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        if len(args) is 1:
            srcp, dstp = None, args[0]

        elif len(args) is 2:
            srcp, dstp = args[0], args[1]

        else:
            raise s_common.BadSyntaxError(mesg='pivot(<srcprop>,<dstprop>)')

        limit = opts.get('limit')
        if limit is not None and limit < 0:
            raise s_common.BadOperArg(oper='pivot', name='limit', mesg='must be >= 0')

        # do we have a relative source property?
        relsrc = srcp is not None and srcp.startswith(':')

        vals = set()
        tufs = query.take()

        if srcp is not None and not relsrc:

            for tufo in tufs:
                valu = tufo[1].get(srcp)
                if valu is not None:
                    vals.add(valu)

        elif not relsrc:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form)
                if valu is not None:
                    vals.add(valu)

        else:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form + srcp)
                if valu is not None:
                    vals.add(valu)

        # do not use fancy by handlers for runt nodes...
        core = self.getStormCore()
        if core.isRuntProp(dstp):

            limt = self.getLiftLimitHelp(limit)
            for valu in vals:

                # the base "eq" handler is aware of runts...
                news = self.stormTufosBy('eq', dstp, valu, limit=limt.get())
                limt.dec(len(news))

                [query.add(n) for n in news]

                if limt.reached():
                    break

            return

        [query.add(t)for t in self.stormTufosBy('in', dstp, list(vals), limit=limit)]

    def _stormOperNextTag(self, query, oper):
        name = None

        args = oper[1].get('args')
        kwargs = dict(oper[1].get('kwlist'))

        doc = kwargs.get('doc', '??')
        name = kwargs.get('core')

        if len(args) != 1:
            raise s_common.BadSyntaxError(mesg='nexttag(<tagname>,doc=<doc>)')

        tag = args[0]

        core = self.getStormCore(name=name)
        valu = core.nextSeqValu(tag)

        node = core.formTufoByProp('syn:tag', valu, doc=doc)

        query.add(node)

    def _stormOperJoin(self, query, oper):

        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        if len(args) is 1:
            srcp, dstp = None, args[0]

        elif len(args) is 2:
            srcp, dstp = args[0], args[1]

        else:
            raise s_common.BadSyntaxError(mesg='join(<srcprop>,<dstprop>)')

        limit = opts.get('limit')
        if limit is not None and limit < 0:
            raise s_common.BadOperArg(oper='join', name='limit', mesg='must be >= 0')

        # do we have a relative source property?
        relsrc = srcp is not None and srcp.startswith(':')

        vals = set()
        tufs = query.data()

        if srcp is not None and not relsrc:

            for tufo in tufs:
                valu = tufo[1].get(srcp)
                if valu is not None:
                    vals.add(valu)

        elif not relsrc:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form)
                if valu is not None:
                    vals.add(valu)

        else:

            for tufo in tufs:
                form = tufo[1].get('tufo:form')
                valu = tufo[1].get(form + srcp)
                if valu is not None:
                    vals.add(valu)

        # do not use fancy by handlers for runt nodes...
        core = self.getStormCore()
        if core.isRuntProp(dstp):

            limt = self.getLiftLimitHelp(limit)
            for valu in vals:

                # the base "eq" handler is aware of runts...
                news = self.stormTufosBy('eq', dstp, valu, limit=limt.get())
                limt.dec(len(news))

                [query.add(n) for n in news]

                if limt.reached():
                    break

            return

        [query.add(t) for t in self.stormTufosBy('in', dstp, list(vals), limit=limit)]

    def _stormOperAddXref(self, query, oper):

        args = oper[1].get('args')
        if len(args) != 3:
            raise s_common.BadSyntaxError(mesg='addxref(<type>,<form>,<valu>)')

        xref, form, valu = args

        core = self.getStormCore()

        # TODO clearer error handling
        for node in query.take():
            sorc = node[1].get(node[1].get('tufo:form'))
            node = core.formTufoByProp(xref, (sorc, (form, valu)))
            query.add(node)

    def _stormOperRefs(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        #TODO opts.get('degrees')
        limt = self.getLiftLimitHelp(opts.get('limit'))

        core = self.getStormCore()

        nodes = query.data()

        #NOTE: we only actually want refs where type is form

        # Build a set of pv props so we can lift by form on 'in'
        pvprops = [prop for prop, pnfo in core.getPropsByType('propvalu')]

        done = set()
        if not args or 'in' in args:

            for node in nodes:

                if limt.reached():
                    break

                form = node[1].get('tufo:form')
                valu = node[1].get(form)

                dkey = (form, valu)
                if dkey in done:
                    continue

                done.add(dkey)

                # Check regular forms
                for prop, info in core.getPropsByType(form):

                    pkey = (prop, valu)
                    if pkey in done:
                        continue

                    done.add(pkey)

                    news = core.getTufosByProp(prop, valu=valu, limit=limt.get())

                    [query.add(n) for n in news]

                    if limt.dec(len(news)):
                        break

                # Check propvalu forms which may point to our current node.
                pv, _ = core.getTypeNorm('propvalu', [form, valu])
                for prop in pvprops:

                    pkey = (prop, pv)
                    if pkey in done:
                        continue

                    done.add(pkey)

                    news = core.getTufosByProp(prop, valu=pv, limit=limt.get())

                    [query.add(n) for n in news]

                    if limt.dec(len(news)):
                        break

        if not args or 'out' in args:

            for node in nodes:

                if limt.reached():
                    break

                form = node[1].get('tufo:form')
                for prop, info in core.getSubProps(form):

                    valu = node[1].get(prop)
                    if valu is None:
                        continue

                    # ensure that the prop's type is also a form
                    name = core.getPropTypeName(prop)
                    if not core.isTufoForm(name) and name != 'propvalu':
                        continue

                    pkey = (prop, valu)
                    if pkey in done:
                        continue

                    done.add(pkey)

                    if name == 'propvalu':
                        name, valu = valu.split('=', 1)

                    news = core.getTufosByProp(name, valu=valu, limit=limt.get())

                    [query.add(n) for n in news]

                    if limt.dec(len(news)):
                        break

    def _stormOperAddNode(self, query, oper):
        args = oper[1].get('args')
        if len(args) != 2:
            raise s_common.BadSyntaxError(mesg='addnode(<form>,<valu>,[:<prop>=<pval>, ...])')

        kwlist = oper[1].get('kwlist')

        core = self.getStormCore()

        props = {}
        for k, v in kwlist:

            if not k[0] == ':':
                raise s_common.BadSyntaxError(mesg='addnode() expects relative props with : prefix')

            prop = k[1:]
            props[prop] = v

        node = self.formTufoByProp(args[0], args[1], **props)

        # call set props if the node is not new...
        if not node[1].get('.new'):
            self.setTufoProps(node, **props)

        query.add(node)

    def _stormOperDelNode(self, query, oper):
        opts = dict(oper[1].get('kwlist'))

        core = self.getStormCore()

        force, _ = core.getTypeNorm('bool', opts.get('force', 0))

        nodes = query.take()
        if force:
            [core.delTufo(n) for n in nodes]
            return

        # TODO: users and perms
        # TODO: use edits here for requested delete

    def _getPropGtor(self, prop):

        # an optimized gtor factory to avoid startswith() over and over...
        if not prop.startswith(':'):

            def fullgtor(node):
                return prop, node[1].get(prop)

            return fullgtor

        def relgtor(node):
            full = node[1].get('tufo:form') + prop
            return full, node[1].get(full)

        return relgtor

    def _stormOperSetProp(self, query, oper):
        # Coverage of this function is affected by the following issue:
        # https://bitbucket.org/ned/coveragepy/issues/198/continue-marked-as-not-covered
        args = oper[1].get('args')
        props = dict(oper[1].get('kwlist'))

        core = self.getStormCore()

        formnodes = collections.defaultdict(list)
        formprops = collections.defaultdict(dict)

        for node in query.data():
            formnodes[node[1].get('tufo:form')].append(node)

        forms = tuple(formnodes.keys())

        for prop, valu in props.items():

            if prop.startswith(':'):
                valid = False
                _prop = prop[1:]
                # Check against every lifted form, since we may have a relative prop
                # Which is valid against
                for form in forms:
                    _fprop = form + prop
                    if core.isSetPropOk(_fprop, isadd=True):
                        formprops[form][_prop] = valu
                        valid = True
                if not valid:
                    mesg = 'Relative prop is not valid on any lifted forms.'
                    raise s_common.BadSyntaxError(name=prop, mesg=mesg)
                continue  # pragma: no cover

            mesg = 'setprop operator requires props to start with relative prop names.'
            raise s_common.BadSyntaxError(name=prop, mesg=mesg)

        for form, nodes in formnodes.items():
            props = formprops.get(form)
            if props:
                [core.setTufoProps(node, **props) for node in nodes]

    def _stormOperAllTag(self, query, oper):

        tags = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        core = self.getStormCore()

        limit = self.getLiftLimit(opts.get('limit'))

        for tag in tags:

            nodes = core.getTufosByTag(tag, limit=limit)

            [query.add(node) for node in nodes]

            if limit is not None:
                limit -= len(nodes)
                if limit <= 0:
                    break

    def _stormOperAddTag(self, query, oper):
        tags = oper[1].get('args')

        core = self.getStormCore()

        nodes = query.data()

        for tag in tags:
            [core.addTufoTag(node, tag) for node in nodes]

    def _stormOperDelTag(self, query, oper):
        tags = oper[1].get('args')

        core = self.getStormCore()

        nodes = query.data()

        for tag in tags:
            [core.delTufoTag(node, tag) for node in nodes]

    def _stormOperJoinTags(self, query, oper):

        args = oper[1].get('args', ())
        opts = dict(oper[1].get('kwlist'))
        core = self.getStormCore()

        forms = set(args)
        keep_nodes = opts.get('keep_nodes', False)

        limt = self.getLiftLimitHelp(opts.get('limit'))

        nodes = query.data()
        if not keep_nodes:
            query.clear()

        tags = {tag for node in nodes for tag in s_tufo.tags(node, leaf=True)}

        if not forms:

            for tag in tags:

                nodes = core.getTufosByTag(tag, limit=limt.get())

                limt.dec(len(nodes))
                [query.add(n) for n in nodes]

                if limt.reached():
                    break

            return

        for form in forms:

            if limt.reached():
                break

            for tag in tags:

                nodes = core.getTufosByTag(tag, form=form, limit=limt.get())

                limt.dec(len(nodes))
                [query.add(n) for n in nodes]

                if limt.reached():
                    break

    def _stormOperToTags(self, query, oper):
        opts = dict(oper[1].get('kwlist'))
        nodes = query.take()
        core = self.getStormCore()

        leaf = opts.get('leaf', True)
        limt = opts.get('limit', 0)
        if limt < 0:
            raise s_common.BadOperArg(oper='totags', name='limit', mesg='limit must be >= 0')

        tags = list({tag for node in nodes for tag in s_tufo.tags(node, leaf=leaf)})
        if limt > 0:
            tags = tags[0:limt]

        [query.add(tufo) for tufo in core.getTufosBy('in', 'syn:tag', tags)]

    def getLiftLimitHelp(self, *limits):
        '''
        Return a LimitHelp object for the specified limits or defaults.

        Args:
            limits (list):  A list of int/None limits

        Returns:
            (LimitHelp)

        '''
        limit = self.getLiftLimit(*limits)
        return LimitHelp(limit)

    def _stormOperFromTags(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        nodes = query.take()

        forms = {arg for arg in args}

        limt = self.getLiftLimitHelp(opts.get('limit'))

        tags = {node[1].get('syn:tag') for node in nodes if node[1].get('tufo:form') == 'syn:tag'}

        core = self.getStormCore()

        if not forms:

            for tag in tags:

                nodes = core.getTufosByTag(tag, limit=limt.get())
                limt.dec(len(nodes))

                [query.add(n) for n in nodes]

                if limt.reached():
                    break

            return

        for form in forms:

            if limt.reached():
                break

            for tag in tags:

                if limt.reached():
                    break

                nodes = core.getTufosByTag(tag, form=form, limit=limt.get())

                limt.dec(len(nodes))
                [query.add(n) for n in nodes]

        return

    def _stormOperGuid(self, query, oper):
        args = oper[1].get('args')
        core = self.getStormCore()

        [query.add(node) for node in core.getTufosByIdens(args)]

    def _stormOperTask(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        if not args:
            mesg = 'task(<taskname1>, <taskname2>, ..., [kwarg1=val1, ...])'
            raise s_common.BadSyntaxError(mesg=mesg)

        nodes = query.data()
        core = self.getStormCore()

        for tname in args:
            evt = ':'.join(['task', tname])
            core.fire(evt, nodes=nodes, storm=True, **opts)

    def _stormOperGetTasks(self, query, oper):

        core = self.getStormCore()
        tasks = core.getCoreTasks()

        for task in tasks:
            node = s_tufo.ephem('task', task)
            query.add(node)

    def _stormOperTree(self, query, oper):

        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        if not args:
            raise s_common.BadSyntaxError(mesg='tree([<srcprop>], <destprop>, [recurlim=<limit>])')

        core = self.getStormCore()

        # Prevent infinite pivots
        try:
            recurlim, _ = core.getTypeNorm('int', opts.get('recurlim', 20))
        except s_common.BadTypeValu as e:
            raise s_common.BadOperArg(oper='tree', name='recurlim', mesg=e.errinfo.get('mesg'))

        if recurlim < 0:
            raise s_common.BadOperArg(oper='tree', name='recurlim', mesg='must be >= 0')

        srcp = None
        dstp = args[0]

        if len(args) > 1:
            srcp = args[0]
            dstp = args[1]

        # do we have a relative source property?
        relsrc = srcp is not None and srcp.startswith(':')

        tufs = query.data()

        queried_vals = set()

        while True:

            vals = set()

            if srcp is not None and not relsrc:

                for tufo in tufs:
                    valu = tufo[1].get(srcp)
                    if valu is not None:
                        vals.add(valu)

            elif not relsrc:

                for tufo in tufs:
                    form, valu = s_tufo.ndef(tufo)
                    if valu is not None:
                        vals.add(valu)

            else:
                for tufo in tufs:
                    form, _ = s_tufo.ndef(tufo)
                    valu = tufo[1].get(form + srcp)
                    if valu is not None:
                        vals.add(valu)

            qvals = list(vals - queried_vals)
            if not qvals:
                break

            [query.add(t) for t in self.stormTufosBy('in', dstp, qvals, limit=opts.get('limit'))]

            queried_vals = queried_vals.union(vals)

            if recurlim > 0:
                recurlim -= 1
                if recurlim < 1:
                    break

            tufs = query.data()

    def _stormOperDelProp(self, query, oper):
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        core = self.getStormCore()

        if not args:
            raise s_common.BadSyntaxError(mesg='delprop(<prop>, [force=1]>')

        prop = args[0]

        if prop[0] != ':':
            raise s_common.BadSyntaxError(mesg='delprop(<prop>, [force=1]>')

        prop = prop.lstrip(':')
        if not prop:
            raise s_common.BadSyntaxError(mesg='delprop(<prop>, [force=1]>')

        force, _ = core.getTypeNorm('bool', opts.get('force', 0))

        if not force:
            return

        nodes = query.take()
        [query.add(core.delTufoProp(n, prop)) for n in nodes]
