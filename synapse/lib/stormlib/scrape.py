import logging

import regex

import synapse.exc as s_exc
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
        {'name': 'forms', 'desc': 'Get a list of available form arguments for built in scrape APIs.',
         'type': {'type': 'function', '_funcname': '_methForms',
                  'returns': {'type': 'list', 'desc': 'A list of '}}},
        {'name': 'context', 'desc': '''
            Attempt to scrape information from a blob of text, getting the context information about the values found.

            Examples:
            Scrape some text and attempt to make nodes out of it::

                for $info in $lib.scrape.context($text) {
                    $form=$info.ptype
                    $valu=$info.valu
                    [ ( *$form ?= $valu ) ]
                }
            ''',
         'type': {'type': 'function', '_funcname': '_methContext',
                  'args': (
                      {'name': 'text', 'type': 'str',
                       'desc': 'The text to scrape', },
                      {'name': 'form', 'type': 'str', 'default': None,
                       'desc': 'Optional type to scrape. If present, only scrape items which match the provided type.', },
                      {'name': 'refang', 'type': 'boolean', 'default': True,
                       'desc': 'Whether to remove de-fanging schemes from text before scraping.', },
                      {'name': 'unique', 'type': 'boolean', 'default': False,
                       'desc': 'Only yield unique items from the text.', },
                  ),
                  'returns': {'name': 'yields', 'type': 'dict',
                              'desc': 'A dictionary of scraped values, rule types, and offsets scraped from the text.',
                              }}},
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
                      {'name': 'form', 'type': 'str', 'default': None,
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
            'forms': self._methForms,
            'context': self._methContext,
            'genMatches': self._methGenMatches,
            'scrapeIface': self._methScrapeIface,
        }

    async def __call__(self, text, ptype=None, refang=True, unique=True):
        # Remove this in 3.0.0 since it is deprecated.
        s_common.deprecated('$lib.scrape()')
        await self.runt.warnonce('$lib.scrape() is deprecated. Use $lib.scrape.ndefs().')
        async for item in self._methNdefs(text, form=ptype, refang=refang, unique=unique):
            yield item

    @s_stormtypes.stormfunc(readonly=True)
    async def _methForms(self):
        return s_scrape.getForms()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methScrapeIface(self, text, form=None, unique=False):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(form, noneok=True)
        unique = await s_stormtypes.tobool(unique)

        todo = s_common.todo('scrape', text, form=form, unique=unique)
        async for (priority, result) in self.runt.snap.view.mergeStormIface('scrape', todo):
            yield result

    @s_stormtypes.stormfunc(readonly=True)
    async def _methContext(self, text, form=None, refang=True, unique=False):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(form, noneok=True)
        refang = await s_stormtypes.tobool(refang)
        unique = await s_stormtypes.tobool(unique)

        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set

            for item in s_scrape.contextScrape(text, form=form, refang=refang, first=False):
                sform = item.pop('form')
                valu = item.pop('valu')
                if unique:
                    key = (form, valu)
                    if key in items:
                        continue
                    await items.add(key)

                try:
                    tobj = self.runt.snap.core.model.type(sform)
                    valu, _ = tobj.norm(valu)
                except s_exc.BadTypeValu:
                    continue

                # Yield a tuple of <form, normed valu, info>
                yield sform, valu, item

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNdefs(self, text, form=None, refang=True, unique=True):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(form, noneok=True)
        refang = await s_stormtypes.tobool(refang)
        unique = await s_stormtypes.tobool(unique)

        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set
            for ftyp, ndef in s_scrape.scrape(text, ptype=form, refang=refang, first=False):
                if unique:
                    if (ftyp, ndef) in items:
                        continue
                    await items.add((ftyp, ndef))
                try:
                    tobj = self.runt.snap.core.model.type(ftyp)
                    ndef, _ = tobj.norm(ndef)
                except s_exc.BadTypeValu:
                    continue
                yield (ftyp, ndef)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGenMatches(self, text, pattern, unique=False, flags=regex.IGNORECASE):
        text = await s_stormtypes.tostr(text)
        pattern = await s_stormtypes.tostr(pattern)
        unique = await s_stormtypes.tobool(unique)

        opts = {}
        regx = regex.compile(pattern, flags=flags)

        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set
            for info in s_scrape.genMatches(text, regx, opts=opts):
                valu = info.pop('valu')
                if unique:
                    if valu in items:
                        continue
                    await items.add(valu)
                yield valu, info
