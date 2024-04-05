import synapse.common as s_common

import synapse.lib.cli as s_cli
import synapse.lib.output as s_output

import synapse.cmds.boss as s_cmds_boss
import synapse.cmds.hive as s_cmds_hive
import synapse.cmds.cortex as s_cmds_cortex

cmdsbycell = {
    'cell': (
        s_cmds_hive.HiveCmd,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
    ),

    'cortex': (
        s_cmds_cortex.Log,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
        s_cmds_hive.HiveCmd,
        s_cmds_cortex.StormCmd,
    ),
}

async def getItemCmdr(cell, outp=None, color=False, **opts):
    '''
    Construct and return a cmdr for the given remote cell.

    Args:
        cell: Cell proxy being commanded.
        outp: Output helper object.
        color (bool): If true, enable colorized output.
        **opts: Additional options pushed into the Cmdr locs.

    Examples:

        Get the cmdr for a proxy::

            cmdr = await getItemCmdr(foo)

    Returns:
        s_cli.Cli: A Cli instance with Cmds loaeded into it.

    '''
    mesg = s_common.deprecated('cmdr', curv='2.164.0')

    if outp is None:
        outp = s_output.OutPut()

    outp.printf(f'WARNING: {mesg}')

    cmdr = await s_cli.Cli.anit(cell, outp=outp)
    if color:
        cmdr.colorsenabled = True
    typename = await cell.getCellType()

    for ctor in cmdsbycell.get(typename, ()):
        cmdr.addCmdClass(ctor)

    return cmdr

async def runItemCmdr(item, outp=None, color=False, **opts):
    '''
    Create a cmdr for the given item and run the cmd loop.

    Args:
        item: Cell proxy being commanded.
        outp: Output helper object.
        color (bool): If true, enable colorized output.
        **opts: Additional options pushed into the Cmdr locs.

    Notes:
        This function does not return while the command loop is run.

    Examples:

        Run the Cmdr for a proxy::

            await runItemCmdr(foo)

    Returns:
        None: This function returns None.
    '''
    cmdr = await getItemCmdr(item, outp=outp, color=color, **opts)
    await cmdr.runCmdLoop()
