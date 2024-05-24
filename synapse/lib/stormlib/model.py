import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.stormtypes as s_stormtypes

import synapse.models.infotech as s_infotech

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
        'name': 'model.edge.set',
        'descr': 'Set a key-value for an edge verb that exists in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to add a key to.'}),
            ('key', {'help': 'The key name (e.g. doc).'}),
            ('valu', {'help': 'The string value to set.'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $key = $cmdopts.key
            $lib.model.edge.set($verb, $key, $cmdopts.valu)
            $lib.print('Set edge key: verb={verb} key={key}', verb=$verb, key=$key)
        ''',
    },
    {
        'name': 'model.edge.get',
        'descr': 'Retrieve key-value pairs for an edge verb in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to retrieve.'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $kvpairs = $lib.model.edge.get($verb)
            if $kvpairs {
                $lib.print('verb = {verb}', verb=$verb)
                for ($key, $valu) in $kvpairs {
                    $lib.print('    {key} = {valu}', key=$key, valu=$valu)
                }
            } else {
                $lib.print('verb={verb} contains no key-value pairs.', verb=$verb)
            }
        ''',
    },
    {
        'name': 'model.edge.del',
        'descr': 'Delete a global key-value pair for an edge verb in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to delete documentation for.'}),
            ('key', {'help': 'The key name (e.g. doc).'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $key = $cmdopts.key
            $lib.model.edge.del($verb, $key)
            $lib.print('Deleted edge key: verb={verb} key={key}', verb=$verb, key=$key)
        ''',
    },
    {
        'name': 'model.edge.list',
        'descr': 'List all edge verbs in the current view and their doc key (if set).',
        'storm': '''
            $edgelist = $lib.model.edge.list()
            if $edgelist {
                $lib.print('\nname       doc')
                $lib.print('----       ---')
                for ($verb, $kvdict) in $edgelist {
                    $verb = $verb.ljust(10)

                    $doc = $kvdict.doc
                    if ($doc=$lib.null) { $doc = '' }

                    $lib.print('{verb} {doc}', verb=$verb, doc=$doc)
                }
                $lib.print('')
            } else {
                $lib.print('No edge verbs found in the current view.')
            }
        ''',
    },
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
                        if $layr.getPropCount($name, maxsize=1) {
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
        return await self.runt.snap.core.delTagModel(tagname)

    @s_stormtypes.stormfunc(readonly=True)
    async def _getTagModel(self, tagname):
        tagname = await s_stormtypes.tostr(tagname)
        return await self.runt.snap.core.getTagModel(tagname)

    @s_stormtypes.stormfunc(readonly=True)
    async def _listTagModel(self):
        return await self.runt.snap.core.listTagModel()

    async def _popTagModel(self, tagname, propname):
        tagname = await s_stormtypes.tostr(tagname)
        propname = await s_stormtypes.tostr(propname)
        self.runt.confirm(('model', 'tag', 'set'))
        return await self.runt.snap.core.popTagModel(tagname, propname)

    async def _setTagModel(self, tagname, propname, propvalu):
        tagname = await s_stormtypes.tostr(tagname)
        propname = await s_stormtypes.tostr(propname)
        propvalu = await s_stormtypes.toprim(propvalu)
        self.runt.confirm(('model', 'tag', 'set'))
        await self.runt.snap.core.setTagModel(tagname, propname, propvalu)

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
                           'stortype': valu.stortype,
                           })

    def getObjLocals(self):
        return {
            'norm': self._methNorm,
            'repr': self._methRepr,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRepr(self, valu):
        nval = self.valu.norm(valu)
        return self.valu.repr(nval[0])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNorm(self, valu):
        return self.valu.norm(valu)

    def value(self):
        return self.valu.getTypeDef()

@s_stormtypes.registry.registerLib
class LibModelEdge(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with light edges and manipulating their key-value attributes.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the key-value data for a given Edge verb.',
         'type': {'type': 'function', '_funcname': '_methEdgeGet',
                  'args': (
                      {'name': 'verb', 'desc': 'The Edge verb to look up.', 'type': 'str', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary representing the key-value data set on a verb.', }}},
        {'name': 'validkeys', 'desc': 'Get a list of the valid keys that can be set on an Edge verb.',
         'type': {'type': 'function', '_funcname': '_methValidKeys',
                  'returns': {'type': 'list', 'desc': 'A list of the valid keys.', }
                  }
        },
        {'name': 'set', 'desc': 'Set a key-value for a given Edge verb.',
         'type': {'type': 'function', '_funcname': '_methEdgeSet',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'The Edge verb to set a value for.', },
                      {'name': 'key', 'type': 'str', 'desc': 'The key to set.', },
                      {'name': 'valu', 'type': 'str', 'desc': 'The value to set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'del', 'desc': 'Delete a key from the key-value store for a verb.',
         'type': {'type': 'function', '_funcname': '_methEdgeDel',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'The name of the Edge verb to remove a key from.', },
                      {'name': 'key', 'type': 'str', 'desc': 'The name of the key to remove from the key-value store.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of (verb, key-value dictionary) pairs for Edge verbs in the current Cortex View.',
         'type': {'type': 'function', '_funcname': '_methEdgeList',
                  'returns': {'type': 'list', 'desc': 'A list of (str, dict) tuples for each verb in the current Cortex View.', }}},
    )
    # Note: The use of extprops in hive paths in this class is an artifact of the
    # original implementation which used extended property language which had a
    # very bad cognitive overload with the cortex extended properties, but we
    # don't want to change underlying data. epiphyte 20200703

    # restrict list of keys which we allow to be set/del through this API.
    validedgekeys = (
        'doc',
    )
    hivepath = ('cortex', 'model', 'edges')

    _storm_lib_path = ('model', 'edge')

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'get': self._methEdgeGet,
            'set': self._methEdgeSet,
            'del': self._methEdgeDel,
            'list': self._methEdgeList,
            'validkeys': self._methValidKeys,
        }

    async def _chkEdgeVerbInView(self, verb):
        async for vverb in self.runt.snap.view.getEdgeVerbs():
            if vverb == verb:
                return

        raise s_exc.NoSuchName(mesg=f'No such edge verb in the current view', name=verb)

    async def _chkKeyName(self, key):
        if key not in self.validedgekeys:
            raise s_exc.NoSuchProp(mesg=f'The requested key is not valid for light edge metadata.',
                                   name=key)

    @s_stormtypes.stormfunc(readonly=True)
    def _methValidKeys(self):
        s_common.deprecated('model.edge.validkeys', curv='2.165.0')
        return self.validedgekeys

    @s_stormtypes.stormfunc(readonly=True)
    async def _methEdgeGet(self, verb):
        s_common.deprecated('model.edge.get', curv='2.165.0')
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        path = self.hivepath + (verb, 'extprops')
        return await self.runt.snap.core.getHiveKey(path) or {}

    async def _methEdgeSet(self, verb, key, valu):
        s_common.deprecated('model.edge.set', curv='2.165.0')
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        key = await s_stormtypes.tostr(key)
        await self._chkKeyName(key)

        valu = await s_stormtypes.tostr(valu)

        path = self.hivepath + (verb, 'extprops')
        kvdict = await self.runt.snap.core.getHiveKey(path) or {}

        kvdict[key] = valu
        await self.runt.snap.core.setHiveKey(path, kvdict)

    async def _methEdgeDel(self, verb, key):
        s_common.deprecated('model.edge.del', curv='2.165.0')
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        key = await s_stormtypes.tostr(key)
        await self._chkKeyName(key)

        path = self.hivepath + (verb, 'extprops')
        kvdict = await self.runt.snap.core.getHiveKey(path) or {}

        oldv = kvdict.pop(key, None)
        if oldv is None:
            raise s_exc.NoSuchProp(mesg=f'Key is not set for this edge verb',
                                   verb=verb, name=key)

        await self.runt.snap.core.setHiveKey(path, kvdict)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methEdgeList(self):
        s_common.deprecated('model.edge.list', curv='2.165.0')
        retn = []
        async for verb in self.runt.snap.view.getEdgeVerbs():
            path = self.hivepath + (verb, 'extprops')
            kvdict = await self.runt.snap.core.getHiveKey(path) or {}
            retn.append((verb, kvdict))

        return retn

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

        async for (verb, n2iden) in src.iterEdgesN1():

            if verb not in verbs:
                self.runt.layerConfirm(('node', 'edge', 'add', verb))
                verbs.add(verb)

            if await self.runt.snap.getNodeByBuid(s_common.uhex(n2iden)) is not None:
                await proto.addEdge(verb, n2iden)

        dstiden = proto.iden()

        async for (verb, n1iden) in src.iterEdgesN2():

            if verb not in verbs:
                self.runt.layerConfirm(('node', 'edge', 'add', verb))
                verbs.add(verb)

            n1proto = await editor.getNodeByBuid(s_common.uhex(n1iden))
            if n1proto is not None:
                await n1proto.addEdge(verb, dstiden)

    async def copyTags(self, src, proto, overwrite=False):

        for name, valu in src.tags.items():
            self.runt.layerConfirm(('node', 'tag', 'add', *name.split('.')))
            await proto.addTag(name, valu=valu)

        for tagname, tagprops in src.tagprops.items():
            for propname, valu in tagprops.items():
                if overwrite or not proto.hasTagProp(tagname, propname):
                    await proto.setTagProp(tagname, propname, valu) # use tag perms


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
    )
    _storm_lib_path = ('model', 'migration')

    def getObjLocals(self):
        return {
            'copyData': self._methCopyData,
            'copyEdges': self._methCopyEdges,
            'copyTags': self._methCopyTags,
        }

    async def _methCopyData(self, src, dst, overwrite=False):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyData() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyData() dest argument must be a node.')

        overwrite = await s_stormtypes.tobool(overwrite)

        async with self.runt.snap.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyData(src, proto, overwrite=overwrite)

    async def _methCopyEdges(self, src, dst):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyEdges() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyEdges() dest argument must be a node.')

        snap = self.runt.snap

        async with snap.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyEdges(editor, src, proto)

    async def _methCopyTags(self, src, dst, overwrite=False):

        if not isinstance(src, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyTags() source argument must be a node.')
        if not isinstance(dst, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.copyTags() dest argument must be a node.')

        overwrite = await s_stormtypes.tobool(overwrite)

        snap = self.runt.snap

        async with snap.getEditor() as editor:
            proto = editor.loadNode(dst)
            await self.copyTags(src, proto, overwrite=overwrite)

@s_stormtypes.registry.registerLib
class LibModelMigrations(s_stormtypes.Lib, MigrationEditorMixin):
    '''
    A Storm library for selectively migrating nodes in the current view.
    '''
    _storm_locals = (
        {'name': 'itSecCpe_2_170_0',
         'desc': '''
            Versions of Synapse prior to v2.169.0 did not correctly parse and
            convert CPE strings from 2.2 -> 2.3 or 2.3 -> 2.2. This migration
            attempts to re-normalize `it:sec:cpe` nodes that may be fixable.

            NOTE: It is highly recommended to test the `it:sec:cpe` migrations
            in a fork first and confirm the migration was successful without any
            issues. Then run the migration in view deporder to migrate the
            entire cortex. E.g.::

                for $view in $lib.view.list(deporder=$lib.true) {
                    view.exec $view.iden {
                        for $n in $lib.layer.get().liftByProp(it:sec:cpe) {
                            $lib.model.migration.s.itSecCpe_2_170_0($n)
                        }
                    }
                }

            Upon completion of the migration, nodedata will contain a
            `migration.s.itSecCpe_2_170_0` dict with information about the
            migration status. This dict may contain the following:

                - `status`: (required str) "success" or "failed"
                - `reason`: (optional str) if "status" is "failed", this key will
                  explain why the migration failed.
                - `valu`: (optional str) if this key is present, it will contain
                  an updated CPE2.3 string since the primary property cannot be
                  changed.
                - `updated`: (optional list[str]) A list of properties that were
                  updated by the migration.

            Failed or incorrect migrations may be helped by updating the :v2_2
            property to be a valid CPE2.2 string and then re-running the
            migration with `force=$lib.true`. If the primary property (CPE2.3)
            is valid but incorrect, users may update the :v2_2 property and then
            run the migration with `prefer_v22=$lib.true` to make the migration
            use the `:v2_2` string instead of the primary property for the
            migration process.
         ''',
         'type': {'type': 'function', '_funcname': '_itSecCpe_2_170_0',
                  'args': (
                      {'name': 'n', 'type': 'node', 'desc': 'The it:sec:cpe node to migrate.'},
                      {'name': 'prefer_v22', 'type': 'bool', 'default': False,
                       'desc': '''
                        Try to renormalize using the :v2_2 prop instead of the
                        primary property. This can be especially useful when the
                        primary property is a valid but incorrect CPE string.
                        '''},
                      {'name': 'force', 'type': 'bool', 'default': False,
                       'desc': 'Perform fixups even if the primary property and :v2_2 are valid.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'Boolean indicating if the migration was successful.'}}},
        {'name': 'riskHasVulnToVulnerable', 'desc': '''
            Create a risk:vulnerable node from the provided risk:hasvuln node.

            Edits will be made to the risk:vulnerable node in the current write layer.

            If multiple vulnerable properties are set on the risk:hasvuln node
            multiple risk:vulnerable nodes will be created (each with a unique guid).
            Otherwise, a single risk:vulnerable node will be created with the same guid
            as the provided risk:hasvuln node. Extended properties will not be migrated.

            Tags, tag properties, edges, and node data will be copied
            to the risk:vulnerable node. However, existing tag properties and
            node data will not be overwritten.
        ''',
        'type': {'type': 'function', '_funcname': '_riskHasVulnToVulnerable',
                 'args': (
                      {'name': 'n', 'type': 'node', 'desc': 'The risk:hasvuln node to migrate.'},
                      {'name': 'nodata', 'type': 'bool', 'default': False,
                       'desc': 'Do not copy nodedata to the risk:vulnerable node.'},
                 ),
                 'returns': {'type': 'list', 'desc': 'A list of idens for the risk:vulnerable nodes.'}}},
    )
    _storm_lib_path = ('model', 'migration', 's')

    def getObjLocals(self):
        return {
            'itSecCpe_2_170_0': self._itSecCpe_2_170_0,
            'riskHasVulnToVulnerable': self._riskHasVulnToVulnerable,
        }

    async def _itSecCpe_2_170_0(self, n, prefer_v22=False, force=False):

        if not isinstance(n, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.s.itSecCpe_2_170_0() argument must be a node.')

        if n.form.name != 'it:sec:cpe':
            raise s_exc.BadArg(f'itSecCpeFix only accepts it:sec:cpe nodes, not {n.form.name}')

        prefer_v22 = await s_stormtypes.tobool(prefer_v22)
        force = await s_stormtypes.tobool(force)

        layr = self.runt.snap.wlyr
        # We only need to check :v2_2 since that's the only property that's
        # writable. Everthing else is readonly. And we can do it here once
        # instead of in the loop below which will cause a perf hit.
        self.runt.confirmPropSet(n.form.prop('v2_2'), layriden=layr.iden)

        curv = n.repr()
        reprvalu = f'it:sec:cpe={curv}'

        nodedata = await n.getData('migration.s.itSecCpe_2_170_0', {})
        if nodedata.get('status') == 'success' and not force:
            if self.runt.debug:
                mesg = f'DEBUG: itSecCpe_2_170_0({reprvalu}): Node already migrated.'
                await self.runt.printf(mesg)
            return True

        modl = self.runt.model.type('it:sec:cpe')

        valu23 = None
        valu22 = None
        invalid = ''

        # Check the primary property for validity.
        cpe23 = s_infotech.cpe23_regex.match(curv)
        if cpe23 is not None and cpe23.group() == curv:
            valu23 = curv

        # Check the v2_2 property for validity.
        v2_2 = n.props.get('v2_2')
        if v2_2 is not None:
            rgx = s_infotech.cpe22_regex.match(v2_2)
            if rgx is not None and rgx.group() == v2_2:
                valu22 = v2_2

        async with self.runt.snap.getNodeEditor(n) as proto:

            # If both values are populated, this node is valid
            if valu23 is not None and valu22 is not None and not force:
                if self.runt.debug:
                    mesg = f'DEBUG: itSecCpe_2_170_0({reprvalu}): Node is valid, no migration necessary.'
                    await self.runt.printf(mesg)

                await proto.setData('migration.s.itSecCpe_2_170_0', {
                    'status': 'success',
                })

                return True

            if valu23 is None and valu22 is None:
                reason = 'Unable to migrate due to invalid data. Primary property and :v2_2 are both invalid.'
                # Invalid 2.3 string and no/invalid v2_2 prop. Nothing
                # we can do here so log, mark, and go around.
                mesg = f'itSecCpe_2_170_0({reprvalu}): {reason}'
                await self.runt.warn(mesg)

                await proto.setData('migration.s.itSecCpe_2_170_0', {
                    'status': 'failed',
                    'reason': reason,
                })

                return False

            if prefer_v22:
                valu = valu22 or valu23
            else:
                valu = valu23 or valu22

            # Re-normalize the data from the 2.3 or 2.2 string, whichever was valid.
            norm, info = modl.norm(valu)
            subs = info.get('subs')

            edits = []
            nodedata = {'status': 'success'}

            if norm != curv:
                # The re-normed value is not the same as the current value.
                # Since we can't change the primary property, store the
                # updated value in nodedata.
                if self.runt.debug:
                    mesg = f'DEBUG: itSecCpe_2_170_0({reprvalu}): Stored updated primary property value to nodedata: {curv} -> {norm}.'
                    await self.runt.printf(mesg)

                nodedata['valu'] = norm

            # Iterate over the existing properties
            for propname, propcurv in n.props.items():
                subscurv = subs.get(propname)
                if subscurv is None:
                    continue

                if propname == 'v2_2' and isinstance(subscurv, list):
                    subscurv = s_infotech.zipCpe22(subscurv)

                # Values are the same, go around
                if propcurv == subscurv:
                    continue

                nodedata.setdefault('updated', [])
                nodedata['updated'].append(propname)

                # Update the existing property with the re-normalized property value.
                await proto.set(propname, subscurv, ignore_ro=True)

            await proto.setData('migration.s.itSecCpe_2_170_0', nodedata)

            if self.runt.debug:
                if nodedata.get('updated'):
                    mesg = f'DEBUG: itSecCpe_2_170_0({reprvalu}): Updated properties: {", ".join(nodedata["updated"])}.'
                    await self.runt.printf(mesg)
                else:
                    mesg = f'DEBUG: itSecCpe_2_170_0({reprvalu}): No property updates required.'
                    await self.runt.printf(mesg)

            return True

    async def _riskHasVulnToVulnerable(self, n, nodata=False):

        nodata = await s_stormtypes.tobool(nodata)

        if not isinstance(n, s_node.Node):
            raise s_exc.BadArg(mesg='$lib.model.migration.s.riskHasVulnToVulnerable() argument must be a node.')

        if n.form.name != 'risk:hasvuln':
            mesg = f'$lib.model.migration.s.riskHasVulnToVulnerable() only accepts risk:hasvuln nodes, not {n.form.name}'
            raise s_exc.BadArg(mesg=mesg)

        retidens = []

        if not (vuln := n.get('vuln')):
            return retidens

        props = {
            'vuln': vuln,
        }

        links = {prop: valu for prop in RISK_HASVULN_VULNPROPS if (valu := n.get(prop)) is not None}

        match len(links):
            case 0:
                return retidens
            case 1:
                guid = n.ndef[1]
            case _:
                guid = None

        riskvuln = self.runt.model.form('risk:vulnerable')

        self.runt.layerConfirm(riskvuln.addperm)
        self.runt.confirmPropSet(riskvuln.props['vuln'])
        self.runt.confirmPropSet(riskvuln.props['node'])

        if (seen := n.get('.seen')):
            self.runt.confirmPropSet(riskvuln.props['.seen'])
            props['.seen'] = seen

        async with self.runt.snap.getEditor() as editor:

            for prop, valu in links.items():

                pguid = guid if guid is not None else s_common.guid((guid, prop))
                pprops = props | {'node': (n.form.props[prop].type.name, valu)}

                proto = await editor.addNode('risk:vulnerable', pguid, props=pprops)
                retidens.append(proto.iden())

                await self.copyTags(n, proto, overwrite=False)
                await self.copyEdges(editor, n, proto)

                if not nodata:
                    await self.copyData(n, proto, overwrite=False)

        return retidens
