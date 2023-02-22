import synapse.exc as s_exc

import synapse.lib.cell as s_cell
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormtypes as s_stormtypes

gdefSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string', 'minLength': 1},
        'desc': {'type': 'string', 'default': ''},
        'scope': {'type': 'string', 'enum': ['user', 'power-up']},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'power-up': {'type': 'string', 'minLength': 1},
        'created': {'type': 'number'},
        'updated': {'type': 'number'},
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
        },
        'permissions': s_msgpack.deepcopy(s_cell.easyPermSchema)
    },
    'additionalProperties': False,
    'required': ['iden', 'name', 'scope'],
    'allOf': [
        {
            'if': {'properties': {'scope': {'const': 'power-up'}}},
            'then': {'required': ['power-up']},
            'else': {'required': ['creator']},
        }
    ]
}

reqValidGdef = s_config.getJsValidator(gdefSchema)

USER_EDITABLE = {
    'desc',
    'name',
    'refs',
    'edges',
    'forms',
    'pivots',
    'degrees',
    'filters',
    'filterinput',
    'yieldfiltered'
}

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
                        "name": "Test Projection",
                        "desc": "My test projection",
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
                      {'name': 'gdef', 'type': 'dict', 'desc': 'A graph projection definition.'},
                  ),
                  'returns': {'type': 'null'}}},

        {'name': 'del', 'desc': 'Delete a graph projection from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the graph projection to delete.'},
                  ),
                  'returns': {'type': 'null'}}},

        {'name': 'get', 'desc': 'Get a graph projection definition from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The iden of the graph projection to get. If not specified, '
                               'returns the current graph projection.'},
                  ),
                  'returns': {'type': 'dict',
                              'desc': 'A graph projection definition, or None if no iden was '
                                      'specified and there is currently no graph projection set.'}}},

        {'name': 'mod', 'desc': 'Modify user editable properties of a graph projection.',
         'type': {'type': 'function', '_funcname': '_methGraphMod',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the graph projection to modify.'},
                      {'name': 'info', 'type': 'dict', 'desc': 'A dictionary of the properties to edit.'},
                  ),
                  'returns': {'type': 'null'}}},

        {'name': 'list', 'desc': 'List the graph projections available in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGraphList',
                  'returns': {'type': 'list', 'desc': 'A list of graph projection definitions.'}}},

        {'name': 'grant', 'desc': 'Modify permissions granted to users/roles on a graph projection.',
         'type': {'type': 'function', '_funcname': '_methGraphGrant',
                  'args': (
                      {'name': 'gden', 'type': 'str', 'desc': 'Iden of the graph projection to modify.', },
                      {'name': 'scope', 'type': 'str', 'desc': 'The scope, either "users" or "roles".', },
                      {'name': 'iden', 'type': 'str', 'desc': 'The user/role iden depending on scope.', },
                      {'name': 'level', 'type': 'int', 'desc': 'The permission level number.', },
                  ),
                  'returns': {'type': 'null', }}},

        {'name': 'activate', 'desc': 'Set the graph projection to use for the top level Storm Runtime.',
         'type': {'type': 'function', '_funcname': '_methGraphActivate',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': 'The iden of the graph projection to use.'},
                  ),
                  'returns': {'type': 'null'}}},
    )

    def getObjLocals(self):
        return {
            'add': self._methGraphAdd,
            'del': self._methGraphDel,
            'get': self._methGraphGet,
            'mod': self._methGraphMod,
            'list': self._methGraphList,
            'grant': self._methGraphGrant,
            'activate': self._methGraphActivate,
        }

    async def _methGraphAdd(self, gdef):
        gdef = await s_stormtypes.toprim(gdef)
        return await self.runt.snap.core.addStormGraph(gdef, user=self.runt.user)

    async def _methGraphGet(self, iden=None):
        iden = await s_stormtypes.tostr(iden, noneok=True)
        if iden is None:
            return self.runt.getGraph()

        return await self.runt.snap.core.getStormGraph(iden, user=self.runt.user)

    async def _methGraphDel(self, iden):
        iden = await s_stormtypes.tostr(iden)
        await self.runt.snap.core.delStormGraph(iden, user=self.runt.user)

    async def _methGraphMod(self, iden, info):
        iden = await s_stormtypes.tostr(iden)
        info = await s_stormtypes.toprim(info)

        for prop in info.keys():
            if prop not in USER_EDITABLE:
                raise s_exc.BadArg(mesg=f'User may not edit the field: {prop}.')

        await self.runt.snap.core.modStormGraph(iden, info, user=self.runt.user)

    async def _methGraphList(self):
        projs = []
        async for proj in self.runt.snap.core.getStormGraphs(user=self.runt.user):
            projs.append(proj)

        return list(sorted(projs, key=lambda x: x.get('name')))

    async def _methGraphGrant(self, gden, scope, iden, level):
        gden = await s_stormtypes.tostr(gden)
        scope = await s_stormtypes.tostr(scope)
        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level, noneok=True)

        await self.runt.snap.core.setStormGraphPerm(gden, scope, iden, level, user=self.runt.user)

    async def _methGraphActivate(self, iden):
        gdef = await self._methGraphGet(iden)
        self.runt.setGraph(gdef)
