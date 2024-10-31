import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.stormtypes as s_stormtypes

RISK_HASVULN_VULNPROPS = (
    'hardware',
    'host',
    'item',
    'org',
    'person',
    'place',
    'software',
    'spec',
)

stormcmds = [
    {
        'name': 'model.deprecated.lock',
        'descr': 'Edit lock status of deprecated model elements.',
        'cmdargs': (
            ('name', {'help': 'The deprecated form or property name to lock or * to lock all.'}),
            ('--unlock', {'help': 'Unlock rather than lock the deprecated property.', 'default': False, 'action': 'store_true'}),
        ),
        'storm': '''
            init {
                if $cmdopts.unlock {
                    $lib.print("Unlocking: {name}", name=$cmdopts.name)
                    $lib.model.deprecated.lock($cmdopts.name, $lib.false)
                } else {
                    if ($cmdopts.name = "*") {
                        $lib.print("Locking all deprecated model elements.")
                        for ($name, $locked) in $lib.model.deprecated.locks() {
                            if (not $locked) { $lib.model.deprecated.lock($name, $lib.true) }
                        }
                    } else {
                        $lib.print("Locking: {name}", name=$cmdopts.name)
                        $lib.model.deprecated.lock($cmdopts.name, $lib.true)
                    }
                }
            }
        ''',
    },
    {
        'name': 'model.deprecated.locks',
        'descr': 'Display lock status of deprecated model elements.',
        'storm': '''
            $locks = $lib.model.deprecated.locks()
            if $locks {
                $lib.print("Lock status for deprecated forms/props:")
                for ($name, $locked) in $lib.sorted($locks) {
                    $lib.print("{name}: {locked}", name=$name, locked=$locked)
                }
            } else {
                $lib.print("No deprecated locks found.")
            }
        ''',
    },
    {
        'name': 'model.deprecated.check',
        'descr': 'Check for lock status and the existence of deprecated model elements',
        'storm': '''
            init {

                $ok = $lib.true
                $lib.print("Checking the cortex for model flag day readiness...")

                $locks = $lib.model.deprecated.locks()

                $lib.print("Checking deprecated model locks:")
                for ($name, $locked) in $locks {
                    if $locked {
                        $lib.print("{name} is locked", name=$name)
                    } else {
                        $lib.warn("{name} is not yet locked", name=$name)
                        $ok = $lib.false
                    }

                }

                $lib.print("Checking for existence of deprecated model elements:")
                for ($name, $locked) in $locks {

                    $lib.print("{name}...", name=$name)

                    for $layr in $lib.layer.list() {
                        if $layr.getPropCount($name) {
                            $lib.warn("Layer {iden} still contains {name}", iden=$layr.iden, name=$name)
                            $ok = $lib.false
                        }
                    }
                }

                if (not $ok) {
                    $lib.print("Your cortex contains deprecated model elements.")
                } else {
                    $lib.print("Congrats! Your Cortex is fully future-model compliant!")
                }

            }
        ''',
    },
]

