import os
import ast
import logging
import traceback
import collections

'''
A synapse cortex is a data storage and indexing abstraction
which is designed to be used as a prop/valu index on various
storage backings.

Most fundamentally, a cortex instance contains rows of:
<id> | <prop> | <valu> | <time>

and is expected to provide indexed access to rows, allow bulk
insertion, and provide for atomic deconfliction if needed.

'''

import synapse.link as s_link
import synapse.async as s_async
import synapse.lib.sched as s_sched

import synapse.cores.ram
import synapse.cores.sqlite
import synapse.cores.postgres

from synapse.eventbus import EventBus

class NoSuchName(Exception):pass
class PermDenied(Exception):pass
class NoSuchScheme(Exception):pass
class DupCortexName(Exception):pass

logger = logging.getLogger(__name__)

class InvalidParam(Exception):
    def __init__(self, name, msg):
        Exception.__init__(self, '%s invalid: %s' % (name,msg))
        self.param = name

corctors = {
    'ram':synapse.cores.ram.initRamCortex,
    'sqlite':synapse.cores.sqlite.Cortex,
    'postgres':synapse.cores.postgres.Cortex,
}

def openurl(url, **opts):
    '''
    Construct or reference a cortex by url.

    Example:

        core = openurl('ram://')

    Notes:
        * ram://
        * sqlite3:///<db>
        * postgres://[[<passwd>:]<user>@][<host>]/[<db>][/<table>]

        * default table name: syncortex

    Todo:
          auditfd=<fd>
          auditfile=<filename>

    '''
    link = s_link.chopLinkUrl(url)

    link[1].update(opts)
    return openlink(link)

def openlink(link):
    '''
    Open a cortex via a link tuple.
    '''
    ctor = corctors.get(link[0])
    if ctor == None:
        raise NoSuchScheme(link[0])

    core = ctor(link)

    savefd = link[1].get('savefd')
    if savefd != None:
        core.setSaveFd(savefd)

    savefile = link[1].get('savefile')
    if savefile != None:
        if not os.path.isfile(savefile):
            dir = os.path.dirname(savefile)
            if dir is not None and dir not in ['', '.', '..']:
                # Create directory if it doesn't exist.
                os.makedirs(dir, exist_ok=True)
            savefd = open(savefile,'w+b')
        else:
            savefd = open(savefile,'r+b')
        core.setSaveFd(savefd,fini=True)

    return core

def choptag(tag):
    '''
    Chop a tag into hierarchal levels.
    '''
    parts = tag.split('.')
    return [ '.'.join(parts[:x+1]) for x in range(len(parts)) ]

def join2tufo(rows):
    byid = collections.defaultdict(dict)
    [ byid[r[0]].__setitem__( r[1], r[2] ) for r in rows ]
    return list(byid.items())

class MetaCortex(EventBus):

    '''
    A MetaCortex provides a unified data view of multiple cortexes.
    '''

    def __init__(self):
        EventBus.__init__(self)

        self.coreok = {}
        self.cordefs = {}
        self.tagsbyname = {}
        self.coresbyname = {}

        self.sched = s_sched.Sched()
        self.coresbytag = collections.defaultdict(list)

        self.onfini( self._onMetaFini )

    def _corNotOk(self, name):
        '''
        Record that a core is not ok, and begin monitoring
        for okness.
        '''
        self.coreok[name] = False
        self.fire('meta:cortex:notok',name=name)
        self.sched.insec(2, self._tryCoreOk, name)

    def _tryCoreOk(self, name):
        '''
        Test if a currently "down" core is available again.

        ( If the core has been removed, bail )
        '''
        if self.coreok.get(name):
            return

        core = self.coresbyname.get(name)
        if core == None:
            self.coreok[name] = False

        else:

            try:
                self.coreok[name] = core.isOk()

            except Exception as e:
                self.coreok[name] = False

        if not self.coreok.get(name):
            self.sched.insec(2, self._tryCoreOk, name)
        else:
            self.fire('meta:cortex:ok',name=name)

    def addLocalCore(self, name, core, tags=()):

        self.coreok[name] = True
        self.coresbyname[name] = core

        alltags = set()

        [ alltags.add(t) for t in choptag(name) ]

        for tag in tags:
            [ alltags.add(t) for t in choptag(tag) ]

        self.tagsbyname[name] = alltags

        for tag in alltags:
            self.coresbytag[tag].append((name,core))

        self._tryCoreOk(name)
        return core

    #def addCortex(self, name, url, tags=()):
        #'''
        #Tell the MetaCortex about a Cortex instance.

        #Example:

            #meta.addCortex('woot0','ram:///',tags=('woot.bar',))

        #'''
        #if self.coresbyname.get(name) != None:
            #raise DupCortexName(name)

        #if not s_compat.isstr(name):
            #raise InvalidParam('name','must be a string!')

        #event = self.fire('meta:cortex:add',name=name,url=url,tags=tags)
        #if not event[1].get('allow',True):
            #raise PermDenied()
