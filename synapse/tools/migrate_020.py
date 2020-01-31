'''
Migrate storage from 0.1.x to 0.2.x.

TODO:
    - Handling multiple layers - right now src/dest are layer dirns
    - Inplace migration or always assume "Fresh" 0.2.0 cortex migrating into?
    - .created may not be moving over for all nodes?
    - Track unmigrated nodes
    - Basic tag set
    - Tagprops
    - Handling for pause/restart
    - Benchmarking / metrics
    - Validation
    - Extended models
    - Other stuff besides nodes/tags
'''
import os
import sys
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
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

class Migrator(s_base.Base):
    '''
    Standalone tool for migrating Synapse storage.
    '''
    async def __anit__(self, conf):
        await s_base.Base.__anit__(self)
        self.src = conf.get('src')
        self.dest = conf.get('dest')

        # load data model for stortypes
        self.model = s_datamodel.Model()
        await self._trnDatamodel()

        # SOURCE
        # get source layer idens
        self.src_lyridens = os.listdir(os.path.join(self.src, 'layers'))

        # get source slabs - right now just one
        path = os.path.join(self.src, 'layers', self.src_lyridens[-1], 'layer.lmdb')
        self.src_lyrslab = await s_lmdbslab.Slab.anit(path, map_async=True, readonly=True)
        self.onfini(self.src_lyrslab)

        # get source dbs - right now just just bybuid for one layer
        self.src_lyrbybuid = self.src_lyrslab.initdb('bybuid')  # <buid><prop>=<valu>

        # DESTINATION
        # get destination layer idens - right now assuming A->B migration
        self.dest_lyridens = os.listdir(os.path.join(self.dest, 'layers'))

        # get destination write layer
        self.dest_wlyr = await self._destGetWlyr(self.dest_lyridens[-1])

    #############################################################
    # Migration operations
    #############################################################

    async def migrate(self):
        '''
        Execute the migration
        '''
        await self._migrateNodes()

    async def _migrateNodes(self):
        '''
        Migrate nodes for all layers

        Returns:
            (dict): For all form types a tuple (src_cnt, dest_cnt)
        '''
        dest_fcntpre = await self.dest_wlyr.getFormCounts()
        if dest_fcntpre:
            logger.warning(f'Destination is not empty: {dest_fcntpre}')

        src_fcnt = collections.defaultdict(int)
        async for node in self._srcIterNodes(self.src_lyrslab, self.src_lyrbybuid):
            # TODO: clean this up
            form = node[1][0]
            if form[0] == '#':
                form = 'syn:tag'
            form = form.replace('.', '').replace('*', '')
            src_fcnt[form] += 1

            nodeedit = await self._trnNodeToNodeedit(node)
            if nodeedit is None:
                #logger.error(f'Unable to create nodeedit for {node}')
                continue

            res = await self._destAddNode(self.dest_wlyr, nodeedit)
            if not res:
                logger.error(f'Unable to add destination node: {node}, {nodeedit}')
                continue

        dest_fcnt = await self.dest_wlyr.getFormCounts()
        fkeys = set(list(src_fcnt.keys()) + list(dest_fcnt.keys()))
        fcnt = {f: [src_fcnt.get(f, '0'), dest_fcnt.get(f, '0')] for f in fkeys}

        # for testing, iterate over the forms
        for form in fkeys:
            sode_cnt = 0
            async for sode in self.dest_wlyr.liftByProp(form, None):
                sode_cnt += 1
            fcnt[form].append(sode_cnt)

        logger.info(f'Final form count: {fcnt}')

        return fcnt

    #############################################################
    # Source (0.1.x) operations
    #############################################################

    async def _srcIterNodes(self, buidslab, buiddb):
        '''
        Yield node information directly from the 0.1.x source slab.

        Yields:
            (bytes, form, list): (<buid>, (<form>, <valu>), [(prop, valu), ...])
        '''
        buid = None
        ndef = None
        props = []
        for lkey, lval in buidslab.scanByFull(db=buiddb):
            rowbuid = lkey[0:32]
            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)  # throwing away indx

            if buid is None or rowbuid != buid:
                # if not at start, yield the last node
                if buid is not None:
                    yield buid, ndef, props

                # setup new node
                buid = rowbuid
                if prop[0] not in ('*', '#'):
                    logger.warning(f'ndef may be incorrect: {buid}, {prop}, {valu}')
                ndef = (prop, valu)
                props = []

            # add secondary props
            else:
                props.append((prop, valu))

        # yield last node
        yield buid, ndef, props

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
            node (tuple): (<buid>, (<form>, <valu>), [(prop, valu), ...])

        Returns:
            nodeedit (tuple): (<buid>, <form>, [edits]) where edits is list of (<type>, <info>)
        '''
        buid = node[0]
        form = node[1][0]
        fval = node[1][1]

        if form[0] == '*':
            formnorm = form[1:]
        elif form[0] == '#':
            # TODO node tag adds
            return None
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
        edits.append((s_layer.EDIT_NODE_ADD, (fval, stortype)))

        # iterate over secondary properties
        for sprop, sval in node[2]:
            sformnorm = sprop.replace('*', '')
            stortype = mform.prop(sformnorm).type.stortype
            if stortype is None:
                logger.error(f'Unable to determine stortype for sprop {sformnorm}')
                return None
            edits.append((s_layer.EDIT_PROP_SET, (sformnorm, sval, None, stortype)))

        return buid, formnorm, edits

    #############################################################
    # Destination (0.2.0) operations
    #############################################################

    async def _destGetWlyr(self, iden):
        '''
        Get the write Layer object for the destination.

        Args:
            iden (str): iden of the layer to create object for

        Returns:
            (synapse.lib.Layer): Write layer
        '''
        info = {
            'iden': iden,
            'type': 'local',
            'conf': {},
        }
        layrinfo = {
            'iden': info['iden'],
            'readonly': False,
            'conf': {
                'lockmemory': None,
            },
        }
        path = os.path.join(self.dest, 'layers')
        lyrstor = await s_layer.LayerStorage.anit(info, path)
        self.onfini(lyrstor)
        wlyr = await lyrstor.initLayr(layrinfo)
        self.onfini(wlyr)

        return wlyr

    async def _destAddNode(self, wlyr, nodeedit):
        '''
        Add node to a write layer from a nodeedit.

        Args:
            wlyr (synapse.lib.Layer): Layer to add node to
            nodeedit (tuple): (<buid>, <form>, [edits])

        Returns:

        '''
        try:
            sodes = await wlyr.storNodeEdits([nodeedit], None)  # meta=None
            return sodes
        except Exception as e:
            logger.error(f'unable to store nodeedit: {e}')
            return None

async def main(argv, outp=s_output.stdout):
    pars = argparse.ArgumentParser(prog='synapse.tools.migrate_stor', description='Tool for migrating Synapse storage.')
    pars.add_argument('--src', required=True, type=str)
    pars.add_argument('--dest', required=True, type=str)
    pars.add_argument('--log-level', default='debug', choices=s_const.LOG_LEVEL_CHOICES,
                      help='Specify the log level', type=str.upper)

    opts = pars.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    conf = {
        'src': opts.src,
        'dest': opts.dest,
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
