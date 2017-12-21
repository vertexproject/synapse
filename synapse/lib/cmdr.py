import synapse.lib.cli as s_cli
import synapse.lib.mixins as s_mixins
import synapse.lib.reflect as s_reflect

# Add our commands to the mixins registry
s_mixins.addSynMixin('cmdr', 'synapse.eventbus.EventBus', 'synapse.cmds.common.PyCmd')
s_mixins.addSynMixin('cmdr', 'synapse.eventbus.EventBus', 'synapse.cmds.common.GuidCmd')
s_mixins.addSynMixin('cmdr', 'synapse.cores.common.Cortex', 'synapse.cmds.cortex.AskCmd')


def getItemCmdr(item, outp=None, **opts):
    '''
    Construct and return a cmdr for the given item.

    Example:

        cmdr = getItemCmdr(foo)

    '''
    cmdr = s_cli.Cli(item, outp=outp)

    refl = s_reflect.getItemInfo(item)
    if refl is None:
        return cmdr

    for name in refl.get('inherits', ()):
        for mixi in s_mixins.getSynMixins('cmdr', name):
            cmdr.addCmdClass(mixi)

    return cmdr

def runItemCmdr(item, outp=None, **opts):
    '''
    Create a cmdr for the given item and run the cmd loop.

    Example:

        runItemCmdr(foo)

    '''
    cmdr = getItemCmdr(item, outp=outp, **opts)
    cmdr.runCmdLoop()
