import bs4

import synapse.lib.coro as s_coro
import synapse.lib.stormtypes as s_stormtypes

def htmlToText(html, separator='\n', strip=True):
    soup = bs4.BeautifulSoup(html, 'html5lib')
    return soup.get_text(separator=separator, strip=strip)

@s_stormtypes.registry.registerLib
class LibMimeHtml(s_stormtypes.Lib):
    '''
    A Storm library for manipulating HTML text.
    '''
    _storm_locals = (
        {'name': 'totext', 'desc': 'Return inner text from all tags within an HTML document.',
         'type': {'type': 'function', '_funcname': 'totext',
                  'args': (
                      {'name': 'html', 'type': 'str', 'desc': 'The HTML text to be parsed.'},
                      {'name': 'separator', 'type': 'str', 'default': '\n',
                       'desc': 'The string used to join text.'},
                      {'name': 'strip', 'type': 'boolean', 'default': True,
                       'desc': 'Strip whitespace from the beginning and end of tag text.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The separator-joined inner HTML text.', }
        }},
    )

    _storm_lib_path = ('mime', 'html')

    def getObjLocals(self):
        return {
            'totext': self.totext,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def totext(self, html, separator='\n', strip=True):
        html = await s_stormtypes.tostr(html)
        separator = await s_stormtypes.tostr(separator, noneok=True)
        strip = await s_stormtypes.tobool(strip)

        if separator is None:
            separator = ''

        return await s_coro.semafork(htmlToText, html, separator, strip)
