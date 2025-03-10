import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.stormtypes as s_stormtypes

import xml.etree.ElementTree as xml_et

@s_stormtypes.registry.registerType
class XmlElement(s_stormtypes.Prim):
    '''
    A Storm object for dealing with elements in an XML tree.
    '''
    _storm_typename = 'xml:element'
    _storm_locals = (
        {'name': 'name', 'desc': 'The element tag name.', 'type': 'str'},
        {'name': 'text', 'desc': 'The element text body.', 'type': 'str'},
        {'name': 'attrs', 'desc': 'The element attributes list.', 'type': 'dict'},

        {'name': 'find', 'desc': 'Find all nested elements with the specified tag name.',
         'type': {'type': 'function', '_funcname': 'find',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the XML tag.'},
                      {'name': 'nested', 'type': 'bool', 'default': True,
                        'desc': 'Set to ``(false)`` to only find direct children.'},
                  ),
                  'returns': {'type': 'generator', 'desc': 'A generator which yields xml:elements.'}}},

        {'name': 'get', 'desc': 'Get a single child element by XML tag name.',
         'type': {'type': 'function', '_funcname': 'get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the child XML element tag.'},
                  ),
                  'returns': {'type': 'xml:element', 'desc': 'The child XML element or ``(null)``.'}}},
    )

    def __init__(self, runt, elem):
        s_stormtypes.Prim.__init__(self, None)
        self.runt = runt
        self.elem = elem
        self.locls.update({
            'get': self.get,
            'find': self.find,
            'name': elem.tag,
            'text': elem.text,
            'attrs': elem.attrib,
        })

    async def iter(self):
        for elem in self.elem:
            yield XmlElement(self.runt, elem)

    @s_stormtypes.stormfunc(readonly=True)
    async def find(self, name, nested=True):
        name = await s_stormtypes.tostr(name)
        nested = await s_stormtypes.tobool(nested)

        if nested:
            for elem in self.elem.iter(name):
                yield XmlElement(self.runt, elem)
        else:
            for elem in self.elem.findall(name):
                yield XmlElement(self.runt, elem)

    @s_stormtypes.stormfunc(readonly=True)
    async def get(self, name):
        name = await s_stormtypes.tostr(name)
        elem = self.elem.find(name)
        if elem is not None:
            return XmlElement(self.runt, elem)

@s_stormtypes.registry.registerLib
class LibXml(s_stormtypes.Lib):
    '''
    A Storm library for parsing XML.
    '''
    _storm_lib_path = ('xml',)
    _storm_locals = (
        {'name': 'parse', 'desc': 'Parse an XML string into an xml:element tree.',
         'type': {'type': 'function', '_funcname': 'parse',
            'args': (
                {'name': 'valu', 'type': 'str', 'desc': 'The XML string to parse into an xml:element tree.'},
            ),
            'returns': {'type': 'xml:element', 'desc': 'An xml:element for the root node of the XML tree.'},
        }},
    )

    def getObjLocals(self):
        return {
            'parse': self.parse,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def parse(self, valu):
        valu = await s_stormtypes.tostr(valu)
        try:
            root = await s_coro.semafork(xml_et.fromstring, valu)
            return XmlElement(self.runt, root)
        except xml_et.ParseError as e:
            raise s_exc.BadArg(mesg=f'Invalid XML text: {str(e)}')
