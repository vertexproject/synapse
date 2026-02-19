import asyncio
import unittest.mock as mock

import synapse.glob as s_glob

import synapse.tests.utils as s_t_utils

class GlobTest(s_t_utils.SynTest):

    def test_glob_sync(self):

        async def afoo():
            return 42

        retn = s_glob.sync(afoo())
        self.eq(retn, 42)

    async def test_glob_stacks(self):

        lines = []
        def mock_print(*args, **kwargs):
            self.isinstance(args[0], str)
            lines.append(args[0])

        with mock.patch('builtins.print', mock_print):
            self.none(s_glob._threadstacks())

        text = '\n'.join(lines)
        self.isin('Faulthandler stack frames per thread', text)

        lines.clear()

        async with self.getTestCore() as core:

            q = 'while (true) { $lib.time.sleep(60) }'
            event = asyncio.Event()

            async def coro(info):
                async for mesg in core.storm(q):
                    if mesg[0] == 'init':
                        info |= mesg[1]
                    event.set()

            init_mesg = {}
            fut = core.schedCoro(coro(init_mesg))

            self.true(await asyncio.wait_for(event.wait(), timeout=12))

            with mock.patch('builtins.print', mock_print):
                self.none(s_glob._asynciostacks())

            fut.cancel()

        text = '\n'.join(lines)
        self.isin('Asyncio task stacks', text)
        self.isin('is a syntask with the following information', text)
        self.isin(q, text)
        self.isin('root=None', text)
        self.isin(f'root={init_mesg.get("task", "newp")}', text)
        self.isin('Faulthandler stack frames per thread', text)
