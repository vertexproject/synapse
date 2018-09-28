import synapse.lib.cli as s_cli
import synapse.lib.coro as s_coro

import synapse.cmds.cortex as s_cmds_cortex

cmdsbycell = {
    'cortex': (
        s_cmds_cortex.StormCmd,
        s_cmds_cortex.Log,
    ),
}

async def getItemCmdr(cell, outp=None, **opts):
    '''
    Construct and return a cmdr for the given remote cell.

    Example:

        cmdr = await getItemCmdr(foo)

    '''
    cmdr = s_cli.Cli(cell, outp=outp)
    typename = await s_coro.ornot(cell.getCellType)

    for ctor in cmdsbycell.get(typename, ()):
        cmdr.addCmdClass(ctor)

    return cmdr

async def runItemCmdr(item, outp=None, **opts):
    '''
    Create a cmdr for the given item and run the cmd loop.

    Example:

        runItemCmdr(foo)

    '''
    cmdr = await getItemCmdr(item, outp=outp, **opts)
    await cmdr.runCmdLoop()
