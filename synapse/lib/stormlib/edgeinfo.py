import datetime

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

edge_set_desc = '''
Set a documentation string for an edge that has been added to the graph.

Example:
    edge.set seen "description for the seen edge verb"
'''

edge_get_desc = '''
Get the documentation string for an edge verb.
'''

edge_del_desc = '''
Delete the documentation entry for a given edge verb.

Note: If the edge is re-added to the graph the entry will re-populate.
'''

edge_list_desc = '''
List all edges that have been added to the graph with their associated documentation.
'''

stormcmds = [
    {
        'name': 'edge.set',
        'descr': edge_set_desc,
        'cmdargs': (
            ('name', {'help': 'The name of the edge verb.'}),
            ('info', {'help': 'The documentation string.'}),
        ),
        'storm': '''
            $lib.edge.set($cmdopts.name, $cmdopts.info)
            $lib.print('Set edge info: {name}', name=$cmdopts.name)
        ''',
    },
    {
        'name': 'edge.get',
        'descr': edge_get_desc,
        'cmdargs': (
            ('name', {'help': 'The name of the edge verb.'}),
        ),
        'storm': '''
            $edef = $lib.edge.get($cmdopts.name)
            if $edef {
                $lib.print('{name}: {info}', name=$cmdopts.name, info=$edef)
            } else {
                $lib.print('Edge entry not found: {name}', name=$cmdopts.name)
            }
        ''',
    },
    {
        'name': 'edge.del',
        'descr': edge_del_desc,
        'cmdargs': (
            ('name', {'help': 'The name of the edge verb.'}),
        ),
        'storm': '''
            $lib.edge.del($cmdopts.name)
            $lib.print('Deleted edge entry: {name}', name=$cmdopts.name)
        ''',
    },
    {
        'name': 'edge.list',
        'descr': edge_list_desc,
        'storm': '''
            $elist = $lib.edge.list()
            if $elist {
                $lib.print('name       edited               info')
                for ($name, $edef) in $elist {
                    $name = $name.ljust(10)
                    $edited = $edef.edited.ljust(20)
                    $lib.print('{name} {edited} {info}', name=$name, edited=$edited, info=$edef.info)
                }
            } else {
                $lib.print('No edge entries found')
            }
        ''',
    },
]

class LibEdge(s_stormtypes.Lib):

    def addLibFuncs(self):
        self.locls.update({
            'set': self._methEdgeSet,
            'get': self._methEdgeGet,
            'del': self._methEdgeDel,
            'list': self._methEdgeList,
        })

    async def _methEdgeSet(self, name, info):
        '''
        Only allow setting info on edges that have been added to the graph
        '''
        name = await s_stormtypes.tostr(name)
        info = await s_stormtypes.tostr(info)

        path = ('cortex', 'storm', 'edges', name)

        edef = await self.runt.snap.core.getHiveKey(path)
        if edef is None:
            raise s_exc.NoSuchName(f'Edge entry not found: {name}')

        edef = {
            'info': info,
            'edited': s_common.now(),
        }

        await self.runt.snap.core.setHiveKey(path, edef)

    async def _methEdgeGet(self, name):
        name = await s_stormtypes.tostr(name)

        path = ('cortex', 'storm', 'edges', name)

        return await self.runt.snap.core.getHiveKey(path)

    async def _methEdgeDel(self, name):
        name = await s_stormtypes.tostr(name)

        path = ('cortex', 'storm', 'edges', name)

        edef = await self.runt.snap.core.getHiveKey(path)
        if edef is None:
            raise s_exc.NoSuchName(f'Edge info name not found: {name}')

        await self.runt.snap.core.popHiveKey(path)

    async def _methEdgeList(self):
        path = ('cortex', 'storm', 'edges')

        retn = []
        for name, edef in await self.runt.snap.core.getHiveKeys(path):
            retn.append((name, {
                'info': edef['info'],
                'edited': datetime.datetime.fromtimestamp(edef['edited'] // 1000).isoformat(),
            }))

        return retn
