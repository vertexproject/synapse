'''
Migrate storage from 0.1.x to 0.2.x.

TODO:
    - Support non-inplace migration?
    - Migrating mirrors (what about existing remote layer?)
    - Handling for pause/restart
    - Validation (esp. check .created)
    - Offset migration
    - Prompt and/or execute a backup?
    - Add ability to do a specific step on a specifc layer?
    - Any migr for views?  Need to iter over views?
    - Teardown / restore options
    - Set an error threshold for canceling migration?  esp on nodes?
    - need to execute a model migration also?  or can that be done after data migration?
    - inbound conditions to start, i.e. at least at 0.1.Y
    - check slab opening props
    - handle custom modules that may have a custom type (and therefore no stortype)
'''
import os
import sys
import time
import shutil
import asyncio
import logging
import argparse
import collections

import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.hive as s_hive
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.modelrev as s_modelrev

logger = logging.getLogger(__name__)

ALL_MIGROPS = (
    'dmodel',
    'hiveauth',
    'hivestor',
    'hivelyr',
    'nodes',
    'nodedata',
    'hive',
)

class Migrator(s_base.Base):
    '''
    Standalone tool for migrating Synapse storage.
    '''
    async def __anit__(self, conf):
        await s_base.Base.__anit__(self)
        self.migrdir = 'migration'

        self.dirn = conf.get('dirn')
        self.migrops = conf.get('migrops')
        self.migrlayer = conf.get('layer')
        self.nodelim = conf.get('nodelim')
        self.nexusoff = conf.get('nexusoff', False)
        self.usehivev1 = conf.get('usehivev1', False)

        if self.migrops is None:
            self.migrops = ALL_MIGROPS

        # data model
        self.model = None

        # create a new slab for tracking migration data
        path = os.path.join(self.dirn, self.migrdir, 'migr.lmdb')
        self.migrslab = await s_lmdbslab.Slab.anit(path, readonly=False)
        self.migrdb = self.migrslab.initdb('migr')
        self.onfini(self.migrslab.fini)

        # optionally create migration nexus
        if not self.nexusoff:
            path = os.path.join(self.dirn, self.migrdir)
            self.nexusroot = await s_nexus.NexsRoot.anit(path)
            self.onfini(self.nexusroot.fini)
            logger.info(f'Storing migration splices at {path}')
        else:
            self.nexusroot = None

        # open hive
        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        self.hiveslab = await s_lmdbslab.Slab.anit(path, readonly=False)
        self.onfini(self.hiveslab.fini)
        self.hivedb = self.hiveslab.initdb('hive')
        self.hivedb_v1 = self.hiveslab.initdb('hive_v1')  # on final step this will contain original copy
        self.hivedb_v2 = self.hiveslab.initdb('hive_v2')  # working copy during migration

        # copy hive before we get started
        if self.usehivev1:
            await self._migrHive(self.hivedb_v1, self.hivedb)  # can also be used to unwind hive migration
        await self._migrHive(self.hivedb, self.hivedb_v2, rmsrc=False)
        self.hive = await s_hive.SlabHive.anit(self.hiveslab, db=self.hivedb_v2)
        self.onfini(self.hive.fini)

    async def migrate(self):
        '''
        Execute the migration
        '''
        # datamodel migration
        if 'dmodel' in self.migrops:
            await self._migrDatamodel()

        # storage info migration
        if 'hivestor' in self.migrops:
            storinfo, layridens = await self._migrHiveStorInfo()
        else:
            storinfo, layridens = None, []

        if self.migrlayer is not None:
            logger.info(f'Restricting migration to one layer: {self.migrlayer}')
            layridens = [self.migrlayer]

        # full layer migration
        for iden in layridens:
            logger.info(f'Starting migration for storage {storinfo.get("iden")} and layer {iden}')
            wlyr = await self._destGetWlyr(self.dirn, storinfo, iden)

            if 'nodes' in self.migrops:
                await self._migrNodes(iden, wlyr)

            if 'nodedata' in self.migrops:
                await self._migrNodeData(iden, wlyr)

            # await self._migrOffsets(foo)  # TODO

            if 'hivelyr' in self.migrops:
                await self._migrHiveLayerInfo(storinfo, iden)

        # auth migration
        if 'hiveauth' in self.migrops:
            await self._migrHiveAuth()  # TODO

        # migrate cell (replace hive with hive_v2)
        if 'hive' in self.migrops:
            await self._migrHive(self.hivedb, self.hivedb_v1, rmsrc=False)
            await self._migrHive(self.hivedb_v2, self.hivedb, rmsrc=True)

    #############################################################
    # Migration operations
    #############################################################

    async def _migrHive(self, src, dest, rmsrc=False):
        '''
        Create a copy of the hive, overwriting destination and optionally removing source.

        Args:
            src (str): Target db to copy
            dest (str): Destination db to copy to
            rmsrc (bool): Whether to remove the source after copying
        '''
        migrop = 'hive'

        self.hiveslab.dropdb(dest)
        self.hiveslab.copydb(src, self.hiveslab, dest)

        if rmsrc:
            self.hiveslab.dropdb(src)

        logger.info(f'Completed Hive copy from {src} to {dest}')
        await self._migrlogAdd(migrop, 'prog', 'none', (src, dest, s_common.now()))

    async def _migrDatamodel(self):
        '''
        Load datamodel in order to fetch stortypes.
        Currently no data modification occuring.
        '''
        migrop = 'dmodel'

        self.model = s_datamodel.Model()

        # load core modules
        mods = list(s_modules.coremods)
        mdefs = []
        for mod in mods:
            modu = s_dyndeps.tryDynLocal(mod)
            mdefs.extend(modu.getModelDefs(self))  # probably not the self its expecting...

        self.model.addDataModels(mdefs)

        # load custom modules
        # check for cell.yaml first otherwise an empty file will be created by yamlload
        yamlpath = os.path.join(self.dirn, 'cell.yaml')
        if os.path.exists(yamlpath):
            conf = s_common.yamlload(self.dirn, 'cell.yaml')
            if conf is not None:
                mdefs = []
                for mod in conf.get('modules', []):
                    modu = s_dyndeps.tryDynLocal(mod)
                    mdefs.extend(modu.getModelDefs(self))

                self.model.addDataModels(mdefs)

        # load extended model
        extprops = await (await self.hive.open(('cortex', 'model', 'props'))).dict()
        extunivs = await (await self.hive.open(('cortex', 'model', 'univs'))).dict()
        exttagprops = await (await self.hive.open(('cortex', 'model', 'tagprops'))).dict()

        for form, prop, tdef, info in extprops.values():
            try:
                self.model.addFormProp(form, prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext prop ({form}:{prop}) error: {e}')

        for prop, tdef, info in extunivs.values():
            try:
                self.model.addUnivProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext univ ({prop}) error: {e}')

        for prop, tdef, info in exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext tag prop ({prop}) error: {e}')

        logger.info('Completed datamodel migration')
        await self._migrlogAdd(migrop, 'prog', 'none', s_common.now())

    async def _migrHiveAuth(self):
        '''
        TODO right now just blowing away authgates to allow startup
        '''
        migrop = 'hiveauth'
        await self.hive.pop(('auth', 'authgates'))

        logger.info('Completed HiveAuth migration')
        await self._migrlogAdd(migrop, 'prog', 'none', s_common.now())

    async def _migrHiveStorInfo(self):
        '''
        Migrate to new storage info syntax.

        Returns:
            (dict): Storage information
            (list): List of layer idens
        '''
        migrop = 'hivestor'

        # Set storage information
        storiden = s_common.guid()
        stornode = await self.hive.open(('cortex', 'storage', storiden))
        stordict = await stornode.dict()

        await stordict.set('iden', storiden)
        await stordict.set('type', 'local')
        await stordict.set('conf', {})

        storinfo = {
            'iden': storiden,
            'type': 'local',
            'conf': {},
        }

        # Set default storage
        await self.hive.set(('cellinfo', 'layr:stor:default'), storiden)

        # Get existing layers
        layridens = []
        for iden, layrnode in await self.hive.open(('cortex', 'layers')):
            layridens.append(iden)

        logger.info('Copmleted Hive storage info migration')
        await self._migrlogAdd(migrop, 'prog', storiden, s_common.now())

        return storinfo, layridens

    async def _migrHiveLayerInfo(self, storinfo, iden):
        '''
        As each layer is migrated update the hive info.

        TODO: Move some of this into a translation step

        Args:
            storinfo (dict): Storage information
            iden (str): Iden of the layer
        '''
        migrop = 'hivelyr'

        # get existing data from the hive
        lyrnode = await self.hive.open(('cortex', 'layers', iden))
        layrinfo = await lyrnode.dict()

        # owner -> creator
        creator = None
        owner = await layrinfo.pop('owner', default=None)
        if owner is None:
            owner = 'root'

        users = await self.hive.open(('auth', 'users'))
        usersd = await users.dict()
        for uiden, uname in usersd.items():
            if uname == owner:
                creator = uiden

        if creator is None:
            raise Exception('Unable to add creator')  # TODO: handle this differently

        # conf
        # TODO should be translating existing config?
        conf = {'lockmemory': True}

        # remove remaining 0.1.x keys
        # TODO check whether we should be keeping these...
        await layrinfo.pop('name')
        await layrinfo.pop('type')
        await layrinfo.pop('config')

        # update layer info for 0.1.x
        await layrinfo.set('iden', iden)
        await layrinfo.set('creator', creator)
        await layrinfo.set('conf', conf)
        await layrinfo.set('stor', storinfo.get('iden'))

        logger.info('Completed Hive layer info migration')
        await self._migrlogAdd(migrop, 'prog', iden, s_common.now())

    async def _migrNodes(self, iden, wlyr):
        '''
        Migrate nodes for a given layer.
        Individual operations are responsible for logging errors, with this migr method continuing past them.

        Args:
            iden (str): Iden of the layer
            wlyr (Layer): 0.2.0 Layer to write to
        '''
        migrop = 'nodes'
        nodelim = self.nodelim

        # open storage
        path = os.path.join(self.dirn, 'layers', iden, 'layer.lmdb')
        src_slab = await s_lmdbslab.Slab.anit(path, map_async=True, readonly=True)
        src_bybuid = src_slab.initdb('bybuid')  # <buid><prop>=<valu>
        self.onfini(src_slab.fini)

        # check if 0.2.0 write layer exists with data
        dest_fcntpre = await wlyr.getFormCounts()
        if dest_fcntpre:
            logger.warning(f'Destination {iden} is not empty')
            logger.debug(dest_fcntpre)

        # update modelrev
        await wlyr.setModelVers(s_modelrev.maxvers)

        # migrate data
        src_fcnt = collections.defaultdict(int)
        nodeedits = []
        editchnks = 10  # batch size for nodeedits to add
        t_strt = s_common.now()
        stot = 0
        async for node in self._srcIterNodes(src_slab, src_bybuid):
            form = node[1]['ndef'][0].replace('.', '').replace('*', '')
            src_fcnt[form] += 1

            stot += 1
            if nodelim is not None and stot >= nodelim:
                logger.warning(f'Stopping node migration due to reaching nodelim {stot}')
                # checkpoint is the next node to add
                await self._migrlogAdd(migrop, 'chkpnt', iden, (node[0], stot, s_common.now()))
                break

            if stot % 10000000 == 0:
                logger.info(f'...on node {stot:,} for layer {iden}')

            nodeedit = await self._trnNodeToNodeedit(node)
            if nodeedit is None:
                continue

            nodeedits.append(nodeedit)
            if len(nodeedits) == editchnks:
                await self._destAddNodes(migrop, wlyr, nodeedits)
                nodeedits = []
                await asyncio.sleep(0)

        # add last edit chunk if needed
        if len(nodeedits) > 0:
            await self._destAddNodes(migrop, wlyr, nodeedits)

        t_end = s_common.now()
        t_dur = t_end - t_strt
        t_dur_s = int(t_dur / 1000) + 1

        # collect final destination form count stats
        dest_fcnt = await wlyr.getFormCounts()

        # store and log creation stats
        rprt = ['\n', '{:<25s}{:<10s}{:<10s}'.format('FORM', 'SRC_CNT', 'DEST_CNT')]
        stot = 0
        dtot = 0
        for form, scnt in src_fcnt.items():
            stot += scnt
            dcnt = dest_fcnt.get(form, 0)
            dtot += dcnt
            rprt.append('{:<25s}{!s:<10s}{!s:<10s}'.format(form, scnt, dcnt))
            await self._migrlogAdd(migrop, 'stat', f'{iden}:form', (scnt, dcnt))

        rprt.append('\n')
        prprt = '\n'.join(rprt)
        logger.debug(f'Final form count for {iden}: {prprt}')

        await self._migrlogAdd(migrop, 'stat', f'{iden}:totnodes', (stot, dtot))
        await self._migrlogAdd(migrop, 'stat', f'{iden}:duration', (stot, t_dur))

        logger.info(f'Migrated {stot:,} nodes in {t_dur_s} seconds ({int(stot/t_dur_s)} nodes/s avg)')
        logger.info(f'Completed node migration for {iden}')
        await self._migrlogAdd(migrop, 'prog', iden, s_common.now())

        return

    async def _migrNodeData(self, iden, wlyr):
        '''
        Migrate nodedata for a given layer.
        Individual operations are responsible for logging errors, with this migr method continuing past them.

        Args:
            iden (str): Iden of the layer
            wlyr (Layer): 0.2.0 Layer to write to
        '''
        migrop = 'nodedata'
        nodelim = self.nodelim

        # open storage
        path = os.path.join(self.dirn, 'layers', iden, 'nodedata.lmdb')
        src_slab = await s_lmdbslab.Slab.anit(path, map_async=True, readonly=True)
        src_bybuid = src_slab.initdb('bybuid')
        self.onfini(src_slab.fini)

        # migrate data
        nodeedits = []
        editchnks = 10  # batch size for nodeedits to add
        t_strt = s_common.now()
        stot = 0
        async for nodedata in self._srcIterNodedata(src_slab, src_bybuid):
            stot += 1
            if nodelim is not None and stot >= nodelim:
                logger.warning(f'Stopping nodedata migration due to reaching nodelim {stot}')
                # checkpoint is the next node to add
                await self._migrlogAdd(migrop, 'chkpnt', iden, (nodedata, stot, s_common.now()))
                break

            if stot % 1000000 == 0:
                logger.info(f'...on node {stot:,} for layer {iden}')

            nodeedit = await self._trnNodedataToNodeedit(nodedata)
            if nodeedit is None:
                continue

            nodeedits.append(nodeedit)
            if len(nodeedits) == editchnks:
                await self._destAddNodes(migrop, wlyr, nodeedits)
                nodeedits = []
                await asyncio.sleep(0)

        # add last edit chunk if needed
        if len(nodeedits) > 0:
            await self._destAddNodes(migrop, wlyr, nodeedits)

        t_end = s_common.now()
        t_dur = t_end - t_strt
        t_dur_s = int(t_dur / 1000) + 1

        logger.info(f'Migrated {stot:,} nodedata entries in {t_dur_s} seconds ({int(stot/t_dur_s)} nodes/s avg)')
        await self._migrlogAdd(migrop, 'stat', f'{iden}:totnodes', (stot, stot))
        await self._migrlogAdd(migrop, 'stat', f'{iden}:duration', (stot, t_dur))

        logger.info(f'Completed nodedata migration for {iden}')
        await self._migrlogAdd(migrop, 'prog', iden, s_common.now())

        return

    #############################################################
    # Migration logging / record keeping
    #############################################################

    async def _migrlogAdd(self, migrop, logtyp, key, val):
        '''
        Add an error record to the migration data

        TODO:
            - enum for migrop

        Args:
            migrop:
            logtyp:
            key:
            val:
        '''
        if isinstance(key, bytes):
            bkey = key
        else:
            bkey = key.encode()

        lkey = migrop.encode() + b'00' + logtyp.encode() + b'00' + bkey
        lval = s_msgpack.en(val)
        try:
            self.migrslab.put(lkey, lval, db=self.migrdb)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f'Unable to store migration log: {migrop}; {logtyp}; {key}; {val}')
            pass

    async def _migrlogGet(self, migrop, logtyp, key=None):
        pass  # TODO

    #############################################################
    # Source (0.1.x) operations
    #############################################################

    async def _srcPackNode(self, buid, ndef, props, tags, tagprops):
        '''
        Return a packaged node
        '''
        return (buid, {
            'ndef': ndef,
            'props': props,
            'tags': tags,
            'tagprops': tagprops,
        })

    async def _srcIterNodes(self, buidslab, buiddb):
        '''
        Yield node information directly from the 0.1.x source slab.

        Yields:
            (tuple):
                (<buid>, {
                    'ndef': (<formname>, <formvalu>),
                    'props': {<propname>: <propvalu>, ...},
                    'tags': {<tagname>: <tagvalu>, ...},
                    'tagprops': {
                        <tagname>: {<propname>: <propvalu>, ...},
                        ...
                    }
                )
        '''
        buid = None
        ndef = None
        props = {}
        tags = {}
        tagprops = collections.defaultdict(dict)
        for lkey, lval in buidslab.scanByFull(db=buiddb):
            rowbuid = lkey[0:32]
            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)  # throwing away indx

            # new node; if not at start, yield the last node and reset
            if buid is not None and rowbuid != buid:
                yield await self._srcPackNode(buid, ndef, props, tags, tagprops)
                buid = None
                ndef = None
                props = {}
                tags = {}
                tagprops = collections.defaultdict(dict)

            if buid is None:
                buid = rowbuid

            # add node information
            if prop[0] == '*':
                if ndef is None:
                    ndef = (prop, valu)
                else:
                    props[prop] = valu

            elif prop[0] == '#':
                if ':' in prop:  # tagprop
                    tname, tprop = prop.split(':')
                    tagprops[tname][tprop] = valu
                else:
                    tags[prop] = valu

            else:
                props[prop] = valu

        # yield last node
        yield await self._srcPackNode(buid, ndef, props, tags, tagprops)

    async def _srcIterNodedata(self, buidslab, buiddb):
        '''
        Iterate over 0.1.0 nodedata

        Yields:
            (tuple): buid, name, val
        '''
        for lkey, lval in buidslab.scanByFull(db=buiddb):
            yield lkey[:32], lkey[32:].decode(), s_msgpack.un(lval)

    #############################################################
    # Translation operations
    #############################################################

    async def _trnNodeToNodeedit(self, node):
        '''
        Create translation of node info to an 0.2.0 node edit.

        Args:
            node (tuple): (<buid>, {'ndef': ..., 'props': ..., 'tags': ..., 'tagprops': ...}

        Returns:
            nodeedit (tuple): (<buid>, <form>, [edits]) where edits is list of (<type>, <info>)
        '''
        migrop = 'nodes'

        buid = node[0]
        form = node[1]['ndef'][0]
        fval = node[1]['ndef'][1]

        if form[0] == '*':
            formnorm = form[1:]
        else:
            err = {'mesg': f'Unable to norm form {form}', 'node': node}
            logger.error(err['mesg'])
            logger.debug(err)
            await self._migrlogAdd(migrop, 'error', buid, err)
            return None

        edits = []

        # setup storage type
        mform = self.model.form(formnorm)
        if mform is None:
            err = {'mesg': f'Unable to determine form for {formnorm}', 'node': node}
            logger.error(err['mesg'])
            logger.debug(err)
            await self._migrlogAdd(migrop, 'error', buid, err)
            return None

        # create first edit for the node

        if not hasattr(mform.type, 'stortype') or mform.type.stortype is None:
            err = {'mesg': f'Unable to determine stortype for {formnorm}', 'node': node}
            logger.error(err['mesg'])
            logger.debug(err)
            await self._migrlogAdd(migrop, 'error', buid, err)
            return None

        stortype = mform.type.stortype
        edits.append((s_layer.EDIT_NODE_ADD, (fval, stortype)))  # name, stype

        # iterate over secondary properties
        for sprop, sval in node[1]['props'].items():
            sformnorm = sprop.replace('*', '')
            prop = mform.prop(sformnorm)
            if prop is None or not hasattr(prop.type, 'stortype') or prop.type.stortype is None:
                err = {'mesg': f'Unable to determine stortype for sprop {formnorm}, {sformnorm}', 'node': node}
                logger.error(err['mesg'])
                logger.debug(err)
                await self._migrlogAdd(migrop, 'error', buid, err)
                return None

            stortype = prop.type.stortype
            edits.append((s_layer.EDIT_PROP_SET, (sformnorm, sval, None, stortype)))  # name, valu, oldv, stype

        # set tags
        for tname, tval in node[1]['tags'].items():
            tnamenorm = tname[1:]
            edits.append((s_layer.EDIT_TAG_SET, (tnamenorm, tval, None)))  # tag, valu, oldv

        # tagprops
        for tname, tprops in node[1]['tagprops'].items():
            tnamenorm = tname[1:]

            for tpname, tpval in tprops.items():
                tptype = self.model.tagprops.get(tpname)

                if tptype is None:
                    err = {'mesg': f'Unable to find tagprop datamodel for {tpname}', 'node': node}
                    logger.error(err['mesg'])
                    logger.debug(err)
                    await self._migrlogAdd(migrop, 'error', buid, err)
                    return None

                if not hasattr(tptype.base, 'stortype') or tptype.base.stortype is None:
                    err = {'mesg': f'Unable to determine stortype for {tpname}', 'node': node}
                    logger.error(err['mesg'])
                    logger.debug(err)
                    await self._migrlogAdd(migrop, 'error', buid, err)
                    return None

                stortype = tptype.base.stortype
                edits.append((s_layer.EDIT_TAGPROP_SET,
                              (tnamenorm, tpname, tpval, None, stortype)))  # tag, prop, valu, oldv, stype

        return buid, formnorm, edits

    async def _trnNodedataToNodeedit(self, nodedata):
        '''
        Create translation of node info to an 0.2.0 node edit.

        Args:
            node (tuple): (<buid>, <name>, <val>)

        Returns:
            nodeedit (tuple): (<buid>, <form>, [edits]) where edits is list of (<type>, <info>)
        '''
        migrop = 'nodedata'

        buid = nodedata[0]
        name = nodedata[1]
        valu = nodedata[2]

        edits = [(s_layer.EDIT_NODEDATA_SET, (name, valu))]

        return buid, None, edits

    #############################################################
    # Destination (0.2.0) operations
    #############################################################

    async def _destGetWlyr(self, dirn, storinfo, iden):
        '''
        Get the write Layer object for the destination.

        Args:
            storinfo (dict): Storage information dict
            iden (str): iden of the layer to create object for

        Returns:
            (synapse.lib.Layer): Write layer
        '''
        layrinfo = {
            'iden': iden,
            'readonly': False,
            'conf': {
                'lockmemory': None,
            },
        }
        path = os.path.join(dirn, 'layers')
        lyrstor = await s_layer.LayerStorage.anit(storinfo, path)
        self.onfini(lyrstor)

        if self.nexusroot is not None:
            wlyr = await lyrstor.initLayr(layrinfo, self.nexusroot)
        else:
            wlyr = await lyrstor.initLayr(layrinfo)
        self.onfini(wlyr)

        return wlyr

    async def _destAddNodes(self, migrop, wlyr, nodeedits):
        '''
        Add nodes/nodedata to a write layer from nodeedits.

        Args:
            wlyr (synapse.lib.Layer): Layer to add node to
            nodeedits (list): list of nodeedits [ (<buid>, <form>, [edits]) ]

        Returns:

        '''
        meta = None

        try:
            if self.nexusoff:
                sodes = [await wlyr._storNodeEdit(ne, meta) for ne in nodeedits]
            else:
                sodes = await wlyr.storNodeEdits(nodeedits, meta)
            return sodes

        except asyncio.CancelledError:
            raise
        except Exception as e:
            lyriden = wlyr.iden
            logger.exception(f'unable to store nodeedits on {lyriden}')
            logger.debug(f'nodeedits: {nodeedits}')
            for ne in nodeedits:
                err = {'mesg': f'Unable to store nodeedit on {lyriden}', 'nodeedit': ne}
                await self._migrlogAdd(migrop, 'error', ne[0], err)
            return None

