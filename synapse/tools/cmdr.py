import sys
import asyncio

import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

async def main(argv):  # pragma: no cover

    if len(argv) != 1:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    async with await s_telepath.openurl(argv[0]) as item:

        cmdr = await s_cmdr.getItemCmdr(item)
        await cmdr.runCmdLoop()

if __name__ == '__main__': # pragma: no cover
    asyncio.run(main(sys.argv[1:]))
