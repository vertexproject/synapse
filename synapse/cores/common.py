import json
import time
import logging
import itertools
import threading
import traceback
import collections

from synapse.compat import queue

import synapse.async as s_async
import synapse.compat as s_compat
import synapse.reactor as s_reactor
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.dark as s_dark
import synapse.lib.tags as s_tags
import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue
import synapse.lib.types as s_types
import synapse.lib.ingest as s_ingest
import synapse.lib.hashset as s_hashset
import synapse.lib.threads as s_threads
import synapse.lib.modules as s_modules
import synapse.lib.hashitem as s_hashitem
import synapse.lib.userauth as s_userauth

from synapse.common import *
from synapse.eventbus import EventBus
from synapse.lib.storm import Runtime
from synapse.datamodel import DataModel
from synapse.lib.config import Configable

logger = logging.getLogger(__name__)

def chunked(n, iterable):
    it = iter(iterable)
    while True:
       chunk = tuple(itertools.islice(it, n))
       if not chunk:
           return

       yield chunk

def reqiden(tufo):
    '''
    Raise an exception if the given tufo is ephemeral.
    '''
    if tufo[0] == None:
        raise NoSuchTufo(iden=None)
    return tufo[0]

def reqstor(name,valu):
    '''
    Raise BadPropValue if valu is not cortex storable.
    '''
    if not s_compat.canstor(valu):
        raise BadPropValu(name=name,valu=valu)
    return valu

class CortexMixin:

    def __init__(self):
        pass

    def formNodeByBytes(self, byts, stor=True, **props):
        '''
        Form a new file:bytes node by passing bytes and optional props.

        If stor=False is specified, the cortex will create the file:bytes
        node even if it is not configured with access to an axon to store
        the bytes.

        Example:

            core.formNodeByBytes(byts,name='foo.exe')

        '''

        hset = s_hashset.HashSet()
        hset.update(byts)

        iden,info = hset.guid()

        props.update(info)

        if stor:

            size = props.get('size')
            upid = self._getAxonWants('guid',iden,size)

            if upid != None:
                for chun in chunks(byts,10000000):
                    self._addAxonChunk(upid,chun)

        return self.formTufoByProp('file:bytes', iden, **props)

    def formNodeByFd(self, fd, stor=True, **props):
        '''
        Form a new file:bytes node by passing a file object and optional props.
        '''
        hset = s_hashset.HashSet()
        iden,info = hset.eatfd(fd)

        props.update(info)


        if stor:

            size = props.get('size')
            upid = self._getAxonWants('guid',iden,size)

            # time to send it!
            if upid != None:
                for byts in iterfd(fd):
                    self._addAxonChunk(upid,byts)

        node = self.formTufoByProp('file:bytes', iden, **props)

        if node[1].get('file:bytes:size') == None:
            self.setTufoProp(node,'size',info.get('size'))

        return node

