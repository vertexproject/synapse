import os
import asyncio

from unittest import mock

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.process as s_process
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
                await s_spawner._spawnerWait(sockpath, timeout=12)

            self.isin('within', cm.exception.errinfo.get('mesg', ''))

            # Clean up the executor future
            try:
                await fut
            except RuntimeError:
                pass

    async def test_spawner_workloop_oserror(self):

        loop = asyncio.get_running_loop()

        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')

            # A regular file at sockpath causes Unix socket bind to raise OSError
            with open(sockpath, 'w') as fd:
                fd.write('')

            todo = (SpawnTarget.anit, (), {})

            # Hook the spawner logger to assert the exact message from line 38.
            # addSignalHandlers raises RuntimeError in a non-main thread, so mock
            # it to a no-op so _ioWorkProc reaches dmon.listen and hits the OSError path.
            async def _noopSignalHandlers(self):
                pass

            with mock.patch.object(s_base.Base, 'addSignalHandlers', _noopSignalHandlers):
                with self.getLoggerStream('synapse.lib.spawner') as stream:
                    fut = loop.run_in_executor(None, s_spawner._ioWorkProc, todo, sockpath)
                    await stream.expect('IO worker failed to open listening socket')

                try:
                    await fut
                except OSError:
                    pass

            # Also exercise via real subprocess spawn so lines 37-39 are covered
            # in CI (subprocess coverage via COVERAGE_PROCESS_START=.coveragerc).
            # The re-raised OSError propagates back through _exectodo as SynErr.
            spawn_task = asyncio.ensure_future(
                s_process.spawn((s_spawner._ioWorkProc, (todo, sockpath), {}))
            )

            with self.raises(s_exc.FatalErr) as cm:
                await s_spawner._spawnerWait(sockpath, timeout=12)
            self.isin('within', cm.exception.errinfo.get('mesg', ''))

            with self.raises(s_exc.SynErr) as cm:
                await spawn_task
            self.eq('OSError', cm.exception.errinfo.get('name', ''))

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
