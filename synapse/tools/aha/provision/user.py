import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
A tool to create a new user auto-enroll entry on an AHA server.

Examples:

    # Create a new one-time use key to enroll a user
    python -m synapse.tools.aha.provision.user visi


    # Create an addtional key for an existing user.
    python -m synapse.tools.aha.provision.user --again visi
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.provision.user', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--again', default=False, action='store_true', help='Generate a new enroll URL for an existing user.')
    pars.add_argument('--only-url', help='Only output the URL upon successful execution',
                      action='store_true', default=False)
    pars.add_argument('username', help='The username which will be enrolled as <username>@<network>.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:
            async with await s_telepath.openurl(opts.url) as aha:
                userinfo = {}
                provurl = await aha.addAhaUserEnroll(opts.username, userinfo=userinfo, again=opts.again)
                if opts.only_url:
                    outp.printf(provurl)
                else:
                    outp.printf(f'one-time use URL: {provurl}')
                return 0
        except s_exc.SynErr as e:
            mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
