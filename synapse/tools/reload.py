import sys
import yaml
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath


import synapse.lib.output as s_output
import synapse.lib.urlhelp as s_urlhelp

descr = '''
List or execute reload subsystems on a Synapse service.
'''

async def main(argv, outp=s_output.stdout):

    pars = getArgParser()
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            if opts.cmd == 'list':
                names = await cell.getReloadableSystems()
                if names:
                    outp.printf(f'Cell at {s_urlhelp.sanitizeUrl(opts.svcurl)} has the following reload subsystems:')
                    for name in names:
                        outp.printf(name)
                else:
                    outp.printf(f'Cell at {s_urlhelp.sanitizeUrl(opts.svcurl)} has no registered reload subsystems.')

            if opts.cmd == 'reload':
                outp.printf(f'Reloading cell at {s_urlhelp.sanitizeUrl(opts.svcurl)}')
                try:
                    ret = await cell.reload(subsystem=opts.name)
                except Exception as e:
                    outp.printf(f'Error reloading cell: {e}')
                    return 1

                if not ret:
                    outp.printf('No subsystems reloaded.')
                else:
                    outp.printf(f'{"Name:".ljust(40)}{"Result:".ljust(10)}Value:')
                    for name, (isok, valu) in ret.items():
                        if isok:
                            mesg = str(valu)
                            result = 'Success'
                        else:
                            mesg = valu[1].get('mesg')
                            if mesg is None:
                                mesg = valu[0]
                            result = 'Failed'

                        outp.printf(f'{name.ljust(40)}{result.ljust(10)}{mesg}')
    return 0

def getArgParser():
    pars = argparse.ArgumentParser(prog='reload', description=descr)
    pars.add_argument('--svcurl', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')

    subpars = pars.add_subparsers(required=True,
                                  title='subcommands',
                                  dest='cmd',)
    pars_list = subpars.add_parser('list', help='List subsystems which can be reloaded.')
    reld_list = subpars.add_parser('reload', help='Reload registered subsystems.')
    reld_list.add_argument('-n', '--name', type=str, help='Name of a subsystem to reload.')

    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
