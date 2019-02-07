import os
import shutil
import logging

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.lmdbslab as s_slab

logger = logging.getLogger(__name__)

class Migration(s_base.Base):
    '''
    A migration instance provides a resume-capable workspace for
    large data migrations within a cortex.
    '''
    async def __anit__(self, core, iden):

        await s_base.Base.__anit__(self)

        self.core = core
        self.iden = iden

        #path = os.path.join(self.core.dirn, 'migrations', iden)
        #if os.path.exists(path):
            #logger.info('resuming migration from %r' % (path,))

        #dirn = s_common.gendir(path)
        #slab

    async def setNodeBuid(self, form, oldb, newb):
        '''
        Carry out the rewrite of a node buid in all layers.
        '''
        sops = (
            ('buid:set', (form, oldb, newb)),
        )
        for layr in self.core.layers:
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
        for layr in self.getLayers():

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

        for layr in self.getLayers():

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

    def getLayers(self):
        # TODO check layers for remote / etc
        return self.core.layers

    async def getFormTodo(self, name):
        # TODO implement lift / store / resume
        for layr in self.getLayers():
            async for buid, valu in layr.iterFormRows(name):
                yield layr, buid, valu
