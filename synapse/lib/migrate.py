import os
import logging
import contextlib

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

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
        self.onfini(self.slab.fini)

        self.buid2ndef = self.slab.initdb('buid2ndef')

    @contextlib.asynccontextmanager
    async def getTempSlab(self):
        with s_common.getTempDir() as dirn:
            path = os.path.join(dirn, 'migrate.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                yield slab

    async def editNodeNdef(self, oldv, newv):

        for layr in self.layers:
            await layr.editNodeNdef(oldv, newv)

        await self.editNdefProps(oldv, newv)

    async def setFormName(self, oldn, newn):
        '''
        Rename a form within all the layers.
        '''
        async with self.getTempSlab() as slab:

            async for layr, buid, valu in self.getFormTodo(oldn):

                # create a de-dupd list of buids to translate
                if not slab.put(buid, b'\x01', overwrite=False):
                    continue

                await self.editNodeNdef((oldn, valu), (newn, valu))

    async def setNodeBuid(self, form, oldb, newb):
        '''
        Carry out the rewrite of a node buid in all layers.
        '''
        sops = (
            ('buid:set', (form, oldb, newb)),
        )
        for layr in self.layers:
            await layr.stor(sops)

    async def editNdefProps(self, oldv, newv):
        '''
        Change all ndef props from oldv to newv.
        '''
        norm, info = self.core.model.type('ndef').norm(newv)
        for prop in self.core.model.getPropsByType('ndef'):

            coff = prop.getCompOffs()
            if coff is not None:
                await self._editCompProp(prop, coff, oldv, newv, info)
                continue

            await self._editEasyProp(prop, oldv, newv, info)

    async def _editCompProp(self, prop, coff, oldv, newv, info):

        lops = prop.getLiftOps(oldv)

        for layr in self.layers:

            async for row in layr.getLiftRows(lops):

                buid = row[0]

                # if this prop is part of a compound, just use the form set method
                _, valu = await layr.getNodeNdef(buid)

                edit = list(valu)
                edit[coff] = newv

                await self.setNodeForm(layr, buid, prop.form.name, valu, edit)

    async def _editEasyProp(self, prop, oldv, newv, info):

        # check for subs on the form from us...
        subtodo = []

        subs = info.get('subs')
        if subs is not None:
            for subn, subv in subs.items():
                subp = self.core.model.prop(prop.full + ':' + subn)
                if subp is None:
                    continue

                subtodo.append((subp, subv))

        lops = prop.getLiftOps(oldv)

        for layr in self.layers:

            async for row in layr.getLiftRows(lops):

                buid = row[0]

                sops = []
                sops.extend(prop.getDelOps(buid))
                sops.extend(prop.getSetOps(buid, newv))

                for subp, subv in subtodo:
                    sops.extend(subp.getDelOps(buid))
                    sops.extend(subp.getSetOps(buid, subv))

                await layr.stor(sops)

    async def setPropsByType(self, name, oldv, newv, info):
        '''
        Update secondary props of the given type.
        '''
        # update secondary props from oldv to newv
        for prop in self.core.model.getPropsByType(name):

            coff = prop.getCompOffs()
            if coff is not None:
                await self._editCompProp(prop, coff, oldv, newv, info)
                continue

            await self._editEasyProp(prop, oldv, newv, info)

    async def setNodeForm(self, layr, buid, name, oldv, newv):
        '''
        Reset the primary property for the given buid.
        '''
        form = self.core.model.form(name)

        norm, info = form.type.norm(newv)

        subtodo = []

        subs = info.get('subs')
        if subs is not None:
            subtodo = list(subs.items())

        newb = s_common.buid((name, norm))

        ops = []
        ops.extend(form.getDelOps(buid))
        ops.extend(form.getSetOps(newb, norm))

        # scoop up any set operations for form subs
        for subn, subv in subtodo:
            subp = self.core.model.prop(name + ':' + subn)
            if subp is None:
                continue

            ops.extend(subp.getDelOps(buid))
            ops.extend(subp.getSetOps(newb, subv))

        # rewrite the primary property and subs
        await layr.stor(ops)

        # update props in all layers
        await self.setNodeBuid(name, buid, newb)

        await self.setPropsByType(name, oldv, norm, info)

        oldndef = (name, oldv)
        newndef = (name, norm)

        await self.editNdefProps(oldndef, newndef)

    async def getFormTodo(self, name):
        for layr in self.layers:
            async for buid, valu in layr.iterFormRows(name):
                yield layr, buid, valu
