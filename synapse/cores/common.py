import json
import logging
import itertools
import threading
import collections

import synapse.compat as s_compat
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.reactor as s_reactor
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.cores.storage as s_storage

import synapse.lib.tags as s_tags
import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue
import synapse.lib.ingest as s_ingest
import synapse.lib.hashset as s_hashset
import synapse.lib.threads as s_threads
import synapse.lib.modules as s_modules
import synapse.lib.hashitem as s_hashitem
import synapse.lib.interval as s_interval
import synapse.lib.userauth as s_userauth

from synapse.eventbus import EventBus, on, onfini
from synapse.lib.storm import Runtime
from synapse.lib.config import confdef
from synapse.datamodel import DataModel

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
    if tufo[0] is None:
        raise s_common.NoSuchTufo(iden=None)
    return tufo[0]

class Cortex(EventBus, DataModel, Runtime, s_ingest.IngestApi):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link, store, **conf):

        Runtime.__init__(self)
        EventBus.__init__(self)

        # a cortex may have a ref to an axon
        self.axon = None
        self.seedctors = {}

        self.modules = [(ctor, modconf) for ctor, smod, modconf in s_modules.ctorlist]
        self.modsdone = False

        self.noauto = {'syn:form', 'syn:type', 'syn:prop'}

        self.onConfOptSet('modules', self._onSetMods)
        self.onConfOptSet('caching', self._onSetCaching)
        self.onConfOptSet('axon:url', self._onSetAxonUrl)

        self.setConfOpts(conf)

        self._link = link

        self.lock = threading.Lock()
        self.inclock = threading.Lock()

        self.coremods = {}  # name:module ( CoreModule() )
        self.statfuncs = {}

        self.auth = None
        self.snaps = s_cache.Cache(maxtime=60)

        self.seqs = s_cache.KeyCache(self.getSeqNode)

        self.formed = collections.defaultdict(int)      # count tufos formed since startup

        self._core_tags = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tag'))
        self._core_tagforms = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tagform'))

        self.tufosbymeths = {}

        self.cache_fifo = collections.deque()               # [ ((prop,valu,limt), {
        self.cache_bykey = {}                               # (prop,valu,limt):( (prop,valu,limt), {iden:tufo,...} )
        self.cache_byiden = s_cache.RefDict()
        self.cache_byprop = collections.defaultdict(dict)   # (<prop>,<valu>):[ ((prop, valu, limt),  answ), ... ]

        #############################################################
        # Handlers for each splice event action
        self.spliceact = s_reactor.Reactor()
        self.spliceact.act('node:add', self._actNodeAdd)
        self.spliceact.act('node:del', self._actNodeDel)
        self.spliceact.act('node:prop:set', self._actNodePropSet)
        self.spliceact.act('node:prop:del', self._actNodePropDel)
        self.spliceact.act('node:tag:add', self._actNodeTagAdd)
        self.spliceact.act('node:tag:del', self._actNodeTagDel)
        self.spliceact.act('node:ival:set', self._actNodeIvalSet)
        self.spliceact.act('node:ival:del', self._actNodeIvalDel)

        #############################################################

        self.addStatFunc('any', self._calcStatAny)
        self.addStatFunc('all', self._calcStatAll)
        self.addStatFunc('min', self._calcStatMin)
        self.addStatFunc('max', self._calcStatMax)
        self.addStatFunc('sum', self._calcStatSum)
        self.addStatFunc('mean', self._calcStatMean)
        self.addStatFunc('count', self._calcStatCount)
        self.addStatFunc('histo', self._calcStatHisto)

        # Strap in default initTufosBy functions
        self.initTufosBy('eq', self._tufosByEq)
        self.initTufosBy('ge', self._tufosByGe)
        self.initTufosBy('gt', self._tufosByGt)
        self.initTufosBy('in', self._tufosByIn)
        self.initTufosBy('le', self._tufosByLe)
        self.initTufosBy('lt', self._tufosByLt)
        self.initTufosBy('has', self._tufosByHas)
        self.initTufosBy('tag', self._tufosByTag)
        self.initTufosBy('type', self._tufosByType)
        self.initTufosBy('dark', self._tufosByDark)
        self.initTufosBy('range', self._tufosByRange)
        self.initTufosBy('inet:cidr', self._tufosByInetCidr)

        # Initialize the storage layer
        self.store = store  # type: s_storage.Storage
        self._registerStore()

        self.isok = True

        DataModel.__init__(self, load=False)

        self.myfo = self.formTufoByProp('syn:core', 'self')
        self.isnew = self.myfo[1].get('.new', False)

        self.modelrevlist = []
        with self.getCoreXact() as xact:
            self._initCoreMods()

        # and finally, strap in our event handlers...
        self.on('node:add', self._onTufoAddSynType, form='syn:type')
        self.on('node:add', self._onTufoAddSynForm, form='syn:form')
        self.on('node:add', self._onTufoAddSynProp, form='syn:prop')

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
        for name, ret, exc in s_modules.call('addCoreOns', self):
            if exc is not None:
                logger.warning('%s.addCoreOns: %s' % (name, exc))

        self.onfini(self._finiCoreMods)

        s_ingest.IngestApi.__init__(self, self)

    @staticmethod
    @confdef(name='common_cortex')
    def _cortex_condefs():
        confdefs = (
            ('autoadd', {'type': 'bool', 'asloc': 'autoadd', 'defval': 1,
                         'doc': 'Automatically add forms for props where type is form'}),
            ('enforce', {'type': 'bool', 'asloc': 'enforce', 'defval': 0, 'doc': 'Enables data model enforcement'}),
            ('caching', {'type': 'bool', 'asloc': 'caching', 'defval': 0,
                         'doc': 'Enables caching layer in the cortex'}),
            ('cache:maxsize', {'type': 'int', 'asloc': 'cache_maxsize', 'defval': 1000,
                               'doc': 'Enables caching layer in the cortex'}),
            ('rev:model', {'type': 'bool', 'defval': 1, 'doc': 'Set to 0 to disallow model version updates'}),
            ('rev:storage', {'type': 'bool', 'defval': 1, 'doc': 'Set to 0 to disallow storage version updates'}),
            ('axon:url', {'type': 'str', 'doc': 'Allows cortex to be aware of an axon blob store'}),
            ('log:save', {'type': 'bool', 'asloc': 'logsave', 'defval': 0,
                          'doc': 'Enables saving exceptions to the cortex as syn:log nodes'}),
            ('log:level', {'type': 'int', 'asloc': 'loglevel', 'defval': 0, 'doc': 'Filters log events to >= level'}),
            ('modules', {'defval': (), 'doc': 'An optional list of (pypath,conf) tuples for synapse modules to load'})
        )
        return confdefs

    def _registerStore(self):
        '''
        Register the cores Storage object with the Cortex.

        This ensures that when we fini() the Cortex, we've removed references
        between the two objects so garbage collection can remove objects.
        '''
        # link events from the Storage back to the Cortex Eventbus
        self.store.link(self.dist)

        # Ensure we clean up any Storage refs and call fini on the Storage obj
        def finiStore():
            self.store.unlink(self.dist)
            self.store.fini()

        self.onfini(finiStore)

    def getModlVers(self, name):
        '''
        Retrieve the model version for the given model name.

        Args:
            name (str): The name of the model

        Returns:
            (int):  The model version ( linear version number ) or -1
        '''
        prop = '.:modl:vers:' + name
        rows = self.getRowsByProp(prop)
        if not rows:
            return -1
        return rows[0][2]

    def setModlVers(self, name, vers):
        '''
        Set the version number for a specific model.

        Args:
            name (str): The name of the model
            vers (int): The new (linear) version number

        Returns:
            (None)

        '''
        prop = '.:modl:vers:' + name

        with self.getCoreXact() as xact:

            rows = self.getRowsByProp(prop)

            if rows:
                iden = rows[0][0]
            else:
                iden = s_common.guid()

            self.setRowsByIdProp(iden, prop, vers)
            return vers

    def revModlVers(self, name, revs):
        '''
        Update a model using a list of (vers,func) tuples.

        Args:
            name (str): The name of the model
            revs ([(int,function)]):  List of (vers,func) revision tuples.

        Returns:
            (None)

        Example:

            with s_cortex.openurl('ram:///') as core:

                def v0():
                    addModelStuff(core)

                def v1():
                    addMoarStuff(core)

                revs = [ (0,v0), (1,v1) ]

                core.revModlVers('foo', revs)

        Each specified function is expected to update the cortex including data migration.
        '''
        if not revs:
            return

        curv = self.getModlVers(name)

        maxver = revs[-1][0]
        if maxver == curv:
            return

        if not self.getConfOpt('rev:model'):
            raise s_common.NoRevAllow(name=name, mesg='add rev:model=1 to cortex url to allow model updates')

        for vers, func in sorted(revs):

            if vers <= curv:
                continue

            if vers and curv != -1:
                mesg = 'Updating model [{}] from [{}] => [{}] - do *not* interrupt.'.format(name, curv, vers)
                logger.warning(mesg)
                self.log(logging.WARNING, mesg=mesg, name=name, curv=curv, vers=vers)

            # allow the revision function to optionally return the
            # revision he jumped to ( to allow initial override )
            retn = func()
            if retn is not None:
                vers = retn

            if vers and curv != -1:
                mesg = 'Updated model [{}] from [{}] => [{}]'.format(name, curv, vers)
                logger.warning(mesg)
                self.log(logging.WARNING, mesg=mesg, name=name, curv=curv, vers=vers)

            curv = self.setModlVers(name, vers)

    def _finiCoreMods(self):
        [modu.fini() for modu in self.coremods.values()]

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
        if self.axon is None:
            raise s_common.NoSuchOpt(name='axon:url', mesg='The cortex does not have an axon configured')
        return self.axon.wants(htype, hvalu, size)

    def _addAxonChunk(self, iden, byts):
        if self.axon is None:
            raise s_common.NoSuchOpt(name='axon:url', mesg='The cortex does not have an axon configured')
        return self.axon.chunk(iden, byts)

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
        if node is None:
            raise s_common.NoSuchSeq(name=name)

        #FIXME perms

        wid = node[1].get('syn:seq:width')
        valu = node[1].get('syn:seq:nextvalu')

        self._incTufoProp(node, 'syn:seq:nextvalu')

        return name + str(valu).rjust(wid, '0')

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

    def addDataModel(self, name, modl):
        '''
        Store all types/forms/props from the given data model in the cortex.

        Args:
            name (str): The name of the model ( depricated/ignored )
            modl (dict):A data model definition dictionary

        Returns:
            (None)

        Example:

            core.addDataModel('synapse.models.foo',
                              {

                                'types':( ('foo:g',{'subof':'guid'}), ),

                                'forms':(
                                    ('foo:f',{'ptype':'foo:g','doc':'a foo'},[
                                        ('a',{'ptype':'str:lwr'}),
                                        ('b',{'ptype':'int'}),
                                    ]),
                                ),
                              })
        '''
        tufo = self.formTufoByProp('syn:model', name)

        # use the normalized hash of the model dict to short
        # circuit loading if it is unchanged.
        mhas = s_hashitem.hashitem(modl)
        if tufo[1].get('syn:model:hash') == mhas:
            return

        # FIXME handle type/form/prop removal
        for name, tnfo in modl.get('types', ()):

            tufo = self.formTufoByProp('syn:type', name, **tnfo)
            tufo = self.setTufoProps(tufo, **tnfo)

        for form, fnfo, props in modl.get('forms', ()):

            # allow forms declared without ptype if their name *is* one
            if fnfo.get('ptype') is None:
                fnfo['ptype'] = form

            tufo = self.formTufoByProp('syn:form', form, **fnfo)
            tufo = self.setTufoProps(tufo, **fnfo)

            for prop, pnfo in props:
                fullprop = form + ':' + prop
                tufo = self.formTufoByProp('syn:prop', fullprop, form=form, **pnfo)
                tufo = self.setTufoProps(tufo, **pnfo)

    def addDataModels(self, modtups):
        [self.addDataModel(name, modl) for (name, modl) in modtups]

    def _getTufosByCache(self, prop, valu, limit):
        # only used if self.caching = 1
        ckey = (prop, valu, limit) # cache key

        # check for this exact query...
        # ( (prop,valu,limit), answ )
        answ = self.cache_bykey.get(ckey)
        if answ is not None:
            return list(answ.values())

        # check for same prop
        pkey = (prop, valu)

        for hkey in tuple(self.cache_byprop.get(pkey, ())):

            hprop, hvalu, hlimit = hkey
            # if there's a hit that's either bigger than us *or* unlimited, use it
            if hlimit is None or (limit is not None and limit < hlimit):
                answ = self.cache_bykey.get(hkey)
                return list(answ.values())[:limit]

        # no match found in the cache
        tufos = self._getTufosByProp(prop, valu=valu, limit=limit)

        self._addCacheKey(ckey, tufos)
        return tufos

    def _addCacheKey(self, ckey, tufos):
        # only one instance of any given tufo in the cache
        tufos = self.cache_byiden.puts([(t[0], t) for t in tufos])

        self.cache_fifo.append(ckey)
        self.cache_bykey[ckey] = {t[0]: t for t in tufos}
        self.cache_byprop[(ckey[0], ckey[1])][ckey] = True

        while len(self.cache_fifo) > self.cache_maxsize:
            oldk = self.cache_fifo.popleft()
            self._delCacheKey(oldk)

        return tufos

    def _delCacheKey(self, ckey):

        # delete a tufo cache entry
        answ = self.cache_bykey.pop(ckey, None)

        # decref our cached tuples
        if answ is not None:
            [self.cache_byiden.pop(t[0]) for t in answ.values()]

        pkey = (ckey[0], ckey[1])
        phits = self.cache_byprop.get(pkey)
        if phits is not None:
            phits.pop(ckey, None)
            if not phits:
                self.cache_byprop.pop(pkey)

    def _bumpTufoCache(self, tufo, prop, oldv, newv):
        '''
        Update or flush cache entries to reflect changes to a tufo.
        '''
        # dodge ephemeral props
        if prop[0] == '.':
            return

        oldkey = (prop, oldv)
        newkey = (prop, newv)

        cachfo = self.cache_byiden.get(tufo[0])
        if cachfo is not None:
            if newv is None:
                cachfo[1].pop(prop, None)
            else:
                cachfo[1][prop] = newv

        # remove ourselves from old ones..
        if oldv is not None:

            # remove ourselves from any cached results for prop=oldv
            for ckey in tuple(self.cache_byprop.get(oldkey, ())):

                answ = self.cache_bykey.get(ckey)
                if answ is None:
                    continue

                atlim = len(answ) == ckey[2]

                # ok... if we're not in the result, no bigs...
                ctup = answ.pop(tufo[0], None)
                if ctup is None:
                    continue

                # removing it, we must decref the byiden cache.
                self.cache_byiden.pop(tufo[0])

                # if we were at our limit, ditch it.
                if atlim:
                    self._delCacheKey(ckey)

        # add ourselves to any cached results for the new value
        if newv is not None:
            for ckey in tuple(self.cache_byprop.get(newkey, ())):
                answ = self.cache_bykey.get(ckey)
                if answ is None:
                    continue

                # If it's at it's limit, no need to add us...
                if len(answ) == ckey[2]:
                    continue

                answ[tufo[0]] = tufo
                self.cache_byiden.put(tufo[0], tufo)

        # check for add prop and add us to (prop,None) pkey
        if oldv is None and newv is not None:
            for ckey in tuple(self.cache_byprop.get((prop, None), ())):
                answ = self.cache_bykey.get(ckey)
                if answ is None:
                    continue

                # If it's at it's limit, no need to add us...
                if len(answ) == ckey[2]:
                    continue

                answ[tufo[0]] = tufo
                self.cache_byiden.put(tufo[0], tufo)

        # check for del prop and del us from the (prop,None) pkey
        if oldv is not None and newv is None:

            for ckey in tuple(self.cache_byprop.get((prop, None), ())):
                answ = self.cache_bykey.get(ckey)
                if answ is None:
                    continue

                atlim = len(answ) == ckey[2]

                ctup = answ.pop(tufo[0], None)
                if ctup is None:
                    continue

                if atlim:
                    self._delCacheKey(ckey)

    def _onSetAxonUrl(self, url):
        self.axon = s_telepath.openurl(url)

    def initCoreModule(self, ctor, conf):
        '''
        Load a cortex module with the given ctor and conf.

        Args:
            ctor (str): The python module class path
            conf (dict):Config dictionary for the module
        '''
        # load modules as dyndeps which construct a module
        # subclass with ctor(<core>,<conf>)
        try:

            oldm = self.coremods.pop(ctor, None)
            if oldm is not None:
                oldm.fini()

            modu = s_dyndeps.tryDynFunc(ctor, self, conf)

            self.coremods[ctor] = modu

            return True

        except Exception as e:
            logger.exception(e)
            logger.warning('mod load fail: %s %s' % (ctor, e))
            return False

    def _synTagsVers0(self):

        # nothing to do...
        if self.isnew:
            return

        # we must transition tags from *|<form>|<tag> to #<tag>
        tags = [n[1].get('syn:tag') for n in self.eval('syn:tag')]
        forms = [n[1].get('syn:form') for n in self.eval('syn:form')]

        logger.warning('syn:core updating... do *not* interrupt')

        for form in forms:

            for tag in tags:

                prop = '#' + tag

                oldp = '*|' + form + '|' + tag
                rows = self.getRowsByProp(oldp)
                if not rows:
                    continue

                logger.warning('syn:core updating #%s on %s' % (tag, form))

                newd = '_:*' + form + prop

                news = [(i, prop, v, t) for (i, p, v, t) in rows]
                darks = [(i[::-1], newd, v, t) for (i, p, v, t) in rows]

                self.addRows(news + darks)

                self.delRowsByProp(oldp)
                self.delRowsByProp('_:dark:tag', valu=tag)

    def _initCoreMods(self):
        # call our interal model revision functions
        revs = [
            (0, self._synTagsVers0),
        ]
        self.revModlVers('syn:core', revs)

        # load each of the configured (and base) modules.
        for ctor, conf in self.modules:
            self.initCoreModule(ctor, conf)

        # Sort the model revlist
        self.modelrevlist.sort(key=lambda x: x[:2])
        for revision, name, func in self.modelrevlist:
            self.revModlVers(name, ((revision, func),))

        for tufo in self.getTufosByProp('syn:type'):
            try:
                self._initTypeTufo(tufo)
            except s_common.DupTypeName as e:
                continue

        for tufo in self.getTufosByProp('syn:form'):
            try:
                self._initFormTufo(tufo)
            except s_common.DupPropName as e:
                continue

        for tufo in self.getTufosByProp('syn:prop'):
            try:
                self._initPropTufo(tufo)
            except s_common.DupPropName as e:
                continue

        self.modelrevlist = []
        self.modsdone = True

    def _onSetMods(self, mods):

        self.modules.extend(mods)
        if not self.modsdone:
            return

        # dynamically load modules if we are already done loading
        for ctor, conf in mods:
            self.initCoreModule(ctor, conf)
        if not self.modelrevlist:
            return

        self.modelrevlist.sort(key=lambda x: x[:2])
        for revision, name, func in self.modelrevlist:
            self.revModlVers(name, ((revision, func),))

        self.modelrevlist = []

    def _onSetCaching(self, valu):
        if not valu:
            self.cache_fifo.clear()
            self.cache_bykey.clear()
            self.cache_byiden.clear()
            self.cache_byprop.clear()

    def _actNodeAdd(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        props = mesg[1].get('props', {})

        node = self.formTufoByProp(form, valu, **props)

    def _actNodeDel(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.getTufoByProp(form, valu=valu)
        if node is None:
            return

        self.delTufo(node)

    def _actNodePropSet(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')
        newv = mesg[1].get('newv')

        node = self.formTufoByProp(form, valu)
        self.setTufoProp(node, prop, newv)

    def _actNodePropDel(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')

        node = self.formTufoByProp(form, valu)
        self.delTufoProp(node, prop)

    def _actNodeTagAdd(self, mesg):

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.formTufoByProp(form, valu)
        self.addTufoTag(node, tag)

    def _actNodeTagDel(self, mesg):

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.formTufoByProp(form, valu)
        self.delTufoTag(node, tag)

    def _actNodeIvalSet(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')
        ival = mesg[1].get('ival')

        node = self.formTufoByProp(form, valu)

        self.setTufoIval(node, prop, ival)

    def _actNodeIvalDel(self, mesg):
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')

        node = self.formTufoByProp(form, valu)

        self.delTufoIval(node, prop)

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
                    logger.warning('splice err: %s %r' % (e, mesg))
                    errs.append((mesg, s_common.excinfo(e)))

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
            fd.write(s_common.msgenpack(mesg))
        self.on('splice', save)

    def eatSpliceFd(self, fd):
        '''
        Consume all cortex splice events from the given file-like object.
        The file bytes are expected to be msgpack encoded (str,dict) splice tuples.

        Example:

            fd = open('saved.mpk','rb')
            core.eatSyncFd(fd)

        '''
        for chnk in s_common.chunks(s_common.msgpackfd(fd), 1000):
            self.splices(chnk)

    @on('node:del', form='syn:tag')
    def _onDelSynTag(self, mesg):
        # deleting a tag node.  delete all sub tags and wipe tufos.
        valu = mesg[1].get('valu')

        [self.delTufo(t) for t in self.getTufosByProp('syn:tag:up', valu)]

        # do the (possibly very heavy) removal of the tag from all known forms.
        [self.delTufoTag(t, valu) for t in self.getTufosByTag(valu)]

        # Flush the tag caches
        self._core_tags.clear()
        self._core_tagforms.clear()

    @on('node:form', form='syn:tag')
    def _onFormSynTag(self, mesg):
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        tags = valu.split('.')

        tlen = len(tags)

        if tlen > 1:
            props['syn:tag:up'] = '.'.join(tags[:-1])

        props['syn:tag:base'] = tags[-1]
        props['syn:tag:depth'] = tlen - 1

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
        self.store.setSaveFd(fd, load, fini)

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
        self.store.addRows(rows)

    def addListRows(self, prop, *vals):
        '''
        Add rows by making a guid for each and using now().

        Example:

            core.addListRows('foo:bar',[ 1, 2, 3, 4])

        '''
        tick = s_common.now()
        rows = [(s_common.guid(), prop, valu, tick) for valu in vals]
        self.addRows(rows)
        return rows

    def getTufoList(self, tufo, name):
        '''
        Retrieve "list" values from a tufo.

        Example:

            for val in core.getTufoList(item,'foolist'):
                dostuff(val)

        '''
        prop = '%s:list:%s' % (tufo[0], name)
        return [v for (i, p, v, t) in self.getRowsByProp(prop)]

    def delTufoListValu(self, tufo, name, valu):
        prop = '%s:list:%s' % (tufo[0], name)
        self.delRowsByProp(prop, valu=valu)

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
        tick = s_common.now()
        prop = '%s:list:%s' % (tufo[0], name)

        haslist = 'tufo:list:%s' % name
        if tufo[1].get(haslist) is None:
            tufo[1][haslist] = 1
            rows.append((tufo[0], haslist, 1, tick))

        [rows.append((s_common.guid(), prop, v, tick)) for v in vals]

        self.addRows(rows)

    def getRowsById(self, iden):
        '''
        Return all the rows for a given iden.

        Example:

            for row in core.getRowsById(iden):
                stuff()

        '''
        return self.store.getRowsById(iden)

    def getRowsByIdProp(self, iden, prop, valu=None):
        '''
        Return rows with the given <iden>,<prop>.

        Example:

            for row in core.getRowsByIdProp(iden,'foo:bar'):
                dostuff(row)

        '''
        return self.store.getRowsByIdProp(iden, prop, valu=valu)

    def delRowsById(self, iden):
        '''
        Delete all the rows for a given iden.

        Example:

            core.delRowsById(iden)

        '''
        self.store.delRowsById(iden)

    def delRowsByIdProp(self, iden, prop, valu=None):
        '''
        Delete rows with the givin combination of iden and prop[=valu].

        Example:

            core.delRowsByIdProp(id, 'foo')

        '''
        return self.store.delRowsByIdProp(iden, prop, valu=valu)

    def setRowsByIdProp(self, iden, prop, valu):
        '''
        Update/insert the value of the row(s) with iden and prop to valu.

        Example:

            core.setRowsByIdProp(iden,'foo',10)

        '''
        self.store.setRowsByIdProp(iden, prop, valu)

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
        return tuple(self.store.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but also lifts all other rows for iden.

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)
        Notes:

            * See getRowsByProp for options

        '''
        return tuple(self.store.getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

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
        return self.store.getSizeByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def getTufosBy(self, name, prop, valu, limit=None):
        '''
        Retrieve tufos by either a specialized method or the lower getRowsBy api
        Specialized methods will be dependant on the storage backing and the data indexed

        Example:

            tufos = core.getTufosBy('in', 'foo', (47,3,8,22))

        '''
        meth = self.tufosbymeths.get(name)
        if not meth:
            rows = self.getRowsBy(name, prop, valu, limit=limit)
            return self.getTufosByIdens({i for (i, p, v, t) in rows})
        return meth(prop, valu, limit=limit)

    def getRowsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve rows by a specialized index within the cortex.

        Example:

            rows = core.getRowsBy('range','foo:bar',(20,30))

        Notes:
            * most commonly used to facilitate range searches

        '''
        meth = self.store.reqRowsByMeth(name)
        return meth(prop, valu, limit=limit)

    def getSizeBy(self, name, prop, valu, limit=None):
        '''
        Retrieve row count by a specialized index within the cortex.

        Example:

            size = core.getSizeBy('range','foo:bar',(20,30))
            print('there are %d rows where 20 <= foo < 30 ' % (size,))

        '''
        meth = self.store.reqSizeByMeth(name)
        return meth(prop, valu, limit=limit)

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

    def getTufoByIden(self, iden):
        '''
        Retrieve a tufo by id.

        Example:

            tufo = core.getTufoByIden(iden)

        '''
        if self.caching:
            tufo = self.cache_byiden.get(iden)
            if tufo is not None:
                return tufo
        rows = self.store.getRowsById(iden)
        if not rows:
            return None
        return (iden, {p: v for (i, p, v, t) in rows})

    def getTufosByIdens(self, idens):
        '''
        Return a list of tufos for the given iden GUIDs.

        Exmple:

            tufos = core.getTufosByIdens(idens)

        '''
        rows = self.store.getRowsByIdens(idens)
        return s_common.rowstotufos(rows)

    def getTufoByProp(self, prop, valu=None):
        '''
        Return an (iden,info) tuple by joining rows based on a property.

        Example:

            tufo = core.getTufoByProp('fqdn','woot.com')

        Notes:

            * This must be used only for rows added with formTufoByProp!

        '''
        if valu is not None:
            valu, subs = self.getPropNorm(prop, valu)

        if self.caching:
            answ = self._getTufosByCache(prop, valu, 1)
            if answ:
                return answ[0]

        rows = self.getJoinByProp(prop, valu=valu, limit=1)
        if not rows:
            return None

        tufo = (rows[0][0], {})
        for iden, prop, valu, stamp in rows:
            tufo[1][prop] = valu

            if self.caching:
                self._bumpTufoCache(tufo, prop, None, valu)

        return tufo

    def getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of tufos by property.

        Example:

            for tufo in core.getTufosByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        norm = None
        if valu is not None:
            norm, subs = self.getPropNorm(prop, valu)
            if norm is None:
                raise s_common.BadPropValu(prop=prop, valu=valu)

        if self.caching and mintime is None and maxtime is None:
            return self._getTufosByCache(prop, norm, limit)

        return self._getTufosByProp(prop, valu=norm, mintime=mintime, maxtime=maxtime, limit=limit)

    def _getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self.getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return s_common.rowstotufos(rows)

    def getTufosByPropType(self, name, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return tufos by interrogating the data model to find fields of the given type.

        Example:

            # return all tufos with an inet:email type property with value foo@bar.com

            for tufo in core.getTufosByPropType('inet:email', valu='foo@bar.com'):
                dostuff(tufo)

        '''
        ret = []

        for prop, info in self.propsbytype.get(name, ()):

            pres = self.getTufosByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
            ret.extend(pres)

            if limit is not None:
                limit -= len(pres)
                if limit <= 0:
                    break

        return ret

    def _tufosByLe(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        rows = self.store.getJoinsBy('le', prop, valu, limit=limit)
        return s_common.rowstotufos(rows)

    def _tufosByGe(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        rows = self.store.getJoinsBy('ge', prop, valu, limit=limit)
        return s_common.rowstotufos(rows)

    def _tufosByLt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        rows = self.store.getJoinsBy('lt', prop, valu, limit=limit)
        return s_common.rowstotufos(rows)

    def _tufosByGt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        rows = self.store.getJoinsBy('gt', prop, valu, limit=limit)
        return s_common.rowstotufos(rows)

    def _tufosByRange(self, prop, valu, limit=None):
        if len(valu) != 2:
            raise s_common.SynErr(mesg='Excepted a valu object with a len of 2', valu=valu)
        minvalu, maxvalu = valu[0], valu[1]
        minvalu, _ = self.getPropNorm(prop, minvalu)
        maxvalu, _ = self.getPropNorm(prop, maxvalu)
        valu = minvalu, maxvalu
        rows = self.store.getJoinsBy('range', prop, valu, limit=limit)
        return s_common.rowstotufos(rows)

    def _genTagForm(self, tag, form):
        self._core_tags.get(tag)
        self._core_tagforms.get((tag, form))

    def addTufoTags(self, tufo, tags):
        '''
        Add multiple tags to a tufo.

        Example:

            core.addTufoTags(tufo,['foo.bar','baz.faz'])

        '''
        with self.getCoreXact():
            [self.addTufoTag(tufo, tag) for tag in tags]
            return tufo

    def addTufoTag(self, tufo, tag, times=()):
        '''
        Add a tag (and optionally time box) to a tufo.

        Args:
            tufo ((str,dict)):  A node in tuple form.
            tag (str):  A synapse tag string
            times ((int,)): A list of time stamps in milli epoch

        Returns:
            ((str,dict)): The node in tuple form (with updated props)

        Example:

            node = core.formTufoByProp('foo','bar')
            node = core.addTufoTag(tufo,'baz.faz')

            # add a tag with a time box
            node = core.addTufoTag(tufo,'foo.bar@2012-2016')

            # add a tag with a list of sample times used to
            # create a timebox.
            node = core.addTufoTag(tufo,'hehe.haha', times=timelist)

        '''
        iden = reqiden(tufo)

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        tag, subs = self.getTypeNorm('syn:tag', tag)

        tagp = '#' + tag

        mins = subs.get('seen:min')
        maxs = subs.get('seen:max')

        ival = s_interval.fold(mins, maxs, *times)

        if tufo[1].get(tagp) is not None:
            if ival is None:
                return tufo

            return self.setTufoIval(tufo, tagp, ival)

        rows = []
        dark = iden[::-1]

        with self.getCoreXact() as xact:

            tick = xact.tick

            for subtag in s_tags.iterTagDown(tag):

                subprop = '#' + subtag
                subdark = '_:*' + form + subprop

                self._genTagForm(subtag, form)

                if tufo[1].get(subprop) is not None:
                    continue

                tufo[1][subprop] = tick
                self._bumpTufoCache(tufo, subprop, None, tick)

                rows.append((iden, subprop, tick, tick))
                rows.append((dark, '_:*' + form + subprop, tick, tick))

                xact.fire('node:tag:add', form=form, valu=valu, tag=subtag, node=tufo)
                xact.spliced('node:tag:add', form=form, valu=valu, tag=subtag)

            self.addRows(rows)

            if ival is not None:
                tufo = self.setTufoIval(tufo, tagp, ival)

            return tufo

    def delTufoTag(self, tufo, tag):
        '''
        Delete a tag from a tufo.

        Args:
            tufo ((str,dict)):  The node in tuple form.
            tag (str):          The tag to remove

        Example:

            for tufo in core.getTufosByTag('baz.faz'):
                core.delTufoTag(tufo,'baz')

        '''
        iden = reqiden(tufo)
        dark = iden[::-1]

        prop = '#' + tag

        if tufo[1].get(prop) is None:
            return tufo

        subprops = s_tags.getTufoSubs(tufo, tag)
        if not subprops:
            return tufo

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        with self.getCoreXact() as xact:

            for subprop in subprops:

                asof = tufo[1].pop(subprop, None)
                if asof is None:
                    continue

                subtag = subprop[1:]
                subdark = '_:*' + form + subprop

                self.delRowsByIdProp(iden, subprop)
                self.delRowsByIdProp(dark, subdark)

                self._bumpTufoCache(tufo, subprop, asof, None)
                self._bumpTufoCache(tufo, subdark, asof, None)

                # fire notification events
                xact.fire('node:tag:del', form=form, valu=valu, tag=subtag, node=tufo)
                xact.spliced('node:tag:del', form=form, valu=valu, tag=subtag, asof=asof)

                self.delTufoIval(tufo, subprop)

    def getTufosByTag(self, tag, form=None, limit=None):
        '''
        Retrieve a list of tufos by tag and optionally form.

        Args:
            tag (str):      A synapse tag name
            form (str):     A synapse node form
            limit (int):    A limit for the query

        Example:

            for node in core.getTufosByTag('foo.bar'):
                dostuff(tufo)

        '''
        prop = '#' + tag
        if form is None:
            return self.getTufosByProp(prop, limit=limit)

        dark = '_:*' + form + prop
        return self._getTufosByDarkRows(dark, limit=limit)

    def setTufoIval(self, tufo, name, ival):
        '''
        Add an interval to a node.

        Args:
            tufo ((str,dict)):  The node to add the interval to
            name (str):         The name of the interval
            ival ((int,int)):   The interval tuple

        Returns:
            ((str,dict)):       The updated tufo

        '''
        minp = '>' + name
        maxp = '<' + name

        tmin = tufo[1].get(minp)
        tmax = tufo[1].get(maxp)

        minv, maxv = ival

        if tmin is not None and tmin <= minv and tmax is not None and tmax >= maxv:
            return tufo

        iden = tufo[0]

        form, valu = s_tufo.ndef(tufo)

        with self.getCoreXact() as xact:

            rows = []
            props = []

            if tmin is None:
                rows.append((iden, minp, minv, xact.tick))
                tufo[1][minp] = minv

            elif minv < tmin:
                props.append((minp, minv, tmin))
                tufo[1][minp] = minv

            if tmax is None:
                rows.append((iden, maxp, maxv, xact.tick))
                tufo[1][maxp] = maxv

            elif maxv > tmax:
                props.append((maxp, maxv, tmax))
                tufo[1][maxp] = maxv

            if rows:
                self.addRows(rows)
                [self._bumpTufoCache(tufo, r[1], None, r[2]) for r in rows]

            for prop, newv, oldv in props:
                self._bumpTufoCache(tufo, prop, oldv, newv)
                self.store.setRowsByIdProp(iden, prop, newv)

            ival = (tufo[1].get(minp), tufo[1].get(maxp))

            xact.fire('node:ival', form=form, valu=valu, prop=name, ival=ival, node=tufo)
            xact.spliced('node:ival:set', form=form, valu=valu, prop=name, ival=ival)

        return tufo

    def delTufoIval(self, tufo, name):
        '''
        Remove an iterval from a node.

        Args:
            tufo ((str,dict)):  The node in tuple form
            name (str):         The name of the interval

        Returns:
            ((str,dict)):       The updated node in tuple form
        '''
        minp = '>' + name
        maxp = '<' + name

        iden = reqiden(tufo)

        minv = tufo[1].get(minp)
        maxv = tufo[1].get(maxp)

        if minv is None and maxv is None:
            return tufo

        form, valu = s_tufo.ndef(tufo)

        with self.getCoreXact() as xact:
            self.delRowsByIdProp(iden, minp)
            self.delRowsByIdProp(iden, maxp)
            self._bumpTufoCache(tufo, minp, minv, None)
            self._bumpTufoCache(tufo, maxp, maxv, None)
            xact.fire('node:ival:del', form=form, valu=valu, prop=name, node=tufo)
            xact.spliced('node:ival:del', form=form, valu=valu, prop=name)

        return tufo

    def addTufoEvent(self, form, **props):
        '''
        Add a "non-deconflicted" tufo by generating a guid

        Example:

            tufo = core.addTufoEvent('foo',bar=baz)

        Notes:

            If props contains a key "time" it will be used for
            the cortex timestap column in the row storage.

        '''
        return self.addTufoEvents(form, (props,))[0]

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
        if statfunc is None:
            knowns = self.statfuncs.keys()
            raise s_common.NoSuchStat(name=stat, knowns=knowns)

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
        if tstamp is None:
            tstamp = s_common.now()

        for chunk in chunked(100, items):

            rows = []
            for item in chunk:
                iden = s_common.guid()

                props = self._primToProps(form, item)
                props = [(p, self.getPropNorm(p, v)[0]) for (p, v) in props]

                rows = [(iden, p, v, tstamp) for (p, v) in props]

                rows.append((iden, form, iden, tstamp))
                rows.append((iden, 'prim:json', json.dumps(item), tstamp))

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
        return [json.loads(r[2]) for r in rows]

    def _primToProps(self, form, item):
        '''
        Take a json compatible primitive item and return a list of
        "index" props for the various fields/values.
        '''
        props = []

        todo = [(form, item)]
        while todo:
            path, item = todo.pop()

            itype = type(item)

            if itype in s_compat.numtypes:
                props.append((path, item))
                continue

            if itype in s_compat.strtypes:
                props.append((path, item))
                continue

            if itype == bool:
                props.append((path, int(item)))
                continue

            if itype in (list, tuple):
                [todo.append((path, valu)) for valu in item]
                continue

            if itype == dict:
                for prop, valu in item.items():
                    todo.append((path + ':' + prop, valu))

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

        doneadd = set()
        tname = self.getPropTypeName(form)
        if tname is None and self.enforce:
            raise s_common.NoSuchForm(name=form)

        if tname and not self.isSubType(tname, 'guid'):
            raise s_common.NotGuidForm(name=form)

        with self.getCoreXact() as xact:

            ret = []

            for chunk in chunked(1000, propss):

                adds = []
                rows = []

                alladd = set()

                for props in chunk:

                    iden = s_common.guid()

                    fulls, toadd = self._normTufoProps(form, props, isadd=True)

                    self._addDefProps(form, fulls)

                    fulls[form] = iden
                    fulls['tufo:form'] = form

                    toadd = [t for t in toadd if t not in doneadd]

                    alladd.update(toadd)
                    doneadd.update(toadd)

                    # fire these immediately since we need them to potentially fill
                    # in values before we generate rows for the new tufo
                    self.fire('node:form', form=form, valu=iden, props=fulls)

                    # Ensure we have ALL the required props after node:form is fired.
                    self._reqProps(form, fulls)

                    rows.extend([(iden, p, v, xact.tick) for (p, v) in fulls.items()])

                    # sneaky ephemeral/hidden prop to identify newly created tufos
                    fulls['.new'] = 1

                    node = (iden, fulls)

                    ret.append(node)
                    adds.append((form, iden, props, node))

                # add "toadd" nodes *first* (for tree/parent issues )
                if self.autoadd:
                    self._runAutoAdd(alladd)

                self.addRows(rows)

                # fire splice events
                for form, valu, props, node in adds:
                    xact.fire('node:add', form=form, valu=valu, node=node)
                    xact.spliced('node:add', form=form, valu=valu, props=props)

        return ret

    def _runAutoAdd(self, toadd):
        for form, valu in toadd:
            if form in self.noauto:
                continue
            self.formTufoByProp(form, valu)

    def _reqProps(self, form, fulls):
        if not self.enforce:
            return

        props = self.getFormReqs(form)

        # Return fast for perf
        if not props:
            return

        props = set(props)

        # Special case for handling syn:prop:glob=1 on will not have a ptype
        # despite the model requiring a ptype to be present.
        if fulls.get('syn:prop:glob') and 'syn:prop:ptype' in props:
            props.remove('syn:prop:ptype')

        missing = props - set(fulls)
        if missing:
            raise s_common.PropNotFound(mesg='Node is missing required a prop during formation',
                                        prop=list(missing)[0], form=form)

    def formTufoByTufo(self, tufo):
        '''
        Form an (iden,info) tufo by extracting information from an existing one.
        '''
        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)
        prefix = '%s:' % (form,)
        prelen = len(prefix)
        props = {k[prelen:]: v for (k, v) in tufo[1].items() if k.startswith(prefix)}

        return self.formTufoByProp(form, valu, **props)

    def formTufosByProps(self, items):
        '''
        Forms tufos by prop, given a tuple of (form, valu, props) tuples.

        Args:

            items (tuple): A tuple of tuples of (form, valu, props)

        Returns:

            tuple: Tuple containing tufos, either with the node or error data

        Example:

            items = ( ('foo:thing', 'hehe', {'a': 1}), ('bar:thing', 'haha', {'b': 2}), )
            results = core.formTufosByProps(items)
        '''
        retval = []

        with self.getCoreXact() as xact:
            for form, valu, props in items:
                try:
                    retval.append(self.formTufoByProp(form, valu, **props))
                except Exception as e:
                    excinfo = s_common.excinfo(e)
                    excval = excinfo.pop('err')
                    retval.append(s_tufo.ephem('syn:err', excval, **excinfo))

        return tuple(retval)

    def formTufoByProp(self, prop, valu, **props):
        '''
        Form an (iden,info) tuple by atomically deconflicting
        the existance of prop=valu and creating it if not present.

        Args:

            prop (str): The primary property (or form) of the node
            valu (obj): The primary valu for the node
            **props:    Additional secondary properties for the node

        Example:

            tufo = core.formTufoByProp('inet:fqdn','woot.com')

        '''
        ctor = self.seedctors.get(prop)
        if ctor is not None:
            return ctor(prop, valu, **props)

        tname = self.getPropTypeName(prop)
        if tname is None and self.enforce:
            raise s_common.NoSuchForm(name=prop)

        # special case for adding nodes with a guid primary property
        # if the value None is specified, generate a new guid and skip
        # deconfliction ( allows highly performant "event" ingest )
        deconf = True
        if valu is None:
            if tname and self.isSubType(tname, 'guid'):
                valu = s_common.guid()
                deconf = False

        valu, subs = self.getPropNorm(prop, valu)

        with self.getCoreXact() as xact:

            if deconf:
                tufo = self.getTufoByProp(prop, valu=valu)
                if tufo is not None:
                    return tufo

            tick = s_common.now()
            iden = s_common.guid()

            props.update(subs)

            fulls, toadd = self._normTufoProps(prop, props, isadd=True)

            # create a "full" props dict which includes defaults
            self._addDefProps(prop, fulls)

            fulls[prop] = valu
            fulls['tufo:form'] = prop

            # update our runtime form counters
            self.formed[prop] += 1

            # fire these immediately since we need them to potentially fill
            # in values before we generate rows for the new tufo
            self.fire('node:form', form=prop, valu=valu, props=fulls)

            # Ensure we have ALL the required props after node:form is fired.
            self._reqProps(prop, fulls)

            rows = [(iden, p, v, tick) for (p, v) in fulls.items()]

            self.addRows(rows)

            tufo = (iden, fulls)

            if self.caching:
                # avoid .new in cache
                cachefo = (iden, dict(fulls))
                for p, v in fulls.items():
                    self._bumpTufoCache(cachefo, p, None, v)

            # fire notification events
            xact.fire('node:add', form=prop, valu=valu, node=tufo)
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
        self.fire('node:del', form=form, valu=valu, node=tufo)

        for name, tick in self.getTufoDsets(tufo):
            self.delTufoDset(tufo, name)

        if self.caching:
            for prop, valu in list(tufo[1].items()):
                self._bumpTufoCache(tufo, prop, valu, None)

        iden = tufo[0]
        with self.getCoreXact() as xact:
            self.delRowsById(iden)
            # delete any dark props/rows
            self.delRowsById(iden[::-1])
            xact.spliced('node:del', form=form, valu=valu)

        lists = [p.split(':', 2)[2] for p in tufo[1].keys() if p.startswith('tufo:list:')]
        for name in lists:
            self.delRowsByProp('%s:list:%s' % (iden, name))

    def addTufoDset(self, tufo, name):
        '''
        Add the tufo to a named dataset.
        '''
        dark = tufo[0][::-1]
        if self.getRowsByIdProp(dark, '_:dset', valu=name):
            return

        rows = [(dark, '_:dset', name, s_common.now())]

        self.addRows(rows)
        self.fire('syn:dset:add', name=name, node=tufo)

    def delTufoDset(self, tufo, name):
        dark = tufo[0][::-1]
        self.delRowsByIdProp(dark, '_:dset', name)
        self.fire('syn:dset:del', name=name, node=tufo)

    def getTufoDsets(self, tufo):
        '''
        Return a list of (name,time) tuples for dset membership.
        '''
        dark = tufo[0][::-1]
        return [(v, t) for (i, p, v, t) in self.getRowsByIdProp(dark, '_:dset')]

    def getTufosByDset(self, name, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of the tufos in the named dataset.

        Example:

            for tufo in getTufosByDset('woot'):
                dostuff(tufo)

        '''
        rows = self.getRowsByProp('_:dset', valu=name, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [r[0][::-1] for r in rows]

        ret = []
        for part in s_common.chunks(idens, 1000):
            ret.extend(self.getTufosByIdens(part))

        return ret

    def snapTufosByDset(self, name, mintime=None, maxtime=None, limit=None):
        rows = self.getRowsByProp('_:dset', valu=name, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [r[0][::-1] for r in rows]
        return self._initTufoSnap(idens)

    def snapTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = [r[0] for r in rows]
        return self._initTufoSnap(idens)

    def _initTufoSnap(self, idens):

        snap = s_common.guid()

        if not idens:
            return {'snap': snap, 'tufos': (), 'count': 0}

        count = len(idens)

        x = collections.deque(s_common.chunks(idens, 1000))

        rets = x.popleft()
        tufos = self.getTufosByIdens(rets)

        if x:
            self.snaps.put(snap, x)

        return {'snap': snap, 'tufos': tufos, 'count': count}

    def getSnapNext(self, snap):
        '''
        Get the next block of tufos for the given snapshot.
        '''
        x = self.snaps.get(snap)
        if x is None:
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
        valu, _ = self.getPropNorm(form, valu)

        item = self.getTufoByProp(form, valu)
        if item is not None:
            self.delTufo(item)

        return item

    def delTufosByProp(self, prop, valu=None):
        '''
        Delete multiple tufos by a single property.

        Example:

            core.delTufosByProp('foo:bar',valu=10)

        '''
        for item in self.getTufosByProp(prop, valu=valu):
            self.delTufo(item)

    def popTufosByProp(self, prop, valu=None):
        '''
        Delete and return multiple tufos by a property.

        Example:

            items = core.popTufosByProp('foo:bar',valu=10)

        '''
        items = self.getTufosByProp(prop, valu=valu)
        for item in items:
            self.delTufo(item)
        return items

    def _addDefProps(self, form, fulls):
        '''
        Add any default values for unspecified properties.
        '''
        for k, v in self.getFormDefs(form):
            fulls.setdefault(k, v)

    def _normTufoProps(self, form, inprops, tufo=None, isadd=False):
        '''
        This will both return a set of fully qualified props as a dict
        as well as modify inprops inband as a normalized set or relatives.
        '''

        toadd = set()

        props = {}
        for name in list(inprops.keys()):

            valu = inprops.get(name)

            prop = form + ':' + name
            if not self.isSetPropOk(prop, isadd=isadd):
                inprops.pop(name, None)
                continue

            oldv = None
            if tufo is not None:
                oldv = tufo[1].get(prop)

            valu, subs = self.getPropNorm(prop, valu, oldval=oldv)
            if tufo is not None and tufo[1].get(prop) == valu:
                inprops.pop(name, None)
                continue

            ptype = self.getPropTypeName(prop)
            if self.isTufoForm(ptype):
                toadd.add((ptype, valu))

            # any sub-properties to populate?
            for sname, svalu in subs.items():

                subprop = prop + ':' + sname
                if self.getPropDef(subprop) is None:
                    continue

                props[subprop] = svalu

                ptype = self.getPropTypeName(subprop)
                if self.isTufoForm(ptype):
                    toadd.add((ptype, svalu))

            props[prop] = valu
            inprops[name] = valu

        return props, toadd

    def addSaveLink(self, func):
        '''
        Add an event callback to receive save events for this cortex.

        Example:

            def savemesg(mesg):
                dostuff()

            core.addSaveLink(savemesg)

        '''
        self.store.addSaveLink(func)

    @s_telepath.clientside
    def formNodeByBytes(self, byts, stor=True, **props):
        '''
        Form a new file:bytes node by passing bytes and optional props.

        If stor=False is specified, the cortex will create the file:bytes
        node even if it is not configured with access to an axon to store
        the bytes.

        Args:
            byts (bytes):   The bytes for a file:bytes node
            stor (bool):    If True, attempt to store the bytes in an axon
            **props:        Additional props for the file:bytes node

        Example:

            core.formNodeByBytes(byts,name='foo.exe')

        '''

        hset = s_hashset.HashSet()
        hset.update(byts)

        iden, info = hset.guid()

        props.update(info)

        if stor:

            size = props.get('size')
            upid = self._getAxonWants('guid', iden, size)

            if upid is not None:
                for chun in s_common.chunks(byts, 10000000):
                    self._addAxonChunk(upid, chun)

        return self.formTufoByProp('file:bytes', iden, **props)

    @s_telepath.clientside
    def formNodeByFd(self, fd, stor=True, **props):
        '''
        Form a new file:bytes node by passing a file object and optional props.

        Args:
            fd (file):      A file-like object to read file:bytes from.
            stor (bool):    If True, attempt to store the bytes in an axon
            **props:        Additional props for the file:bytes node

        '''
        hset = s_hashset.HashSet()
        iden, info = hset.eatfd(fd)

        props.update(info)

        if stor:

            size = props.get('size')
            upid = self._getAxonWants('guid', iden, size)

            # time to send it!
            if upid is not None:
                for byts in s_common.iterfd(fd):
                    self._addAxonChunk(upid, byts)

        node = self.formTufoByProp('file:bytes', iden, **props)

        if node[1].get('file:bytes:size') is None:
            self.setTufoProp(node, 'size', info.get('size'))

        return node

    def isSetPropOk(self, prop, isadd=False):
        '''
        Check for enforcement and validity of a full prop name.

        This can be used to determine if a property name may be set on a node,
        given the data models currently loaded in a Cortex.

        Args:
            prop (str): Full property name to check.

        Examples:
            Check if a value is valid before calling a function.::

                prop = 'foo:bar:baz'
                if core.isSetPropOk(prop):
                    doSomething(...)

        Returns:
            bool: True if the property can be set on the node; False if it cannot be set.
        '''
        #
        if not self.enforce:
            return True

        pdef = self.getPropDef(prop)
        if pdef is None:
            return False

        if not isadd and pdef[1].get('ro'):
            return False

        return True

    def delTufoProp(self, tufo, name):
        '''
        Delete a property from a node in tufo format.

        Args:
            tufo ((str,dict)):  The node in tufo form
            name (str): The relative property name to delete

        Returns:
            ((str,dict))    The updated node in tufo form

        '''
        form, valu = s_tufo.ndef(tufo)

        prop = form + ':' + name

        pdef = self.getPropDef(prop)

        if pdef is not None:

            # if the prop is read only, it may not be deleted
            if pdef[1].get('ro'):
                raise s_common.CantDelProp(name=prop, mesg='property is read only')

            # if the prop has a default value, it may not be deleted
            if pdef[1].get('defval') is not None:
                raise s_common.CantDelProp(name=prop, mesg='property has default value')

        oldv = tufo[1].pop(prop, None)
        if oldv is None:
            return tufo

        with self.getCoreXact() as xact:

            # update the tufo cache if present
            if self.caching:
                self._bumpTufoCache(tufo, prop, oldv, None)

            # delete the rows from the storage layer...
            self.delRowsByIdProp(tufo[0], prop)

            # fire notification event
            xact.fire('node:prop:del', form=form, valu=valu, prop=prop, oldv=oldv, node=tufo)

            # fire the splice event
            xact.spliced('node:prop:del', form=form, valu=valu, prop=prop)

        return tufo

    def setTufoProps(self, tufo, **props):
        '''
        Set ( with de-duplication ) the given tufo props.

        Args:
            tufo ((str, dict)): The tufo to set properties on.
            **props:  Properties to set on the tufo.

        Examples:
            ::

                tufo = core.setTufoProps(tufo, woot='hehe', blah=10)

        Returns:
            ((str, dict)): The source tufo, with any updated properties.
        '''
        reqiden(tufo)
        # add tufo form prefix to props
        form = tufo[1].get('tufo:form')
        fulls, toadd = self._normTufoProps(form, props, tufo=tufo)
        if not fulls:
            return tufo

        iden = tufo[0]
        valu = tufo[1].get(form)

        with self.getCoreXact() as xact:

            for p, v in fulls.items():

                oldv = tufo[1].get(p)
                self.setRowsByIdProp(iden, p, v)

                tufo[1][p] = v

                # update the tufo cache if present
                if self.caching:
                    self._bumpTufoCache(tufo, p, oldv, v)

                # fire notification event
                xact.fire('node:prop:set', form=form, valu=valu, prop=p, newv=v, oldv=oldv, node=tufo)

                # fire the splice event
                xact.spliced('node:prop:set', form=form, valu=valu, prop=p[len(form) + 1:], newv=v, oldv=oldv,
                             node=tufo)

            if self.autoadd:
                self._runAutoAdd(toadd)

        return tufo

    def setTufoProp(self, tufo, prop, valu):
        '''
        Set a single tufo property.

        Example:

            core.setTufoProp(tufo, 'woot', 'hehe')

        '''
        self.setTufoProps(tufo, **{prop: valu})
        return tufo

    def incTufoProp(self, tufo, prop, incval=1):
        '''
        Atomically increment/decrement the value of a given tufo property.

        Example:

            tufo = core.incTufoProp(tufo,prop)

        '''
        form = tufo[1].get('tufo:form')
        prop = form + ':' + prop

        if not self.isSetPropOk(prop):
            return tufo

        return self._incTufoProp(tufo, prop, incval=incval)

    def _incTufoProp(self, tufo, prop, incval=1):

        # to allow storage layer optimization
        iden = tufo[0]

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        with self.inclock:
            rows = self.getRowsByIdProp(iden, prop)
            if len(rows) == 0:
                raise s_common.NoSuchTufo(iden=iden, prop=prop)

            oldv = rows[0][2]
            newv = oldv + incval

            self.setRowsByIdProp(iden, prop, newv)

            tufo[1][prop] = newv
            self.fire('node:prop:set', form=form, valu=valu, prop=prop, newv=newv, oldv=oldv, node=tufo)

        return tufo

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)

        '''
        return self.store.delRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete a group of rows by selecting for property and joining on iden.

        Example:

            core.delJoinByProp('foo',valu=10)

        '''
        return self.store._delJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def _getPivotRows(self, prop, byprop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self.store.getRowsByProp(byprop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit):
            for jrow in self.store.getRowsByIdProp(irow[0], prop):
                yield jrow

    def _calcStatSum(self, rows):
        return sum([r[2] for r in rows])

    def _calcStatHisto(self, rows):
        histo = collections.defaultdict(int)
        for row in rows:
            histo[row[2]] += 1
        return histo

    def _calcStatCount(self, rows):
        return len(rows)

    def _calcStatMin(self, rows):
        return min([r[2] for r in rows])

    def _calcStatMax(self, rows):
        return max([r[2] for r in rows])

    def _calcStatMean(self, rows):
        count = len(rows)
        tot = sum([r[2] for r in rows])
        return tot / float(count)

    def _calcStatAny(self, rows):
        return any([r[2] for r in rows])

    def _calcStatAll(self, rows):
        return all([r[2] for r in rows])

    def _tufosByIn(self, prop, valus, limit=None):
        if len(valus) == 0:
            return []

        _valus = []
        for valu in valus:
            nv, _ = self.getPropNorm(prop, valu)
            _valus.append(nv)

        rows = self.store.getJoinsBy('in', prop, _valus, limit=limit)
        return s_common.rowstotufos(rows)

    def _tufosByInetCidr(self, prop, valu, limit=None):
        lowerbound, upperbound = self.getTypeCast('inet:ipv4:cidr', valu)
        return self.getTufosBy('range', prop, (lowerbound, upperbound), limit=limit)

    def _onTufoAddSynType(self, mesg):
        tufo = mesg[1].get('node')
        if tufo is None:
            return

        self._initTypeTufo(tufo)

    def _onTufoAddSynForm(self, mesg):
        tufo = mesg[1].get('node')
        if tufo is None:
            return

        self._initFormTufo(tufo)

    def _onTufoAddSynProp(self, mesg):
        tufo = mesg[1].get('node')
        if tufo is None:
            return

        self._initPropTufo(tufo)

    def _initTypeTufo(self, tufo):
        '''
        Initialize a TypeLib Type from syn:type tufo
        '''
        name = tufo[1].get('syn:type')
        info = s_tufo.props(tufo)
        self.addType(name, **info)

    def _initFormTufo(self, tufo):
        '''
        Initialize a DataModel Form from syn:form tufo
        '''
        name = tufo[1].get('syn:form')
        info = s_tufo.props(tufo)
        # add the tufo definition to the DataModel
        self.addTufoForm(name, **info)

    def _initPropTufo(self, tufo):
        '''
        Initialize a DataModel Prop from syn:prop tufo
        '''
        name = tufo[1].get('syn:prop')
        info = s_tufo.props(tufo)

        form = info.pop('form')
        prop = name[len(form) + 1:]

        self.addTufoProp(form, prop, **info)
        return

    def _stormOperStat(self, query, oper):

        #TODO make these also operate on already lifted tufos
        name, prop = oper[1].get('args')
        kwargs = dict(oper[1].get('kwlist'))

        valu = kwargs.get('valu')
        sval = self.getStatByProp(name, prop, valu=valu)

        query.add(s_tufo.ephem('stat:' + name, prop, valu=sval))

    def _stormOperDset(self, query, oper):
        for name in oper[1].get('args'):
            [query.add(t) for t in self.getTufosByDset(name)]

    # some helpers to allow *all* queries to be processed via getTufosBy()
    def _tufosByEq(self, prop, valu, limit=None):
        return self.getTufosByProp(prop, valu=valu, limit=limit)

    def _tufosByHas(self, prop, valu, limit=None):
        return self.getTufosByProp(prop, limit=limit)

    def _tufosByTag(self, prop, valu, limit=None):
        return self.getTufosByTag(valu, form=prop, limit=limit)

    def _tufosByType(self, prop, valu, limit=None):
        return self.getTufosByPropType(prop, valu=valu, limit=limit)

    def _tufosByDark(self, prop, valu, limit=None):
        return self.getTufosByDark(name=prop, valu=valu, limit=limit)

    def getSplicePump(self, core):
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
        pump.onfini(wrkr.fini)

        return pump

    def getCoreXact(self, size=1000):
        '''
        Get a Storage transaction context for use in a with block.

        This object allows bulk storage layer optimization and proper ordering
        of events.  The context manager created through this function supports
        firing splice events.

        Args:
            size (int): Number of transactions to cache before starting to
                execute storage layer events.

        Examples:
            Get a context manager, use it to do stuff and fire splices::

                with core.getCoreXact() as xact:
                    result = dostuff()
                    xact.spliced('some:slice:evt', **result)

        Notes:
            This API does **not** work over a Telepath proxy object and it
            will raise an exception. Managing a transaction with from a remote
            caller is inherently difficult since the transaction can be
            opened, the caller then go away, unfortunately leaving the system
            in a weird state.

        Returns:
            s_xact.StoreXact: Transaction context manager.
        '''
        return self.store.getCoreXact(size=size, core=self)

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
        dark_name = '_:dark:' + name
        if self.getRowsByIdProp(dark, dark_name, valu=valu):
            return

        rows = [(dark, dark_name, valu, s_common.now())]
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
        self.delRowsByIdProp(dark, '_:dark:' + name, valu)

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
        dprop = '_:dark:' + name
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
        prop = '_:dark:' + name
        return self._getTufosByDarkRows(prop, valu=valu, limit=limit)

    def _getTufosByDarkRows(self, prop, valu=None, limit=None):
        rows = self.getRowsByProp(prop, valu=valu, limit=limit)
        idens = list(set([r[0][::-1] for r in rows]))  # Unique the idens we pull.

        ret = []
        for part in s_common.chunks(idens, 1000):
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
        rows = self.getRowsByProp('_:dark:' + name, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        idens = list(set([r[0][::-1] for r in rows]))  # Unique the idens we pull.
        return self._initTufoSnap(idens)

    def getStoreType(self):
        return self.store.getStoreType()

    # TODO: Wrap this in a userauth layer
    def getBlobValu(self, key, default=None):
        '''
        Get a value from the blob key/value (KV) store.

        This resides below the tufo storage layer and is Cortex implementation
        dependent. In purely memory backed cortexes, this KV store may not be
        persistent, even if the tufo-layer is persistent, through something
        such as the savefile mechanism.

        Notes:
            Data which is retrieved from the KV store is msgpacked, so caveats
            with that apply.

        Args:
            key (str): Value to retrieve
            default: Value returned if the key is not present in the blob store.

        Returns:
            The value from the KV store or the default valu (None).

        '''
        return self.store.getBlobValu(key, default)

    # TODO: Wrap this in a userauth layer
    def getBlobKeys(self):
        '''
        Get a list of keys in the blob key/value store.

        Returns:
            list: List of keys in the store.
        '''
        return self.store.getBlobKeys()

    # TODO: Wrap this in a userauth layer
    def setBlobValu(self, key, valu):
        '''
        Set a value from the blob key/value (KV) store.

        This resides below the tufo storage layer and is Cortex implementation
        dependent. In purely memory backed cortexes, this KV store may not be
        persistent, even if the tufo-layer is persistent, through something
        such as the savefile mechanism.

        Notes:
            Data which is stored in the KV store is msgpacked, so caveats with
            that apply.

        Args:
            key (str): Name of the value to store.
            valu: Value to store in the KV store.

        Returns:
            The input value, unchanged.
        '''
        return self.store.setBlobValu(key, valu)

    # TODO: Wrap this in a userauth layer
    def hasBlobValu(self, key):
        '''
        Check the blob store to see if a key is present.

        Args:
            key (str): Key to check

        Returns:
            bool: If the key is present, returns True, otherwise False.

        '''
        return self.store.hasBlobValu(key)

    # TODO: Wrap this in a userauth layer
    def delBlobValu(self, key):
        '''
        Remove and return a value from the blob store.

        Args:
            key (str): Key to remove.

        Returns:
            Content in the blob store for a given key.

        Raises:
            NoSuchName: If the key is not present in the store.
        '''
        return self.store.delBlobValu(key)