async def main(argv, outp=s_output.stdout):
    pars = argparse.ArgumentParser(prog='synapse.tools.migrate_stor', description='Tool for migrating Synapse storage.')
    pars.add_argument('--dirn', required=True, type=str)
    pars.add_argument('--migr-ops', required=False, type=str, nargs='+', choices=ALL_MIGROPS,
                      help='Limit migration operations to run.')
    pars.add_argument('--layer', required=False, type=str, help='Migrate specific layer by iden')
    pars.add_argument('--nodelim', required=False, type=int, help="Stop after migrating nodelim nodes")
    pars.add_argument('--nexus-off', action='store_true', required=False,
                      help="Do not create Nexus splicelog")
    pars.add_argument('--use-hivev1', action='store_true', required=False, help='Initialize hive from hive_v1 backup')
    pars.add_argument('--log-level', default='info', choices=s_const.LOG_LEVEL_CHOICES,
                      help='Specify the log level', type=str.upper)

    opts = pars.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    conf = {
        'dirn': opts.dirn,
        'migrops': opts.migr_ops,
        'layer': opts.layer,
        'nodelim': opts.nodelim,
        'nexusoff': opts.nexus_off,
        'usehivev1': opts.use_hivev1,
    }

    migr = await Migrator.anit(conf=conf)

    try:
        await migr.migrate()

    except Exception:
        await migr.fini()
        raise

    finally:
        await migr.fini()

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
