import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.stormtypes as s_stormtypes

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

    async def _getTagModel(self, tagname):
        tagname = await s_stormtypes.tostr(tagname)
        return await self.runt.snap.core.getTagModel(tagname)

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
                  'returns': {'type': ['storm:model:type', 'null'],
                              'desc': 'The ``storm:model:type`` instance if the type if present on the form or null.',
                              }}},
        {'name': 'prop', 'desc': 'Get a prop object by name.',
         'type': {'type': 'function', '_funcname': '_methProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the prop to retrieve.', },
                  ),
                  'returns': {'type': ['storm:model:property', 'null'],
                              'desc': 'The ``storm:model:property`` instance if the type if present or null.',
                              }}},
        {'name': 'form', 'desc': 'Get a form object by name.',
         'type': {'type': 'function', '_funcname': '_methForm',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the form to retrieve.', },
                  ),
                  'returns': {'type': ['storm:model:form', 'null'],
                              'desc': 'The ``storm:model:form`` instance if the form is present or null.',
                              }}},
        {'name': 'tagprop', 'desc': 'Get a tag property object by name.',
         'type': {'type': 'function', '_funcname': '_methTagProp',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the tag prop to retrieve.', },
                  ),
                  'returns': {'type': ['storm:model:tagprop', 'null'],
                              'desc': 'The ``storm:model:tagprop`` instance if the tag prop if present or null.',
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
    async def _methType(self, name):
        type_ = self.model.type(name)
        if type_ is not None:
            return ModelType(type_)

    @s_cache.memoizemethod(size=100)
    async def _methProp(self, name):
        prop = self.model.prop(name)
        if prop is not None:
            return ModelProp(prop)

    @s_cache.memoizemethod(size=100)
    async def _methForm(self, name):
        form = self.model.form(name)
        if form is not None:
            return ModelForm(form)

    @s_cache.memoize(size=100)
    async def _methTagProp(self, name):
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
                  'returns': {'type': ['storm:model:property', 'null'],
                              'desc': 'The ``storm:model:property`` instance if the property if present on the form or null.'
                              }}},
        {'name': 'type', 'desc': 'Get the Type for the form.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorFormType',
                  'returns': {'type': 'storm:model:type'}}},
    )
    _storm_typename = 'storm:model:form'
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

    def _getFormProp(self, name):
        prop = self.valu.prop(name)
        if prop is not None:
            return ModelProp(prop)

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
                  'returns': {'type': ['storm:model:form', 'null']}}},
        {'name': 'type', 'desc': 'Get the Type for the Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorPropType',
                  'returns': {'type': 'storm:model:type'}}},
    )
    _storm_typename = 'storm:model:property'
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

@s_stormtypes.registry.registerType
class ModelTagProp(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Tag Property.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Tag Property.', 'type': 'str', },
        {'name': 'type', 'desc': 'Get the Type for the Tag Property.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorTagPropType',
                  'returns': {'type': 'storm:model:type'}}},
    )
    _storm_typename = 'storm:model:tagprop'
    def __init__(self, tagprop, path=None):

        s_stormtypes.Prim.__init__(self, tagprop, path=path)

        self.ctors.update({
            'type': self._ctorTagPropType,
        })

        self.locls['name'] = self.valu.name

    def _ctorTagPropType(self, path=None):
        return ModelType(self.valu.type, path=path)

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
    _storm_typename = 'storm:model:type'

    def __init__(self, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())
        self.locls.update({'name': valu.name,
                           'norm': self._methNorm,
                           'repr': self._methRepr,
                           'stortype': valu.stortype,
                           })

    async def _methRepr(self, valu):
        nval = self.valu.norm(valu)
        return self.valu.repr(nval[0])

    async def _methNorm(self, valu):
        return self.valu.norm(valu)

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
    # dont' want to change underlying data. epiphyte 20200703

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

    def _methValidKeys(self):
        return self.validedgekeys

    async def _methEdgeGet(self, verb):
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        path = self.hivepath + (verb, 'extprops')
        return await self.runt.snap.core.getHiveKey(path) or {}

    async def _methEdgeSet(self, verb, key, valu):
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

    async def _methEdgeList(self):
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
