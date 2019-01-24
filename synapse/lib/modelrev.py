import logging

import synapse.exc as s_exc

logger = logging.getLogger(__file__)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 0, 0), self._addModelVers),
        )

    async def revCoreLayers(self):

        version = self.revs[-1][0]

        # do a first pass to detect layers at the wrong version
        # that we are not able to rev ourselves and bail...
        for layr in self.core.layers:
            vers = await layr.getModelVers()
            if not layr.canrev and vers != version:
                mesg = f'layer {layr.iden} ({layr.dirn}) can not be updated.'
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

    def _addModelVers(self, core, layr):
        pass
