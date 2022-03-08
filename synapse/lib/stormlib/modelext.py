import synapse.exc as s_exc
import synapse.lib.grammar as s_grammar

from synapse.lib.stormtypes import Lib, registry, confirm, tostr, toprim

@registry.registerLib
class LibModelExt(Lib):
    '''
    A Storm library for manipulating extended model elements.
    '''
    _storm_locals = (
        {'name': 'addForm', 'desc': 'Add an extended form definition to the data model.',
         'type': {'type': 'function', '_funcname': 'addForm',
                  'args': (
                      {'name': 'formname', 'type': 'str', 'desc': 'The name of the form to add.', },
                      {'name': 'basetype', 'type': 'str', 'desc': 'The base type the form is derived from.', },
                      {'name': 'typeopts', 'type': 'dict', 'desc': 'A Synapse type opts dictionary.', },
                      {'name': 'typeinfo', 'type': 'dict', 'desc': 'A Synapse form info dictionary.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addFormProp', 'desc': 'Add an extended property definition to the data model.',
         'type': {'type': 'function', '_funcname': 'addFormProp',
                  'args': (
                      {'name': 'formname', 'type': 'str', 'desc': 'The name of the form to add the property to.', },
                      {'name': 'propname', 'type': 'str', 'desc': 'The name of the extended property.', },
                      {'name': 'typedef', 'type': 'list', 'desc': 'A Synapse type definition tuple.', },
                      {'name': 'propinfo', 'type': 'dict', 'desc': 'A synapse property definition dictionary.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addUnivProp', 'desc': 'Add an extended universal property definition to the data model.',
         'type': {'type': 'function', '_funcname': 'addUnivProp',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'The name of the universal property.', },
                      {'name': 'typedef', 'type': 'list', 'desc': 'A Synapse type definition tuple.', },
                      {'name': 'propinfo', 'type': 'dict', 'desc': 'A synapse property definition dictionary.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addTagProp', 'desc': 'Add an extended tag property definition to the data model.',
         'type': {'type': 'function', '_funcname': 'addTagProp',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'The name of the tag property.', },
                      {'name': 'typedef', 'type': 'list', 'desc': 'A Synapse type definition tuple.', },
                      {'name': 'propinfo', 'type': 'dict', 'desc': 'A synapse property definition dictionary.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delForm', 'desc': 'Remove an extended form definition from the model.',
         'type': {'type': 'function', '_funcname': 'delForm',
                  'args': (
                      {'name': 'formname', 'type': 'str', 'desc': 'The extended form to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delFormProp', 'desc': 'Remove an extended property definition from the model.',
         'type': {'type': 'function', '_funcname': 'delFormProp',
                  'args': (
                      {'name': 'formname', 'type': 'str', 'desc': 'The form with the extended property.', },
                      {'name': 'propname', 'type': 'str', 'desc': 'The extended property to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delUnivProp',
         'desc': 'Remove an extended universal property definition from the model.',
         'type': {'type': 'function', '_funcname': 'delUnivProp',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'Name of the universal property to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delTagProp', 'desc': 'Remove an extended tag property definition from the model.',
         'type': {'type': 'function', '_funcname': 'delTagProp',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'Name of the tag property to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_lib_path = ('model', 'ext')

    def getObjLocals(self):
        return {
            'addForm': self.addForm,
            'addFormProp': self.addFormProp,
            'addUnivProp': self.addUnivProp,
            'addTagProp': self.addTagProp,
            'delForm': self.delForm,
            'delFormProp': self.delFormProp,
            'delUnivProp': self.delUnivProp,
            'delTagProp': self.delTagProp,
        }

    # TODO type docs in the new convention

    async def addForm(self, formname, basetype, typeopts, typeinfo):
        formname = await tostr(formname)
        basetype = await tostr(basetype)
        typeopts = await toprim(typeopts)
        typeinfo = await toprim(typeinfo)
        confirm(('model', 'form', 'add', formname))
        await self.runt.snap.core.addForm(formname, basetype, typeopts, typeinfo)

    async def addFormProp(self, formname, propname, typedef, propinfo):
        formname = await tostr(formname)
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'prop', 'add', formname))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(prop=propname, mesg=mesg)
        await self.runt.snap.core.addFormProp(formname, propname, typedef, propinfo)

    async def addUnivProp(self, propname, typedef, propinfo):
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'univ', 'add'))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(name=propname, mesg=mesg)
        await self.runt.snap.core.addUnivProp(propname, typedef, propinfo)

    async def addTagProp(self, propname, typedef, propinfo):
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'tagprop', 'add'))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(name=propname, mesg=mesg)
        await self.runt.snap.core.addTagProp(propname, typedef, propinfo)

    async def delForm(self, formname):
        formname = await tostr(formname)
        confirm(('model', 'form', 'del', formname))
        await self.runt.snap.core.delForm(formname)

    async def delFormProp(self, formname, propname):
        formname = await tostr(formname)
        propname = await tostr(propname)
        confirm(('model', 'prop', 'del', formname))
        await self.runt.snap.core.delFormProp(formname, propname)

    async def delUnivProp(self, propname):
        propname = await tostr(propname)
        confirm(('model', 'univ', 'del'))
        await self.runt.snap.core.delUnivProp(propname)

    async def delTagProp(self, propname):
        propname = await tostr(propname)
        confirm(('model', 'tagprop', 'del'))
        await self.runt.snap.core.delTagProp(propname)