##
        #self.cordefs[name] = (name,url,tags)
        #return self._tryAddCorUrl(name, url, tags=tags)
#
    #def delCortex(self, name):
        #'''
        #Remove a given cortex instance by name.

        #Example:

            #meta.delCortex('woot0')

        #'''
        #core = self.coresbyname.pop(name,None)
        #if core == None:
            #raise NoSuchName(name)

        #tags = self.tagsbyname.pop(name,())
        #for tag in tags:
            #self.coresbytag[tag].remove( (name,core) )

        #core.fini()
        #return

    def getCortex(self, name):
        '''
        Return a single Cortex by name ( or None ).

        Example:

            core = meta.getCortex('woot0')
            if core != None:
                stuff(core)

        '''
        return self.coresbyname.get(name)

    def getCortexNames(self):
        '''
        Retrieve a list of cortex names within this metacortex.

        Example:

            names = meta.getCortexNames()

        '''
        return list(self.coresbyname.keys())

    def getCortexes(self, tag):
        '''
        Return a list of cortex instances by tag.

        Example:

            for core in meta.getCortexes('foo.bar'):
                stuff(core)

        '''
        return self.coresbytag.get(tag,())

    def _parseQuery(self, query):
        '''
        Return a parsed dictionary of query info.

        <tag>:<prop>@<mintime>,<maxtime>#<limit>*<by> = <literal>

        '''
        ret = {}
        parts = query.split('=',1)
        if len(parts) == 2:
            ret['valu'] = ast.literal_eval(parts[1])

        parts = parts[0].split('*',1)
        if len(parts) == 2:
            ret['by'] = parts[1]

        parts = parts[0].split('#',1)
        if len(parts) == 2:
            ret['limit'] = int(parts[1],0)

        parts = parts[0].split('@',1)
        if len(parts) == 2:
            timeparts = parts[1].split(',')

        tag,prop = parts[0].split(':',1)

        ret['tag'] = tag.lower()
        ret['prop'] = prop.lower()

        return ret

    def getRowsByQuery(self, query):
        '''
        Retrieve rows using a cortex query.

        Example:

            rows = meta.getRowsByQuery('foo:bar=10')

        '''
        qinfo = self._parseQuery(query)
        event = self.fire('meta:query:rows',query=qinfo)

        if not event[1].get('allow',True):
            return ()

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')
        mintime = qinfo.get('mintime')
        maxtime = qinfo.get('maxtime')

        jobs = []
        for name,core in self._iterCoresByTag(tag):

            try:

                if by != None:
                    job = core.call('getRowsBy',by,prop,valu,limit=limit)
                    jobs.append( (name,core,job) )
                    continue

                if prop == 'id':
                    job = core.call('getRowsById',valu)
                    jobs.append( (name,core,job) )
                    continue

                job = core.call('getRowsByProp',prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit)
                jobs.append( (name,core,job) )

            except Exception as e:
                self._corNotOk(name)
                self.fire('meta:cortex:exc', name=name, exc=e)

        rows = []
        for name,core,job in jobs:
            try:
                rows.extend( core.sync(job) )
            except Exception as e:
                self._corNotOk(name)
                self.fire('meta:cortex:exc', name=name, exc=e)

        return rows

    def getJoinByQuery(self, query):
        '''
        Retrieve a set of rows by cortex query and subsequent join.

        Example:

            rows = meta.getJoinByQuery('foo:bar=10')

        '''
        qinfo = self._parseQuery(query)
        event = self.fire('meta:query:join',query=qinfo)
        if not event[1].get('allow',True):
            return ()

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')
        mintime = qinfo.get('mintime')
        maxtime = qinfo.get('maxtime')

        jobs = []
        for name,core in self._iterCoresByTag(tag):

            try:

                if by != None:
                    job = core.call('getJoinBy',by,prop,valu,limit=limit)
                    jobs.append( (name,core,job) )
                    continue

                if prop == 'id':
                    job = core.call('getJoinById',valu)
                    jobs.append( (name,core,job) )
                    continue

                job = core.call('getJoinByProp',prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit)
                jobs.append( (name,core,job) )

            except Exception as e:
                self._corNotOk(name)
                logger.warning('getJoinByQuery@async (%s): %s', name, e)

        rows = []
        for name,core,job in jobs:
            try:
                rows.extend( core.sync(job) )
            except Exception as e:
                self._corNotOk(name)
                logger.warning('getJoinByQuery@resync (%s): %s', name, e)

        return rows

    def _iterCoresByTag(self, tag):
        '''
        Iterate name,core tuples which are "ok".
        '''
        cores = self.coresbytag.get(tag)
        if cores == None:
            return

        for name,core in cores:
            if not self.coreok.get(name):
                continue

            yield name,core

    def getSizeByQuery(self, query):
        '''
        Retrieve the number of rows which match a given cortex query.

        Example:

            count = meta.getSizeByQuery('foo:bar=10')

        '''
        qinfo = self._parseQuery(query)
        event = self.fire('meta:query:size',query=qinfo)

        if not event[1].get('allow',True):
            return 0

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')
        mintime = qinfo.get('mintime')
        maxtime = qinfo.get('maxtime')

        jobs = []
        for name,core in self._iterCoresByTag(tag):

            try:

                if by != None:
                    job = core.call('getSizeBy',by,prop,valu,limit=limit)
                    jobs.append( (name,core,job) )
                    continue

                if prop == 'id':
                    job = core.call('getSizeById',valu)
                    jobs.append( (name,core,job) )
                    continue

                job = core.call('getSizeByProp',prop,valu=valu,mintime=mintime,maxtime=maxtime)
                jobs.append( (name,core,job) )

            except Exception as e:
                self._corNotOk(name)
                traceback.print_exc()
                self.fire('meta:cortex:exc', name=name, exc=e)

        size = 0
        for name,core,job in jobs:
            try:
                size += core.sync(job)
            except Exception as e:
                self._corNotOk(name)
                traceback.print_exc()
                self.fire('meta:cortex:exc', name=name, exc=e)

        return size

    def getTufosByQuery(self, query):
        '''
        Retrieve a folded set of (ident,info) tuples via join.

        Example:

            tufos = meta.getSizeByQuery('foo:bar=10')

            for tufo in tufos:
                print( tufo[1].get('baz') )

        '''
        rows = self.getJoinByQuery(query)
        return join2tufo(rows)

    def addMetaRows(self, name, rows):
        '''
        Add the given rows to the specified cortex by name.

        Example:

            meta.addMetaRows('woot',rows)

        '''
        event = self.fire('meta:rows:add',name=name,rows=rows)
        if not event[1].get('allow',True):
            raise PermDenied()

        core = self.coresbyname.get(name)
        if core == None:
            raise NoSuchName(name)

        return core.addRows(rows)

    def callCorApi(self, name, api, *args, **kwargs):
        '''
        Use the MetaCortex to call an API on the named Cortex.

        Example:

            rows = meta.callCorApi('woot','getRowsByProp','hehe',valu=10)

        '''
        event = self.fire('meta:call',name=name,api=api,args=args,kwargs=kwargs)
        if not event[1].get('allow',True):
            raise PermDenied()

        core = self.coresbyname.get(name)
        if core == None:
            raise NoSuchName(name)

        # purposely blow up if getattr fails...
        return getattr(core,api)(*args,**kwargs)

    def _onMetaFini(self):
        [ c.fini() for c in self.coresbyname.values() ]
