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

            async def coro():
                async for _ in core.storm(q):
                    event.set()

            fut = core.schedCoro(coro())

            self.true(await asyncio.wait_for(event.wait(), timeout=12))

            with mock.patch('builtins.print', mock_print):
                self.none(s_glob._asynciostacks())

            fut.cancel()

        text = ''.join(lines)
        self.isin('Asyncio task stacks', text)
        self.isin('Task is a syntask with the following information', text)
        self.isin(q, text)
        self.isin('Faulthandler stack frames per thread', text)
