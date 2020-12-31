from synapse.lib.stormtypes import Lib, registry, confirm, tostr, toprim

@registry.registerLib
class LibModelExt(Lib):
    '''
    A Storm library for manipulating extended model elements.
    '''
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
        '''
        Add an extended form definition to the data model.
        '''
        formname = await tostr(formname)
        basetype = await tostr(basetype)
        typeopts = await toprim(typeopts)
        typeinfo = await toprim(typeinfo)
        confirm(('model', 'form', 'add', formname))
        await self.runt.snap.core.addForm(formname, basetype, typeopts, typeinfo)

    async def addFormProp(self, formname, propname, typedef, propinfo):
        '''
        Add an extended property definition to the data model.
        '''
        formname = await tostr(formname)
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'prop', 'add', formname))
        await self.runt.snap.core.addFormProp(formname, propname, typedef, propinfo)

    async def addUnivProp(self, propname, typedef, propinfo):
        '''
        Add an extended universal property definition to the data model.
        '''
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'univ', 'add'))
        await self.runt.snap.core.addUnivProp(propname, typedef, propinfo)

    async def addTagProp(self, propname, typedef, propinfo):
        '''
        Add an extended tag property definition to the data model.
        '''
        propname = await tostr(propname)
        typedef = await toprim(typedef)
        propinfo = await toprim(propinfo)
        confirm(('model', 'tagprop', 'add'))
        await self.runt.snap.core.addTagProp(propname, typedef, propinfo)

    async def delForm(self, formname):
        '''
        Remove an extended form definition from the model.
        '''
        formname = await tostr(formname)
        confirm(('model', 'form', 'del', formname))
        await self.runt.snap.core.delForm(formname)

    async def delFormProp(self, formname, propname):
        '''
        Remove an extended property definition from the model.
        '''
        formname = await tostr(formname)
        propname = await tostr(propname)
        confirm(('model', 'prop', 'del', formname))
        await self.runt.snap.core.delFormProp(formname, propname)

    async def delUnivProp(self, propname):
        '''
        Remove an extended universal property definition from the model.
        '''
        propname = await tostr(propname)
        confirm(('model', 'univ', 'del'))
        await self.runt.snap.core.delUnivProp(propname)

    async def delTagProp(self, propname):
        '''
        Remove an extended tag property definition from the model.
        '''
        propname = await tostr(propname)
        confirm(('model', 'tagprop', 'del'))
        await self.runt.snap.core.delTagProp(propname)
