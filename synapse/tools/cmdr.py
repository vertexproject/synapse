import synapse.glob as s_glob
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr

def main(argv):  # pragma: no cover

    if len(argv) != 2:
        print('usage: python -m synapse.tools.cmdr <url>')
        return -1

    with s_telepath.openurl(argv[1]) as item:

        cmdr = s_glob.sync(s_cmdr.getItemCmdr(item))
        # This causes a dropped connection to the cmdr'd item to
        # cause cmdr to exit. We can't safely test this in CI since
        # the fini handler sends a SIGINT to mainthread; which can
        # be problematic for test runners.
        cmdr.finikill = True
        cmdr.runCmdLoop()
        cmdr.finikill = False

if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main(sys.argv))
