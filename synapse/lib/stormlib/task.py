import asyncio
import logging

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

stormcmds = [
    {
        'name': 'task.list',
        'descr': 'List running tasks on the Cortex and any mirrors.',
        'cmdargs': (
            ('--verbose', {'default': False, 'action': 'store_true', 'help': 'Enable verbose output.'}),
        ),
        'storm': '''
            $tcnt = (0)
            for $task in $lib.task.list() {
                $lib.print(`task iden: {$task.iden}`)
                $lib.print(`    name: {$task.name}`)
                $lib.print(`    user: {$task.username}`)
                $lib.print(`    service: {$task.service}`)
                $lib.print(`    start time: {$lib.time.format($task.tick, '%Y-%m-%d %H:%M:%S')}`)
                $lib.print('    metadata:')
                if $cmdopts.verbose {
                    $lib.pprint($task.info, prefix='    ')
                } else {
                    $lib.pprint($task.info, prefix='    ', clamp=120)
                }
                $tcnt = ($tcnt + 1)
            }

            if ($tcnt = 1) {
                $lib.print('1 task found.')
            } else {
                $lib.print(`{$tcnt} tasks found.`)
            }
        ''',
    },
    {
        'name': 'task.kill',
        'descr': 'Kill a running task on the Cortex or a mirror.',
        'cmdargs': (
            ('iden', {'help': 'Any prefix that matches exactly one valid task iden is accepted.'}),
        ),
        'storm': '''
            $kild = $lib.task.kill($cmdopts.iden)
            $lib.print("kill status: {kild}", kild=$kild)
        ''',
    },
]

@s_stormtypes.registry.registerLib
class LibTask(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with tasks on a Cortex and its mirrors.
    '''
    _storm_locals = (
        {'name': 'list', 'desc': 'List tasks the current user can access on the Cortex and its mirrors.',
         'type': {'type': 'function', '_funcname': '_methTaskList', 'args': (),
                  'returns': {'name': 'yields', 'type': 'dict', 'desc': 'Task definitions.'}}},
        {'name': 'kill', 'desc': 'Stop a running task on the Cortex or a mirror.',
         'type': {'type': 'function', '_funcname': '_methTaskKill', 'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'The prefix of the task to stop. '
                               'Tasks will only be stopped if there is a single prefix match.'},),
                  'returns': {'type': 'boolean', 'desc': 'True if the task was cancelled, False otherwise.'}}},
    )
    _storm_lib_path = ('task',)
    _storm_lib_perms = (
        {'perm': ('task', 'get'), 'gate': 'cortex',
         'desc': 'Permits a user to view tasks owned by other users.'},
        {'perm': ('task', 'del'), 'gate': 'cortex',
         'desc': 'Permits a user to kill tasks owned by other users.'},
    )

    def getObjLocals(self):
        return {
            'list': self._methTaskList,
            'kill': self._methTaskKill,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methTaskList(self):
        useriden = self.runt.user.iden
        isallowed = self.runt.allowed(('task', 'get'))

        async for task in self.runt.snap.core.getTasks():
            if isallowed or task['user'] == useriden:
                yield task

    async def _methTaskKill(self, prefix):
        useriden = self.runt.user.iden
        isallowed = self.runt.allowed(('task', 'del'))

        prefix = await s_stormtypes.tostr(prefix)
        if not prefix:
            mesg = 'An empty task iden prefix is not allowed.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        iden = None
        async for task in self.runt.snap.core.getTasks():
            taskiden = task['iden']
            if (isallowed or task['user'] == useriden) and taskiden.startswith(prefix):
                if iden is None:
                    iden = taskiden
                else:
                    mesg = 'Provided iden matches more than one task.'
                    raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        if iden is None:
            mesg = 'Provided iden does not match any tasks.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        return await self.runt.snap.core.killTask(iden)
