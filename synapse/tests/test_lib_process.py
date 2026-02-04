import sys
import time
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.process as s_process
import synapse.tests.utils as s_t_utils

class FakeError(Exception): pass

def spawnfunc(x, y=10):
    return x + y

def spawnsleep(n=10):
    time.sleep(n)
    return True

def spawnfakeit():
    raise FakeError()

def spawnexit():
    sys.exit(0)

def synerr():
    raise s_exc.SynErr(mesg='fail')

def nopickle():
    class Bar: pass
    return Bar()

class ProcessTest(s_t_utils.SynTest):

    async def test_lib_process_spawn(self):

        todo = (spawnfunc, (20,), {'y': 30})
        self.eq(50, await s_process.spawn(todo))

        todo = (spawnsleep, (1.5,), {})
        self.true(await s_process.spawn(todo))

        todo = (spawnsleep, (), {})
        with self.raises(asyncio.TimeoutError):
            await s_process.spawn(todo, timeout=0.1)

        todo = (spawnfakeit, (), {})
        with self.raises(s_exc.SynErr) as cm:
            await s_process.spawn(todo)
        self.eq('FakeError', cm.exception.get('name'))
        self.isin('Error executing spawn function: FakeError', cm.exception.get('mesg'))

        todo = (spawnexit, (), {})
        with self.raises(s_exc.SpawnExit):
            await s_process.spawn(todo)

        todo = (synerr, (), {})
        with self.raises(s_exc.SynErr) as cm:
            await s_process.spawn(todo)
        self.eq('fail', cm.exception.get('mesg'))

        # by convention spawn functions should
        # never return non-pickleable results
        todo = (nopickle, (), {})
        with self.raises(s_exc.SpawnExit) as cm:
            await s_process.spawn(todo)
        self.eq(0, cm.exception.get('code'))
        self.isin('without a result', cm.exception.get('mesg'))
