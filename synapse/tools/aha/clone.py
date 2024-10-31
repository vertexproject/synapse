import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
Generate a new clone URL to deploy an AHA mirror.

Examples:

    python -m synapse.tools.aha.clone 01.aha.loop.vertex.link

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.clone', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('dnsname', help='The DNS name of the new AHA server.')
    pars.add_argument('--port', type=int, default=27492, help='The port that the new AHA server should listen on.')
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--only-url', help='Only output the URL upon successful execution',
                      action='store_true', default=False)
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:
            async with await s_telepath.openurl(opts.url) as aha:
                curl = await aha.addAhaClone(opts.dnsname, port=opts.port)

                if opts.only_url:
                    outp.printf(curl)
                else:
                    outp.printf(f'one-time use URL: {curl}')
                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))

            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
