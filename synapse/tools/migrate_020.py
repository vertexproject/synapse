'''
Migrate storage from 0.1.x to 0.2.x.

TODO:
    - Support non-inplace migration?
    - Track unmigrated nodes / errors
    - Tagprops
    - Handling for pause/restart
    - Benchmarking / metrics
    - Validation (esp. check .created)
    - Extended models
    - Other stuff besides nodes/tags
    - Prompt and/or execute a backup?
    - Add ability to do a specific step on a specifc layer?
    - Any migr for views?  Need to iter over views?
'''
import os
import sys
import time
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
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.modelrev as s_modelrev

logger = logging.getLogger(__name__)

class Migrator(s_base.Base):
    '''
    Standalone tool for migrating Synapse storage.
    '''
    async def __anit__(self, conf):
        await s_base.Base.__anit__(self)
        self.dirn = conf.get('dirn')

        # load data model for stortypes
        self.model = s_datamodel.Model()
        await self._trnDatamodel()

        # open hive
        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        self.hiveslab = await s_lmdbslab.Slab.anit(path, readonly=False)
        self.hivedb = self.hiveslab.initdb('hive')
        self.hive = await s_hive.SlabHive.anit(self.hiveslab, db=self.hivedb)
        self.onfini(self.hive.fini)
        self.onfini(self.hiveslab.fini)

        # backup hive by deafult? Or cp to new cell_v2 and then replace?
        # TODO

    #############################################################
    # Migration operations
    #############################################################

    async def migrate(self):
        '''
        Execute the migration
        '''
        # auth migration
        await self._migrHiveAuth()  # TODO

        # storage info migration
        storinfo, layridens = await self._migrHiveStorInfo()

        # full layer migration
        for iden in layridens:
            logger.info(f'Starting migration for storage {storinfo.get("iden")} and layer {iden}')
            await self._migrNodes(storinfo, iden)
            # await self._migrNodeData(foo)
            # await self._migrSplices(foo)
            # await self._migrOffsets(foo)
            await self._migrHiveLayerInfo(storinfo, iden)

    async def _migrHiveAuth(self):
        '''
        TODO right now just blowing away authgates to allow startup
        '''
        await self.hive.pop(('auth', 'authgates'))

    async def _migrHiveStorInfo(self):
        '''
        Migrate to new storage info syntax.

        Returns:
            (dict): Storage information
            (list): List of layer idens
        '''
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

        # TODO: teardown of unneeded data

        return storinfo, layridens

    async def _migrHiveLayerInfo(self, storinfo, iden):
        '''
        As each layer is migrated update the hive info.

        Args:
            storinfo (dict): Storage information
            iden (str): Iden of the layer
        '''
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

    async def _migrNodes(self, storinfo, iden):
        '''
        Migrate nodes for a given layer

        Args:
            storinfo (dict): Storage information dict
            iden (str): Iden of the layer

        Returns:
            (dict): For all form types a tuple (src_cnt, dest_cnt)
        '''
        # open storage
        dest_wlyr = await self._destGetWlyr(self.dirn, storinfo, iden)

        path = os.path.join(self.dirn, 'layers', iden, 'layer.lmdb')
        src_slab = await s_lmdbslab.Slab.anit(path, map_async=True, readonly=True)
        src_bybuid = src_slab.initdb('bybuid')  # <buid><prop>=<valu>
        self.onfini(src_slab.fini)

        # check if 0.2.0 write layer exists with data
        dest_fcntpre = await dest_wlyr.getFormCounts()
        if dest_fcntpre:
            logger.warning(f'Destination is not empty: {dest_fcntpre}')

        # update modelrev
        await dest_wlyr.setModelVers(s_modelrev.maxvers)

        # migrate data
        src_fcnt = collections.defaultdict(int)
        nodeedits = []
        editchnks = 10  # batch size for nodeedits to add
        t_strt = time.time()
        async for node in self._srcIterNodes(src_slab, src_bybuid):
            form = node[1]['ndef'][0].replace('.', '').replace('*', '')
            src_fcnt[form] += 1

            nodeedit = await self._trnNodeToNodeedit(node)
            if nodeedit is None:
                #logger.error(f'Unable to create nodeedit for {node}')
                # TODO: Log error nodes
                continue

            nodeedits.append(nodeedit)
            if len(nodeedits) == editchnks:
                sodes = await self._destAddNodes(dest_wlyr, nodeedits)
                if sodes is None or len(sodes) != editchnks:
                    logger.error(f'Unable to add destination node: {nodeedits}, {sodes}')
                    # TODO: verify whether this is valid chunk error condition
                    # TODO: Log error nodes
                nodeedits = []
                await asyncio.sleep(0)

        # add last edit chunk if needed
        if len(nodeedits) > 0:
            sodes = await self._destAddNodes(dest_wlyr, nodeedits)
            if sodes is None or len(sodes) != editchnks:
                logger.error(f'Unable to add destination node: {nodeedits}, {sodes}')
                # TODO: Log error nodes

        t_end = time.time()
        t_dur = int(t_end - t_strt)

        # collect final form count stats
        dest_fcnt = await dest_wlyr.getFormCounts()
        fcnt = {f: [v, dest_fcnt.get(f, '0')] for f, v in src_fcnt.items()}
        totnodes = sum([v[1] for v in fcnt.values()])

        # for testing, iterate over the forms and print a report
        # TODO: Move to an optional reporting method or delete
        rprt = ['\n', '{:<25s}{:<10s}{:<10s}{:<10s}'.format('FORM', 'SRC_CNT', 'DEST_CNT', 'LIFT_CNT')]
        for form in src_fcnt.keys():
            sode_cnt = 0
            async for sode in dest_wlyr.liftByProp(form, None):
                sode_cnt += 1
            fcnt[form].append(sode_cnt)
            rprt.append('{:<25s}{!s:<10s}{!s:<10s}{!s:<10s}'.format(form, fcnt[form][0], fcnt[form][1], fcnt[form][2]))
        rprt.append('\n')

        rprt.append(f'Migrated {totnodes:,} nodes in {t_dur} seconds ({int(totnodes/t_dur)} nodes/s avg)')

        prprt = '\n'.join(rprt)
        logger.info(f'Final form count: {prprt}')

        return

    #############################################################
    # Source (0.1.x) operations
    #############################################################

    async def _pack(self, buid, ndef, props, tags, tagprops):
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
        tagprops = {}
        for lkey, lval in buidslab.scanByFull(db=buiddb):
            rowbuid = lkey[0:32]
            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)  # throwing away indx

            # new node; if not at start, yield the last node and reset
            if buid is not None and rowbuid != buid:
                yield await self._pack(buid, ndef, props, tags, tagprops)
                buid = None
                ndef = None
                props = {}
                tags = {}
                tagprops = {}

            if buid is None:
                buid = rowbuid

            # add node information
            if prop[0] == '*':
                if ndef is None:
                    ndef = (prop, valu)
                else:
                    props[prop] = valu

            elif prop[0] == '#':
                tags[prop] = valu

            else:
                props[prop] = valu

        # yield last node
        yield await self._pack(buid, ndef, props, tags, tagprops)

    #############################################################
    # Translation operations
    #############################################################

    async def _trnDatamodel(self):
        '''
        Load existing data model using 0.2.0 impl in order to get stor types
        '''
        # load core modules
        mods = list(s_modules.coremods)
        mdefs = []
        for mod in mods:
            modu = s_dyndeps.tryDynLocal(mod)
            mdefs.extend(modu.getModelDefs(self))  # probably not the self its expecting...

        self.model.addDataModels(mdefs)

        # TODO: load extended model - what about stortypes for these?

    async def _trnNodeToNodeedit(self, node):
        '''
        Create translation of node info to an 0.2.0 node edit.

        Args:
            node (tuple): (<buid>, {'ndef': ..., 'props': ..., 'tags': ..., 'tagprops': ...}

        Returns:
            nodeedit (tuple): (<buid>, <form>, [edits]) where edits is list of (<type>, <info>)
        '''
        buid = node[0]
        form = node[1]['ndef'][0]
        fval = node[1]['ndef'][1]

        if form[0] == '*':
            formnorm = form[1:]
        else:
            logger.error(f'Unable to norm form {form}, {node}')
            return None

        edits = []

        # setup storage type
        mform = self.model.form(formnorm)
        if mform is None:
            logger.error(f'Unable to determine form for {formnorm}')
            return None

        # create first edit for the node
        stortype = mform.type.stortype
        if stortype is None:
            logger.error(f'Unable to determine stortype for {formnorm}')
            return None
        edits.append((s_layer.EDIT_NODE_ADD, (fval, stortype)))  # name, stype

        # iterate over secondary properties
        for sprop, sval in node[1]['props'].items():
            sformnorm = sprop.replace('*', '')
            stortype = mform.prop(sformnorm).type.stortype
            if stortype is None:
                logger.error(f'Unable to determine stortype for sprop {sformnorm}')
                return None
            edits.append((s_layer.EDIT_PROP_SET, (sformnorm, sval, None, stortype)))  # name, valu, oldv, stype

        # set tags
        for tname, tval in node[1]['tags'].items():
            tnamenorm = tname[1:]
            edits.append((s_layer.EDIT_TAG_SET, (tnamenorm, tval, None)))  # tag, valu, oldv

        # tagprops
        # TODO

        return buid, formnorm, edits

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
        wlyr = await lyrstor.initLayr(layrinfo)
        self.onfini(wlyr)

        return wlyr

    async def _destAddNodes(self, wlyr, nodeedits):
        '''
        Add nodes to a write layer from nodeedits.

        Args:
            wlyr (synapse.lib.Layer): Layer to add node to
            nodeedits (list): list of nodeedits [ (<buid>, <form>, [edits]) ]

        Returns:

        '''
        try:
            sodes = await wlyr.storNodeEdits(nodeedits, None)  # meta=None
            return sodes
        except Exception as e:
            logger.error(f'unable to store nodeedit: {e}')
            return None

async def main(argv, outp=s_output.stdout):
    pars = argparse.ArgumentParser(prog='synapse.tools.migrate_stor', description='Tool for migrating Synapse storage.')
    pars.add_argument('--dirn', required=True, type=str)
    pars.add_argument('--log-level', default='debug', choices=s_const.LOG_LEVEL_CHOICES,
                      help='Specify the log level', type=str.upper)

    opts = pars.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    conf = {
        'dirn': opts.dirn,
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
