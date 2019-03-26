import logging
import contextlib

import synapse.exc as s_exc
import synapse.lib.migrate as s_migrate

logger = logging.getLogger(__name__)

maxvers = (0, 1, 0)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 0, 0), self._addModelVers),
            ((0, 1, 0), self._addFormNameSpaces),
        )

    async def revCoreLayers(self):

        version = self.revs[-1][0]

        # do a first pass to detect layers at the wrong version
        # that we are not able to rev ourselves and bail...

        layers = []
        for layr in self.core.layers.values():

            if layr.fresh:
                await layr.setModelVers(version)
                continue

            vers = await layr.getModelVers()
            if vers == version:
                continue

            if not layr.canrev and vers != version:
                mesg = f'layer {layr.__class__.__name__} {layr.iden} ({layr.dirn}) can not be updated.'
                raise s_exc.CantRevLayer(layer=layr.iden, mesg=mesg)

            if vers > version:
                mesg = f'layer {layr.__class__.__name__} {layr.iden} ({layr.dirn}) is from the future!'
                raise s_exc.CantRevLayer(layer=layr.iden, mesg=mesg)

            # realistically all layers are probably at the same version... but...
            layers.append(layr)

        # got anything to do?
        if not layers:
            return

        for revvers, revmeth in self.revs:

            todo = [l for l in layers if await l.getModelVers() < revvers]
            if not todo:
                continue

            logger.warning(f'beginning model migration -> {revvers}')

            await revmeth(todo)

            [await l.setModelVers(revvers) for l in todo]

        logger.warning('...model migrations complete!')

    @contextlib.asynccontextmanager
    async def getCoreMigr(self, layers):
        async with await s_migrate.Migration.anit(self.core, layers=layers) as migr:
            yield migr

    async def _addModelVers(self, layers):
        pass

    async def _addFormNameSpaces(self, layers):

        async with self.getCoreMigr(layers) as migr:

            # delay ndef prop cascade so we can rename everything first
            async with migr.delayNdefProps():

                await migr.setFormName('seen', 'meta:seen')
                await migr.setFormName('source', 'meta:source')

                await migr.setFormName('has', 'edge:has')
                await migr.setFormName('refs', 'edge:refs')
                await migr.setFormName('wentto', 'edge:wentto')

                await migr.setFormName('event', 'graph:event')
                await migr.setFormName('cluster', 'graph:cluster')
                await migr.setFormName('graph:link', 'graph:edge')
                await migr.setFormName('graph:timelink', 'graph:timeedge')
