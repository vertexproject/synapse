import asyncio
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
                  'returns': {'type': 'list',
                              'desc': 'A list of (form, valu, info) where info is a dictionart of metadata. '}}},
        {'name': 'context', 'desc': '''
            Attempt to scrape information from a blob of text, getting the context information about the values found.

            Notes:
                This does call the ``scrape`` Storm interface if that behavior is enabled on the Cortex.

            Examples:
                Scrape some text and make nodes out of it::

                    for ($form, $valu, $info) in $lib.scrape.context($text) {
                        [ ( *$form ?= $valu ) ]
                    }
            ''',
         'type': {'type': 'function', '_funcname': '_methContext',
                  'args': (
                      {'name': 'text', 'type': 'str',
                       'desc': 'The text to scrape', },
                      {'name': 'form', 'type': 'str', 'default': None,
                       'desc': 'Optional type to scrape. If present, only scrape items which match the provided type.', },
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
                      {'name': 'unique', 'type': 'boolean', 'default': True,
                       'desc': 'Only yield unique items from the text.', },
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'A list of (form, value) tuples scraped from the text.', }}},
        {'name': 'genMatches', 'desc': '''
        genMatches is a generic helper function for constructing scrape interfaces using pure Storm.

        It accepts the text, a regex pattern, and produce results that can easily be used to create

        Notes:
            The pattern must have a named regular expression match for the key ``valu`` using the
            named group synapse. For example ``(somekey\\s)(?<valu>[a-z0-9]+)\\s``.

        Examples:
            A scrape implementation with a regex that matches name keys in text::

                $re="(Name\\:\\s)(?<valu>[a-z0-9]+)\\s"
                $form="ps:name"

                function scrape(text, form) {
                        $ret = $lib.list()
                        for ($valu, $info) in $lib.scrape.genMatches($text, $re) {
                            $ret.append(($form, $valu, $info))
                        }
                        return ( $ret )
                    }
        ''',
         'type': {'type': 'function', '_functname': '_methGenMatches',
                  'args': (
                      {'name': 'text', 'type': 'str',
                       'desc': 'The text to scrape', },
                      {'name': 'pattern', 'type': 'str',
                       'desc': 'The regular expression pattern to match against.', },
                      {'name': 'unique', 'type': 'boolean', 'default': False,
                       'desc': 'Only yield unique items from the text.', },
                      {'name': 'flags', 'type': 'int', 'default': regex.IGNORECASE,
                       'desc': 'Regex flags to use (defaults to IGNORECASE).'},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': ''}}}
    )
    _storm_lib_path = ('scrape', )

    def getObjLocals(self):
        return {
            'ndefs': self._methNdefs,
            'forms': self._methForms,
            'context': self._methContext,
            'genMatches': self._methGenMatches,
        }

    async def __call__(self, text, ptype=None, refang=True, unique=True):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(ptype, noneok=True)
        refang = await s_stormtypes.tobool(refang)
        unique = await s_stormtypes.tobool(unique)
        # Remove this in 3.0.0 since it is deprecated.
        s_common.deprecated('$lib.scrape()')
        await self.runt.warnonce('$lib.scrape() is deprecated. Use $lib.scrape.ndefs().')
        async with await s_spooled.Set.anit() as items:  # type: s_spooled.Set
            for item in s_scrape.scrape(text, ptype=form, refang=refang, first=False):
                if unique:
                    if item in items:
                        continue
                    await items.add(item)

                # This is a change for early adopters of $lib.scrape
                # sform, valu = item
                # try:
                #     tobj = self.runt.snap.core.model.type(sform)
                #     valu, _ = tobj.norm(valu)
                # except (AttributeError, s_exc.BadTypeValu):
                #     logger.exception('Oh shit?')
                #     await asyncio.sleep(0)
                #     continue
                # yield (sform, valu)

                yield item
                await asyncio.sleep(0)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methForms(self):
        return s_scrape.getForms()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methContext(self, text, form=None, unique=False):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(form, noneok=True)
        unique = await s_stormtypes.tobool(unique)

        genr = self.runt.snap.view.scrapeIface(text, form=form, unique=unique)
        async for (form, valu, info) in genr:
            yield (form, valu, info)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNdefs(self, text, form=None, unique=True):
        text = await s_stormtypes.tostr(text)
        form = await s_stormtypes.tostr(form, noneok=True)
        unique = await s_stormtypes.tobool(unique)

        genr = self._methContext(text, form=form, unique=unique)
        async for (form, valu, info) in genr:
            yield (form, valu)

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
