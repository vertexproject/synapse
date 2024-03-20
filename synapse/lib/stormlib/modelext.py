import synapse.exc as s_exc
import synapse.lib.grammar as s_grammar

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibModelExt(s_stormtypes.Lib):
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
        {'name': 'getExtModel', 'desc': 'Get all extended model elements.',
         'type': {'type': 'function', '_funcname': 'getExtModel', 'args': (),
                  'returns': {'type': 'dict'}}},
        {'name': 'addExtModel', 'desc': 'Add extended model elements to the Cortex from getExtModel().',
        'type': {'type': 'function', '_funcname': 'addExtModel', 'args': (
                      {'name': 'model', 'type': 'dict', 'desc': 'A model dictionary from getExtModel().', },
                  ),
                  'returns': {'type': 'boolean'}}},
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
            'getExtModel': self.getExtModel,
            'addExtModel': self.addExtModel,
        }

    # TODO type docs in the new convention

    async def addForm(self, formname, basetype, typeopts, typeinfo):
        formname = await s_stormtypes.tostr(formname)
        basetype = await s_stormtypes.tostr(basetype)
        typeopts = await s_stormtypes.toprim(typeopts)
        typeinfo = await s_stormtypes.toprim(typeinfo)
        s_stormtypes.confirm(('model', 'form', 'add', formname))
        await self.runt.snap.core.addForm(formname, basetype, typeopts, typeinfo)

    async def addFormProp(self, formname, propname, typedef, propinfo):
        formname = await s_stormtypes.tostr(formname)
        propname = await s_stormtypes.tostr(propname)
        typedef = await s_stormtypes.toprim(typedef)
        propinfo = await s_stormtypes.toprim(propinfo)
        s_stormtypes.confirm(('model', 'prop', 'add', formname))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(prop=propname, mesg=mesg)
        await self.runt.snap.core.addFormProp(formname, propname, typedef, propinfo)

    async def addUnivProp(self, propname, typedef, propinfo):
        propname = await s_stormtypes.tostr(propname)
        typedef = await s_stormtypes.toprim(typedef)
        propinfo = await s_stormtypes.toprim(propinfo)
        s_stormtypes.confirm(('model', 'univ', 'add'))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(name=propname, mesg=mesg)
        await self.runt.snap.core.addUnivProp(propname, typedef, propinfo)

    async def addTagProp(self, propname, typedef, propinfo):
        propname = await s_stormtypes.tostr(propname)
        typedef = await s_stormtypes.toprim(typedef)
        propinfo = await s_stormtypes.toprim(propinfo)
        s_stormtypes.confirm(('model', 'tagprop', 'add'))
        if not s_grammar.isBasePropNoPivprop(propname):
            mesg = f'Invalid prop name {propname}'
            raise s_exc.BadPropDef(name=propname, mesg=mesg)
        await self.runt.snap.core.addTagProp(propname, typedef, propinfo)

    async def delForm(self, formname):
        formname = await s_stormtypes.tostr(formname)
        s_stormtypes.confirm(('model', 'form', 'del', formname))
        await self.runt.snap.core.delForm(formname)

    async def delFormProp(self, formname, propname):
        formname = await s_stormtypes.tostr(formname)
        propname = await s_stormtypes.tostr(propname)
        s_stormtypes.confirm(('model', 'prop', 'del', formname))
        await self.runt.snap.core.delFormProp(formname, propname)

    async def delUnivProp(self, propname):
        propname = await s_stormtypes.tostr(propname)
        s_stormtypes.confirm(('model', 'univ', 'del'))
        await self.runt.snap.core.delUnivProp(propname)

    async def delTagProp(self, propname):
        propname = await s_stormtypes.tostr(propname)
        s_stormtypes.confirm(('model', 'tagprop', 'del'))
        await self.runt.snap.core.delTagProp(propname)

    @s_stormtypes.stormfunc(readonly=True)
    async def getExtModel(self):
        return await self.runt.snap.core.getExtModel()

    async def addExtModel(self, model):
        model = await s_stormtypes.toprim(model)
        return await self.runt.snap.core.addExtModel(model)
