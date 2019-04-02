import os
import logging
import contextlib

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

logger = logging.getLogger(__name__)

_progress = 25000

class Migration(s_base.Base):
    '''
    A migration instance provides a resume-capable workspace for
    large data migrations within a cortex.
    '''
    async def __anit__(self, core, layers=None):

        await s_base.Base.__anit__(self)

        if layers is None:
            layers = core.layers.values()

        self.core = core
        self.layers = layers

        self.dirn = await self.enter_context(s_common.getTempDir())

        path = os.path.join(self.dirn, 'migr.lmdb')

        self.slab = await s_lmdbslab.Slab.anit(path)
        self.oldb2indx = self.slab.initdb('oldb2indx')

        self.onfini(self.slab.fini)

        self.ndefdelay = None

        for layr in layers:
            await self.enter_context(layr.disablingBuidCache())

    @contextlib.asynccontextmanager
    async def getTempSlab(self):
        with s_common.getTempDir() as dirn:
            path = os.path.join(dirn, 'migrate.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                yield slab

    @contextlib.asynccontextmanager
    async def delayNdefProps(self):
        '''
        Hold this during a series of renames to delay ndef
        secondary property processing until the end....
        '''
        async with self.getTempSlab() as slab:

            seqn = s_slabseqn.SlabSeqn(slab, 'ndef')

            self.ndefdelay = seqn

            yield

            self.ndefdelay = None

            logger.info(f'Processing {seqn.index()} delayed values.')

            # process them all now...
            for i, (oldv, newv) in seqn.iter(0):
                await self.editNdefProps(oldv, newv)

                if i and i % _progress == 0:
                    logger.info(f'Processed {i} delayed values.')

    async def editNodeNdef(self, oldv, newv):

        oldb = s_common.buid(oldv)

        for layr in self.layers:

            indx = await layr.getFormIndx(oldb)

            # save off any old indx valu so we can scan for them
            if indx is not None:
                self.slab.put(oldb, indx, overwrite=False, db=self.oldb2indx)

            await layr.editNodeNdef(oldv, newv)

        if self.ndefdelay is not None:
            self.ndefdelay.append((oldv, newv))
            return

        await self.editNdefProps(oldv, newv)

    async def setFormName(self, oldn, newn):
        '''
        Rename a form within all the layers.
        '''
        logger.info(f'Migrating [{oldn}] to [{newn}]')

        async with self.getTempSlab():

            i = 0
            async for buid, valu in self.getFormTodo(oldn):

                await self.editNodeNdef((oldn, valu), (newn, valu))

                i = i + 1
                if i and i % _progress == 0:
                    logger.info(f'Migrated {i} buids.')

    async def editNdefProps(self, oldndef, newndef):
        '''
        Change all props as a result of an ndef change.
        '''
        oldbuid = s_common.buid(oldndef)

        oldname, oldvalu = oldndef
        newname, newvalu = newndef

        rename = newname != oldname

        # we only need to update secondary props if they have diff vals
        # ( vs for example a pure rename )
        if oldvalu != newvalu:

            # get the indx bytes for the *value* of the ndef
            indx = self.slab.get(oldbuid, db=self.oldb2indx)
            if indx is not None:

                # the only way for indx to be None is if we dont have the node...
                for prop in self.core.model.getPropsByType(newname):

                    coff = prop.getCompOffs()

                    for layr in self.layers:

                        async for buid, valu in layr.iterPropIndx(prop.form.name, prop.name, indx):

                            await layr.storPropSet(buid, prop, newvalu)

                            # for now, assume any comp sub is on the same layer as it's form prop
                            if coff is not None:

                                ndef = await layr.getNodeNdef(buid)

                                edit = list(ndef[1])
                                edit[coff] = newvalu

                                await self.editNodeNdef(ndef, (ndef[0], edit))

        for prop in self.core.model.getPropsByType('ndef'):

            formsub = self.core.model.prop(prop.full + ':' + 'form')

            coff = prop.getCompOffs()

            for layr in self.layers:

                async for buid, valu in layr.iterPropIndx(prop.form.name, prop.name, oldbuid):

                    await layr.storPropSet(buid, prop, newndef)

                    if rename and formsub is not None:
                        await layr.storPropSet(buid, formsub, newname)

                    if coff is not None:

                        # for now, assume form and prop on the same layer...
                        ndef = await layr.getNodeNdef(buid)

                        edit = list(ndef[1])
                        edit[coff] = newndef

                        await self.editNodeNdef(ndef, (ndef[0], edit))

    async def getFormTodo(self, name):
        '''
        Produce a deconflicted list of form values across layers
        as a *copy* to avoid iter vs edit issues in the indexes.
        '''
        size = 0
        logger.warning(f'MIGRATION: calculating form todo: {name}')
        async with self.getTempSlab() as slab:

            for layr in self.layers:

                async for buid, valu in layr.iterFormRows(name):
                    slab.put(buid, s_msgpack.en(valu), overwrite=False)
                    size += 1

            logger.warning(f'MIGRATION: {name} todo size: {size}')

            for buid, byts in slab.scanByFull():
                yield buid, s_msgpack.un(byts)
