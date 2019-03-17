import sys
import asyncio

import synapse.glob as s_glob
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

async def main(argv):  # pragma: no cover

    if len(argv) != 2:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    async with s_telepath.openurl(argv[1]) as item:

        cmdr = await s_cmdr.getItemCmdr(item)
        cmdr.inithist = True
        await cmdr.runCmdLoop()

async def main(argv, outp=s_output.stdout):

    opts = parse(argv)

    s_common.setlogging(logger)

    lisn = f'tcp://{opts.host}:{opts.port}/cortex'

    core = await s_cortex.Cortex.anit(opts.coredir)

    try:

        core.insecure = opts.insecure

        if core.insecure:
            logger.warning('INSECURE MODE ENABLED')

        outp.printf('starting cortex at: %s' % (lisn,))

        await core.dmon.listen(lisn)

        await core.addHttpsPort(opts.https_port)

        return core

    except Exception as e:
        await core.fini()
        raise

if __name__ == '__main__': # pragma: no cover
    asyncio.run(main(sys.argv[1:]))