@s_stormtypes.registry.registerLib
class LibModelTags(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with tag specifications in the Cortex Data Model.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': '''
        Retrieve a tag model specification.

        Examples:
            Get the tag model specification for ``cno.threat``::

                $dict = $lib.model.tags.get(cno.threat)''',
         'type': {'type': 'function', '_funcname': '_getTagModel',
                  'args': (
                    {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The tag model definition.'}}},
        {'name': 'set', 'desc': '''
        Set a tag model property for a tag.

        Examples:
            Create a tag model for the ``cno.cve`` tag::

                $regx = ($lib.null, $lib.null, "[0-9]{4}", "[0-9]{5}")
                $lib.model.tags.set(cno.cve, regex, $regx)''',
         'type': {'type': 'function', '_funcname': '_setTagModel',
                  'args': (
                      {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag.', },
                      {'name': 'propname', 'type': 'str', 'desc': 'The name of the tag model property.', },
                      {'name': 'propvalu', 'type': 'prim', 'desc': 'The value to set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'pop', 'desc': '''
            Pop and return a tag model property.

            Examples:
                Remove the regex list from the ``cno.threat`` tag model::

                    $regxlist = $lib.model.tags.pop(cno.threat, regex)''',
         'type': {'type': 'function', '_funcname': '_popTagModel',
                  'args': (
                      {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag.', },
                      {'name': 'propname', 'type': 'str', 'desc': 'The name of the tag model property.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The value of the property.', }}},
        {'name': 'del', 'desc': '''
        Delete a tag model specification.

        Examples:
            Delete the tag model specification for ``cno.threat``::

                $lib.model.tags.del(cno.threat)''',
         'type': {'type': 'function', '_funcname': '_delTagModel',
                  'args': (
                      {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': '''
        List all tag model specifications.

        Examples:
            Iterate over the tag model specifications in the Cortex::

                for ($name, $info) in $lib.model.tags.list() {
                    ...
                }''',
         'type': {'type': 'function', '_funcname': '_listTagModel',
                  'returns': {'type': 'list', 'desc': 'List of tuples containing the tag name and model definition', }}},
    )
    _storm_lib_path = ('model', 'tags', )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'get': self._getTagModel,
            'set': self._setTagModel,
            'pop': self._popTagModel,
            'del': self._delTagModel,
            'list': self._listTagModel,
        }

    async def _delTagModel(self, tagname):
        tagname = await s_stormtypes.tostr(tagname)
        self.runt.confirm(('model', 'tag', 'set'))
        return await self.runt.view.core.delTagModel(tagname)

    @s_stormtypes.stormfunc(readonly=True)
    async def _getTagModel(self, tagname):
        tagname = await s_stormtypes.tostr(tagname)
        return await self.runt.view.core.getTagModel(tagname)

    @s_stormtypes.stormfunc(readonly=True)
    async def _listTagModel(self):
        return await self.runt.view.core.listTagModel()

    async def _popTagModel(self, tagname, propname):
        tagname = await s_stormtypes.tostr(tagname)
        propname = await s_stormtypes.tostr(propname)
        self.runt.confirm(('model', 'tag', 'set'))
        return await self.runt.view.core.popTagModel(tagname, propname)

    async def _setTagModel(self, tagname, propname, propvalu):
        tagname = await s_stormtypes.tostr(tagname)
        propname = await s_stormtypes.tostr(propname)
        propvalu = await s_stormtypes.toprim(propvalu)
        self.runt.confirm(('model', 'tag', 'set'))
        await self.runt.view.core.setTagModel(tagname, propname, propvalu)

@s_stormtypes.registry.registerLib
class LibModel(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Data Model in the Cortex.
    '''
    _storm_lib_path = ('model',)
    _storm_locals = (
        {'name': 'type', 'desc': 'Get a type object by name.',
         'type': {'type': 'function', '_funcname': '_methType',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the type to retrieve.', },
                  ),
                  'returns': {'type': ['model:type', 'null'],
                              'desc': 'The ``model:type`` instance if the type if present on the form or null.',
                              }}},
        {'name': 'prop', 'desc': 'Get a prop object by name.',
         'type': {'type': 'function', '_funcname': '_methProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the prop to retrieve.', },
                  ),
                  'returns': {'type': ['model:property', 'null'],
                              'desc': 'The ``model:property`` instance if the type if present or null.',
                              }}},
        {'name': 'form', 'desc': 'Get a form object by name.',
         'type': {'type': 'function', '_funcname': '_methForm',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the form to retrieve.', },
                  ),
                  'returns': {'type': ['model:form', 'null'],
                              'desc': 'The ``model:form`` instance if the form is present or null.',
                              }}},
        {'name': 'tagprop', 'desc': 'Get a tag property object by name.',
         'type': {'type': 'function', '_funcname': '_methTagProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the tag prop to retrieve.', },
                  ),
                  'returns': {'type': ['model:tagprop', 'null'],
                              'desc': 'The ``model:tagprop`` instance of the tag prop if present or null.',
                              }}},
    )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)
        self.model = runt.model

    def getObjLocals(self):
        return {
            'type': self._methType,
            'prop': self._methProp,
            'form': self._methForm,
            'tagprop': self._methTagProp,
        }

    @s_cache.memoizemethod(size=100)
    @s_stormtypes.stormfunc(readonly=True)
    async def _methType(self, name):
        name = await s_stormtypes.tostr(name)
        type_ = self.model.type(name)
        if type_ is not None:
            return ModelType(type_)

    @s_cache.memoizemethod(size=100)
    @s_stormtypes.stormfunc(readonly=True)
    async def _methProp(self, name):
        name = await s_stormtypes.tostr(name)
        prop = self.model.prop(name)
        if prop is not None:
            return ModelProp(prop)

    @s_cache.memoizemethod(size=100)
    @s_stormtypes.stormfunc(readonly=True)
    async def _methForm(self, name):
        name = await s_stormtypes.tostr(name)
        form = self.model.form(name)
        if form is not None:
            return ModelForm(form)

    @s_cache.memoize(size=100)
    @s_stormtypes.stormfunc(readonly=True)
    async def _methTagProp(self, name):
        name = await s_stormtypes.tostr(name)
        tagprop = self.model.getTagProp(name)
        if tagprop is not None:
            return ModelTagProp(tagprop)

