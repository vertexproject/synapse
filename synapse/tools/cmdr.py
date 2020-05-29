import sys
import asyncio
import logging
import warnings

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

reqver = '>=0.2.0,<3.0.0'

async def runcmdr(argv, item):  # pragma: no cover
    cmdr = await s_cmdr.getItemCmdr(item)
    await cmdr.addSignalHandlers()
    # Enable colors for users
    cmdr.colorsenabled = True

    if len(argv) == 2:
        await cmdr.runCmdLine(argv[1])
        return

    await cmdr.runCmdLoop()

async def main(argv):  # pragma: no cover

    if len(argv) not in (1, 2):
        print('usage: python -m synapse.tools.cmdr <url> [<single quoted command>]')
        return 1

    s_common.setlogging(logger, 'WARNING')

    async with await s_telepath.openurl(argv[0]) as item:
        try:
            s_version.reqVersion(item._getSynVers(), reqver)
        except s_exc.BadVersion as e:
            valu = s_version.fmtVersion(*e.get('valu'))
            print(f'Proxy version {valu} is outside of the cmdr supported range ({reqver}).')
            print(f'Please use a version of Synapse which supports {valu}; current version is {s_version.verstring}.')
            return 1
        await runcmdr(argv, item)
    return 0

if __name__ == '__main__': # pragma: no cover
    warnings.filterwarnings("default", category=PendingDeprecationWarning)
    sys.exit(asyncio.run(main(sys.argv[1:])))
