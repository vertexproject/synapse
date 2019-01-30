import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.migrate as s_migrate

logger = logging.getLogger(__file__)

version = (0, 1, 0)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 0, 0), self._addModelVers),
            ((0, 1, 0), self._init010Model),
        )

    async def revCoreLayers(self):

        version = self.revs[-1][0]

        # do a first pass to detect layers at the wrong version
        # that we are not able to rev ourselves and bail...
        for layr in self.core.layers:
            vers = await layr.getModelVers()
            if not layr.canrev and vers != version:
                mesg = f'layer {layr.__class__.__name__} {layr.iden} ({layr.dirn}) can not be updated.'
                raise s_exc.CantRevLayer(layer=layr.iden, mesg=mesg)

        for layr in self.core.layers:

            # just bump brand new layers all the way up
            if layr.fresh:
                await layr.setModelVers(version)
                continue

            # skip layers with the right version
            vers = await layr.getModelVers()
            if vers == version:
                continue

            for revvers, revmeth in self.revs:
                if vers < revvers:
                    logger.warning(f'beginning model {vers} -> {revvers} (layer: {layr.iden})')
                    await revmeth(self.core, layr)
                    await layr.setModelVers(revvers)
                    logger.warning('...complete!')
                    vers = revvers

    async def _addModelVers(self, core, layr):
        pass

    async def _init010Model(self, core, layr):

        iden = '9bb1cd19373ae8228485a544ec976bde'
        async with await s_migrate.Migration.anit(core, iden) as migr:

            def indxFileBytes(p, v):
                return v.encode('utf8')

            migr.addOldIndx('file:bytes', indxFileBytes)

            def norm(valu):
                if valu.find(':') == -1:
                    return valu, {}
                return s_common.guid(valu.split(':')), {}

            await migr.setTypeNorm('file:bytes', norm)
