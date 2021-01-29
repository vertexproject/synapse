import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes

macro_set_descr = '''
Set a macro definition in the cortex.

Variables can also be used that are defined outside the definition.

Examples:
    macro.set foobar ${ [+#foo] }

    # Use variable from parent scope
    macro.set bam ${ [ inet:ipv4=$val ] }
    $val=1.2.3.4 macro.exec bam
'''

macro_del_descr = '''
Remove a macro definition from the cortex.
'''

macro_get_descr = '''
Display the storm query for a macro in the cortex.
'''

macro_list_descr = '''
List the macros set on the cortex.
'''

stormcmds = [
    {
        'name': 'macro.del',
        'descr': macro_del_descr,
        'cmdargs': (
            ('name', {'help': 'The name of the macro to delete.'}),
        ),
        'storm': '''
            $lib.macro.del($cmdopts.name)
            $lib.print('Removed macro: {name}', name=$cmdopts.name)
        ''',
    },
    {
        'name': 'macro.set',
        'descr': macro_set_descr,
        'cmdargs': (
            ('name', {'help': 'The name of the macro to set.'}),
            ('storm', {'help': 'The storm command string or embedded query to set.'}),
        ),
        'storm': '''
            $lib.macro.set($cmdopts.name, $cmdopts.storm)
            $lib.print('Set macro: {name}', name=$cmdopts.name)
        ''',
    },
    {
        'name': 'macro.get',
        'descr': macro_get_descr,
        'cmdargs': (
            ('name', {'help': 'The name of the macro to display.'}),
        ),
        'storm': '''
            $mdef = $lib.macro.get($cmdopts.name)
            if $mdef {
                $lib.print($mdef.storm)
            } else {
                $lib.print('Macro not found: {name}', name=$cmdopts.name)
            }
        ''',
    },
    {
        'name': 'macro.list',
        'descr': macro_list_descr,
        'storm': '''
            $count = $(0)
            for ($name, $mdef) in $lib.macro.list() {
                $user = $lib.auth.users.get($mdef.user)
                $lib.print('{name} (owner: {user})', name=$name.ljust(20), user=$user.name)
                $count = $($count + 1)
            }
            $lib.print('{count} macros found', count=$count)
        ''',
    },
]

class MacroExecCmd(s_storm.Cmd):
    '''
    Execute a named macro.

    Example:

        inet:ipv4#cno.threat.t80 | macro.exec enrich_foo

    '''

    name = 'macro.exec'

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('name', help='The name of the macro to execute')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe:
            mesg = 'macro.exec does not support per-node invocation'
            raise s_exc.StormRuntimeError(mesg=mesg)

        name = await s_stormtypes.tostr(self.opts.name)
        hivepath = ('cortex', 'storm', 'macros', name)

        mdef = await runt.snap.core.getHiveKey(hivepath)
        if mdef is None:
            mesg = f'Macro name not found: {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        query = await runt.getStormQuery(mdef['storm'])

        async with runt.getSubRuntime(query) as subr:
            async for nnode, npath in subr.execute(genr=genr):
                yield nnode, npath

@s_stormtypes.registry.registerLib
class LibMacro(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Storm Macros in the Cortex.
    '''
    _storm_locals = (
        {'name': 'set', 'desc': 'Add or modify an existing Storm Macro in the Cortex.',
         'type': {'type': 'function', '_funcname': '_funcMacroSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the Storm Macro to add or modify.', },
                      {'name': 'storm', 'type': ['str', 'storm:query'], 'desc': 'The Storm query to add to the macro.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a Storm Macro definition by name from the Cortex.',
         'type': {'type': 'function', '_funcname': '_funcMacroGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the macro to get.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A macro definition.', }}},
        {'name': 'del', 'desc': 'Delete a Storm Macro by name from the Cortex.',
         'type': {'type': 'function', '_funcname': '_funcMacroDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the macro to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Storm Macros in the Cortex.',
         'type': {'type': 'function', '_funcname': '_funcMacroList',
                  'returns': {'type': 'list', 'desc': 'A list of ``dict`` objects containing Macro definitions.', }}},
    )
    _storm_lib_path = ('macro',)

    def getObjLocals(self):
        return {
            'set': self._funcMacroSet,
            'get': self._funcMacroGet,
            'del': self._funcMacroDel,
            'list': self._funcMacroList,
        }

    async def _funcMacroList(self):
        path = ('cortex', 'storm', 'macros')
        return await self.runt.snap.core.getHiveKeys(path)

    async def _funcMacroGet(self, name):
        name = await s_stormtypes.tostr(name)

        path = ('cortex', 'storm', 'macros', name)
        return await self.runt.snap.core.getHiveKey(path)

    async def _funcMacroDel(self, name):
        name = await s_stormtypes.tostr(name)
        path = ('cortex', 'storm', 'macros', name)

        mdef = await self.runt.snap.core.getHiveKey(path)
        if mdef is None:
            mesg = f'Macro name not found: {name}'
            raise s_exc.NoSuchName(mesg)

        user = self.runt.user
        if mdef['user'] != user.iden and not user.isAdmin():
            mesg = 'Macro belongs to a different user'
            raise s_exc.AuthDeny(mesg=mesg)

        await self.runt.snap.core.popHiveKey(path)

    async def _funcMacroSet(self, name, storm):
        name = await s_stormtypes.tostr(name)
        storm = await s_stormtypes.tostr(storm)

        # validation
        await self.runt.getStormQuery(storm)

        path = ('cortex', 'storm', 'macros', name)

        user = self.runt.user

        mdef = await self.runt.snap.core.getHiveKey(path)
        if mdef is not None:
            if mdef['user'] != user.iden and not user.isAdmin():
                mesg = 'Macro belongs to a different user'
                raise s_exc.AuthDeny(mesg=mesg)

        mdef = {
            'user': user.iden,
            'storm': storm,
            'edited': s_common.now(),
        }

        await self.runt.snap.core.setHiveKey(path, mdef)
