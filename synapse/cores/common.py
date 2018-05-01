import os
import json
import shutil
import logging
import itertools
import threading
import collections

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.storage as s_storage

import synapse.lib.auth as s_auth
import synapse.lib.cell as s_cell
import synapse.lib.fifo as s_fifo
import synapse.lib.tags as s_tags
import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest
import synapse.lib.syntax as s_syntax
import synapse.lib.reflect as s_reflect
import synapse.lib.service as s_service
import synapse.lib.hashset as s_hashset
import synapse.lib.threads as s_threads
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack
import synapse.lib.trigger as s_trigger
import synapse.lib.version as s_version
import synapse.lib.interval as s_interval
import synapse.lib.membrane as s_membrane

from synapse.eventbus import EventBus
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

class CoreApi:
    '''
    A limited Cortex API which is shared when auth:en=1
    '''
    def __init__(self, core, dmon):
        '''

        Args:
            core (Cortex): Cortex being shared.
            dmon (s_daemon.Daemon): A Daemon
        '''
        # Hold onto a reference to the core so we can
        # refer to it for any decorated functions.
        self.core = core
        # Hold a ref to core.auth so we can use the reqAdmin decorator.
        self.auth = core.auth

        # API for auth management
        self.authReact = self.core.authReact

        # APIs that do perms enforcement
        self.ask = self.core.ask
        self.eval = self.core.eval
        self.splices = self.core.splices

        # Metadata APIs that need no perms enforcement
        self.isDataModl = self.core.isDataModl
        self.isDataType = self.core.isDataType
        self.getConfDefs = self.core.getConfDefs
        self.getCoreMods = self.core.getCoreMods
        self.getPropNorm = self.core.getPropNorm
        self.getPropRepr = self.core.getPropRepr
        self.getTypeRepr = self.core.getTypeRepr
        self.getTypeNorm = self.core.getTypeNorm
        self.getModelDict = self.core.getModelDict
        self.getUnivProps = self.core.getUnivProps

        # getTufo
        self.getTufoByProp = self.core.getTufoByProp
        self.getTufoByIden = self.core.getTufoByIden

        # getTufos
        self.getTufosBy = self.core.getTufosBy
        self.getTufosByTag = self.core.getTufosByTag
        self.getTufoByIden = self.core.getTufoByIden
        self.getTufosByDark = self.core.getTufosByDark
        self.getTufosByProp = self.core.getTufosByProp
        self.getTufosByIdens = self.core.getTufosByIdens
        self.getTufosByDset = self.core.getTufosByDset
        self.getTufosByPropType = self.core.getTufosByPropType

        # getRows
        self.getRowsBy = self.core.getRowsBy
        self.getRowsByProp = self.core.getRowsByProp
        self.getRowsById = self.core.getRowsById
        self.getRowsByIdProp = self.core.getRowsByIdProp

        # allow on/off but no fire/dist
        self.on = self.core.on
        self.off = self.core.off

        # pushfile support
        self._formFileBytesNode = self.core._formFileBytesNode

    @s_telepath.clientside
    def formNodeByBytes(self, byts, stor=True, **props):
        hset = s_hashset.HashSet()
        hset.update(byts)
        iden, info = hset.guid()
        return self._formFileBytesNode(iden, info, [byts], stor, **props)

    @s_telepath.clientside
    def formNodeByFd(self, fd, stor=True, **props):
        hset = s_hashset.HashSet()
        data = []
        for byts in s_common.iterfd(fd):
            hset.update(byts)
            data.append(byts)
        iden, info = hset.guid()
        return self._formFileBytesNode(iden, info, data, stor, **props)

    # Methods which must be proxied
    def addTufoTag(self, tufo, tag, times=()):
        perm = ('node:tag:add', {'tag': tag})
        self.core.reqUserPerm(perm)
        return self.core.addTufoTag(tufo, tag, times)

    def addTufoTags(self, tufo, tags):
        with self.core.getCoreXact():
            [self.addTufoTag(tufo, tag) for tag in tags]
            return tufo

    def formTufosByProps(self, items):
        retval = []

        with self.core.getCoreXact() as xact:
            for form, valu, props in items:
                try:
                    retval.append(self.formTufoByProp(form, valu, **props))
                except Exception as e:
                    excinfo = s_common.excinfo(e)
                    excval = excinfo.pop('err')
                    retval.append(s_tufo.ephem('syn:err', excval, **excinfo))

        return tuple(retval)

    def formTufoByProp(self, prop, valu, **props):
        perm = ('node:add', {'form': prop})
        self.core.reqUserPerm(perm)
        return self.core.formTufoByProp(prop, valu, **props)

    def delTufoTag(self, tufo, tag):
        perm = ('node:tag:del', {'tag': tag})
        self.core.reqUserPerm(perm)
        return self.core.delTufoTag(tufo, tag)

    def setTufoProp(self, tufo, prop, valu):
        form, _ = s_tufo.ndef(tufo)
        perm = ('node:prop:set', {'form': form,
                                  'prop': prop})
        self.core.reqUserPerm(perm)
        return self.core.setTufoProp(tufo, prop, valu)

    @s_auth.reqAdmin
    def addDataModel(self, name, modl):
        return self.core.addDataModel(name, modl)

    @s_auth.reqAdmin
    def getConfOpts(self):
        return self.core.getConfOpts()

