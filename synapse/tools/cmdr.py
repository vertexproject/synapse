import sys
import logging

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

logger = logging.getLogger(__name__)

async def main(argv):  # pragma: no cover

    if len(argv) != 2:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    async with await s_telepath.openurl(argv[1]) as item:

        cmdr = await s_cmdr.getItemCmdr(item)
        # This causes a dropped connection to the cmdr'd item to
        # cause cmdr to exit. We can't safely test this in CI since
        # the fini handler sends a SIGINT to mainthread; which can
        # be problematic for test runners.
        cmdr.finikill = True
        await cmdr.runCmdLoop()
        cmdr.finikill = False

async def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    return await main(sys.argv)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(s_glob.sync(_main()))
