import os
import asyncio
import unittest.mock as mock

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.spawner as s_spawner

import synapse.tests.utils as s_t_utils


class SpawnTarget(s_base.Base, s_spawner.SpawnerMixin):

    async def __anit__(self):
        await s_base.Base.__anit__(self)


class SpawnerTest(s_t_utils.SynTest):

    async def test_spawner_wait_errfile(self):

        # _spawnerWait raises FatalErr and cleans up the errpath when it exists
        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')
            errpath = sockpath + '.err'

            with open(errpath, 'w') as fd:
                fd.write('test error message')

            with self.raises(s_exc.FatalErr) as cm:
                await s_spawner._spawnerWait(sockpath)

            self.isin('test error message', cm.exception.errinfo.get('mesg', ''))
            self.false(os.path.exists(errpath))

    async def test_spawner_wait_errfile_read_error(self):

        # _spawnerWait uses 'unknown' in the FatalErr message when errpath cannot be read
        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')
            errpath = sockpath + '.err'

            with open(errpath, 'w') as fd:
                fd.write('test error')

            real_open = open

            def mock_open(path, *args, **kwargs):
                if path == errpath:
                    raise OSError('permission denied')
                return real_open(path, *args, **kwargs)

            with mock.patch('builtins.open', side_effect=mock_open):
                with self.raises(s_exc.FatalErr) as cm:
                    await s_spawner._spawnerWait(sockpath)

            self.isin('unknown', cm.exception.errinfo.get('mesg', ''))

    async def test_spawner_wait_errfile_unlink_error(self):

        # _spawnerWait still raises FatalErr even when the errpath unlink fails
        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')
            errpath = sockpath + '.err'

            with open(errpath, 'w') as fd:
                fd.write('test error')

            with mock.patch('os.unlink', side_effect=OSError('unlink failed')):
                with self.raises(s_exc.FatalErr):
                    await s_spawner._spawnerWait(sockpath)

    async def test_spawner_wait_timeout(self):

        # _spawnerWait raises FatalErr when the socket never becomes available
        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')

            with self.raises(s_exc.FatalErr) as cm:
                await s_spawner._spawnerWait(sockpath, timeout=0.001)

            self.isin('within', cm.exception.errinfo.get('mesg', ''))

    async def test_spawner_ioworkproc_listen_oserror(self):

        # _ioWorkProc writes the errpath file when dmon.listen() raises OSError
        loop = asyncio.get_running_loop()

        with self.getTestDir() as dirn:

            sockpath = os.path.join(dirn, 'test.sock')
            errpath = sockpath + '.err'

            # A regular file at sockpath causes asyncio Unix socket bind to fail
            with open(sockpath, 'w') as fd:
                fd.write('')

            todo = (SpawnTarget.anit, (), {})

            try:
                await loop.run_in_executor(None, s_spawner._ioWorkProc, todo, sockpath)
                self.fail('Expected OSError from listen failure')  # pragma: no cover
            except OSError:
                pass

            self.true(os.path.exists(errpath))

    async def test_spawner_ioworkproc_errfile_write_error(self):

        # _ioWorkProc silently ignores errpath write failure when the directory does not exist
        loop = asyncio.get_running_loop()

        with self.getTestDir() as dirn:

            # Use a sockpath in a nonexistent subdirectory so both listen and errpath write fail
            sockpath = os.path.join(dirn, 'nonexistent', 'test.sock')
            errpath = sockpath + '.err'

            todo = (SpawnTarget.anit, (), {})

            try:
                await loop.run_in_executor(None, s_spawner._ioWorkProc, todo, sockpath)
                self.fail('Expected OSError from listen failure')  # pragma: no cover
            except OSError:
                pass

            self.false(os.path.exists(errpath))
