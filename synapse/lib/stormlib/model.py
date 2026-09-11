import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
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
        'desc': 'Edit lock status of deprecated model elements.',
        'cmdargs': (
            ('name', {'help': 'The deprecated form or property name to lock or * to lock all.'}),
            ('--unlock', {'help': 'Unlock rather than lock the deprecated property.', 'default': False, 'action': 'store_true'}),
        ),
        'storm': '''
            init {
                if $cmdopts.unlock {
                    $lib.print(`Unlocking: {$cmdopts.name}`)
                    $lib.model.deprecated.lock($cmdopts.name, (false))
                } else {
                    if ($cmdopts.name = "*") {
                        $lib.print("Locking all deprecated model elements.")
                        for ($name, $locked) in $lib.model.deprecated.locks() {
                            if (not $locked) { $lib.model.deprecated.lock($name, (true)) }
                        }
                    } else {
                        $lib.print(`Locking: {$cmdopts.name}`)
                        $lib.model.deprecated.lock($cmdopts.name, (true))
                    }
                }
            }
        ''',
    },
    {
        'name': 'model.deprecated.locks',
        'desc': 'Display lock status of deprecated model elements.',
        'storm': '''
            $locks = $lib.model.deprecated.locks()
            if $locks {
                $lib.print("Lock status for deprecated forms/props:")
                for ($name, $locked) in $lib.sorted($locks) {
                    $lib.print(`{$name}: {$locked}`)
                }
            } else {
                $lib.print("No deprecated locks found.")
            }
        ''',
    },
    {
        'name': 'model.deprecated.check',
        'desc': 'Check for lock status and the existence of deprecated model elements',
        'storm': '''
            init {

                $ok = (true)
                $lib.print("Checking the cortex for model flag day readiness...")

                $locks = $lib.model.deprecated.locks()

                $lib.print("Checking deprecated model locks:")
                for ($name, $locked) in $locks {
                    if $locked {
                        $lib.print(`{$name} is locked`)
                    } else {
                        $lib.warn(`{$name} is not yet locked`)
                        $ok = (false)
                    }

                }

                $lib.print("Checking for existence of deprecated model elements:")
                for ($name, $locked) in $locks {

                    $lib.print(`{$name}...`)

                    for $layr in $lib.layer.list() {
                        if $layr.getPropCount($name) {
                            $lib.warn(`Layer {$layr.iden} still contains {$name}`)
                            $ok = (false)
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
            Get the tag model specification for `cno.threat`::

                $dict = $lib.model.tags.get(cno.threat)''',
         'type': {'type': 'function', '_funcname': '_getTagModel',
                  'args': (
                    {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The tag model definition.'}}},
        {'name': 'set', 'desc': '''
        Set a tag model property for a tag.

        Examples:
            Create a tag model for the `cno.cve` tag::

                $regx = ([(null), (null), "[0-9]{4}", "[0-9]{5}"])
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
                Remove the regex list from the `cno.threat` tag model::

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
            Delete the tag model specification for `cno.threat`::

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
                              'desc': 'The `model:type` instance if the type if present on the form or null.',
                              }}},
        {'name': 'prop', 'desc': 'Get a prop object by name.',
         'type': {'type': 'function', '_funcname': '_methProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the prop to retrieve.', },
                  ),
                  'returns': {'type': ['model:property', 'null'],
                              'desc': 'The `model:property` instance if the type if present or null.',
                              }}},
        {'name': 'form', 'desc': 'Get a form object by name.',
         'type': {'type': 'function', '_funcname': '_methForm',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the form to retrieve.', },
                  ),
                  'returns': {'type': ['model:form', 'null'],
                              'desc': 'The `model:form` instance if the form is present or null.',
                              }}},
        {'name': 'tagprop', 'desc': 'Get a tag property object by name.',
         'type': {'type': 'function', '_funcname': '_methTagProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the tag prop to retrieve.', },
                  ),
                  'returns': {'type': ['model:tagprop', 'null'],
                              'desc': 'The `model:tagprop` instance of the tag prop if present or null.',
                              }}},
        {'name': 'edge', 'desc': 'Get an edge object by name.',
         'type': {'type': 'function', '_funcname': '_methEdge',
                  'args': (
                      {'name': 'n1form', 'type': 'str', 'desc': 'The form of the n1 node of the edge to retrieve.'},
                      {'name': 'verb', 'type': 'str', 'desc': 'The verb of the edge to retrieve.'},
                      {'name': 'n2form', 'type': 'str', 'desc': 'The form of the n2 node of the edge to retrieve.'},
                  ),
                  'returns': {'type': ['model:edge', 'null'],
                              'desc': 'The `model:edge` instance of the edge if present or null.',
                              }}},
    )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)
        self.model = runt.model

    def getObjLocals(self):
        return {
            'edge': self._methEdge,
            'type': self._methType,
            'prop': self._methProp,
            'form': self._methForm,
            'tagprop': self._methTagProp,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methEdge(self, n1form, verb, n2form):
        verb = await s_stormtypes.tostr(verb)
        n1form = await s_stormtypes.tostr(n1form, noneok=True)
        n2form = await s_stormtypes.tostr(n2form, noneok=True)

        if (edge := self.model.edge((n1form, verb, n2form))) is not None:
            return ModelEdge(edge)

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
        {'name': 'name', 'desc': 'The name of the Form.', 'type': 'str', },
        {'name': 'prop', 'desc': 'Get a Property on the Form.',
         'type': {'type': 'function', '_funcname': '_getFormProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The property to retrieve.', },
                  ),
                  'returns': {'type': ['model:property', 'null'],
                              'desc': 'The `model:property` instance if the property if present on the form or null.'
                              }}},
        {'name': 'props', 'desc': 'Get a dictionary of Properties on the Form.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorFormProps',
                  'returns': {'type': 'model:form:props'}}},
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
            'props': self._ctorFormProps,
        })

    def getObjLocals(self):
        return {
            'prop': self._getFormProp,
        }

    def _ctorFormType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _ctorFormProps(self, path=None):
        return ModelFormProps(self.valu.props, path=path)

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
        {'name': 'computed', 'desc': "True if the Property has been computed from another.", 'type': 'boolean', },
        {'name': 'form', 'desc': 'Get the Form for the Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorPropForm',
                  'returns': {'type': ['model:form', 'null']}}},
        {'name': 'types', 'desc': 'Get the types allowed for the property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorPropTypes',
                  'returns': {'type': 'list', 'desc': 'A list of `model:type` objects for the types allowed in the property.'}}},
    )
    _storm_typename = 'model:property'
    def __init__(self, prop, path=None):

        s_stormtypes.Prim.__init__(self, prop, path=path)

        self.ctors.update({
            'form': self._ctorPropForm,
            'types': self._ctorPropTypes,
        })

        self.locls['name'] = self.valu.name
        self.locls['full'] = self.valu.full
        self.locls['computed'] = bool(self.valu.info.get('computed', False))

    def _ctorPropTypes(self, path=None):
        ptyp = self.valu.type

        if self.valu.isform:
            return (ModelType(ptyp),)

        if ptyp.isarray:
            ptyp = ptyp.arraytype

        return tuple(ModelType(tobj) for tobj in ptyp.getTypeSet())

    def _ctorPropForm(self, path=None):
        if self.valu.form is None:
            return None

        return ModelForm(self.valu.form, path=path)

    def value(self):
        return self.valu.pack()

@s_stormtypes.registry.registerType
class ModelFormProps(s_stormtypes.Prim):
    '''
    A Storm Primitive representing the properties on a Form.
    '''
    _storm_typename = 'model:form:props'

    def __init__(self, props, path=None):
        s_stormtypes.Prim.__init__(self, props, path=path)
        self.locls.update(self.getObjLocals())

    async def _storm_contains(self, item):
        item = await s_stormtypes.tostr(item)
        return item in self.valu

    async def _derefGet(self, name):
        name = await s_stormtypes.tostr(name)
        prop = self.valu.get(name)
        if prop is not None:
            return ModelProp(prop)

    async def iter(self):
        for name, prop in self.valu.items():
            yield name, ModelProp(prop)

    @s_stormtypes.stormfunc(readonly=True)
    def value(self):
        return {name: ModelProp(prop) for name, prop in self.valu.items()}

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
        {'name': 'stortype', 'desc': 'The stortype of the Type.', 'type': 'int', },
        {'name': 'opts', 'desc': 'The options for the Type.', 'type': 'dict', },
        {'name': 'mutable', 'desc': 'True if the type is mutable.', 'type': 'boolean', },
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
                           'mutable': valu.ismutable,
                           })

    def getObjLocals(self):
        return {
            'norm': self._methNorm,
            'repr': self._methRepr,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRepr(self, valu):
        valu = await s_stormtypes.tostor(valu)
        nval = await self.valu.norm(valu)
        return self.valu.repr(nval[0])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNorm(self, valu):
        valu = await s_stormtypes.tostor(valu)
        return await self.valu.norm(valu)

    def value(self):
        return self.valu.getTypeDef()

@s_stormtypes.registry.registerType
class ModelEdge(s_stormtypes.Prim):
    '''
    Implements the Storm API for an Edge.
    '''
    _storm_locals = (
        {'name': 'n1form', 'type': 'str',
         'desc': 'The form of the n1 node. May be null to specify "any".'},
        {'name': 'verb', 'type': 'str', 'desc': 'The edge verb.'},
        {'name': 'n2form', 'type': 'str',
         'desc': 'The form of the n2 node. May be null to specify "any".'},
    )
    _storm_typename = 'model:edge'
    def __init__(self, edge, path=None):

        s_stormtypes.Prim.__init__(self, edge, path=path)

        (n1form, verb, n2form) = edge.edgetype

        self.locls.update({'n1form': n1form,
                           'verb': verb,
                           'n2form': n2form})

    def value(self):
        return self.valu.pack()

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

        for tagname, tagprops in src.getStormTagProps().items():
            for propname, valu in tagprops.items():
                if overwrite or not proto.hasTagProp(tagname, propname):
                    valu = await s_stormtypes.tostor(valu)
                    await proto.setTagProp(tagname, propname, valu) # use tag perms

    async def copyExtProps(self, src, proto):

        form = src.form

        for name, valu in src.getStormProps().items():
            prop = form.props.get(name)
            if not prop.isext:
                continue

            await proto.set(name, await s_stormtypes.tostor(valu))

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
        {'name': 'fuse', 'desc': '''
            Merge one node into another node, then delete the source node.

            This operates on the whole Cortex rather than the current view. Every layer is
            processed, so after the fuse the source node no longer exists in any view.

            The following are transferred from src to dst. dst is the survivor, so its
            existing value wins wherever both nodes hold a conflicting value:

            - Secondary properties (dst values win on conflict).
            - Extended properties (dst values win on conflict).
            - Tags (additive; two intervals are unioned, and an interval on dst is never
              replaced by an unbounded tag on src).
            - Tag properties (dst values win on conflict).
            - Light edges (additive; both N1 and N2 edges are moved to dst).
            - Node data (dst values win on conflict).

            The following special cases apply regardless of the conflict policy:

            - The `.created` node meta property on dst is always the earlier of the two.
            - A property whose type merges rather than overwrites is merged rather than
              having one value win. That covers interval typed properties and tag
              properties, the `:seen` interval, and minimum and maximum time properties.
            - Computed secondary properties are never copied from src. A computed property
              restates the node's own primary property rather than being data src can hand
              over, so after the fuse it must describe dst. dst keeps its own, which are
              copied from whichever layer already holds them when the fuse creates dst in a
              layer it did not previously exist in.

              One consequence is worth noting: a computed property a form populates from a
              callback rather than from normalization is not recomputed either, because a
              fuse writes to layers directly and runs no form callbacks. This only applies
              to a layer in which the fuse creates dst, since dst retains its own computed
              properties in the layer it was created in.
            - Inbound references (properties on other nodes which point at src) are
              rewritten to point at dst. This includes typed value (poly) properties and
              array properties. A property which is declared for one of src's ancestor
              forms may have filed its reference under that ancestor rather than under
              src's own form; such a reference keeps the ancestor it was filed under.
            - A computed comp key sub-property which references src causes that comp form
              node to be renamed, which is applied as a further fuse. Where a comp form
              embeds src in more than one of its computed sub-properties, every one of them
              is remapped by that single rename, so the renamed node never keeps a slot
              naming a node the fuse deleted. Those renames are all computed before any
              edit is applied, so if one of them cannot be re-normalized the fuse is
              refused and nothing is changed.
            - A computed secondary property which is not a comp sub-property is rewritten
              in place. The referring node keeps its own primary property, so that computed
              property will no longer match the value it was derived from.
            - A reference src holds to itself, whether a property or a light edge, follows
              the node and becomes a reference dst holds to itself.

            Requirements and restrictions:

            - The caller must be a global admin.
            - src and dst must be the same form, or one form must inherit from the other.
            - src and dst may not be runt nodes.

            Form inheritance:

            Where src and dst are not the same form, one must be an ancestor of the other.
            dst's own form is the one which survives; a fuse never reclassifies a node.

            Because properties are inherited from a parent form by its children and never
            the other way around, fusing a child form node into a parent form node can find
            a property src holds which dst's form does not declare. There is nowhere to put
            such a value, so it is discarded and a warning naming the property and both
            forms is emitted.

            An inbound reference is refused rather than rewritten where the referring
            property cannot hold dst's form - a typed value property declared for src's
            child form cannot hold a parent form node. That is detected while the fuse is
            still being computed, so the fuse is refused and nothing is changed.

            Layer behavior:

            Each property, tag, tag property, light edge and node data value is written to the
            same layer it was already stored in, so a fuse does not move data between layers.
            One consequence is that property merges only happen within a layer. Where src and
            dst hold the same property in different layers, the value visible in any given view
            is decided by that view's normal layer precedence.

            Read only layers cannot be written to. Those layers are skipped and a warning is
            emitted for each one which held any of src's data, because that data remains and
            will still make src visible in any view which includes that layer. A fuse does
            not write a tombstone into a layer above such a layer to hide it.

            State src holds only as a tombstone in a layer is treated as absent and is not
            transferred. Where dst holds a tombstone which would mask a value being
            transferred to it, that tombstone is removed so the transferred value is
            visible.

            Concurrency:

            The edits which make up a fuse are computed by reading every layer, and are then
            applied by Cortex wide operations which carry them.

            Those reads are not serialized against other writes, so a write to src can land
            between the reads and the apply. That write is not detected and is not reported: a
            fuse is responsible for executing the merge it was asked to make, not for policing
            edits other callers make to src while it runs, the same way an ordinary concurrent
            property write is never flagged as having lost a race to another writer. Running a
            fuse during a maintenance window, as recommended below, avoids this entirely.

            A fuse is not transactional. The edits are written with one call per layer, and
            fusing a heavily referenced node is applied in several operations rather than one,
            so a failure part way through can leave some of the fuse applied. Nothing is
            removed from src until dst holds it and the references to src have been repointed,
            so an interruption cannot lose data or leave a reference pointing at a node which
            no longer exists. Re-running fuse() with the same arguments completes it.

            There is no limit on how many edits a fuse may make. A fuse of a very heavily
            referenced node takes longer and spans more operations, but is not refused.

            Notes:

            - Triggers do not fire for the edits a fuse makes. A fuse rewrites the same data
              across every layer in the Cortex rather than making an analytical change in one
              view, so there is no single view whose triggers are the right ones to run.
            - A light edge between src and dst becomes a self-edge on dst after the fuse.
            - Node objects which other running queries already hold for src become stale, so
              running a fuse during a maintenance window is recommended.

            Known gaps:

            - Inbound tag property references are not rewritten. A tag property may be typed
              as a form, and a tag property which references src is left pointing at a node
              the fuse deleted.
            - A guid form whose primary value is constructed from a deconfliction set of its
              own properties is not renamed when one of those properties references src.
              That property is rewritten in place, so the node's guid is no longer the hash
              of its own current property values. Nothing records which properties a guid
              was deconflicted on, so the fuse cannot re-derive the value and rename the
              node the way it renames a comp form.

              The node itself remains usable. Guid deconfliction falls back to lifting by
              the deconfliction properties when the exact guid is not found, so a
              construction from the node's current values - the deconfliction set with the
              fused value substituted in - still deconflicts to it. Only the stale primary
              value is left behind, and only a construction from the pre-fuse value is
              affected by it.

              Such a construction no longer deconflicts to the node, because the
              deconfliction re-check sees the rewritten property. A second node is created
              with a new guid instead, and re-creates src along with it. The fused node
              keeps the analytical data and the new node holds only the deconfliction
              properties, so the two are then divergent records of the same thing. This
              settles at one extra node rather than adding one per attempt, since the new
              node is found by property deconfliction afterwards.

              This is reached by ordinary use of the Synapse data model rather than only by
              an extended form: any guid form deconflicted on a property which references
              another node qualifies, since a deconfliction set is chosen when the node is
              constructed and is not a property of the form. A power-up which re-ingests
              the same source data on a schedule will therefore re-create a node which was
              fused away, along with a duplicate of whatever referenced it.
        ''',
         'type': {'type': 'function', '_funcname': '_methFuse',
                  'args': (
                      {'name': 'src', 'type': 'node', 'desc': 'The node to merge from (will be deleted).', },
                      {'name': 'dst', 'type': 'node', 'desc': 'The node to merge into (will be kept).', },
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
            'fuse': self._methFuse,
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

    async def _methFuse(self, src, dst):

        self.runt.reqAdmin(mesg='$lib.model.migration.fuse() requires global admin.')

        # NodeBase rather than Node, so that a runt node reaches the runt check below and
        # gets told it is a runt rather than being told it is not a node: RuntNode is a
        # sibling of Node rather than a subclass of it.
        if not isinstance(src, s_node.NodeBase):
            raise s_exc.BadArg(mesg='$lib.model.migration.fuse() src argument must be a node.')

        if not isinstance(dst, s_node.NodeBase):
            raise s_exc.BadArg(mesg='$lib.model.migration.fuse() dst argument must be a node.')

        # Checked ahead of the form compatibility check below, so that naming a runt node is
        # reported as the runt node it is rather than as a form mismatch. A runt form is
        # never in an inheritance chain with a non-runt one, so a compatible pair naming one
        # runt node always names two, and this would otherwise never be reached for dst.
        if src.form.isrunt:
            raise s_exc.IsRuntForm(mesg='$lib.model.migration.fuse() cannot fuse runt nodes.',
                                   form=src.form.full)

        if dst.form.isrunt:
            raise s_exc.IsRuntForm(mesg='$lib.model.migration.fuse() cannot fuse runt nodes.',
                                   form=dst.form.full)

        # dst's own form is the survivor, so the two only need to be compatible rather than
        # identical: a property or a typed value declared for an ancestor form accepts either
        # of them, which is what makes transferring state between them meaningful.
        if src.form is not dst.form and \
                src.form.name not in dst.form.formtypes and \
                dst.form.name not in src.form.formtypes:
            raise s_exc.BadArg(mesg='$lib.model.migration.fuse() requires src and dst to be the '
                                    'same form or for one form to inherit from the other.')

        if src.nid == dst.nid:
            await self.runt.warn('$lib.model.migration.fuse() src and dst are the same node, skipping.')
            return

        runt = self.runt
        core = runt.view.core

        srcndef = src.ndef
        dstndef = dst.ndef

        result = await core.fuseNodes(srcndef, dstndef, runt.user.iden)

        # A fuse is computed and applied down in the Cortex, with no Storm runtime to warn
        # into, so the warnings are collected and emitted out here.
        for mesg in result.get('warnings', ()):
            await runt.warn(mesg, log=False)

        failed = result.get('failed')
        if failed:
            mesg = '$lib.model.migration.fuse() failed to apply edits to some layers: '
            mesg += ', '.join([f'{iden} ({errm})' for iden, errm in failed])
            raise s_exc.SynErr(mesg=mesg, layers=[iden for iden, _ in failed])

@s_stormtypes.registry.registerLib
class LibModelMigrations(s_stormtypes.Lib, MigrationEditorMixin):
    '''
    A Storm library for selectively migrating nodes in the current view.
    '''
    _storm_locals = ()
    _storm_lib_path = ('model', 'migration', 's')

    def getObjLocals(self):
        return {}
