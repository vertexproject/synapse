import argparse

import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.lib.output as s_output
import synapse.lib.reflect as s_reflect

def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='cmdr', description='Connect to a remote commander interface for an object via Telepath.')
    pars.add_argument('url', type=str, help='URL to connect too.')
    opts = pars.parse_args(argv)

    proxy = s_telepath.openurl(opts.url)

    reflections = s_reflect.getItemInfo(proxy)
    classes = reflections.get('inherits')
    if 'synapse.lib.cmdr.CliServer' in classes:
        cli = s_cmdr.CliProxy(proxy, outp)
    else:
        cli = s_cmdr.getItemCmdr(proxy, outp)
    cli.runCmdLoop()
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main(sys.argv[1:]))
