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
    A Storm Library for providing helpers for scraping nodes from text.
    '''
    _storm_locals = (
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
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'A list of (form, value) tuples scraped from the text.', }}},
        {'name': 'genMatches', 'desc': '''
        genMatches is a generic helper function for constructing scrape interfaces using pure Storm.

        It accepts the text, a regex pattern, and produce results that can easily be used to create

        Notes:
            The pattern must have a named regular expression match for the key ``valu`` using the
            named group syntax. For example ``(somekey\\s)(?P<valu>[a-z0-9]+)\\s``.

        Examples:
            A scrape implementation with a regex that matches name keys in text::

                $re="(Name\\:\\s)(?P<valu>[a-z0-9]+)\\s"
                $form="ps:name"

                function scrape(text, form) {
                        $ret = $lib.list()
                        for ($valu, $info) in $lib.scrape.genMatches($text, $re) {
                            $ret.append(($form, $valu, $info))
                        }
                        return ( $ret )
                    }
        ''',
         'type': {'type': 'function', '_funcname': '_methGenMatches',
                  'args': (
                      {'name': 'text', 'type': 'str',
                       'desc': 'The text to scrape', },
                      {'name': 'pattern', 'type': 'str',
                       'desc': 'The regular expression pattern to match against.', },
                      {'name': 'fangs', 'type': 'list', 'default': None,
                       'desc': 'A list of (src, dst) pairs to refang from text. The src must be equal or larger '
                               'than the dst in length.'},
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

                yield item
                await asyncio.sleep(0)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methContext(self, text):
        text = await s_stormtypes.tostr(text)

        genr = self.runt.snap.view.scrapeIface(text)
        async for (form, valu, info) in genr:
            yield (form, valu, info)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNdefs(self, text):
        text = await s_stormtypes.tostr(text)

        genr = self.runt.snap.view.scrapeIface(text, unique=True)
        async for (form, valu, _) in genr:
            yield (form, valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGenMatches(self, text, pattern, fangs=None, flags=regex.IGNORECASE):
        text = await s_stormtypes.tostr(text)
        pattern = await s_stormtypes.tostr(pattern)
        fangs = await s_stormtypes.toprim(fangs)
        flags = await s_stormtypes.toint(flags)

        opts = {}
        regx = regex.compile(pattern, flags=flags)

        _fangs = None
        _fangre = None
        offsets = None
        scrape_text = text
        if fangs:
            _fangs = {src: dst for (src, dst) in fangs}
            _fangre = s_scrape.genFangRegex(_fangs)
            scrape_text, offsets = s_scrape.refang_text2(text, re=_fangre, fangs=_fangs)

        for info in s_scrape.genMatches(scrape_text, regx, opts=opts):
            valu = info.pop('valu')

            if _fangs and offsets:
                s_scrape._rewriteRawValu(text, offsets, info)

            yield valu, info
