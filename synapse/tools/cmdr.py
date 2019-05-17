import sys
import asyncio
import logging

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

logger = logging.getLogger(__name__)

async def main(argv):  # pragma: no cover

    if len(argv) not in (1, 2):
        print('usage: python -m synapse.tools.cmdr <url> [<single quoted command>]')
        return -1

    s_common.setlogging(logger, 'WARNING')

    async with await s_telepath.openurl(argv[0]) as item:

        cmdr = await s_cmdr.getItemCmdr(item)
        await cmdr.addSignalHandlers()

        if len(argv) == 2:
            await cmdr.runCmdLine(argv[1])
            return

        await cmdr.runCmdLoop()

if __name__ == '__main__': # pragma: no cover
    asyncio.run(main(sys.argv[1:]))
