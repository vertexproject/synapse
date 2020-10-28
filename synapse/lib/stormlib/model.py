import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.stormtypes as s_stormtypes

stormcmds = [
    {
        'name': 'model.edge.set',
        'descr': 'Set an key-value for an edge verb that exists in the current view.',
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
        'descr': 'Retrieve key-value pairs an edge verb in the current view.',
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
        'descr': 'Check for lock status and the existance of deprecated model elements',
        'storm': '''
            init {

                $ok = $lib.true
                $lib.print("Checking the cortex for 3.0.0 upgrade readiness...")

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

                $lib.print("Checking for existance of deprecated model elements:")
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
class LibModel(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Data Model in the Cortex.
    '''
    _storm_lib_path = ('model',)

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)
        self.model = runt.model

    def getObjLocals(self):
        return {
            'type': self._methType,
            'prop': self._methProp,
            'form': self._methForm,
        }

    @s_cache.memoize(size=100)
    async def _methType(self, name):
        '''
        Get a ModelType by name.

        Args:
            name (str): The name of the type to retrieve.

        Returns:
            ModelType: A Storm ModelType object.
        '''
        type_ = self.model.type(name)
        if type_ is not None:
            return ModelType(type_)

    @s_cache.memoize(size=100)
    async def _methProp(self, name):
        '''
        Get a ModelProp by name.

        Args:
            name (str): The name of the prop to retrieve.

        Returns:
            ModelProp: A Storm ModelProp object.
        '''
        prop = self.model.prop(name)
        if prop is not None:
            return ModelProp(prop)

    @s_cache.memoize(size=100)
    async def _methForm(self, name):
        '''
        Get a ModelForm by name.

        Args:
            name (str): The name of the form to retrieve.

        Returns:
            ModelForm: A Storm ModelForm object.
        '''
        form = self.model.form(name)
        if form is not None:
            return ModelForm(form)

@s_stormtypes.registry.registerType
class ModelForm(s_stormtypes.Prim):

    def __init__(self, form, path=None):

        s_stormtypes.Prim.__init__(self, form, path=path)

        self.locls.update({
            'name': form.name,
        })
        self.locls.update(self.getObjLocals())

        self.ctors.update({
            'type': self._ctorFormType,
        })

    def getObjLocals(self):
        return {
            'prop': self._getFormProp
        }

    def _ctorFormType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _getFormProp(self, name):
        prop = self.valu.prop(name)
        if prop is not None:
            return ModelProp(prop)

@s_stormtypes.registry.registerType
class ModelProp(s_stormtypes.Prim):

    def __init__(self, prop, path=None):

        s_stormtypes.Prim.__init__(self, prop, path=path)

        # Todo: Plumb name and full access via a @property and implement getObjLocals
        self.locls.update({
            'name': prop.name,
            'full': prop.full,
        })

        self.ctors.update({
            'form': self._ctorPropForm,
            'type': self._ctorPropType,
        })

    def _ctorPropType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _ctorPropForm(self, path=None):
        return ModelForm(self.valu.form, path=path)

@s_stormtypes.registry.registerType
class ModelType(s_stormtypes.Prim):
    '''
    A Storm types wrapper around a lib.types.Type
    '''
    def __init__(self, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.locls.update({
            'name': valu.name,
        })
        self.locls.update(self.getObjLocals())

    # Todo: Plumb name access via a @property
    def getObjLocals(self):
        return {
            'repr': self._methRepr,
            'norm': self._methNorm,
        }

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
        '''
        Get a list of the valid keys that can be set on an Edge verb.

        Returns:
            list: A list of the valid keys.
        '''
        return self.validedgekeys

    async def _methEdgeGet(self, verb):
        '''
        Get the key-value data for a given Edge verb.

        Args:
            verb (str): The Edge verb to look up.

        Returns:
            dict: A dictionary representing the key-value data set on a verb.
        '''
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        path = self.hivepath + (verb, 'extprops')
        return await self.runt.snap.core.getHiveKey(path) or {}

    async def _methEdgeSet(self, verb, key, valu):
        '''
        Set a key-value for a given Edge verb.

        Args:
            verb (str): The Edge verb to set a value for.

            key (str): The key to set.

            valu (str): The value to set.

        Returns:
            None: Returns None.
        '''
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
        '''
        Delete a key from the key-value store for a verb.

        Args:
            verb (str): The name of the Edge verb to remove a key from.

            key (str): The name of the key to remove from the key-value store.

        Returns:
            None: Returns None.
        '''
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
        '''
        Get a list of (verb, key-value dictionary) pairs for Edge verbs in the current Cortex View.

        Returns:
            list: A list of (str, dict) tuples for each verb in the current Cortex View.
        '''
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
