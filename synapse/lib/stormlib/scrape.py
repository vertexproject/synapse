import logging

import synapse.common as s_common

import synapse.lib.scrape as s_scrape
import synapse.lib.spooled as s_spooled
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerLib
class LibScrape(s_stormtypes.Lib):
    '''
    A Storm Library for providing ipv6 helpers.
    '''
    _storm_locals = (
        {'name': 'ndefs', 'desc': '''
            Attempt to scrape node form, value tuples from a blob of text.

            Examples:
                Scrape some text and attempt to make nodes out of it::

                    for ($form, $valu) in $lib.scrape($text) {
                        [ ( *$form ?= $valu ) ]
                    }''',
         'type': {'type': 'function', '_funcname': '_methNdefs',
                  'args': (
                      {'name': 'text', 'type': 'str',
                       'desc': 'The text to scrape', },
                      {'name': 'ptype', 'type': 'str', 'default': None,
                       'desc': 'Optional type to scrape. If present, only scrape items which match the provided type.', },
                      {'name': 'refang', 'type': 'boolean', 'default': True,
                       'desc': 'Whether to remove de-fanging schemes from text before scraping.', },
                      {'name': 'unique', 'type': 'boolean', 'default': True,
                       'desc': 'Only yield unique items from the text.', },
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'A list of (form, value) tuples scraped from the text.', }}},
    )
    _storm_lib_path = ('scrape', )

    def getObjLocals(self):
        return {
            'ndefs': self._methNdefs,
            'ptypes': self._methPtypes,
            'context': self._methContext,
        }

    async def __call__(self, text, ptype=None, refang=True, unique=True):
        await self.runt.warnonce('$lib.scrape() is deprecated. Use $lib.scrape.ndefs().')
        async for item in self._methNdefs(text, ptype=ptype, refang=refang, unique=unique):
            yield item

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPtypes(self):
        return s_scrape.getPtypes()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methContext(self, text, ptype=None, refang=True, unique=True):
        text = await s_stormtypes.tostr(text)
        ptype = await s_stormtypes.tostr(ptype, noneok=True)
        refang = await s_stormtypes.tobool(refang)
        unique = await s_stormtypes.tobool(unique)

        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set

            for item in s_scrape.contextScrape(text, ptype=ptype, refang=refang, first=False):
                if unique:
                    key = (item.get('ptype'), item.get('valu'))
                    if key in items:
                        continue
                    await items.add(key)
                yield item

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNdefs(self, text, ptype=None, refang=True, unique=True):
        text = await s_stormtypes.tostr(text)
        ptype = await s_stormtypes.tostr(ptype, noneok=True)
        refang = await s_stormtypes.tobool(refang)
        unique = await s_stormtypes.tobool(unique)

        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set
            for ptyp, ndef in s_scrape.scrape(text, ptype=ptype, refang=refang, first=False):
                if unique:
                    if (ptype, ndef) in items:
                        continue
                    await items.add((ptype, ndef))
                yield (ptyp, ndef)
