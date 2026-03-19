import os
import asyncio

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.spawner as s_spawner

import synapse.tests.utils as s_t_utils


class SpawnTarget(s_base.Base, s_spawner.SpawnerMixin):

    async def __anit__(self):
        await s_base.Base.__anit__(self)


class SpawnerTest(s_t_utils.SynTest):

    async def test_spawner_wait_timeout(self):

        # _spawnerWait raises FatalErr when the socket never becomes available
        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')

            with self.raises(s_exc.FatalErr) as cm:
                await s_spawner._spawnerWait(sockpath, timeout=0.001)

            self.isin('within', cm.exception.errinfo.get('mesg', ''))

    async def test_spawner_workloop_fail_timeout(self):

        # When the workloop fails to bind, _spawnerWait times out with FatalErr
        loop = asyncio.get_running_loop()

        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')

            # A regular file at sockpath causes asyncio Unix socket bind to fail
            with open(sockpath, 'w') as fd:
                fd.write('')

            todo = (SpawnTarget.anit, (), {})

            # Run the workloop in a background thread (simulating a subprocess)
            fut = loop.run_in_executor(None, s_spawner._ioWorkProc, todo, sockpath)

            with self.raises(s_exc.FatalErr) as cm:
                await s_spawner._spawnerWait(sockpath, timeout=2)

            self.isin('within', cm.exception.errinfo.get('mesg', ''))

            # Clean up the executor future
            try:
                await fut
            except RuntimeError:
                pass

    async def test_spawner_ioworkproc_signal_runtimeerror(self):

        # _ioWorkProc re-raises when signal handlers cannot be installed
        loop = asyncio.get_running_loop()

        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')

            todo = (SpawnTarget.anit, (), {})

            try:
                await loop.run_in_executor(None, s_spawner._ioWorkProc, todo, sockpath)
                self.fail('Expected RuntimeError from addSignalHandlers failure')  # pragma: no cover
            except RuntimeError:
                pass
