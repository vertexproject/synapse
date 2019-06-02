import synapse.lib.cli as s_cli

import synapse.cmds.boss as s_cmds_boss
import synapse.cmds.cron as s_cmds_cron
import synapse.cmds.hive as s_cmds_hive
import synapse.cmds.cortex as s_cmds_cortex
import synapse.cmds.trigger as s_cmds_trigger


# cmdsbycell was the 0.1.0-0.1.9 way that commands were loaded into a cmdr
# object by getItemCmdr.  This list should be considered frozen now, since
# we can now load the commands dynamically based on the reflected classes
# from the Proxy object.
cmdsbycell = {
    'cell': (
        s_cmds_hive.HiveCmd,
    ),

    'cortex': (
        s_cmds_cortex.Log,
        s_cmds_cortex.StormCmd,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
        s_cmds_cron.At,
        s_cmds_cron.Cron,
        s_cmds_hive.HiveCmd,
        s_cmds_trigger.Trigger,
    ),
}


cmdsbyclass = {

    'synapse.lib.cell.CellApi': (
        s_cmds_hive.HiveCmd,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
    ),

    'synapse.cortex.CoreApi': (
        s_cmds_cortex.Log,
        s_cmds_cortex.StormCmd,
        s_cmds_cron.At,
        s_cmds_cron.Cron,
        s_cmds_trigger.Trigger,
    ),

}


async def getItemCmdr(item, outp=None, **opts):
    '''
    Construct and return a cmdr for the given remote item.

    Example:

        cmdr = await getItemCmdr(foo)

    Returns:
        s_cli.Cli: A CLI object with object specific commands loaded.

    '''
    cmdr = await s_cli.Cli.anit(item, outp=outp)

    classes = item._getClasses()

    if classes is None:

        typename = await item.getCellType()

        for ctor in cmdsbycell.get(typename, ()):
            cmdr.addCmdClass(ctor)

    else:
        for clsname in classes:
            for ctor in cmdsbyclass.get(clsname, ()):
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