@s_stormtypes.registry.registerType
class ModelForm(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Form.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Form', 'type': 'str', },
        {'name': 'prop', 'desc': 'Get a Property on the Form',
         'type': {'type': 'function', '_funcname': '_getFormProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The property to retrieve.', },
                  ),
                  'returns': {'type': ['model:property', 'null'],
                              'desc': 'The ``model:property`` instance if the property if present on the form or null.'
                              }}},
        {'name': 'type', 'desc': 'Get the Type for the form.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorFormType',
                  'returns': {'type': 'model:type'}}},
    )
    _storm_typename = 'model:form'
    def __init__(self, form, path=None):

        s_stormtypes.Prim.__init__(self, form, path=path)

        self.locls.update(self.getObjLocals())
        self.locls['name'] = self.valu.name

        self.ctors.update({
            'type': self._ctorFormType,
        })

    def getObjLocals(self):
        return {
            'prop': self._getFormProp,
        }

    def _ctorFormType(self, path=None):
        return ModelType(self.valu.type, path=path)

    @s_stormtypes.stormfunc(readonly=True)
    async def _getFormProp(self, name):
        name = await s_stormtypes.tostr(name)
        prop = self.valu.prop(name)
        if prop is not None:
            return ModelProp(prop)

    def value(self):
        return self.valu.pack()

@s_stormtypes.registry.registerType
class ModelProp(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Property.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The short name of the Property.', 'type': 'str', },
        {'name': 'full', 'desc': 'The full name of the Property.', 'type': 'str', },
        {'name': 'form', 'desc': 'Get the Form for the Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorPropForm',
                  'returns': {'type': ['model:form', 'null']}}},
        {'name': 'type', 'desc': 'Get the Type for the Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorPropType',
                  'returns': {'type': 'model:type'}}},
    )
    _storm_typename = 'model:property'
    def __init__(self, prop, path=None):

        s_stormtypes.Prim.__init__(self, prop, path=path)

        self.ctors.update({
            'form': self._ctorPropForm,
            'type': self._ctorPropType,
        })

        self.locls['name'] = self.valu.name
        self.locls['full'] = self.valu.full

    def _ctorPropType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _ctorPropForm(self, path=None):
        if self.valu.form is None:
            return None

        return ModelForm(self.valu.form, path=path)

    def value(self):
        return self.valu.pack()

@s_stormtypes.registry.registerType
class ModelTagProp(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Tag Property.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Tag Property.', 'type': 'str', },
        {'name': 'type', 'desc': 'Get the Type for the Tag Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorTagPropType',
                  'returns': {'type': 'model:type'}}},
    )
    _storm_typename = 'model:tagprop'
    def __init__(self, tagprop, path=None):

        s_stormtypes.Prim.__init__(self, tagprop, path=path)

        self.ctors.update({
            'type': self._ctorTagPropType,
        })

        self.locls['name'] = self.valu.name

    def _ctorTagPropType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def value(self):
        return self.valu.pack()

