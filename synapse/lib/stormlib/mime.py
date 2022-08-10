import bs4

import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.stormtypes as s_stormtypes

def htmlToText(html):
    soup = bs4.BeautifulSoup(html, 'html5lib')
    return soup.get_text(separator='\n', strip=True)

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
                  ),
                  'returns': {'type': 'str', 'desc': 'The newline-joined inner HTML text.', }
        }},
    )

    _storm_lib_path = ('mime', 'html')

    def getObjLocals(self):
        return {
            'totext': self.totext,
        }

    async def totext(self, html):
        html = await s_stormtypes.tostr(html)
        todo = s_common.todo(htmlToText, html)
        return await s_coro.spawn(todo, log_conf=self.runt.spawn_log_conf)
