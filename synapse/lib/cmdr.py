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
        s_cmds_cron.At,
        s_cmds_cron.Cron,
        s_cmds_cortex.Log,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
        s_cmds_hive.HiveCmd,
        s_cmds_cortex.StormCmd,
        s_cmds_trigger.Trigger,
    ),
}


cmdsbyclass = {

    'CellApi': (
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
        s_cmds_hive.HiveCmd,
    ),

    'CoreApi': (
        s_cmds_cron.At,
        s_cmds_cron.Cron,
        s_cmds_cortex.Log,
        s_cmds_cortex.StormCmd,
        s_cmds_trigger.Trigger,
    ),

}


async def getItemCmdr(item, outp=None, color=False, **opts):
    '''
    Construct and return a cmdr for the given remote item.

    Args:
        cell: Cell proxy being commanded.
        outp: Output helper object.
        color (bool): If true, enable colorized output.
        **opts: Additional options pushed into the Cmdr locs.

    Examples:

        Get the cmdr for a proxy::

            cmdr = await getItemCmdr(foo)

    Returns:
        s_cli.Cli: A CLI object with object specific commands loaded.

    '''
    cmdr = await s_cli.Cli.anit(item, outp=outp)
    if color:
        cmdr.colorsenabled = True
    classes = item._getClasses()

    if classes is None:  # pragma: no cover
        # This path exists to support clients to older
        # servers (primarily Cortexes). This allows the
        # client to load their commands via the Cell type
        # instead of class reflection.

        typename = await item.getCellType()

        for ctor in cmdsbycell.get(typename, ()):
            cmdr.addCmdClass(ctor)

    else:
        for clspath in classes:
            _, clsname = clspath.rsplit('.', 1)
            for ctor in cmdsbyclass.get(clsname, ()):
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