@s_stormtypes.registry.registerType
class ModelType(s_stormtypes.Prim):
    '''
    A Storm types wrapper around a lib.types.Type
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Type.', 'type': 'str', },
        {'name': 'stortype', 'desc': 'The storetype of the Type.', 'type': 'int', },
        {'name': 'opts', 'desc': 'The options for the Type.', 'type': 'dict', },
        {'name': 'repr', 'desc': 'Get the repr of a value for the Type.',
         'type': {'type': 'function', '_funcname': '_methRepr',
                  'args': (
                      {'name': 'valu', 'desc': 'The value to get the repr of.', 'type': 'any', },
                  ),
                  'returns': {'desc': 'The string form of the value as represented by the type.', 'type': 'str', }}},
        {'name': 'norm', 'desc': 'Get the norm and info for the Type.',
         'type': {'type': 'function', '_funcname': '_methNorm',
                  'args': (
                      {'name': 'valu', 'desc': 'The value to norm.', 'type': 'any', },
                  ),
                  'returns': {'desc': 'A tuple of the normed value and its information dictionary.', 'type': 'list'}}},
    )
    _storm_typename = 'model:type'

    def __init__(self, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())
        self.locls.update({'name': valu.name,
                           'opts': valu.opts,
                           'stortype': valu.stortype,
                           })

    def getObjLocals(self):
        return {
            'norm': self._methNorm,
            'repr': self._methRepr,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRepr(self, valu):
        valu = await s_stormtypes.toprim(valu)
        nval = self.valu.norm(valu)
        return self.valu.repr(nval[0])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNorm(self, valu):
        valu = await s_stormtypes.toprim(valu)
        return self.valu.norm(valu)

    def value(self):
        return self.valu.getTypeDef()

@s_stormtypes.registry.registerLib
class LibModelDeprecated(s_stormtypes.Lib):
    '''
    A storm library for interacting with the model deprecation mechanism.
    '''
    _storm_locals = (
        {'name': 'lock', 'desc': 'Set the locked property for a deprecated model element.',
         'type': {'type': 'function', '_funcname': '_lock',
                  'args': (
                      {'name': 'name', 'desc': 'The full path of the model element to lock.', 'type': 'str', },
                      {'name': 'locked', 'desc': 'The lock status.', 'type': 'boolean', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'locks', 'desc': 'Get a dictionary of the data model elements which are deprecated and their lock status in the Cortex.',
         'type': {'type': 'function', '_funcname': '_locks',
                  'returns': {'type': 'dict', 'desc': 'A dictionary of named elements to their boolean lock values.', }}},
    )
    _storm_lib_path = ('model', 'deprecated')

    def getObjLocals(self):
        return {
            'lock': self._lock,
            'locks': self._locks,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _locks(self):
        todo = s_common.todo('getDeprLocks')
        locks = await self.runt.dyncall('cortex', todo)
        return s_stormtypes.Dict(locks)

    async def _lock(self, name, locked):
        name = await s_stormtypes.tostr(name)
        locked = await s_stormtypes.tobool(locked)
        todo = s_common.todo('setDeprLock', name, locked)
        gatekeys = ((self.runt.user.iden, ('model', 'deprecated', 'lock'), None),)
        await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

class MigrationEditorMixin:
    '''
    Mixin helpers for migrating data within an editor context.
    '''

    async def copyData(self, src, proto, overwrite=False):

        async for name in src.iterDataKeys():
            if overwrite or not await proto.hasData(name):
                self.runt.layerConfirm(('node', 'data', 'set', name))
                valu = await src.getData(name)
                await proto.setData(name, valu)

    async def copyEdges(self, editor, src, proto):

        verbs = set()

        async for (verb, n2nid) in src.iterEdgesN1():

            if verb not in verbs:
                self.runt.layerConfirm(('node', 'edge', 'add', verb))
                verbs.add(verb)

            if await self.runt.view.getNodeByNid(n2nid) is not None:
                await proto.addEdge(verb, n2nid)

        if (dstnid := proto.nid) is None:
            return

        async for (verb, n1nid) in src.iterEdgesN2():

            if verb not in verbs:
                self.runt.layerConfirm(('node', 'edge', 'add', verb))
                verbs.add(verb)

            n1proto = await editor.getNodeByNid(n1nid)
            if n1proto is not None:
                await n1proto.addEdge(verb, dstnid)

    async def copyTags(self, src, proto, overwrite=False):

        for name, valu in src._getTagsDict().items():
            self.runt.layerConfirm(('node', 'tag', 'add', *name.split('.')))
            await proto.addTag(name, valu=valu)

        for tagname, tagprops in src._getTagPropsDict().items():
            for propname, valu in tagprops.items():
                if overwrite or not proto.hasTagProp(tagname, propname):
                    await proto.setTagProp(tagname, propname, valu) # use tag perms

    async def copyExtProps(self, src, proto):

        form = src.form

        for name, valu in src.getProps().items():
            prop = form.props.get(name)
            if not prop.isext:
                continue

            await proto.set(name, valu)

@s_stormtypes.registry.registerLib
class LibModelMigration(s_stormtypes.Lib, MigrationEditorMixin):
    '''
    A Storm library containing migration tools.
    '''
    _storm_locals = (
        {'name': 'copyData', 'desc': 'Copy node data from the src node to the dst node.',
         'type': {'type': 'function', '_funcname': '_methCopyData',
                  'args': (
                      {'name': 'src', 'type': 'node', 'desc': 'The node to copy data from.', },
                      {'name': 'dst', 'type': 'node', 'desc': 'The node to copy data to.', },
                      {'name': 'overwrite', 'type': 'boolean', 'default': False,
                       'desc': 'Copy data even if the key exists on the destination node.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'copyEdges', 'desc': 'Copy edges from the src node to the dst node.',
         'type': {'type': 'function', '_funcname': '_methCopyEdges',
                  'args': (
                      {'name': 'src', 'type': 'node', 'desc': 'The node to copy edges from.', },
                      {'name': 'dst', 'type': 'node', 'desc': 'The node to copy edges to.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'copyTags', 'desc': 'Copy tags, tag timestamps, and tag props from the src node to the dst node.',
         'type': {'type': 'function', '_funcname': '_methCopyTags',
                  'args': (
                      {'name': 'src', 'type': 'node', 'desc': 'The node to copy tags from.', },
                      {'name': 'dst', 'type': 'node', 'desc': 'The node to copy tags to.', },
                      {'name': 'overwrite', 'type': 'boolean', 'default': False,
                       'desc': 'Copy tag property value even if the property exists on the destination node.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'copyExtProps', 'desc': 'Copy extended properties from the src node to the dst node.',
         'type': {'type': 'function', '_funcname': '_methCopyExtProps',
                  'args': (
                      {'name': 'src', 'type': 'node', 'desc': 'The node to copy extended props from.', },
                      {'name': 'dst', 'type': 'node', 'desc': 'The node to copy extended props to.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_lib_path = ('model', 'migration')

    def getObjLocals(self):
        return {
            'copyData': self._methCopyData,
            'copyEdges': self._methCopyEdges,
            'copyTags': self._methCopyTags,
            'copyExtProps': self._methCopyExtProps,
        }

    async def _methCopyData(self, src, dst, overwrite=False):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyData() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyData() dest argument must be a node.')

        overwrite = await s_stormtypes.tobool(overwrite)

        async with self.runt.view.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyData(src, proto, overwrite=overwrite)

    async def _methCopyEdges(self, src, dst):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyEdges() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyEdges() dest argument must be a node.')

        view = self.runt.view

        async with view.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyEdges(editor, src, proto)

    async def _methCopyTags(self, src, dst, overwrite=False):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyTags() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyTags() dest argument must be a node.')

        overwrite = await s_stormtypes.tobool(overwrite)

        view = self.runt.view

        async with view.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyTags(src, proto, overwrite=overwrite)

    async def _methCopyExtProps(self, src, dst):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyExtProps() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyExtProps() dest argument must be a node.')

        view = self.runt.view

        async with view.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyExtProps(src, proto)

@s_stormtypes.registry.registerLib
class LibModelMigrations(s_stormtypes.Lib, MigrationEditorMixin):
    '''
    A Storm library for selectively migrating nodes in the current view.
    '''
    _storm_locals = ()
    _storm_lib_path = ('model', 'migration', 's')

    def getObjLocals(self):
        return {}
