import synapse.exc as s_exc

import synapse.lib.cache as s_cache
import synapse.lib.stormtypes as s_stormtypes

stormcmds = [
    {
        'name': 'model.edge.set',
        'descr': 'Set a global extended property for an edge verb that exists in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to add an extended property to.'}),
            ('prop', {'help': 'The extended property name (e.g. doc).'}),
            ('valu', {'help': 'The extended property string value to set.'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $prop = $cmdopts.prop
            $lib.model.edge.set($verb, $prop, $cmdopts.valu)
            $lib.print('Set edge extended prop: verb={verb} prop={prop}', verb=$verb, prop=$prop)
        ''',
    },
    {
        'name': 'model.edge.get',
        'descr': 'Retrieve global extended properties for an edge verb in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to retrieve.'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $props = $lib.model.edge.get($verb)
            $doc = $props.doc
            if ($doc=$lib.null) { $doc = '' }
            $lib.print('\nverb={verb}\ndoc="{doc}"\n', verb=$verb, doc=$doc)
        ''',
    },
    {
        'name': 'model.edge.del',
        'descr': 'Delete a global extended property for an edge verb in the current view.',
        'cmdargs': (
            ('verb', {'help': 'The edge verb to delete documentation for.'}),
            ('prop', {'help': 'The extended property name (e.g. doc).'}),
        ),
        'storm': '''
            $verb = $cmdopts.verb
            $prop = $cmdopts.prop
            $lib.model.edge.del($verb, $prop)
            $lib.print('Deleted edge extended property: verb={verb} prop={prop}', verb=$verb, prop=$prop)
        ''',
    },
    {
        'name': 'model.edge.list',
        'descr': 'List all edge verbs in the current view and their extended properties.',
        'storm': '''
            $edgelist = $lib.model.edge.list()
            if $edgelist {
                $lib.print('\nname       doc')
                $lib.print('----       ---')
                for ($verb, $props) in $edgelist {
                    $verb = $verb.ljust(10)

                    $doc = $props.doc
                    if ($doc=$lib.null) { $doc = '' }

                    $lib.print('{verb} {doc}', verb=$verb, doc=$doc)
                }
                $lib.print('')
            } else {
                $lib.print('No edge verbs found in the current view.')
            }
        ''',
    },
]

class LibModel(s_stormtypes.Lib):
    '''
    A collection of method around the data model
    '''
    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)
        self.model = runt.model

    def addLibFuncs(self):
        self.locls.update({
            'type': self._methType,
            'prop': self._methProp,
            'form': self._methForm,
            'edge': ModelEdge(self.runt),
        })

    @s_cache.memoize(size=100)
    async def _methType(self, name):
        type_ = self.model.type(name)
        if type_ is not None:
            return ModelType(type_)

    @s_cache.memoize(size=100)
    async def _methProp(self, name):
        prop = self.model.prop(name)
        if prop is not None:
            return ModelProp(prop)

    @s_cache.memoize(size=100)
    async def _methForm(self, name):
        form = self.model.form(name)
        if form is not None:
            return ModelForm(form)

class ModelForm(s_stormtypes.Prim):

    def __init__(self, form, path=None):

        s_stormtypes.Prim.__init__(self, form, path=path)

        self.locls.update({
            'name': form.name,
            'prop': self._getFormProp,
        })

        self.ctors.update({
            'type': self._ctorFormType,
        })

    def _ctorFormType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _getFormProp(self, name):
        prop = self.valu.prop(name)
        if prop is not None:
            return ModelProp(prop)

class ModelProp(s_stormtypes.Prim):

    def __init__(self, prop, path=None):

        s_stormtypes.Prim.__init__(self, prop, path=path)

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

class ModelType(s_stormtypes.Prim):
    '''
    A Storm types wrapper around a lib.types.Type
    '''
    def __init__(self, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.locls.update({
            'name': valu.name,
            'repr': self._methRepr,
            'norm': self._methNorm,
        })

    async def _methRepr(self, valu):
        nval = self.valu.norm(valu)
        return self.valu.repr(nval[0])

    async def _methNorm(self, valu):
        return self.valu.norm(valu)

class ModelEdge(s_stormtypes.Prim):
    '''
    Inspect edges and manipulate extended attributes
    '''

    def __init__(self, runt):

        s_stormtypes.Prim.__init__(self, None)

        self.runt = runt

        self.hivepath = ('cortex', 'model', 'edges')

        # restrict list of extended props that can be set
        self.extpropnames = (
            'doc',
        )

        self.locls.update({
            'get': self._methEdgeGet,
            'set': self._methEdgeSet,
            'del': self._methEdgeDel,
            'list': self._methEdgeList,
        })

    async def _chkEdgeVerbInView(self, verb):
        async for vverb in self.runt.snap.view.getEdgeVerbs():
            if vverb == verb:
                return

        raise s_exc.NoSuchName(mesg=f'No such edge verb in the current view', name=verb)

    async def _chkExtPropName(self, prop):
        if prop not in self.extpropnames:
            raise s_exc.NoSuchProp(mesg=f'No such edge extended property name', name=prop)

    async def _methEdgeGet(self, verb):
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        path = self.hivepath + (verb, 'extprops')
        return await self.runt.snap.core.getHiveKey(path) or {}

    async def _methEdgeSet(self, verb, prop, valu):
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        prop = await s_stormtypes.tostr(prop)
        await self._chkExtPropName(prop)

        valu = await s_stormtypes.tostr(valu)

        path = self.hivepath + (verb, 'extprops')
        extprops = await self.runt.snap.core.getHiveKey(path) or {}

        extprops[prop] = valu
        await self.runt.snap.core.setHiveKey(path, extprops)

    async def _methEdgeDel(self, verb, prop):
        verb = await s_stormtypes.tostr(verb)
        await self._chkEdgeVerbInView(verb)

        prop = await s_stormtypes.tostr(prop)
        await self._chkExtPropName(prop)

        path = self.hivepath + (verb, 'extprops')
        extprops = await self.runt.snap.core.getHiveKey(path) or {}

        oldv = extprops.pop(prop, None)
        if not oldv:
            raise s_exc.NoSuchProp(mesg=f'Extended property does not exist for this edge verb', name=prop)

        await self.runt.snap.core.setHiveKey(path, extprops)

    async def _methEdgeList(self):
        retn = []
        async for verb in self.runt.snap.view.getEdgeVerbs():
            path = self.hivepath + (verb, 'extprops')
            extprops = await self.runt.snap.core.getHiveKey(path) or {}
            retn.append((verb, extprops))

        return retn