class Cortex(EventBus,DataModel,Runtime,Configable,CortexMixin,s_ingest.IngestApi):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link, **conf):
        Runtime.__init__(self)
        EventBus.__init__(self)
        CortexMixin.__init__(self)
        Configable.__init__(self)

        # a cortex may have a ref to an axon
        self.axon = None
        self.seedctors = {}

        self.noauto = {'syn:form','syn:type','syn:prop'}
        self.addConfDef('autoadd',type='bool',asloc='autoadd',defval=1,doc='Automatically add forms for props where type is form')
        self.addConfDef('enforce',type='bool',asloc='enforce',defval=0,doc='Enables data model enforcement')
        self.addConfDef('caching',type='bool',asloc='caching',defval=0,doc='Enables caching layer in the cortex')
        self.addConfDef('cache:maxsize',type='int',asloc='cache_maxsize',defval=1000,doc='Enables caching layer in the cortex')

        self.addConfDef('axon:url',type='str',doc='Allows cortex to be aware of an axon blob store')

        self.addConfDef('log:save',type='bool',asloc='logsave', defval=0, doc='Enables saving exceptions to the cortex as syn:log nodes')
        self.addConfDef('log:level',type='int',asloc='loglevel',defval=0,doc='Filters log events to >= level')

        self.onConfOptSet('caching', self._onSetCaching)
        self.onConfOptSet('axon:url', self._onSetAxonUrl)

        self.setConfOpts(conf)

        self._link = link

        self.lock = threading.Lock()
        self.inclock = threading.Lock()
        self.xlock = threading.Lock()

        self._core_xacts = {}

        self.statfuncs = {}

        self.auth = None
        self.snaps = s_cache.Cache(maxtime=60)

        self.seqs = s_cache.KeyCache(self.getSeqNode)

        self.formed = collections.defaultdict(int)      # count tufos formed since startup

        self._core_tags = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tag') )
        self._core_tagforms = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tagform') )

        self.sizebymeths = {}
        self.rowsbymeths = {}
        self.tufosbymeths = {}

        self.cache_fifo = collections.deque()               # [ ((prop,valu,limt), {
        self.cache_bykey = {}                               # (prop,valu,limt):( (prop,valu,limt), {iden:tufo,...} )
        self.cache_byiden = s_cache.RefDict()
        self.cache_byprop = collections.defaultdict(dict)   # (<prop>,<valu>):[ ((prop, valu, limt),  answ), ... ]

        #############################################################
        # buses to save/load *raw* save events
        #############################################################
        self.savebus = EventBus()
        self.loadbus = EventBus()

        self.loadbus.on('core:save:add:rows', self._loadAddRows)
        self.loadbus.on('core:save:del:rows:by:iden', self._loadDelRowsById)
        self.loadbus.on('core:save:del:rows:by:prop', self._loadDelRowsByProp)
        self.loadbus.on('core:save:set:rows:by:idprop', self._loadSetRowsByIdProp)
        self.loadbus.on('core:save:del:rows:by:idprop', self._loadDelRowsByIdProp)

        #############################################################
        # Handlers for each splice event action
        self.spliceact = s_reactor.Reactor()
        self.spliceact.act('node:add', self._actNodeAdd )
        self.spliceact.act('node:del', self._actNodeDel )
        self.spliceact.act('node:set', self._actNodeSet )
        self.spliceact.act('node:tag:add', self._actNodeTagAdd )
        self.spliceact.act('node:tag:del', self._actNodeTagDel )

        #############################################################

        self.onfini( self.savebus.fini )
        self.onfini( self.loadbus.fini )

        self.addStatFunc('any',self._calcStatAny)
        self.addStatFunc('all',self._calcStatAll)
        self.addStatFunc('min',self._calcStatMin)
        self.addStatFunc('max',self._calcStatMax)
        self.addStatFunc('sum',self._calcStatSum)
        self.addStatFunc('mean',self._calcStatMean)
        self.addStatFunc('count',self._calcStatCount)
        self.addStatFunc('histo',self._calcStatHisto)

        self._initCortex()

        DataModel.__init__(self,load=False)

        self.on('tufo:add:syn:tag', self._onAddSynTag)
        self.on('tufo:del:syn:tag', self._onDelSynTag)
        self.on('tufo:form:syn:tag', self._onFormSynTag)

        self.isok = True

        self.initTufosBy('eq',self._tufosByEq)
        self.initTufosBy('in',self._tufosByIn)
        self.initTufosBy('has',self._tufosByHas)
        self.initTufosBy('tag',self._tufosByTag)
        self.initTufosBy('type',self._tufosByType)
        self.initTufosBy('inet:cidr',self._tufosByInetCidr)
        self.initTufosBy('dark', self._tufosByDark)

        # process a savefile/savefd if we have one
        savefd = link[1].get('savefd')
        if savefd != None:
            self.setSaveFd(savefd)

        savefile = link[1].get('savefile')
        if savefile != None:
            savefd = genfile(savefile)
            self.setSaveFd(savefd,fini=True)

        self.myfo = self.formTufoByProp('syn:core','self')

        with self.getCoreXact() as xact:
            self._initCoreModels()

        # and finally, strap in our event handlers...
        self.on('tufo:add:syn:type', self._onTufoAddSynType )
        self.on('tufo:add:syn:form', self._onTufoAddSynForm )
        self.on('tufo:add:syn:prop', self._onTufoAddSynProp )

        self.addTufoForm('syn:log', ptype='guid', local=1)
        self.addTufoProp('syn:log', 'subsys', defval='??', help='Named subsystem which originated the log event')
        self.addTufoProp('syn:log', 'level', ptype='int', defval=logging.WARNING)
        self.addTufoProp('syn:log', 'time', ptype='time', doc='When did the log event occur')
        self.addTufoProp('syn:log', 'exc', ptype='str', help='Exception class name if caused by an exception')
        self.addTufoProp('syn:log', 'info:*', glob=1)

        self.addTufoForm('syn:ingest', ptype='str:lwr', local=1)
        self.addTufoProp('syn:ingest', 'time', ptype='time')
        self.addTufoProp('syn:ingest', 'text', ptype='json')

        # storm operators specific to the cortex
        self.setOperFunc('stat', self._stormOperStat)
        self.setOperFunc('dset', self._stormOperDset)

        # allow modules a shot at hooking cortex events for model ctors
        for name,ret,exc in s_modules.call('addCoreOns',self):
            if exc != None:
                logger.warning('%s.addCoreOns: %s' % (name,exc))

        s_ingest.IngestApi.__init__(self, self)

    def _getFormFunc(self, name):
        # easy way to construct a single argument node constructor
        # ( used for constructing onmiss cache callbacks )
        def func(valu, **props):
            return self.formTufoByProp(name, valu, **props)
        return func

    # over-ride to allow the storm runtime to lift/join/pivot tufos
    def _stormTufosBy(self, by, prop, valu=None, limit=None):
        return self.getTufosBy(by, prop, valu=valu, limit=limit)

    def _getStormCore(self, name=None):
        return self

    def _getAxonWants(self, htype, hvalu, size):
        if self.axon == None:
            raise NoSuchOpt(name='axon:url',mesg='The cortex does not have an axon configured')
        return self.axon.wants(htype,hvalu,size)

    def _addAxonChunk(self, iden, byts):
        if self.axon == None:
            raise NoSuchOpt(name='axon:url',mesg='The cortex does not have an axon configured')
        return self.axon.chunk(iden,byts)

    def getSeqNode(self, name):
        '''
        API helper/wrapper to form a syn:seq sequential id tracker
        '''
        return self.getTufoByProp('syn:seq', name)

    def nextSeqValu(self, name):
        '''
        Return the next sequence identifier for the given name.

        Example:

            name = core.nextSeqValu('foo')
            # name is now foo0 or fooN from sequence

        '''
        node = self.seqs.get(name)
        if node == None:
            raise NoSuchSeq(name=name)

        #FIXME perms

        wid = node[1].get('syn:seq:width')
        valu = node[1].get('syn:seq:nextvalu')

        self._incTufoProp(node,'syn:seq:nextvalu')

        return name + str(valu).rjust(wid,'0')

    def addSeedCtor(self, name, func):
        '''
        Add a "seed constructor" to the cortex.  This allows modules
        to register functions to construct nodes by a "seed name" which
        they transform into an existing node from the model.

        Example:

            def seedOrgName(name, valu, **props):
                orgn = core.getTufoByProp('org:iden:name',valu)
                if orgn == None:
                    orgn = core.formTufoByProp('org:iden',guid(),name=valu)
                return orgn

            core.addSeedCtor('org:iden:name', seedOrgName)

            core.formTufoByProp('org:iden:name','The Vertex Project, LLC')
        '''
        self.seedctors[name] = func

    def logCoreExc(self, exc, subsys='??', level=logging.ERROR):
        '''
        Report an exception to/within the cortex.  This unified API is
        used to facilitate optional cortex exception logging within the
        cortex itself.

        Example:

            try:

                dostuff()

            except Exception as e:

                core.logCoreExc(e,subsys='mything')

        '''
        # TODO make an object to wrap a cortex as a logger to allow
        # cortex based log aggrigation
        if not self.logsave:
            return

        if level < self.loglevel:
            return

        logger.exception(exc)

        name = '%s.%s' % (exc.__class__.__module__,exc.__class__.__name__)
        props = {'exc':name,'time':now(),'level':level,'subsys':subsys}

        if isinstance(exc,SynErr):
            [ props.__setitem__('info:%s' % k, v) for (k,v) in exc.items() ]

        self.addTufoEvent('syn:log', **props)

    def addDataModel(self, name, modl):
        '''
        Store all types/forms/props from the given data model in the cortex.

        Example:

            core.addDataModel('synapse.models.foo',
                              {
                                'prefix':'foo',

                                'types':( ('foo:g',{'subof':'guid'}), ),

                                'forms':(
                                    ('foo:f',{'ptype':'foo:g','doc':'a foo'},[
                                        ('a',{'ptype':'str:lwr'}),
                                        ('b',{'ptype':'int'}),
                                    ]),
                                ),
                              })
        '''
        tufo = self.formTufoByProp('syn:model',name)

        # use the normalized hash of the model dict to short
        # circuit loading if it is unchanged.
        mhas = s_hashitem.hashitem(modl)
        if tufo[1].get('syn:model:hash') == mhas:
            return

        # FIXME handle type/form/prop removal
        for name,tnfo in modl.get('types',()):

            tufo = self.formTufoByProp('syn:type',name,**tnfo)
            tufo = self.setTufoProps(tufo,**tnfo)

        for form,fnfo,props in modl.get('forms',()):

            # allow forms declared without ptype if their name *is* one
            if fnfo.get('ptype') == None:
                fnfo['ptype'] = form

            tufo = self.formTufoByProp('syn:form',form,**fnfo)
            tufo = self.setTufoProps(tufo,**fnfo)

            for prop,pnfo in props:
                fullprop = '%s:%s' % (form,prop)
                tufo = self.formTufoByProp('syn:prop',fullprop,form=form,**pnfo)
                tufo = self.setTufoProps(tufo,**pnfo)

    def addDataModels(self, modtups):
        [ self.addDataModel(name,modl) for (name,modl) in modtups ]

    def _initCoreModels(self):

        for name,modl,exc in s_modules.call('getDataModel'):

            if exc != None:
                logger.warning('%s.getDataModel(): %s' % (name,exc))
                continue

            self.addDataModel(name,modl)

        # now we lift/initialize from the tufos...
        for tufo in self.getTufosByProp('syn:type'):
            self._initTypeTufo(tufo)

        for tufo in self.getTufosByProp('syn:form'):
            self._initFormTufo(tufo)

        for tufo in self.getTufosByProp('syn:prop'):
            self._initPropTufo(tufo)

    def _getTufosByCache(self, prop, valu, limit):
        # only used if self.caching = 1
        ckey = (prop,valu,limit) # cache key

        # check for this exact query...
        # ( (prop,valu,limit), answ )
        answ = self.cache_bykey.get(ckey)
        if answ != None:
            return list(answ.values())

        # check for same prop
        pkey = (prop,valu)

        for hkey in tuple(self.cache_byprop.get(pkey,())):

            hprop,hvalu,hlimit = hkey
            # if there's a hit that's either bigger than us *or* unlimited, use it
            if hlimit == None or ( limit != None and limit < hlimit ):
                answ = self.cache_bykey.get(hkey)
                return list(answ.values())[:limit]

        # no match found in the cache
        tufos = self._getTufosByProp(prop, valu=valu, limit=limit)

        self._addCacheKey(ckey,tufos)
        return tufos

    def _addCacheKey(self, ckey, tufos):
        # only one instance of any given tufo in the cache
        tufos = self.cache_byiden.puts( [ (t[0],t) for t in tufos ] )

        self.cache_fifo.append(ckey)
        self.cache_bykey[ckey] = { t[0]:t for t in tufos }
        self.cache_byprop[(ckey[0],ckey[1])][ckey] = True

        while len(self.cache_fifo) > self.cache_maxsize:
            oldk = self.cache_fifo.popleft()
            self._delCacheKey(oldk)

        return tufos

    def _delCacheKey(self, ckey):

        # delete a tufo cache entry
        answ = self.cache_bykey.pop(ckey,None)

        # decref our cached tuples
        if answ != None:
            [ self.cache_byiden.pop(t[0]) for t in answ.values() ]

        pkey = (ckey[0],ckey[1])
        phits = self.cache_byprop.get(pkey)
        if phits != None:
            phits.pop(ckey,None)
            if not phits:
                self.cache_byprop.pop(pkey)

    def _bumpTufoCache(self, tufo, prop, oldv, newv):
        '''
        Update or flush cache entries to reflect changes to a tufo.
        '''
        # dodge ephemeral props
        if prop[0] == '.':
            return

        oldkey = (prop,oldv)
        newkey = (prop,newv)

        cachfo = self.cache_byiden.get(tufo[0])
        if cachfo != None:
            if newv == None:
                cachfo[1].pop(prop,None)
            else:
                cachfo[1][prop] = newv

        # remove ourselves from old ones..
        if oldv != None:

            # remove ourselves from any cached results for prop=oldv
            for ckey in tuple(self.cache_byprop.get(oldkey,())):

                answ = self.cache_bykey.get(ckey)
                if answ == None:
                    continue

                atlim = len(answ) == ckey[2]

                # ok... if we're not in the result, no bigs...
                ctup = answ.pop(tufo[0],None)
                if ctup == None:
                    continue

                # removing it, we must decref the byiden cache.
                self.cache_byiden.pop(tufo[0])

                # if we were at our limit, ditch it.
                if atlim:
                    self._delCacheKey(ckey)

        # add ourselves to any cached results for the new value
        if newv != None:
            for ckey in tuple(self.cache_byprop.get(newkey,())):
                answ = self.cache_bykey.get(ckey)
                if answ == None:
                    continue

                # If it's at it's limit, no need to add us...
                if len(answ) == ckey[2]:
                    continue

                answ[tufo[0]] = tufo
                self.cache_byiden.put(tufo[0],tufo)

        # check for add prop and add us to (prop,None) pkey
        if oldv == None and newv != None:
            for ckey in tuple(self.cache_byprop.get((prop,None), ())):
                answ = self.cache_bykey.get(ckey)
                if answ == None:
                    continue

                # If it's at it's limit, no need to add us...
                if len(answ) == ckey[2]:
                    continue

                answ[tufo[0]] = tufo
                self.cache_byiden.put(tufo[0],tufo)

        # check for del prop and del us from the (prop,None) pkey
        if oldv != None and newv == None:

            for ckey in tuple(self.cache_byprop.get((prop,None), ())):
                answ = self.cache_bykey.get(ckey)
                if answ == None:
                    continue

                atlim = len(answ) == ckey[2]

                ctup = answ.pop(tufo[0],None)
                if ctup == None:
                    continue

                if atlim:
                    self._delCacheKey(ckey)

    def _onSetAxonUrl(self, url):
        self.axon = s_telepath.openurl(url)

    def _onSetCaching(self, valu):
        if not valu:
            self.cache_fifo.clear()
            self.cache_bykey.clear()
            self.cache_byiden.clear()
            self.cache_byprop.clear()

    def _reqSpliceInfo(self, act, info, prop):
        valu = info.get(prop)
        if prop == None:
            raise Exception('Splice: %s requires %s' % (act,prop))
        return valu

    def _actNodeAdd(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        tags = mesg[1].get('tags',())
        props = mesg[1].get('props',{})

        node = self.formTufoByProp(form,valu,**props)

        if tags:
            self.addTufoTags(node,tags)

    def _actNodeDel(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.getTufoByProp(form,valu=valu)
        if node == None:
            return

        self.delTufo(node)

    def _actNodeSet(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        node = self.formTufoByProp(form,valu)
        self.setTufoProps(node,**props)

    def _actNodeTagAdd(self, mesg):

        tag = mesg[1].get('tag')
        # TODO make these operate on multiple tags?
        #tags = mesg[1].get('tags',())
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.formTufoByProp(form,valu)
        self.addTufoTag(node,tag)

    def _actNodeTagDel(self, mesg):

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.formTufoByProp(form,valu)
        self.delTufoTag(node,tag)

    def splices(self, msgs):
        '''
        Process a list of splices in bulk (see splice()).

        Args:
            msgs (list): The list of splices.

        '''
        errs = []

        with self.getCoreXact() as xact:
            for mesg in msgs:
                try:
                    self.splice(mesg)
                except Exception as e:
                    logger.exception(e)
                    logger.warning('splice err: %s %r' % (e,mesg))
                    errs.append( (mesg,excinfo(e)) )

        return errs

    def splice(self, mesg):
        '''
        Feed the cortex a splice event to make changes to the hypergraph.

        Args:
            mesg ((str,dict)):    The (name,info) for the splice event.

        Returns:
            None

        Example:

            core.splice(mesg)

        '''
        act = mesg[1].get('act')
        self.spliceact.react(mesg, name=act)

    # TODO
    #def setSyncDir(self, path):
        #'''
        #Set the given directory as the archive of core:sync events
        #for this cortex.  The sync dir may then be used to populate
        #and synchronize other cortexes.
        #'''

    #@s_telepath.clientside
    def addSpliceFd(self, fd):
        '''
        Write all cortex splice events to the specified file-like object.

        Example:

            fd = open('audit.mpk','r+b')
            core.addSpliceFd(fd)
        '''
        def save(mesg):
            fd.write(msgenpack(mesg))
        self.on('splice', save)

    def eatSpliceFd(self, fd):
        '''
        Consume all cortex splice events from the given file-like object.
        The file bytes are expected to be msgpack encoded (str,dict) splice tuples.

        Example:

            fd = open('saved.mpk','rb')
            core.eatSyncFd(fd)

        '''
        for chnk in chunks(msgpackfd(fd),1000):
            self.splices(chnk)

    def _onDelSynTag(self, mesg):
        # deleting a tag.  delete all sub tags and wipe tufos.
        tufo = mesg[1].get('tufo')
        valu = tufo[1].get('syn:tag')

        [ self.delTufo(t) for t in self.getTufosByProp('syn:tag:up',valu) ]

        # do the (possibly very heavy) removal of the tag from all known forms.
        [self.delTufoTag(t, valu) for t in self.getTufosByDark('tag', valu)]

    def _onAddSynTag(self, mesg):
        tufo = mesg[1].get('tufo')
        form = tufo[1].get('tufo:form')
        utag = tufo[1].get('syn:tag:up')

        if utag != None:
            self._genTagForm(utag,form)

    def _onFormSynTag(self, mesg):
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        tags = valu.split('.')

        tlen = len(tags)

        if tlen > 1:
            props['syn:tag:up'] = '.'.join(tags[:-1])

        props['syn:tag:depth'] = tlen - 1
        props['syn:tag:base'] = tags[-1]

    def setSaveFd(self, fd, load=True, fini=False):
        '''
        Set a save fd for the cortex and optionally load.

        Args:
            fd (file):  A file like object to save splice events to using msgpack
            load (bool):    If True, load splice event from fd before starting to record
            fini (bool):    If True, close() the fd automatically on cortex fini()

        Returns:
            (None)

        Example:

            core.setSaveFd(fd)

        NOTE: This save file is allowed to be storage layer specific.
              If you want to store cortex splice events, use addSpliceFd().

        '''
        if load:
            for mesg in msgpackfd(fd):
                self.loadbus.dist(mesg)

        self.onfini( fd.flush )
        if fini:
            self.onfini( fd.close )

        def savemesg(mesg):
            fd.write( msgenpack(mesg) )

        self.savebus.link(savemesg)

    def isOk(self):
        '''
        An API allowing Cortex to test for internal error states.
        '''
        return self.isok

    def delAddRows(self, iden, rows):
        '''
        Delete rows by iden and add rows as a single operation.

        Example:

            core.delAddRows( iden, rows )

        Notes:

            This API is oriented toward "reparse" cases where iden
            will be the same for the new rows.

        '''
        self.delRowsById(iden)
        self.addRows(rows)

    def addRows(self, rows):
        '''
        Add (iden,prop,valu,time) rows to the Cortex.

        Example:

            import time
            tick = now()

            rows = [
                (id1,'baz',30,tick),
                (id1,'foo','bar',tick),
            ]

            core.addRows(rows)

        '''
        [ reqstor(p,v) for (i,p,v,t) in rows ]
        self.savebus.fire('core:save:add:rows', rows=rows)
        self._addRows(rows)

    def _loadAddRows(self, mesg):
        self._addRows( mesg[1].get('rows') )

    def addListRows(self, prop, *vals):
        '''
        Add rows by making a guid for each and using now().

        Example:

            core.addListRows('foo:bar',[ 1, 2, 3, 4])

        '''
        tick = millinow()
        rows = [ (guid(), prop, valu, tick) for valu in vals ]
        self.addRows(rows)
        return rows

    def getTufoList(self, tufo, name):
        '''
        Retrieve "list" values from a tufo.

        Example:

            for val in core.getTufoList(item,'foolist'):
                dostuff(val)

        '''
        prop = '%s:list:%s' % (tufo[0],name)
        return [ v for (i,p,v,t) in self.getRowsByProp(prop) ]

    def delTufoListValu(self, tufo, name, valu):
        prop = '%s:list:%s' % (tufo[0],name)
        self.delRowsByProp(prop,valu=valu)

    def addTufoList(self, tufo, name, *vals):
        '''
        Add "list" rows to a tufo.

        Example:

            core.addTufoList(tufo, 'counts', 99, 300, 1773)

        Notes:

            * this creates the tufo:list:<name> prop on the
              tufo to indicate that the list is present.

        '''
        reqiden(tufo)

        rows = []
        tick = now()
        prop = '%s:list:%s' % (tufo[0],name)

        haslist = 'tufo:list:%s' % name
        if tufo[1].get(haslist) == None:
            tufo[1][haslist] = 1
            rows.append( ( tufo[0], haslist, 1, tick) )

        [ rows.append( (guid(),prop,v,tick) ) for v in vals ]

        self.addRows( rows )

    def getRowsById(self, iden):
        '''
        Return all the rows for a given iden.

        Example:

            for row in core.getRowsById(iden):
                stuff()

        '''
        return self._getRowsById(iden)

    def getRowsByIdProp(self, iden, prop, valu=None):
        '''
        Return rows with the given <iden>,<prop>.

        Example:

            for row in core.getRowsByIdProp(iden,'foo:bar'):
                dostuff(row)

        '''
        return self._getRowsByIdProp(iden, prop, valu=valu)

    def delRowsById(self, iden):
        '''
        Delete all the rows for a given iden.

        Example:

            core.delRowsById(iden)

        '''
        self.savebus.fire('core:save:del:rows:by:iden', iden=iden)
        self._delRowsById(iden)

    def _loadDelRowsById(self, mesg):
        self._delRowsById( mesg[1].get('iden') )

    def delRowsByIdProp(self, iden, prop, valu=None):
        '''
        Delete rows with the givin combination of iden and prop[=valu].

        Example:

            core.delRowsByIdProp(id, 'foo')

        '''
        self.savebus.fire('core:save:del:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        return self._delRowsByIdProp(iden, prop, valu=valu)

    def _loadDelRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        self._delRowsByIdProp(iden,prop)

    def _loadSetRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        self._setRowsByIdProp(iden,prop,valu)

    def setRowsByIdProp(self, iden, prop, valu):
        '''
        Update/insert the value of the row(s) with iden and prop to valu.

        Example:

            core.setRowsByIdProp(iden,'foo',10)

        '''
        reqstor(prop,valu)
        self.savebus.fire('core:save:set:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        self._setRowsByIdProp(iden, prop, valu)

    def getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a tuple of (iden,prop,valu,time) rows by prop[=valu].

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)

        Notes:

            * Specify limit=<count> to limit return size
            * Specify mintime=<time> in epoch to filter rows
            * Specify maxtime=<time> in epoch to filter rows

        '''
        return tuple(self._getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but also lifts all other rows for iden.

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)
        Notes:

            * See getRowsByProp for options

        '''
        return tuple(self._getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getPivotRows(self, prop, byprop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but pivots through "iden" to a different property.
        This can be a light way to return a single property from a tufo rather than lifting the whole.

        Example:

            # return rows for the foo:bar prop by lifting foo:baz=10 and pivoting through iden.

            for row in core.getPivotRows('foo:bar', 'foo:baz', valu=10):
                dostuff()

        '''
        return tuple(self._getPivotRows(prop, byprop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Return the count of matching rows by prop[=valu]

        Example:

            if core.getSizeByProp('foo',valu=10) > 30:
                stuff()

        '''
        return self._getSizeByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def getTufosBy(self, name, prop, valu, limit=None):
        '''
        Retrieve tufos by either a specialized method or the lower getRowsBy api
        Specialized methods will be dependant on the storage backing and the data indexed

        Example:

            tufos = core.getTufosBy('in', 'foo', (47,3,8,22))

        '''
        meth = self.tufosbymeths.get(name)

        if not meth:
            rows = self.getRowsBy(name,prop,valu,limit=limit)
            return [ self.getTufoByIden(row[0]) for row in rows ]

        return meth(prop, valu, limit=limit)

    def getRowsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve rows by a specialized index within the cortex.

        Example:

            rows = core.getRowsBy('range','foo:bar',(20,30))

        Notes:
            * most commonly used to facilitate range searches

        '''
        meth = self._reqRowsByMeth(name)
        return meth(prop,valu,limit=limit)

    def getSizeBy(self, name, prop, valu, limit=None):
        '''
        Retrieve row count by a specialized index within the cortex.

        Example:

            size = core.getSizeBy('range','foo:bar',(20,30))
            print('there are %d rows where 20 <= foo < 30 ' % (size,))

        '''
        meth = self._reqSizeByMeth(name)
        return meth(prop,valu,limit=limit)

    def initTufosBy(self, name, meth):
        '''
        Initialize a "tufos by" handler for the Cortex.  This is useful
        when the index or storage backing can optimize tufo creation from
        raw rows.

        Example:
            def getbyin(prop,valus,limit=None):
                ret = []

                for valu in valus:
                    res = self.getTufosByProp(prop, valu=valu, limit=limit)
                    ret.extend(res)

                    if limit != None:
                        limit -= len(res)
                        if limit <= 0:
                            break

                return ret

            core.initTufos('in',getbyin)

        Notes:
            * Used by Cortex implementers to facilitate getTufosBy(...)
        '''
        self.tufosbymeths[name] = meth

    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Cortex.

        Example:

            def getbywoot(prop,valu,limit=None):
                return stuff() # list of rows

            core.initRowsBy('woot',getbywoot)

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        '''
        Initialize a "size by" handler for the Cortex.

        Example:

            def sizebywoot(prop,valu,limit=None):
                return stuff() # size of rows

            core.initSizeBy('woot',meth)

        '''
        self.sizebymeths[name] = meth

    def getTufoByIden(self, iden):
        '''
        Retrieve a tufo by id.

        Example:

            tufo = core.getTufoByIden(iden)

        '''
        if self.caching:
            tufo = self.cache_byiden.get(iden)
            if tufo != None:
                return tufo

        rows = self.getRowsById(iden)
        if not rows:
            return None

        return (iden,{ p:v for (i,p,v,t) in rows })

    def getTufosByIdens(self, idens):
        '''
        Return a list of tufos for the given iden GUIDs.

        Exmple:

            tufos = core.getTufosByIdens(idens)

        '''
        return self._getTufosByIdens(idens)

    def _getTufosByIdens(self, idens):
        # storage layers may optimize here!
        ret = []
        for iden in idens:
            tufo = self.getTufoByIden(iden)
            if tufo == None:
                continue
            ret.append(tufo)
        return ret

    def getTufoByProp(self, prop, valu=None):
        '''
        Return an (iden,info) tuple by joining rows based on a property.

        Example:

            tufo = core.getTufoByProp('fqdn','woot.com')

        Notes:

            * This must be used only for rows added with formTufoByProp!

        '''
        if valu != None:
            valu,subs = self.getPropNorm(prop,valu)

        if self.caching:
            answ = self._getTufosByCache(prop,valu,1)
            if answ:
                return answ[0]

        rows = self.getJoinByProp(prop, valu=valu, limit=1)
        if not rows:
            return None

        tufo = ( rows[0][0], {} )
        for iden,prop,valu,stamp in rows:
            tufo[1][prop] = valu

            if self.caching:
                self._bumpTufoCache(tufo,prop,None,valu)

        return tufo

    def _rowsToTufos(self, rows):
        res = collections.defaultdict(dict)
        [ res[i].__setitem__(p,v) for (i,p,v,t) in rows ]
        return list(res.items())

    def getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of tufos by property.

        Example:

            for tufo in core.getTufosByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        norm = None
        if valu != None:
            norm,subs = self.getPropNorm(prop,valu)
            if norm == None:
                raise BadPropValu(prop=prop,valu=valu)

        if self.caching and mintime == None and maxtime == None:
            return self._getTufosByCache(prop,norm,limit)

        return self._getTufosByProp(prop, valu=norm, mintime=mintime, maxtime=maxtime, limit=limit)

    def _getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self.getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return self._rowsToTufos(rows)

    def getTufosByPropType(self, name, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return tufos by interrogating the data model to find fields of the given type.

        Example:

            # return all tufos with an inet:email type property with value foo@bar.com

            for tufo in core.getTufosByPropType('inet:email', valu='foo@bar.com'):
                dostuff(tufo)

        '''
        ret = []

        for prop,info in self.propsbytype.get(name,()):

            pres = self.getTufosByProp(prop,valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
            ret.extend(pres)

            if limit != None:
                limit -= len(pres)
                if limit <= 0:
                    break

        return ret

    def _genTagForm(self, tag, form):
        self._core_tags.get(tag)
        self._core_tagforms.get( (tag,form) )

    def addTufoTags(self, tufo, tags, asof=None):
        '''
        Add multiple tags to a tufo.

        Example:

            core.addTufoTags(tufo,['foo.bar','baz.faz'])

        '''
        with self.getCoreXact():
            [ self.addTufoTag(tufo,tag,asof=asof) for tag in tags ]
            return tufo

    def addTufoTag(self, tufo, tag, asof=None):
        '''
        Add a tag to a tufo.

        Example:

            tufo = core.formTufoByProp('foo','bar')
            core.addTufoTag(tufo,'baz.faz')

        '''
        reqiden(tufo)

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        self._genTagForm(tag,form)

        rows = s_tags.genTufoRows(tufo,tag,valu=asof)
        if rows:

            with self.getCoreXact() as xact:

                formevt = 'tufo:tag:add:%s' % tufo[1].get('tufo:form')

                dark_row_gen = s_dark.genDarkRows(tufo[0], 'tag', [t[0] for t in rows])
                _rows = [t[1] for t in rows]
                _rows.extend(dark_row_gen)
                self.addRows(_rows)

                for subtag,(i,p,v,t) in rows:

                    tufo[1][p] = v
                    self._bumpTufoCache(tufo,p,None,v)
                    xact.fire('tufo:tag:add', tufo=tufo, tag=subtag, asof=asof)
                    xact.fire(formevt, tufo=tufo, tag=subtag, asof=asof)

                    xact.spliced('node:tag:add', form=form, valu=valu, tag=tag)

        return tufo

    def delTufoTag(self, tufo, tag):
        '''
        Delete a tag from a tufo.

        Example:

            tufo = core.getTufosByTag('foo','baz.faz')
            core.delTufoTag(tufo,'baz')

        '''
        iden = reqiden(tufo)

        props = s_tags.getTufoSubs(tufo,tag)
        if not props:
            return tufo

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        with self.getCoreXact() as xact:

            formevt = 'tufo:tag:del:%s' % tufo[1].get('tufo:form')

            [ self.delRowsByIdProp(iden,prop) for prop in props ]

            for p in props:

                asof = tufo[1].pop(p,None)
                if asof == None:
                    continue

                self._bumpTufoCache(tufo,p,asof,None)

                # FIXME: optimize string join/chop behavior up in here...
                subtag = s_tags.choptag(p)
                self.delTufoDark(tufo, 'tag', subtag)

                # fire notification events
                xact.fire('tufo:tag:del', tufo=tufo, tag=subtag)
                xact.fire(formevt, tufo=tufo, tag=subtag)

                xact.spliced('node:tag:del', form=form, valu=valu, tag=tag)

    def getTufosByTag(self, form, tag, limit=None):
        '''
        Retrieve a list of tufos by form and tag.

        Example:

            for tufo in core.getTufosByTag('woot','foo.bar'):
                dostuff(tufo)

        '''
        prop = '*|%s|%s' % (form,tag)
        return self.getTufosByProp(prop,limit=limit)

    def addTufoKeys(self, tufo, keyvals, stamp=None):
        '''
        A raw row adding API to allow tufo selection by more than one possible value.

        Note: only use this API if you really know how it effects your model.
        '''
        iden = reqiden(tufo)
        if stamp == None:
            stamp = now()

        rows = []
        form = tufo[1].get('tufo:form')
        for key,val in keyvals:
            prop = '%s:%s' % (form,key)
            valu,subs = self.getPropNorm(prop,val)

            rows.append( (iden, prop, valu, stamp) )

        self.addRows(rows)

    def addTufoEvent(self, form, **props):
        '''
        Add a "non-deconflicted" tufo by generating a guid

        Example:

            tufo = core.addTufoEvent('foo',bar=baz)

        Notes:

            If props contains a key "time" it will be used for
            the cortex timestap column in the row storage.

        '''
        return self.addTufoEvents(form,(props,))[0]

    def addJsonText(self, form, text):
        '''
        Add and fully index a blob of JSON text.

        Example:

        '''
        item = json.loads(text)
        return self.addJsonItem(item)

    def addJsonItem(self, form, item, tstamp=None):
        '''
        Add and fully index a JSON compatible data structure ( not in text form ).

        Example:

            foo = { 'bar':10, 'baz':{ 'faz':'hehe', 'woot':30 } }

            core.addJsonItem('foo',foo)

        '''
        return self.addJsonItems(form, (item,), tstamp=tstamp)

    def getStatByProp(self, stat, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Calculate and return a statistic for the specified rows.
        ( See getRowsByProp docs for most args )

        Various statistics types are builtin.

        sum     - total of all row values
        count   - number of rows
        histo   - histogram of values
        average - sum / count

        min     - minimum value
        max     - maximum value

        any     - True if any value is true
        all     - True if every value is true

        Example:

            minval = core.getStatByProp('min','foo:bar')

        '''
        statfunc = self.statfuncs.get(stat)
        if statfunc == None:
            knowns = self.statfuncs.keys()
            raise NoSuchStat(name=stat,knowns=knowns)

        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return statfunc(rows)

    def addStatFunc(self, name, func):
        '''
        Add a callback function to implement a statistic type.

        Example:

            def calcwoot(rows):
                sum([ r[2] for r in rows ]) + 99
                ...

            core.addStatFunc('woot', calcwoot)

            # later..
            woot = core.getStatByProp('woot','haha')

        '''
        self.statfuncs[name] = func

    def addJsonItems(self, form, items, tstamp=None):
        '''
        Add and fully index a list of JSON compatible data structures.

        Example:

            core.addJsonItems('foo', foolist)

        '''
        if tstamp == None:
            tstamp = now()

        for chunk in chunked(100,items):

            for item in chunk:
                iden = guid()

                props = self._primToProps(form,item)
                props = [ (p,self.getPropNorm(p,v)[0]) for (p,v) in props ]

                rows = [ (iden,p,v,tstamp) for (p,v) in props ]

                rows.append( (iden, form, iden, tstamp) )
                rows.append( (iden, 'prim:json', json.dumps(item), tstamp) )

            self.addRows(rows)

    def getJsonItems(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of (iden,item) tuples (similar to tufos, but with hierarchical structure )

        Example:

            x = {
                'bar':10,
            }

            core.addJsonItem('foo',x)

            # ... later ...

            for prim in core.getJsonsByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        rows = self.getPivotRows('prim:json', prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return [ json.loads(r[2]) for r in rows ]

    def _primToProps(self, form, item):
        '''
        Take a json compatible primitive item and return a list of
        "index" props for the various fields/values.
        '''
        props = []

        todo = [ (form,item) ]
        while todo:
            path,item = todo.pop()

            itype = type(item)

            if itype in s_compat.numtypes:
                props.append( (path,item) )
                continue

            if itype in s_compat.strtypes:
                props.append( (path,item) )
                continue

            if itype == bool:
                props.append( (path,int(item)) )
                continue

            if itype in (list,tuple):
                [ todo.append((path,valu)) for valu in item ]
                continue

            if itype == dict:
                for prop,valu in item.items():
                    todo.append( ('%s:%s' % (path,prop), valu ) )

        return props

    def addTufoEvents(self, form, propss):
        '''
        Add a list of tufo events in bulk.

        Example:

            propss = [
                {'foo':10,'bar':30},
                {'foo':11,'bar':99},
            ]

            core.addTufoEvents('woot',propss)

        '''
        alladd = set()

        with self.getCoreXact() as xact:

            ret = []
            for chunk in chunked(1000,propss):

                rows = []
                tufos = []
                splices = []

                for props in chunk:

                    iden = guid()

                    fulls,toadd = self._normTufoProps(form,props)

                    self._addDefProps(form,fulls)

                    fulls[form] = iden

                    alladd.update(toadd)

                    splices.append((form,iden,props))

                    self.fire('tufo:form', form=form, valu=iden, props=fulls)
                    self.fire('tufo:form:%s' % form, form=form, valu=iden, props=fulls)

                    rows.extend([ (iden,p,v,xact.tick) for (p,v) in fulls.items() ])

                    # sneaky ephemeral/hidden prop to identify newly created tufos
                    fulls['.new'] = 1
                    tufos.append( (iden,fulls) )

                self.addRows(rows)

                # fire splice events
                for form,valu,props in splices:
                    xact.spliced('node:add', form=form, valu=valu, props=props)

                for tufo in tufos:
                    # fire notification events
                    xact.fire('tufo:add', tufo=tufo)
                    xact.fire('tufo:add:%s' % form, tufo=tufo)

                ret.extend(tufos)

            if self.autoadd:
                self._runAutoAdd(alladd)

        return ret

    def _runAutoAdd(self, toadd):
        for form,valu in toadd:
            if form in self.noauto:
                continue
            self.formTufoByProp(form,valu)

    def formTufoByTufo(self, tufo):
        '''
        Form an (iden,info) tufo by extracting information from an existing one.
        '''
        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)
        prefix = '%s:' % (form,)
        prelen = len(prefix)
        props = { k[prelen:]:v for (k,v) in tufo[1].items() if k.startswith(prefix) }

        return self.formTufoByProp(form,valu,**props)

    def formTufoByProp(self, prop, valu, **props):
        '''
        Form an (iden,info) tuple by atomically deconflicting
        the existance of prop=valu and creating it if not present.

        Example:

            tufo = core.formTufoByProp('inet:fqdn','woot.com')

        Notes:

            * this will trigger an 'tufo:add' event if the
              tufo does not yet exist and is being construted.

        '''
        ctor = self.seedctors.get(prop)
        if ctor != None:
            return ctor(prop,valu,**props)

        # special case for adding nodes with a guid primary property
        # if the value None is specified, generate a new guid and skip
        # deconfliction ( allows highly performant "event" ingest )
        deconf = True
        if valu == None:
            tname = self.getPropTypeName(prop)
            if tname and self.isSubType(tname,'guid'):
                valu = guid()
                deconf = False

        valu,subs = self.getPropNorm(prop,valu)

        with self.getCoreXact() as xact:

            if deconf:
                tufo = self.getTufoByProp(prop,valu=valu)
                if tufo != None:
                    return tufo

            tick = now()
            iden = guid()

            props.update(subs)

            fulls,toadd = self._normTufoProps(prop,props)

            # create a "full" props dict which includes defaults
            self._addDefProps(prop,fulls)

            fulls[prop] = valu

            # update our runtime form counters
            self.formed[prop] += 1

            # fire these immediately since we need them to potentially fill
            # in values before we generate rows for the new tufo
            self.fire('tufo:form', form=prop, valu=valu, props=fulls)
            self.fire('tufo:form:%s' % prop, form=prop, valu=valu, props=fulls)

            rows = [ (iden,p,v,tick) for (p,v) in fulls.items() ]

            self.addRows(rows)

            tufo = (iden,fulls)

            if self.caching:
                # avoid .new in cache
                cachefo = (iden,dict(fulls))
                for p,v in fulls.items():
                    self._bumpTufoCache(cachefo,p,None,v)


            # fire notification events
            xact.fire('tufo:add',tufo=tufo)
            xact.fire('tufo:add:%s' % prop, tufo=tufo)

            xact.spliced('node:add', form=prop, valu=valu, props=props)

            if self.autoadd:
                self._runAutoAdd(toadd)

        tufo[1]['.new'] = True

        return tufo

    def delTufo(self, tufo):
        '''
        Delete a tufo and it's associated props/lists/etc.


        Example:

            core.delTufo(foob)

        '''
        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        # fire notification events
        self.fire('tufo:del',tufo=tufo)
        self.fire('tufo:del:%s' % form, tufo=tufo)

        for name,tick in self.getTufoDsets(tufo):
            self.delTufoDset(tufo,name)

        if self.caching:
            for prop,valu in tufo[1].items():
                self._bumpTufoCache(tufo,prop,valu,None)

        iden = tufo[0]
        with self.getCoreXact() as xact:
            self.delRowsById(iden)
            # delete any dark props/rows
            self.delRowsById(iden[::-1])
            xact.spliced('node:del', form=form, valu=valu)

        lists = [ p.split(':',2)[2] for p in tufo[1].keys() if p.startswith('tufo:list:') ]
        for name in lists:
            self.delRowsByProp('%s:list:%s' % (iden,name))

    def addTufoDset(self, tufo, name):
        '''
        Add the tufo to a named dataset.
        '''
        dark = tufo[0][::-1]
        if self.getRowsByIdProp(dark,'_:dset',valu=name):
            return

        rows = [ (dark, '_:dset', name, now()) ]
        self.addRows(rows)
        #NOTE: may add this if a use cases occurs
        #self.fire('syn:dset:add', name=name, tufo=tufo)
        self.fire('syn:dset:add:%s' % name, name=name, tufo=tufo)

    def delTufoDset(self, tufo, name):
        dark = tufo[0][::-1]
        self.delRowsByIdProp(dark,'_:dset',name)
        self.fire('syn:dset:del:%s' % name, name=name, tufo=tufo)

    def getTufoDsets(self, tufo):
        '''
        Return a list of (name,time) tuples for dset membership.
        '''
        dark = tufo[0][::-1]
        return [ (v,t) for (i,p,v,t) in self.getRowsByIdProp(dark,'_:dset') ]

    def getTufosByDset(self, name, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of the tufos in the named dataset.

        Example:

            for tufo in getTufosByDset('woot'):
                dostuff(tufo)

        '''
        rows = self.getRowsByProp('_:dset', valu=name, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [ r[0][::-1] for r in rows ]

        ret = []
        for part in chunks(idens,1000):
            ret.extend( self.getTufosByIdens(part) )

        return ret

    def snapTufosByDset(self, name, mintime=None, maxtime=None, limit=None):
        rows = self.getRowsByProp('_:dset', valu=name, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [ r[0][::-1] for r in rows ]
        return self._initTufoSnap(idens)

    def snapTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [ r[0] for r in rows ]
        return self._initTufoSnap(idens)

    def _initTufoSnap(self, idens):

        snap = guid()

        if not idens:
            return {'snap':snap,'tufos':(),'count':0}

        count = len(idens)

        x = collections.deque( chunks(idens,1000) )

        rets = x.popleft()
        tufos = self.getTufosByIdens(rets)

        if x:
            self.snaps.put(snap,x)

        return {'snap':snap, 'tufos':tufos, 'count':count}

    def getSnapNext(self, snap):
        '''
        Get the next block of tufos for the given snapshot.
        '''
        x = self.snaps.get(snap)
        if x == None:
            return None

        idens = x.popleft()

        if not x:
            self.snaps.pop(snap)

        return self.getTufosByIdens(idens)

    def finiSnap(self, snap):
        '''
        Cancel a tufo snapshot.
        '''
        self.snaps.pop(snap)

    def delTufoByProp(self, form, valu):
        '''
        Delete a tufo from the cortex by prop=valu.

        Example:

            core.delTufoByProp('foo','bar')

        '''
        valu,_ = self.getPropNorm(form,valu)

        item = self.getTufoByProp(form,valu)
        if item != None:
            self.delTufo(item)

        return item

    def delTufosByProp(self, prop, valu=None):
        '''
        Delete multiple tufos by a single property.

        Example:

            core.delTufosByProp('foo:bar',valu=10)

        '''
        for item in self.getTufosByProp(prop,valu=valu):
            self.delTufo(item)

    def popTufosByProp(self, prop, valu=None):
        '''
        Delete and return multiple tufos by a property.

        Example:

            items = core.popTufosByProp('foo:bar',valu=10)

        '''
        items = self.getTufosByProp(prop,valu=valu)
        for item in items:
            self.delTufo(item)
        return items

    def _addDefProps(self, form, fulls):
        '''
        Add any default values for unspecified properties.
        '''
        for k,v in self.getFormDefs(form):
            fulls.setdefault(k,v)

    def _normTufoProps(self, form, inprops, tufo=None):
        '''
        This will both return a set of fully qualified props as a dict
        as well as modify inprops inband as a normalized set or relatives.
        '''

        toadd = set()
        props = {'tufo:form':form}

        for name in list(inprops.keys()):

            valu = inprops.get(name)

            prop = '%s:%s' % (form,name)
            if not self._okSetProp(prop):
                inprops.pop(name,None)
                continue

            oldv = None
            if tufo is not None:
                oldv = tufo[1].get(prop)

            valu,subs = self.getPropNorm(prop,valu, oldval=oldv)
            if tufo is not None and tufo[1].get(prop) == valu:
                inprops.pop(name,None)
                continue

            ptype = self.getPropTypeName(prop)
            if self.isTufoForm(ptype):
                toadd.add( (ptype,valu) )

            # any sub-properties to populate?
            for sname,svalu in subs.items():

                subprop = '%s:%s' % (prop,sname)
                if self.getPropDef(subprop) == None:
                    continue

                props[subprop] = svalu

                ptype = self.getPropTypeName(subprop)
                if self.isTufoForm(ptype):
                    toadd.add( (ptype,svalu) )

            props[prop] = valu
            inprops[name] = valu

        return props,toadd

    def addSaveLink(self, func):
        '''
        Add an event callback to receive save events for this cortex.

        Example:

            def savemesg(mesg):
                dostuff()

            core.addSaveLink(savemesg)

        '''
        self.savebus.link(func)

    def _okSetProp(self, prop):
        # check for enforcement and validity of a full prop name
        if not self.enforce:
            return True

        return self.getPropDef(prop) != None

    def setTufoProps(self, tufo, **props):
        '''
        Set ( with de-duplication ) the given tufo props.

        Example:

            tufo = core.setTufoProps(tufo, woot='hehe', blah=10)

        '''
        reqiden(tufo)
        # add tufo form prefix to props
        form = tufo[1].get('tufo:form')
        fulls,toadd = self._normTufoProps(form, props, tufo=tufo)
        if not fulls:
            return tufo

        iden = tufo[0]
        valu = tufo[1].get(form)

        with self.getCoreXact() as xact:

            # fire notification events
            self.fire('tufo:set', tufo=tufo, props=fulls)
            self.fire('tufo:props:%s' % (form,), tufo=tufo, props=fulls)

            xact.spliced('node:set', form=form, valu=valu, props=props)

            for p,v in fulls.items():

                oldv = tufo[1].get(p)
                self.setRowsByIdProp(iden,p,v)

                tufo[1][p] = v

                # update the tufo cache if present
                if self.caching:
                    self._bumpTufoCache(tufo,p,oldv,v)

                # fire notification events
                xact.fire('tufo:set:%s' % (p,), tufo=tufo, prop=p, valu=v, oldv=oldv)

        return tufo

    def setTufoProp(self, tufo, prop, valu):
        '''
        Set a single tufo property.

        Example:

            core.setTufoProp(tufo, 'woot', 'hehe')

        '''
        self.setTufoProps(tufo, **{prop:valu})
        return tufo

    def incTufoProp(self, tufo, prop, incval=1):
        '''
        Atomically increment/decrement the value of a given tufo property.

        Example:

            tufo = core.incTufoProp(tufo,prop)

        '''
        form = tufo[1].get('tufo:form')
        prop = '%s:%s' % (form,prop)

        if not self._okSetProp(prop):
            return tufo

        return self._incTufoProp(tufo,prop,incval=incval)

    def _incTufoProp(self, tufo, prop, incval=1):

        # to allow storage layer optimization
        iden = tufo[0]

        with self.inclock:
            rows = self._getRowsByIdProp(iden,prop)
            if len(rows) == 0:
                raise NoSuchTufo(iden=iden,prop=prop)

            oldv = rows[0][2]
            valu = oldv + incval

            self.setRowsByIdProp(iden,prop,valu)

            tufo[1][prop] = valu
            self.fire('tufo:set:%s' % (prop,), tufo=tufo, prop=prop, valu=valu, oldv=oldv)

        return tufo

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)

        '''
        self.savebus.fire('core:save:del:rows:by:prop', prop=prop, valu=valu, mintime=mintime, maxtime=maxtime)
        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _loadDelRowsByProp(self, mesg):
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        mint = mesg[1].get('mintime')
        maxt = mesg[1].get('maxtime')
        self._delRowsByProp(prop, valu=valu, mintime=mint, maxtime=maxt)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete a group of rows by selecting for property and joining on iden.

        Example:

            core.delJoinByProp('foo',valu=10)

        '''
        return self._delJoinByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsById(irow[0]):
                yield jrow

    def _getPivotRows(self, prop, byprop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(byprop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsByIdProp( irow[0], prop ):
                yield jrow

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)
        done = set()
        for row in rows:
            iden = row[0]
            if iden in done:
                continue

            self.delRowsById(iden)
            done.add(iden)

    def _reqSizeByMeth(self, name):
        meth = self.sizebymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name=name)
        return meth

    def _reqRowsByMeth(self, name):
        meth = self.rowsbymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name=name)
        return meth

    def _setRowsByIdProp(self, iden, prop, valu):
        # base case is delete and add
        self._delRowsByIdProp(iden, prop)
        rows = [ (iden, prop, valu, now()) ]
        self.addRows(rows)

    def _calcStatSum(self, rows):
        return sum([ r[2] for r in rows ])

    def _calcStatHisto(self, rows):
        histo = collections.defaultdict(int)
        for row in rows:
            histo[row[2]] += 1
        return histo

    def _calcStatCount(self, rows):
        return len(rows)

    def _calcStatMin(self, rows):
        return min([ r[2] for r in rows ])

    def _calcStatMax(self, rows):
        return max([ r[2] for r in rows ])

    def _calcStatMean(self, rows):
        count = len(rows)
        tot = sum([ r[2] for r in rows ])
        return tot / float(count)

    def _calcStatAny(self, rows):
        return any([ r[2] for r in rows ])

    def _calcStatAll(self, rows):
        return all([ r[2] for r in rows ])

    def _tufosByIn(self, prop, valus, limit=None):
        ret = []

        for valu in valus:
            res = self.getTufosByProp(prop, valu=valu, limit=limit)
            ret.extend(res)

            if limit != None:
                limit -= len(res)
                if limit <= 0:
                    break

        return ret

    def _tufosByInetCidr(self, prop, valu, limit=None):

        ipv4str, cidr = valu.split('/', 1)
        ipv4addr,_ = s_datamodel.getTypeParse('inet:ipv4', ipv4str)
        mask = ( 2** ( 32 - int(cidr) ))
        ipv4addr &= ~mask

        return self.getTufosBy('range', prop, (ipv4addr, ipv4addr+mask), limit=limit)

    def _onTufoAddSynType(self, mesg):
        # tufo:add:syn:type
        tufo = mesg[1].get('tufo')
        if tufo == None:
            return

        self._initTypeTufo(tufo)

    def _onTufoAddSynForm(self, mesg):
        # tufo:add:syn:form
        tufo = mesg[1].get('tufo')
        if tufo == None:
            return

        self._initFormTufo(tufo)

    def _onTufoAddSynProp(self, mesg):
        # tufo:add:syn:prop
        tufo = mesg[1].get('tufo')
        if tufo == None:
            return

        self._initPropTufo(tufo)

    def _initTypeTufo(self, tufo):
        '''
        Initialize a TypeLib Type from syn:type tufo
        '''
        name = tufo[1].get('syn:type')
        info = s_tufo.props(tufo)
        self.addType(name,**info)

    def _initFormTufo(self, tufo):
        '''
        Initialize a DataModel Form from syn:form tufo
        '''
        name = tufo[1].get('syn:form')
        info = s_tufo.props(tufo)
        # add the tufo definition to the DataModel
        self.addTufoForm(name,**info)

    def _initPropTufo(self, tufo):
        '''
        Initialize a DataModel Prop from syn:prop tufo
        '''
        name = tufo[1].get('syn:prop')
        info = s_tufo.props(tufo)

        form = info.pop('form')
        prop = name[len(form)+1:]

        self.addTufoProp(form, prop, **info)
        return

    def _stormOperStat(self, query, oper):

        #TODO make these also operate on already lifted tufos
        name,prop = oper[1].get('args')
        kwargs = dict(oper[1].get('kwlist'))

        valu = kwargs.get('valu')
        sval = self.getStatByProp(name,prop,valu=valu)

        query.add( s_tufo.ephem('stat:%s' % name, prop, valu=sval) )

    def _stormOperDset(self, query, oper):
        for name in oper[1].get('args'):
            [ query.add(t) for t in self.getTufosByDset(name) ]

    # some helpers to allow *all* queries to be processed via getTufosBy()
    def _tufosByEq(self, prop, valu, limit=None):
        return self.getTufosByProp(prop,valu=valu,limit=limit)

    def _tufosByHas(self, prop, valu, limit=None):
        return self.getTufosByProp(prop,limit=limit)

    def _tufosByTag(self, prop, valu, limit=None):
        return self.getTufosByTag(prop,valu,limit=limit)

    def _tufosByType(self, prop, valu, limit=None):
        valu,_ = self.getTypeNorm(prop,valu)
        return self.getTufosByPropType(prop,valu=valu,limit=limit)

    def _tufosByDark(self, prop, valu, limit=None):
        return self.getTufosByDark(name=prop, valu=valu, limit=limit)

    # these helpers allow a storage layer to simply implement
    # and register _getTufosByGe and _getTufosByLe

    def _rowsByLt(self, prop, valu, limit=None):
        return self._rowsByLe(prop, valu-1, limit=limit)

    def _rowsByGt(self, prop, valu, limit=None):
        return self._rowsByGe(prop, valu+1, limit=limit)

    def _tufosByLt(self, prop, valu, limit=None):
        return self._tufosByLe(prop, valu-1, limit=limit)

    def _tufosByGt(self, prop, valu, limit=None):
        return self._tufosByGe(prop, valu+1, limit=limit)

    def getSplicePump(self,core):
        '''
        Return a splice pump for the remote cortex.

        #Example:

            with core.getSplicePump(prox):
                core.formTufoByProp('inet:fqdn','vertex.link')

        '''
        pump = s_queue.Queue()
        self.on('splice', pump.put)

        def splicepump():

            while not self.isfini:

                try:

                    for msgs in pump.slices(1000):
                        errs = core.splices(msgs)
                        for err in errs:
                            logger.warning('splice pump: %r' % (err,))

                except Exception as e:
                    logger.exception(e)

        wrkr = s_threads.worker(splicepump)
        pump.onfini( wrkr.fini )

        return pump

    def getCoreXact(self, size=1000):
        '''
        Get a cortex transaction context for use in a with block.
        This object allows bulk storage layer optimization and
        proper ordering of events.

        Example:

            with core.getCoreXact() as xact:
                core.dostuff()

        '''
        iden = s_threads.iden()

        xact = self._core_xacts.get(iden)
        if xact != None:
            return xact

        xact = self._getCoreXact(size)
        self._core_xacts[iden] = xact
        return xact

    def _popCoreXact(self):
        # Used by the CoreXact fini routine
        self._core_xacts.pop( s_threads.iden(), None)

    def _getCoreXact(self, size):
        raise NoSuchImpl(name='_getCoreXact')

    def addTufoDark(self, tufo, name, valu):
        '''
        Add a dark row to a tufo with a given name and value.

        Dark rows get their own index and can be used to quickly pull tufos.
        While similar to dsets, these are primarily intended for implementing
        features inside of Synapse directly.

        Args:
            tufo ((str, dict)): Tufo to add the dark row too.
            name (str): Dark row name.
            value (str): Value to set on the dark property. May be any data type which may stored in a cortex.

        Returns:
            None: Returns None.
        '''
        dark = tufo[0][::-1]
        dark_name = '_:dark:%s' % name
        if self.getRowsByIdProp(dark, dark_name, valu=valu):
            return

        rows = [(dark, dark_name, valu, now())]
        self.addRows(rows)

    def delTufoDark(self, tufo, name, valu=None):
        '''
        Remove dark rows from a tufo for a given name and optional value.

        Args:
            tufo ((str, dict)): Tufo to remove data dark rows from.
            name (str): Specific dark rows to remove.
            valu (str): Value to remove (optional).

        Returns:
            None: Returns None.
        '''
        dark = tufo[0][::-1]
        self.delRowsByIdProp(dark, '_:dark:%s' % name, valu)

    def getTufoDarkValus(self, tufo, name):
        '''
        Get a list of dark row values on a given tufo with a specific name.

        Args:
            tufo ((str, dict)): Tufo to look up.
            name (str): Specific dark rows to look up.

        Returns:
            list: List of (value, time) tuples for a given tufos dark rows.

        '''
        dark = tufo[0][::-1]
        dprop = '_:dark:%s' % name
        return [(v, t) for (i, p, v, t) in self.getRowsByIdProp(dark, dprop)]

    def getTufoDarkNames(self, tufo):
        '''
        Get a list of dark row names on a tufo.

        Args:
            tufo ((str, dict)): Tufo to look up. 

        Returns:
            list: List of (name, time) tuples for a given tufos dark rows.
        '''
        dark = tufo[0][::-1]
        rows = self.getRowsById(dark)
        ret = {(p.split(':', 2)[2], t) for (i, p, v, t) in rows if p.startswith('_:dark:')}
        return list(ret)

    def getTufosByDark(self, name, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Get a list of tufos with the named dark rows and optional values.

        Args:
            name (str): Dark row name to retrieve tufos by.
            valu (str): Value to retrieve.
            mintime (int): Minimum timevalue on tufos to return.
            maxtime (int): Maximum timevalue on tufos to return.
            limit (int): Maximum number of tufos to return.

        Examples:
            Get a list of tufos by a tag::

                for tufo in getTufosByDark('tag', 'foo.bar.baz'):
                    dostuff(tufo)

        Returns:
            list: List of tufos
        '''
        rows = self.getRowsByProp('_:dark:%s' % name, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = list(set([r[0][::-1] for r in rows]))  # Unique the idens we pull.

        ret = []
        for part in chunks(idens,1000):
            ret.extend(self.getTufosByIdens(part))

        return ret

    def snapTufosByDark(self, name, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Create a snapshot of tufos by dark name/values.

        Args:
            name (str): Dark row name to snapshot tufos by.
            valu (str): Optional value to retrieve tufos by.
            mintime (int): Minimum timevalue on tufos to return.
            maxtime (int): Maximum timevalue on tufos to return.
            limit (int): Maximum number of tufos to return.

        Returns:
            dict: Snapshot generator for getting tufos.
        '''
        rows = self.getRowsByProp('_:dark:%s' % name, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = list(set([r[0][::-1] for r in rows]))  # Unique the idens we pull.
        return self._initTufoSnap(idens)

class CoreXact:
    '''
    A context manager for a cortex "transaction".
    '''
    def __init__(self, core, size=None):
        self.core = core
        self.size = size

        self.tick = now()

        self.refs = 0
        self.ready = False
        self.exiting = False

        self.events = []

    def spliced(self, act, **info):

        form = info.get('form')

        pdef = self.core.getPropDef(form)
        if pdef != None and pdef[1].get('local'):
            return

        info['act'] = act
        info['time'] = self.tick
        info['user'] = s_userauth.getSynUser()

        self.fire('splice', **info)

    def _coreXactAcquire(self):
        # allow implementors to acquire any synchronized resources
        pass

    def _coreXactRelease(self):
        # allow implementors to release any synchronized resources
        pass

    def _coreXactInit(self):
        # called once during the first __enter__
        pass

    def _coreXactFini(self):
        # called once during the last __exit__
        pass

    def _coreXactBegin(self):
        raise NoSuchImpl(name='_coreXactBegin')

    def _coreXactCommit(self):
        raise NoSuchImpl(name='_coreXactCommit')

    def acquire(self):
        self._coreXactAcquire()
        self.core.xlock.acquire()

    def release(self):
        self.core.xlock.release()
        self._coreXactRelease()

    def begin(self):
        self._coreXactBegin()

    def commit(self):
        '''
        Commit the results thus far ( without closing / releasing )
        '''
        self._coreXactCommit()

    def fireall(self):

        events = self.events
        self.events = []

        [ self.core.fire(name,**props) for (name,props) in events ]

    def cedetime(self):
        # release and re acquire the form lock to allow others a shot
        # give up our scheduler quanta to allow acquire() priority to go
        # to any existing waiters.. ( or come back almost immediately if none )
        self.release()
        time.sleep(0)
        self.acquire()

    def fire(self, name, **props):
        '''
        Pend an event to fire when the transaction next commits.
        '''
        self.events.append( (name,props) )

        if self.size != None and len(self.events) >= self.size:
            self.sync()
            self.cedetime()
            self.begin()

    def sync(self):
        '''
        Loop commiting and syncing events until there are no more
        events that need to fire.
        '''
        self.commit()

        # odd thing during exit... we need to fire events
        # ( possibly causing more xact uses ) until there are
        # no more events left to fire.
        while self.events:
            self.begin()
            self.fireall()
            self.commit()

    def __enter__(self):
        self.refs += 1
        if self.refs == 1 and not self.ready:
            self._coreXactInit()
            self.acquire()
            self.begin()
            self.ready = True

        return self

    def __exit__(self, exc, cls, tb):
        # FIXME handle rollback on exc not None
        self.refs -= 1
        if self.refs > 0 or self.exiting:
            return

        self.exiting = True

        self.sync()
        self.release()
        self._coreXactFini()
        self.core._popCoreXact()

