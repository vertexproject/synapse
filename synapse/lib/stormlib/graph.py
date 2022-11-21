import synapse.exc as s_exc
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

gdefSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string', 'minLength': 1},
        'scope': {'type': 'string', 'enum': ['user', 'global', 'power-up']},
        'creatoriden': {'type': 'string', 'pattern': s_config.re_iden},
        'creatorname': {'type': 'string', 'minLength': 1},
        'refs': {'type': 'boolean', 'default': False},
        'edges': {'type': 'boolean', 'default': True},
        'degrees': {'type': ['integer', 'null'], 'minimum': 0},
        'filterinput': {'type': 'boolean', 'default': True},
        'yieldfiltered': {'type': 'boolean', 'default': False},
        'filters': {
            'type': ['array', 'null'],
            'items': {'type': 'string'}
        },
        'pivots': {
            'type': ['array', 'null'],
            'items': {'type': 'string'}
        },
        'forms': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'filters': {
                            'type': ['array', 'null'],
                            'items': {'type': 'string'}
                        },
                        'pivots': {
                            'type': ['array', 'null'],
                            'items': {'type': 'string'}
                        }
                    },
                    'additionalProperties': False,
                }
            }
        }
    },
    'additionalProperties': False,
    'required': ['iden', 'name', 'scope'],
    'allOf': [
        {
            'if': {'properties': {'scope': {'const': 'power-up'}}},
            'then': {'required': ['creatorname']},
            'else': {'required': ['creatoriden']},
        }
    ]
}

reqValidGdef = s_config.getJsValidator(gdefSchema)

@s_stormtypes.registry.registerLib
class GraphLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with graph projections in the Cortex.
    '''
    _storm_lib_path = ('graph',)
    _storm_locals = (
        {'name': 'add',
         'desc': '''
            Add a graph projection to the Cortex.

            Example:
                    $rules = ({
                        "name": "My test projection",
                        "degrees": 2,
                        "pivots": ["<- meta:seen <- meta:source"],
                        "filters": ["-#nope"],
                        "forms": {
                            "inet:fqdn": {
                                "pivots": ["<- *", "-> *"],
                                "filters": ["-inet:fqdn:issuffix=1"]
                            },
                            "*": {
                                "pivots": ["-> #"],
                            }
                        }
                    })
                    $lib.graph.add($rules)
         ''',
         'type': {'type': 'function', '_funcname': '_methGraphAdd',
                  'args': (
                      {'name': 'gdef', 'type': 'dict', 'desc': 'A graph projection definition.', },
                      {'name': 'public', 'type': 'bool', 'default': False,
                       'desc': 'Add the graph projection to the global namespace.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'del', 'desc': 'Delete a graph projection from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the graph projection to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a graph projection definition from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The iden of the graph projection to get. If not specified, returns the current graph projection.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The graph projection definition.', }}},
        {'name': 'list', 'desc': 'List the graph projections available in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphList',
                  'returns': {'type': 'list', 'desc': 'A list of graph projection definitions.', }}},
        {'name': 'activate', 'desc': 'Set the graph projection to use for the top level Storm Runtime.',
         'type': {'type': 'function', '_funcname': '_methGraphActivate',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': 'The iden of the graph projection to use.', },
                  ),
                  'returns': {'type': 'null'}}},
    )

    def getObjLocals(self):
        return {
            'add': self._methGraphAdd,
            'del': self._methGraphDel,
            'get': self._methGraphGet,
            'list': self._methGraphList,
            'activate': self._methGraphActivate,
        }

    async def _methGraphAdd(self, gdef, public=False):
        gdef = await s_stormtypes.toprim(gdef)
        public = await s_stormtypes.tobool(public)
        if public:
            self.runt.confirm(('graph', 'add'), None)
            gdef['scope'] = 'global'
        else:
            gdef['scope'] = 'user'

        gdef['creatoriden'] = self.runt.user.iden

        return await self.runt.snap.core.addStormGraph(gdef)

    async def _methGraphGet(self, iden=None):
        iden = await s_stormtypes.tostr(iden, noneok=True)
        if iden is None:
            return self.runt.getGraph()
        elif self.runt.isAdmin():
            gdef = await self.runt.snap.core.getStormGraph(iden)
        else:
            gdef = await self.runt.snap.core.getStormGraph(iden, useriden=self.runt.user.iden)

        if gdef is None:
            mesg = f'No graph projection exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)
        return gdef

    async def _methGraphDel(self, iden):
        iden = await s_stormtypes.tostr(iden)
        if self.runt.isAdmin():
            gdef = await self.runt.snap.core.getStormGraph(iden)
        else:
            gdef = await self.runt.snap.core.getStormGraph(iden, useriden=self.runt.user.iden)

        if gdef is None:
            mesg = f'No graph projection exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        scope = gdef['scope']
        if scope == 'global':
            if gdef['creatoriden'] != self.runt.user.iden:
                self.runt.confirm(('graph', 'del'), None)

        elif scope == 'power-up' and not self.runt.isAdmin():
            mesg = 'Deleting power-up graph projections requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        await self.runt.snap.core.delStormGraph(iden)

    async def _methGraphList(self):
        if self.runt.isAdmin():
            genr = self.runt.snap.core.getStormGraphs()
        else:
            genr = self.runt.snap.core.getStormGraphs(useriden=self.runt.user.iden)

        projs = []
        async for proj in genr:
            projs.append(proj)

        return list(sorted(projs, key=lambda x: x.get('name')))

    async def _methGraphActivate(self, iden):
        iden = await s_stormtypes.tostr(iden)
        if self.runt.isAdmin():
            gdef = await self.runt.snap.core.getStormGraph(iden)
        else:
            gdef = await self.runt.snap.core.getStormGraph(iden, useriden=self.runt.user.iden)

        if gdef is None:
            mesg = f'No graph projection exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        self.runt.setGraph(gdef)
