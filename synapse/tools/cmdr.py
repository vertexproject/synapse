import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

def main(argv):

    if len(argv) != 2:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    prox = s_telepath.openurl(argv[1])

    with s_cmdr.Cmdr(prox) as cmdr:
        cmdr.onfini(prox.fini)
        cmdr.runCmdLoop()

if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main(sys.argv))
