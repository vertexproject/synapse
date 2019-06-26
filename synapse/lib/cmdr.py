import synapse.exc as s_exc

import synapse.lib.cli as s_cli

import synapse.cmds.boss as s_cmds_boss
import synapse.cmds.cron as s_cmds_cron
import synapse.cmds.hive as s_cmds_hive
import synapse.cmds.cortex as s_cmds_cortex
import synapse.cmds.trigger as s_cmds_trigger

cmdsbyinterface = {
    'cell': (s_cmds_boss.PsCmd,
             s_cmds_boss.KillCmd,
             s_cmds_hive.HiveCmd,
             ),

    'cortex':
        (s_cmds_cron.At,
         s_cmds_cron.Cron,
         s_cmds_cortex.Log,
         s_cmds_cortex.StormCmd,
         s_cmds_trigger.Trigger,
         ),
}

cmdsbycell = {
    'cell': (
        s_cmds_hive.HiveCmd,
        s_cmds_boss.PsCmd,
        s_cmds_boss.KillCmd,
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

def addInterfaceCmd(interface, ctor):
    '''
    Add a CLI Cmd for a given interface.

    Args:
        interface (str): Name of the interface.
        ctor: The ctor for the command.

    Returns:
        None
    '''
    ctors = cmdsbyinterface.get(interface)
    if ctors is None:
        cmdsbyinterface[interface] = (ctor,)
    else:
        cmdsbyinterface[interface] = ctors + (ctor,)

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
    cmdr = await s_cli.Cli.anit(cell, outp=outp, **opts)
    if color:
        cmdr.colorsenabled = True

    try:
        interfaces = await cell.getCellInterfaces()

        for itype, version in interfaces:
            for ctor in cmdsbyinterface.get(itype, ()):
                cmdr.addCmdClass(ctor)

    except s_exc.NoSuchMeth as e:  # pragma: no cover
        # This is fallback code
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
