import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
A tool to prepare provisioning entries in the AHA server.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='provision', description=descr)
    pars.add_argument('--url', default='cell://vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('svcname', help='The name of the service relative to the AHA network.')

    opts = pars.parse_args(argv)
    async with await s_telepath.openurl(opts.url) as aha:
        iden = await aha.addAhaSvcProv(opts.svcname)
        outp.printf(f'one-time use provisioning key: {iden}')

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
