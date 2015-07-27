import ast
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
import synapse.telepath as s_telepath

import synapse.cores.ram
import synapse.cores.sqlite
import synapse.cores.postgres

class NoSuchScheme(Exception):pass

corclasses = {
    'tcp':s_telepath.Proxy,

    'ram':synapse.cores.ram.Cortex,
    'sqlite':synapse.cores.sqlite.Cortex,
    'postgres':synapse.cores.postgres.Cortex,
}

def openurl(url):
    '''
    Construct or reference a cortex by url.

    Example:

        core = getCortex('ram://')

    Notes:
        * ram://
        * sqlite3:///<db>[?table=<table>]
        * postgres://[[<passwd>:]<user>@][<host>]/[<db>][?table=<table>]

        * default table name: syncortex

    Todo:
          auditfd=<fd>
          auditfile=<filename>

    '''
    link = s_link.chopLinkUrl(url)
    return openlink(link)

def openlink(link):
    '''
    Open a cortex via a link tuple.
    '''
    cls = corclasses.get(link[0])
    if cls == None:
        raise NoSuchScheme(link[0])
    return cls(link)

def choptag(tag):
    '''
    Chop a tag into hierarchal levels.
    '''
    parts = tag.split('.')
    return [ '.'.join(parts[:x+1]) for x in range(len(parts)) ]

class MetaCortex:

    def __init__(self):
        self.tagsbyname = {}
        self.coresbyname = {}

        self.coresbytag = collections.defaultdict(list)

    def addCortex(self, name, url, tags=None):
        '''
        Tell the MetaCortex about a Cortex instance.

        Example:

            meta.addCortex('woot0','ram:///',tags=('woot.bar',))

        '''
        if self.coresbyname.get(name) != None:
            raise Exception('Coretex Exists: %s' % (name,))

        core = openurl(url)
        self.coresbyname[name] = core

        alltags = set()

        [ alltags.add(t) for t in choptag(name) ]

        if tags != None:
            for tag in tags:
                [ alltags.add(t) for t in choptag(tag) ]

        self.tagsbyname[name] = alltags

        for tag in alltags:
            self.coresbytag[tag].append(core)

        return core

    def delCortex(self, name):
        '''
        Remove a given cortex instance by name.

        Example:

            meta.delCortex('woot0')

        '''
        core = self.coresbyname.get(name)
        if core == None:
            raise Exception('No Such Cortex: %s' % (name,))

        tags = self.tagsbyname.pop(name,())
        for tag in tags:
            self.coresbytag[tag].remove( core )

        return

    def getCortex(self, name):
        '''
        Return a single Cortex by name ( or None ).

        Example:

            core = meta.getCortex('woot0')
            if core != None:
                stuff(core)

        '''
        return self.coresbyname.get(name)

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
        qinfo = self._parseQuery(query)

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')

        cores = self.coresbytag.get(tag)
        if cores == None:
            return ()

        rows = []
        for core in cores:
            if by != None:
                rows.extend( core.getRowsBy(by,prop,valu,limit=limit) )
                continue

            if prop == 'id':
                rows.extend( core.getRowsById(valu) )
                continue

            rows.extend( core.getRowsByProp(prop,**qinfo) )

        return rows

    def getJoinByQuery(self, query):
        qinfo = self._parseQuery(query)

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')

        cores = self.coresbytag.get(tag)
        if cores == None:
            return []

        rows = []
        for core in cores:
            if by != None:
                rows.extend( core.getJoinBy(by,prop,valu,limit=limit) )
                continue

            if prop == 'id':
                rows.extend( core.getJoinById(valu) )
                continue

            rows.extend( core.getJoinByProp(prop,**qinfo) )

        return rows

    def getSizeByQuery(self, query):
        qinfo = self._parseQuery(query)

        by = qinfo.pop('by',None)
        tag = qinfo.pop('tag',None)
        prop = qinfo.pop('prop',None)

        valu = qinfo.get('valu')
        limit = qinfo.get('limit')

        cores = self.coresbytag.get(tag)
        if cores == None:
            return ()

        size = 0
        for core in cores:
            if by != None:
                size += core.getSizeBy(by,prop,valu,limit=limit)
                continue

            if prop == 'id':
                size += core.getSizeById(valu)
                continue

            size += core.getJoinByProp(prop,**qinfo)

        return size
