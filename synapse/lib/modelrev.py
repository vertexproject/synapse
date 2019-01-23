import logging

logger = logging.getLogger(__file__)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 0, 0), self._addModelVers),
        )

    async def revCoreLayers(self):

        version = self.revs[-1][0]

        for layr in self.core.layers:

            # just bump brand new layers all the way up
            if layr.fresh:
                await layr.setModelVers(version)
                continue

            # skip layers with the right version
            vers = await layr.getModelVers()
            if vers == version:
                continue

            if layr.readonly:
                # TODO: disable?  explode? check maj.min?
                logger.warning('readonly layer has model version: %r' % (vers,))
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
