import synapse.lib.cli as s_cli
import synapse.cmds.cortex as s_cmds_cortex

cmdsbycell = {
    'cortex': (
        s_cmds_cortex.Log,
        s_cmds_cortex.StormCmd,
    ),
}

def getItemCmdr(cell, outp=None, **opts):
    '''
    Construct and return a cmdr for the given remote cell.

    Example:

        cmdr = getItemCmdr(foo)

    '''
    cmdr = s_cli.Cli(cell, outp=outp)
    typename = cell.getCellType()

    for ctor in cmdsbycell.get(typename, ()):
        cmdr.addCmdClass(ctor)

    return cmdr

def runItemCmdr(item, outp=None, **opts):
    '''
    Create a cmdr for the given item and run the cmd loop.

    Example:

        runItemCmdr(foo)

    '''
    cmdr = getItemCmdr(item, outp=outp, **opts)
    cmdr.runCmdLoop()
