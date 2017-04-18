import synapse.cortex as s_cortex
import synapse.telepath as s_telepath


import synapse.lib.cmdr as s_cmdr

def main(argv):

    if len(argv) != 2:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    item = s_telepath.openurl(argv[1])

    cmdr = s_cmdr.getItemCmdr(item)

    cmdr.runCmdLoop()

if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main(sys.argv))