class Cortex(EventBus, DataModel, Runtime, s_ingest.IngestApi, s_telepath.Aware,
             s_auth.AuthMixin):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link, store, **conf):
        Runtime.__init__(self)
        EventBus.__init__(self)

        s_telepath.Aware.__init__(self)

        logger.debug('Initializing Cortex')

        # Store the link tufo
        self._link = link

        self.auth = None  # type: s_auth.Auth

        # Core modules and model related structs
        self.modules = [(ctor, modconf) for ctor, smod, modconf in s_modules.ctorlist]
        self.coremods = {}  # name:module ( CoreModule() )
        self.modsdone = False
        self.seedctors = {}
        self.modelrevlist = []

        # Tag Caches
        self._core_tags = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tag'))
        self._core_tagforms = s_cache.FixedCache(maxsize=10000, onmiss=self._getFormFunc('syn:tagform'))

        # we keep an in-ram set of "ephemeral" nodes which are runtime-only ( non-persistent )
        self.runt_forms = set()
        self.runt_props = collections.defaultdict(list)

        # We keep a cache of recently accessed nodes to redeuce hitting storage layers
        self.cache_fifo = collections.deque()               # [ ((prop,valu,limt), {
        self.cache_bykey = {}                               # (prop,valu,limt):( (prop,valu,limt), {iden:tufo,...} )
        self.cache_byiden = s_cache.RefDict()
        self.cache_byprop = collections.defaultdict(dict)   # (<prop>,<valu>):[ ((prop, valu, limt),  answ), ... ]

        # Function helpers
        self.statfuncs = {}
        self.tufosbymeths = {}

        # Runtime stats
        self.formed = collections.defaultdict(int)      # count tufos formed since startup

        # Cell Pool
        self.cellpool = None
        self.cellpool_ready = False

        # Axon
        self.axon_name = None
        self.axon_ready = False
        self.axon_client = None

        # Misc
        self.isok = True
        self.seqs = s_cache.KeyCache(self.getSeqNode)  # Used for sequence generation
        self.snaps = s_cache.Cache(maxtime=60)  # Used for caching tufos for the snaps apis
        self.inclock = threading.Lock()  # Used for atomically incrementing a tufo property
        self.spliceact = s_reactor.Reactor() # Reactor for handling splice events
        self._core_triggers = s_trigger.Triggers()  # Trigger subsystem
        self._core_membranes = {}

        # Initialize various helpers / callbacks
        self._initCoreSpliceHandlers()
        self._initCoreStatFuncs()
        self._initCoreTufosByHandlers()
        self._initCoreNodeEventHandlers()
        self._initCoreStormOpers()

        # Initialize the storage layer and register it
        self.store = store  # type: s_storage.Storage
        self._registerStore()

        # Initialize the datamodel and add universal props
        DataModel.__init__(self)
        self._addUnivProps()

        self.myfo = self.formTufoByProp('syn:core', 'self')
        self.isnew = self.myfo[1].get('.new', False)

        # Set handlers which are not race-condition prone; stamp in conf;
        # then set handlers and handle any config options which may have
        # need reacting to them.
        self._initCortexConfSetPre()

        logger.debug('Setting Cortex conf opts')

        self.setConfOpts(conf)

        s_auth.AuthMixin.__init__(self, self.auth)

        self._initCortexConfSetPost()

        # Load any syn:trigger nodes in the Cortex
        self._loadTrigNodes()

        logger.debug('Loading coremodules from s_modules.ctorlist')
        with self.getCoreXact() as xact:
            mods = [(ctor, modconf) for ctor, smod, modconf in s_modules.ctorlist]
            self.addCoreMods(mods)
        self.onfini(self._finiCoreMods)

        # allow modules a shot at hooking cortex events for model ctors
        logger.debug('Executing s_modules.call(addCoreOns, self)')
        for name, ret, exc in s_modules.call('addCoreOns', self):
            if exc is not None:
                logger.warning('%s.addCoreOns: %s' % (name, exc))

        # Initialize the IngestApi mixin
        s_ingest.IngestApi.__init__(self, self)

        logger.debug('Setting the syn:core:synapse:version value.')
        self.setBlobValu('syn:core:synapse:version', s_version.version)

        # The iden of self.myfo is persistent
        logger.debug('Done starting up cortex %s', self.myfo[0])

    def getTeleApi(self, dmon):

        if self.auth is None:
            return self

        return CoreApi(self, dmon)

    def reqUserPerm(self, perm, name=None, elev=True):

        if self.auth is None:
            return

        if name is None:
            name = s_auth.whoami()

        user = self.auth.users.get(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        if not user.allowed(perm, elev=elev):
            raise s_exc.AuthDeny(perm=perm, user=name)

    def _initCoreSpliceHandlers(self):
        self.spliceact.act('node:add', self._actNodeAdd)
        self.spliceact.act('node:del', self._actNodeDel)
        self.spliceact.act('node:prop:set', self._actNodePropSet)
        self.spliceact.act('node:prop:del', self._actNodePropDel)
        self.spliceact.act('node:tag:add', self._actNodeTagAdd)
        self.spliceact.act('node:tag:del', self._actNodeTagDel)
        self.spliceact.act('node:ival:set', self._actNodeIvalSet)
        self.spliceact.act('node:ival:del', self._actNodeIvalDel)

    def _initCoreStatFuncs(self):
        self.addStatFunc('any', self._calcStatAny)
        self.addStatFunc('all', self._calcStatAll)
        self.addStatFunc('min', self._calcStatMin)
        self.addStatFunc('max', self._calcStatMax)
        self.addStatFunc('sum', self._calcStatSum)
        self.addStatFunc('mean', self._calcStatMean)
        self.addStatFunc('count', self._calcStatCount)
        self.addStatFunc('histo', self._calcStatHisto)

    def _initCoreTufosByHandlers(self):
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

    def _initCoreNodeEventHandlers(self):
        self.on('node:del', self._onDelSynTag, form='syn:tag')
        self.on('node:form', self._onFormSynTag, form='syn:tag')
        self.on('node:add', self._loadTrigNodes, form='syn:trigger')
        self.on('node:del', self._loadTrigNodes, form='syn:trigger')
        self.on('node:prop:set', self._loadTrigNodes, form='syn:trigger')

    def _initCoreStormOpers(self):
        self.setOperFunc('stat', self._stormOperStat)
        self.setOperFunc('dset', self._stormOperDset)

    def _initCortexConfSetPre(self):
        # Setup handlers for confOpt changes which are not racy
        self.onConfOptSet('caching', self._onSetCaching)

    def _initCortexConfSetPost(self):

        # Configure our auth data:
        if self.getConfOpt('auth:en'):
            self._onSetAuthEn(True)
        self.onConfOptSet('auth:en', self._onSetAuthEn)

        # It is not safe to load modules during SetConfOpts() since the path
        # value may not be set due to dictionary ordering, and there may be
        # modules which rely on it being present
        self.onConfOptSet('modules', self._onSetMods)
        # Load any existing modules which may have been configured
        valu = self.getConfOpt('modules')
        if valu:
            self.fire('syn:conf:set:%s' % 'modules', valu=valu)

        # Add the cellpool handler
        self.onConfOptSet('cellpool:conf', self._onSetCellPoolConf)
        valu = self.getConfOpt('cellpool:conf')
        if valu:
            self.fire('syn:conf:set:%s' % 'cellpool:conf', valu=valu)

        # Add the axon:name handler - it relies on the cellpool:conf
        self.onConfOptSet('axon:name', self._onSetAxonName)
        valu = self.getConfOpt('axon:name')
        if valu:
            self.fire('syn:conf:set:%s' % 'axon:name', valu=valu)

    def addRuntNode(self, form, valu, props=None):
        '''
        Add a "runtime" node which does not persist.
        This is used for ephemeral node "look aside" registration.

        Args:
            form (str): The primary property for the node
            valu (obj): The primary value for the node
            props (dict): The node secondary properties ( if modeled, they will be indexed )

        Returns:
            ((None,dict)):  The ephemeral node

        '''
        if props is None:
            props = {}

        self.runt_forms.add(form)

        node = (None, {})
        norm, subs = self.getPropNorm(form, valu)

        node[1][form] = norm
        node[1]['tufo:form'] = form
        node[1]['node:created'] = s_common.now()
        node[1]['node:ndef'] = s_common.guid((form, norm))

        self.runt_props[(form, None)].append(node)
        self.runt_props[(form, norm)].append(node)

        for prop, pval in props.items():

            full = form + ':' + prop
            norm, subs = self.getPropNorm(full, pval)

            node[1][full] = norm
            self.runt_props[(full, None)].append(node)

            if self.getPropDef(full) is not None:
                self.runt_props[(full, norm)].append(node)

        return node

    def isRuntForm(self, prop):
        '''
        Returns True if the given property name is a runtime node form.

        Args:
            prop (str):  The property name

        Returns:
            (bool):  True if the property is a runtime node form.
        '''
        return prop in self.runt_forms

    def genCorePath(self, *paths):
        '''
        Construct and create a path relative to the cortex metadata dir (or Raise).

        Args:
            *paths ([str,]): A set of path elements

        Returns:
            str: Full path to the directory.

        Raises:
            ReqConfOpt: If the cortex does not have a metadata directory.
        '''
        ret = self.reqCorePath(*paths)
        s_common.gendir(ret)
        return ret

    def getCorePath(self, *paths):
        '''
        Construct a path relative to the cortex metadata dir (or None).

        Args:
            *paths ([str,]): A set of path elements

        Returns:
            (str):  The full path ( or None ).
        '''
        dirn = self.getConfOpt('dir')
        if dirn is None:
            return None

        return s_common.genpath(dirn, *paths)

    def reqCorePath(self, *paths):
        '''
        Use getCorePath and raise if dir is not set.

        Args:
            paths ([str,...]):  A list of path elements to join.

        Returns:
            (str):  The full path for the cortex directory.

        Raises:
            NoSuchOpt
        '''
        retn = self.getCorePath(*paths)
        if retn is None:
            raise s_common.ReqConfOpt(name='dir', mesg='reqCorePath requires a cortex dir')
        return retn

    def getCoreTasks(self):
        '''
        Get a list of tasks which have been registered on the Cortex.

        Returns:
            list: A list of tasks which may be tasked via storm task() command.
        '''
        ret = [name.split('task:')[1] for name in list(self._syn_funcs.keys()) if name.startswith('task:')]
        ret.sort()
        return ret

    def isRuntProp(self, prop):
        '''
        Return True if the given property name is a runtime node prop.

        Args:
            prop (str): The property name

        Returns:
            (bool): True if the property is a runtime node property.
        '''
        return (prop, None) in self.runt_props

    @staticmethod
    @confdef(name='common_cortex')
    def _cortex_condefs():
        confdefs = (

            ('dir', {'type': 'str',
                'doc': 'The cortex metadata directory'}),

            ('autoadd', {'type': 'bool', 'asloc': 'autoadd', 'defval': 1,
                'doc': 'Automatically add forms for props where type is form'}),

            ('auth:en', {'type': 'bool', 'defval': 0,
                'doc': 'Enable auth/perm enforcement for splicing/storm (requires a cortex dir setting)'}),

            ('auth:admin', {'type': 'str', 'defval': None,
                'doc': 'Bootstrap the given user name as an admin.'}),

            ('enforce', {'type': 'bool', 'asloc': 'enforce', 'defval': 1,
                'doc': 'Enables data model enforcement'}),

            ('caching', {'type': 'bool', 'asloc': 'caching', 'defval': 0,
                'doc': 'Enables caching layer in the cortex'}),

            ('cache:maxsize', {'type': 'int', 'asloc': 'cache_maxsize', 'defval': 1000,
                'doc': 'Enables caching layer in the cortex'}),

            ('rev:model', {'type': 'bool', 'defval': 1,
                'doc': 'Set to 0 to disallow model version updates'}),

            ('cellpool:conf', {'defval': None,
                'doc': 'Allows cortex to be aware of a neuron cell pool'}),

            ('cellpool:timeout', {'defval': 30, 'type': 'int', 'asloc': 'cell_timeout',
                'doc': 'Timeout for cellpool related operations'}),

            ('axon:name', {'defval': None,
                'doc': 'Allows cortex to be aware of an axon blob store'}),

            ('log:save', {'type': 'bool', 'asloc': 'logsave', 'defval': 0,
                'doc': 'Enables saving exceptions to the cortex as syn:log nodes'}),

            ('log:level', {'type': 'int', 'asloc': 'loglevel', 'defval': 0,
                'doc': 'Filters log events to >= level'}),

            ('modules', {'defval': (),
                'doc': 'An optional list of (pypath,conf) tuples for synapse modules to load'}),
        )
        return confdefs

    def _loadTrigNodes(self, *args):

        self._core_triggers.clear()

        for node in self.getTufosByProp('syn:trigger'):
            try:

                if not node[1].get('syn:trigger:en'):
                    continue

                self._trigFromTufo(node)

            except Exception as e:
                logger.warning('failed to load trigger: %r' % (node,))
                logger.exception(e)

    def _trigFromTufo(self, tufo):

        text = tufo[1].get('syn:trigger:on')
        perm, _ = s_syntax.parse_perm(text)

        text = tufo[1].get('syn:trigger:run')
        opers = s_syntax.parse(text)

        user = tufo[1].get('syn:trigger:user')

        def func(node):
            with s_auth.runas(user):
                self.run(opers, data=(node,))

        self._core_triggers.add(func, perm)

    def _fireNodeTrig(self, node, perm):
        # this is called by the xact handler
        self._core_triggers.trigger(perm, node)

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
        self.store.setModlVers(name, vers)

    def _addDataModels(self, modtups):

        DataModel._addDataModels(self, modtups)

        for name, modl in modtups:

            for tnam, tnfo in modl.get('types', ()):
                tdef = self.getTypeDef(tnam)
                self.addRuntNode('syn:type', tnam, props=tdef[1])

            for fnam, fnfo, props in modl.get('forms', ()):
                pdef = self.getPropDef(fnam)
                self.addRuntNode('syn:form', fnam, props=pdef[1])
                self.addRuntNode('syn:prop', fnam, props=pdef[1])

                for pnam, pnfo in props:
                    full = fnam + ':' + pnam
                    pdef = self.getPropDef(full)
                    self.addRuntNode('syn:prop', full, pdef[1])

    def _addUnivProps(self):
        for pname in self.uniprops:
            pdef = self.getPropDef(pname)
            self.addRuntNode('syn:prop', pname, pdef[1])

    def revModlVers(self, name, vers, func):
        '''
        Update and track a model version using a callback function.

        Args:
            name (str): The name of the model
            vers (int): The version int ( in YYYYMMDDHHMM int format )
            func (function):  The version update function

        Returns:
            (None)


        Each specified function is expected to update the cortex including data migration.
        '''
        if not self.getConfOpt('rev:model'):
            raise s_common.NoRevAllow(name=name, vers=vers)

        curv = self.getModlVers(name)
        if curv >= vers:
            return False

        mesg = 'Updating model [{}] from [{}] => [{}] - do *not* interrupt.'.format(name, curv, vers)
        logger.warning(mesg)
        self.log(logging.WARNING, mesg=mesg, name=name, curv=curv, vers=vers)

        # fire a pre-revision event into the storage layer to allow
        # tests to "hook" prior to migration callbacks to insert rows.
        self.store.fire('modl:vers:rev', name=name, vers=vers)

        func()
        mesg = 'Finished updating model [{}] to [{}].'.format(name, vers)
        logger.warning(mesg)
        self.log(logging.WARNING, mesg=mesg, name=name, curv=curv, vers=vers)

        self.setModlVers(name, vers)
        return True

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

    def _get_axon_client(self):
        if not self.cellpool_ready:
            raise s_common.NoSuchOpt(name='cellpool:conf', mesg='The cortex does not have a cell pool configured or it is not yet ready')
        if not self.axon_ready:
            raise s_common.NoSuchOpt(name='axon:name', mesg='The cortex does not have an axon configured or it is not yet ready')
        return self.axon_client

    def _axonclient_wants(self, hashes, timeout=None):
        client = self._get_axon_client()
        if timeout is None:
            timeout = self.cell_timeout
        return client.wants(hashes, timeout=timeout)

    def _axonclient_upload(self, genr, timeout=None):
        client = self._get_axon_client()
        if timeout is None:
            timeout = self.cell_timeout
        return client.upload(genr, timeout=timeout)

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

    def _onSetAuthEn(self, conf):
        if not conf:
            return

        dirn = self.getConfOpt('dir')
        if dirn is None:
            raise s_exc.ReqConfOpt(name='dir', mesg='auth:en=1 requires a cortex dir')

        path = self.genCorePath('auth')

        self.auth = s_auth.Auth(path)
        self.onfini(self.auth.fini)

        name = self.getConfOpt('auth:admin')
        if name is not None:

            user = self.auth.users.get(name)
            if user is None:
                user = self.auth.addUser(name)

            user.setAdmin(True)

    def _onSetCellPoolConf(self, conf):
        auth = conf.get('auth')
        if not auth:
            raise s_common.BadConfValu(mesg='auth must be set', key='cellpool:conf')
        auth = s_msgpack.un(s_common.debase64(auth))

        neuraddr = (conf.get('host'), conf.get('port'))
        if not all(part is not None for part in neuraddr):
            logger.info('Popping "auth" with private data from mesg.')
            conf.pop('auth', None)
            raise s_common.BadConfValu(mesg='host and port must be set', key='cellpool:conf')

        if self.cellpool:
            self.cellpool.fini()

        cellpool = s_cell.CellPool(auth, neuraddr)
        if not cellpool.neurwait(timeout=self.cell_timeout):
            cellpool.fini()
            logger.info('Popping "auth" with private data from mesg.')
            conf.pop('auth', None)
            raise s_common.BadConfValu(mesg='unable to set up cell pool', key='cellpool:conf')
        self.cellpool = cellpool
        self.onfini(self.cellpool.fini)

        self.cellpool_ready = True

    def _onSetAxonName(self, name):
        self.axon_name = name

        def _setAxonClient(sess):
            self.axon_client = s_axon.AxonClient(sess)
            self.axon_ready = True

        waiter = self.cellpool.waiter(1, 'cell:add')
        self.cellpool.add(name, _setAxonClient)
        waiter.wait(self.cell_timeout)

        # Setup a handler to react when the cellpool is disconnected from the axon
        def _onAxonDisconnect(mesg):
            self.axon_ready = False
            self.axon_client = None

        self.cellpool.on('cell:disc', _onAxonDisconnect, name=name)

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

            return modu

        except Exception as e:
            logger.exception(e)
            logger.warning('mod load fail: %s %s' % (ctor, e))
            return None

    def addCoreMods(self, mods):
        '''
        Add a list of (name,conf) tuples to the cortex.
        '''
        revs = []

        maxvers = collections.defaultdict(list)

        toadd = []
        isnew = set()

        for ctor, conf in mods:

            modu = self.initCoreModule(ctor, conf)
            if modu is None:
                continue

            for name, modl in modu.getBaseModels():

                # make sure the module's modl dict is loaded
                if not self.isDataModl(name):
                    toadd.append((name, modl))

                # set the model version to 0 if it's -1
                if self.getModlVers(name) == -1:
                    isnew.add(name)
                    self.setModlVers(name, 0)

            # group up versions by name so we can get max
            for name, vers, func in modu.getModlRevs():
                maxvers[name].append(vers)

                revs.append((vers, name, func))

        if toadd:
            self.addDataModels(toadd)

        # if we didn't have it at all, forward wind...
        for name, vals in maxvers.items():
            if name in isnew:
                self.setModlVers(name, max(vals))

        revs.sort()

        for vers, name, func in revs:
            self.revModlVers(name, vers, func)

    def _onSetMods(self, mods):
        self.addCoreMods(mods)

    def getCoreMods(self):
        '''
        Get a list of CoreModules loaded in the current Cortex.

        Returns:
            list: List of python paths to CoreModule classes which are loaded in the current Cortex.
        '''
        return list(self.coremods.keys())

    def _onSetCaching(self, valu):
        if not valu:
            self.cache_fifo.clear()
            self.cache_bykey.clear()
            self.cache_byiden.clear()
            self.cache_byprop.clear()

    def _actNodeAdd(self, mesg):

        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        tags = mesg[1].get('tags', ())
        props = mesg[1].get('props', {})

        node = self.formTufoByProp(form, valu, **props)

        for tag in tags:
            self.addTufoTag(node, tag)

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

        node = self.getTufoByProp(form, valu)
        if not node:
            return

        self.setTufoProp(node, prop, newv)

    def _actNodePropDel(self, mesg):

        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')

        node = self.getTufoByProp(form, valu)
        if not node:
            return

        self.delTufoProp(node, prop)

    def _actNodeTagAdd(self, mesg):

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        times = mesg[1].get('ival', ())

        node = self.getTufoByProp(form, valu)
        if not node:
            return

        self.addTufoTag(node, tag, times)

    def _actNodeTagDel(self, mesg):

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')
        valu = mesg[1].get('valu')

        node = self.getTufoByProp(form, valu)
        if not node:
            return

        self.delTufoTag(node, tag)

    def _actNodeIvalSet(self, mesg):

        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')
        ival = mesg[1].get('ival')

        node = self.getTufoByProp(form, valu)
        if not node:
            return

        self.setTufoIval(node, prop, ival)

    def _actNodeIvalDel(self, mesg):

        form = mesg[1].get('form')
        valu = mesg[1].get('valu')
        prop = mesg[1].get('prop')

        node = self.getTufoByProp(form, valu)
        if not node:
            return

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
        if self.auth is not None:
            self.reqUserPerm(mesg)

        self.spliceact.react(mesg)

    @s_telepath.clientside
    def addSpliceFd(self, fd):
        '''
        Write all cortex splice events to the specified file-like object.

        Example:

            fd = open('audit.mpk','r+b')
            core.addSpliceFd(fd)
        '''
        def save(mesg):
            fd.write(s_msgpack.en(mesg[1]['mesg']))
        self.on('splice', save)

    def eatSpliceFd(self, fd):
        '''
        Consume all cortex splice events from the given file-like object.
        The file bytes are expected to be msgpack encoded (str,dict) splice tuples.

        Example:

            fd = open('saved.mpk','rb')
            core.eatSyncFd(fd)

        '''
        for splices in s_common.chunks(s_msgpack.iterfd(fd), 1000):
            self.splices(splices)

    def _onDelSynTag(self, mesg):
        # deleting a tag node.  delete all sub tags and wipe tufos.
        valu = mesg[1].get('valu')

        [self.delTufo(t) for t in self.getTufosByProp('syn:tag:up', valu)]

        # do the (possibly very heavy) removal of the tag from all known forms.
        [self.delTufoTag(t, valu) for t in self.getTufosByTag(valu)]

        # Flush the tag caches
        self._core_tags.clear()
        self._core_tagforms.clear()

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
            dostuff('there are %d rows where 20 <= foo < 30 ' % (size,))

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

        # check our runt/ephemeral nodes...
        answ = self.runt_props.get((prop, valu))
        if answ is not None:
            return answ[0]

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

        # check our runt/ephemeral nodes...
        answ = self.runt_props.get((prop, norm))
        if answ is not None:
            return answ

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

        Examples:

            Form a node, and add the baz.faz tag to it::

                node = core.formTufoByProp('foo','bar')
                node = core.addTufoTag(tufo,'baz.faz')

            Add a timeboxed tag to a node::

                node = core.addTufoTag(tufo,'foo.bar@2012-2016')


            Add a list of times sample times to a tag to create a timebox

                timeslist = (1513382400000, 1513468800000)
                node = core.addTufoTag(tufo,'hehe.haha', times=timelist)

        Returns:
            ((str,dict)): The node in tuple form (with updated props)
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
                if ival:
                    xact.spliced('node:tag:add', form=form, valu=valu, tag=subtag, ival=ival)
                else:
                    xact.spliced('node:tag:add', form=form, valu=valu, tag=subtag)
                xact.trigger(tufo, 'node:tag:add', form=form, tag=subtag)

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
            Remove the tag baz tag (and its subtags) from all tufos tagged baz.faz::

                for tufo in core.getTufosByTag('baz.faz'):
                    core.delTufoTag(tufo,'baz')

            Remove a tag from a tufo and then do something with the tufo::

                tufo = core.delTufoTag(tufo, 'hehe.haha')
                dostuff(tufo)

        Returns:
            ((str,dict)): The node in tuple form (with updated props)
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
                xact.trigger(tufo, 'node:tag:del', form=form, tag=subtag)

                self.delTufoIval(tufo, subprop)

        return tufo

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
        tag, _ = self.getTypeNorm('syn:tag', tag)
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
            xact.trigger(tufo, 'node:ival:set', form=form, prop=name)

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
            xact.trigger(tufo, 'node:ival:del', form=form, prop=name)

        return tufo

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

        if valu is not None:
            valu, _ = self.getPropNorm(prop, valu)

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
                rows.append((iden, 'prim:json', json.dumps(item, sort_keys=True, separators=(',', ':')), tstamp))

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

            if isinstance(itype, int):
                props.append((path, item))
                continue

            if isinstance(itype, str):
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

    def _reqProps(self, form, fulls):
        if not self.enforce:
            return

        props = self.getFormReqs(form)
        props = set(props)

        # Add in universal props which are required
        props = props.union(self.unipropsreq)

        # Return fast for perf
        if not props:
            return

        # Special case for handling syn:prop:glob=1 on will not have a ptype
        # despite the model requiring a ptype to be present.
        if fulls.get('syn:prop:glob') and 'syn:prop:ptype' in props:
            props.remove('syn:prop:ptype')

        # Compute any missing props
        missing = props - set(fulls)
        if missing:
            raise s_common.PropNotFound(mesg='Node is missing required a prop during formation',
                                        prop=list(missing)[0], form=form)

    def formTufoByTufo(self, tufo):
        '''
        Form an (iden,info) tufo by extracting information from an existing one.

        Args:
            tufo ((str, dict)): An existing tufo to form a new tufo from.

        Examples:
            Create an IPv4 node from an existing node::

                t0 = (None, {'inet:ipv4':0x01020304, 'inet:ipv4:asn': 1024})
                new_tufo = core.formTufoByTufo(t0)

        Notes:
            This API uses the formTufoByProp API to form the new tufo; after extracting
            the form, primary property and sub properties from the input tufo.
            In addition, this API does not utilize the iden value present in the first
            element of the tuple when making a new node.

        Returns:
            ((str, dict)): The new tufo, or an existing tufo if the tufo already existed.
        '''
        form, valu = s_tufo.ndef(tufo)
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
        the existence of prop=valu and creating it if not present.

        Args:

            prop (str): The primary property (or form) of the node
            valu (obj): The primary valu for the node
            **props:    Additional secondary properties for the node

        Example:
            Make a node for the FQDN woot.com::

                tufo = core.formTufoByProp('inet:fqdn','woot.com')

        Notes:
            When forming nodes whose primary property is derived from the
            GuidType, deconfliction can be skipped if the value is set to
            None. This allows for high-speed ingest of event type data which
            does note require deconfliction.

            This API will fire a ``node:form`` event prior to creating rows,
            allowing callbacks to populate any additional properties on the
            node.  After node creation is finished, ``node:add`` events are
            fired on for the Cortex event bus, splices and triggers.

            For each property in the newly created node, a ``node:prop:set``
            event will be fired.

        Returns:
            ((str, dict)): The newly formed tufo, or the existing tufo if
            the node already exists.  The ephemeral property ".new" can be
            checked to see if the node was newly created or not.
        '''
        ctor = self.seedctors.get(prop)
        if ctor is not None:
            return ctor(prop, valu, **props)

        if self.enforce:
            self.reqTufoForm(prop)
        tname = self.getPropTypeName(prop)

        # special case for adding nodes with a guid primary property
        # if the value None is specified, generate a new guid and skip
        # deconfliction ( allows highly performant "event" ingest )
        deconf = True
        if valu is None:
            if tname and self.isSubType(tname, 'guid'):
                valu = s_common.guid()
                deconf = False

        valu, subs = self.getPropNorm(prop, valu)

        # dont allow formation of nodes which are runts
        if self.isRuntForm(prop):
            raise s_common.IsRuntProp(form=prop, valu=valu,
                  mesg='Runtime nodes may not be created with formTufoByProp')

        with self.getCoreXact() as xact:

            if deconf:
                tufo = self.getTufoByProp(prop, valu=valu)
                if tufo is not None:
                    if props:
                        tufo = self.setTufoProps(tufo, **props)
                    return tufo

            tick = s_common.now()
            iden = s_common.guid()

            props.update(subs)

            # create a "full" props dict which includes defaults
            fulls = self._normTufoProps(prop, props)
            self._addDefProps(prop, fulls)

            fulls[prop] = valu

            # Set universal node values
            fulls['tufo:form'] = prop
            fulls['node:created'] = s_common.now()
            fulls['node:ndef'] = s_common.guid((prop, valu))
            # fulls['node:ndef'] = self.reqPropNorm('node:ndef', (prop, valu))[0]

            # Examine the fulls dictionary and identify any props which are
            # themselves forms, and extract the form/valu/subs from the fulls
            # dictionary so we can later make those nodes
            toadds = None
            if self.autoadd:
                toadds = self._formToAdd(prop, fulls)

            # Remove any non-model props present in the props and fulls
            # dictionary which may have been added during _normTufoProps
            self._pruneFulls(prop, fulls, props, isadd=True)

            # update our runtime form counters
            self.formed[prop] += 1

            # Fire these immediately since we need them to potentially fill
            # in values before we generate rows for the new tufo. It is
            # possible this callback may generate extra-model values.
            self.fire('node:form', form=prop, valu=valu, props=fulls)

            # Ensure we have ALL the required props after node:form is fired.
            self._reqProps(prop, fulls)

            rows = [(iden, p, v, tick) for (p, v) in fulls.items()]

            self.addRows(rows)

            tufo = (iden, fulls)

            # Cache the tufo data now so we can avoid having a .new ephemeral
            # property in the cache
            if self.caching:
                cachefo = (iden, dict(fulls))
                for p, v in fulls.items():
                    self._bumpTufoCache(cachefo, p, None, v)

            # Run any autoadd nodes we may have. In the event of autoadds being
            # present, our subsequent node:add events are fired depth-first
            if self.autoadd and toadds is not None:
                self._runToAdd(toadds)

            # fire the node:add events from the xact
            xact.fire('node:add', form=prop, valu=valu, node=tufo)
            xact.spliced('node:add', form=prop, valu=valu, props=props)
            xact.trigger(tufo, 'node:add', form=prop)

            # fire prop set notifications for each prop
            for p, v in tufo[1].items():
                # fire notification event
                xact.fire('node:prop:set', form=prop, valu=valu, prop=p, newv=v, oldv=None, node=tufo)
                xact.trigger(tufo, 'node:prop:set', form=prop, prop=p)

        tufo[1]['.new'] = True
        return tufo

    def _pruneFulls(self, form, fulls, props, isadd=False):
        '''
        Modify fulls and props dicts in place to remove non-model props.

        Args:
            form (str): Form of the dictionary being operated on.
            fulls (dict): Dictionary of full property name & valu pairs.
            props (dict): Dictionary of property name & value pairs.
            isadd (bool): Bool indicating if the data is newly being added or not.

        Returns:
            None
        '''
        splitp = form + ':'
        for name in list(fulls.keys()):
            if name in self.uniprops:
                continue
            if not self.isSetPropOk(name, isadd):
                prop = name.split(splitp)[1]
                props.pop(prop, None)
                fulls.pop(name, None)

    def _formToAdd(self, form, fulls):
        '''
        Build a list of property, valu, **props from a dictionary of fulls.

        Args:
            form (str): Form of fulls
            fulls (dict):

        Returns:
            list: List of tuples (prop,valu,**props) for consumption by formTufoByProp.
        '''
        ret = []
        skips = self.uniprops
        valu = fulls.get(form)
        for fprop, fvalu in fulls.items():
            if fprop in skips:
                continue
            ptype = self.getPropTypeName(fprop)
            prefix = fprop + ':'
            plen = len(prefix)
            for stype in self.getTypeOfs(ptype):
                if self.isRuntForm(stype):
                    continue
                if self.isTufoForm(stype):
                    # We don't want to recurse on forming ourself with all our same properties
                    if stype == form and valu == fvalu:
                        continue
                    subs = {}

                    for _fprop, _fvalu in fulls.items():
                        if _fprop.startswith(prefix):
                            k = _fprop[plen:]
                            subs[k] = _fvalu
                    ret.append((stype, fvalu, subs))
        return ret

    def delTufo(self, tufo):
        '''
        Delete a tufo and it's associated props/lists/etc.


        Example:

            core.delTufo(foob)

        '''
        form, valu = s_tufo.ndef(tufo)
        logger.info('Deleting tufo: [%s]/[%s] by [%s]', form, valu, s_auth.whoami())

        for name, tick in self.getTufoDsets(tufo):
            self.delTufoDset(tufo, name)

        if self.caching:
            for prop, pvalu in list(tufo[1].items()):
                self._bumpTufoCache(tufo, prop, pvalu, None)

        iden = tufo[0]
        with self.getCoreXact() as xact:
            self.delRowsById(iden)
            # delete any dark props/rows
            self.delRowsById(iden[::-1])

            # fire set None events for the props.
            pref = form + ':'
            for p, v in tufo[1].items():
                if not p.startswith(pref):
                    continue

                xact.fire('node:prop:set', form=form, valu=valu, prop=p, newv=None, oldv=v, node=tufo)

            xact.fire('node:del', form=form, valu=valu, node=tufo)
            xact.spliced('node:del', form=form, valu=valu)
            xact.trigger(tufo, 'node:del', form=form)

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

    def _runToAdd(self, toadds):
        for form, valu, props in toadds:
            self.formTufoByProp(form, valu, **props)

    def _normTufoProps(self, form, props, tufo=None):
        '''
        This will both return a dict of fully qualified props as
        well as modify the given props dict inband to normalize
        the values.
        '''
        fulls = {}
        for name in list(props.keys()):

            valu = props.get(name)

            if name in self.uniprops:
                prop = name

            else:
                prop = form + ':' + name

            oldv = None
            if tufo is not None:
                oldv = tufo[1].get(prop)

            valu, subs = self.getPropNorm(prop, valu, oldval=oldv)
            if tufo is not None:
                if oldv == valu:
                    props.pop(name, None)
                    continue
                _isadd = not bool(oldv)
                if not self.isSetPropOk(prop, isadd=_isadd):
                    props.pop(name, None)
                    continue

            # any sub-properties to populate?
            for sname, svalu in subs.items():

                subprop = prop + ':' + sname
                if self.getPropDef(subprop) is None:
                    continue

                fulls[subprop] = svalu

            fulls[prop] = valu
            props[name] = valu

        return fulls

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
            core.formNodeByBytes(byts, name='foo.exe')
        '''
        hset = s_hashset.HashSet()
        hset.update(byts)
        iden, info = hset.guid()
        return self._formFileBytesNode(iden, info, [byts], stor, **props)

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
        data = []
        for byts in s_common.iterfd(fd):
            hset.update(byts)
            data.append(byts)
        iden, info = hset.guid()
        return self._formFileBytesNode(iden, info, data, stor, **props)

    def _formFileBytesNode(self, iden, info, data, stor=True, **props):
        perm = ('node:add', {'form': 'file:bytes'})
        self.reqUserPerm(perm)
        props.update(info)
        sha256 = s_common.uhex(info.get('sha256'))

        if stor and self._axonclient_wants([sha256]) is not None:
            logger.debug('uploading hash to axon: %r', sha256)
            self._axonclient_upload(data)

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
            isadd (bool): Bool indicating that the property check is being
            done on a property which has not yet been set on a node.

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
            xact.trigger(tufo, 'node:prop:del', form=form, prop=prop)

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
        fulls = self._normTufoProps(form, props, tufo=tufo)
        if not fulls:
            return tufo

        iden = tufo[0]
        valu = tufo[1].get(form)

        toadds = None
        if self.autoadd:
            toadds = self._formToAdd(form, fulls)
        self._pruneFulls(form, fulls, props, isadd=True)

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

                xact.trigger(tufo, 'node:prop:set', form=form, prop=p)

            if self.autoadd and toadds is not None:
                self._runToAdd(toadds)

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

        # strip the splice out of the event...
        def pumpmesg(mesg):
            pump.put(mesg[1].get('mesg'))

        self.on('splice', pumpmesg)

        def splicepump():

            while not self.isfini:

                try:

                    for msgs in pump.slices(1000):
                        errs = core.splices(msgs)
                        for err in errs:
                            logger.warning('splice pump: %r' % (err,))

                        logger.debug('Spliced [%s] mesgs, got [%s] errors, [%s] remaining in queue',
                                     len(msgs), len(errs), pump.size())

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

    # TODO: Wrap this in a auth layer
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

    # TODO: Wrap this in a auth layer
    def getBlobKeys(self):
        '''
        Get a list of keys in the blob key/value store.

        Returns:
            list: List of keys in the store.
        '''
        return self.store.getBlobKeys()

    # TODO: Wrap this in a auth layer
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

    # TODO: Wrap this in a auth layer
    def hasBlobValu(self, key):
        '''
        Check the blob store to see if a key is present.

        Args:
            key (str): Key to check

        Returns:
            bool: If the key is present, returns True, otherwise False.

        '''
        return self.store.hasBlobValu(key)

    # TODO: Wrap this in a auth layer
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
