import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
A tool to prepare provisioning entries in the AHA server.

Examples:

    # provision a new serivce named 00.axon from within the AHA container.
    python -m synapse.tools.aha.provision.service 00.axo.servicen

    # provision a new serivce named 01.cortex as a mirror from within the AHA container.
    python -m synapse.tools.aha.provision.service 01.cortex --mirror 00.cortex

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='provision', description=descr)
    pars.add_argument('--url', default='cell://vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--user', help='Provision the new service with the username.')
    pars.add_argument('--cellyaml', help='Specify the path to a YAML file containing config options for the service.')
    pars.add_argument('--mirror', help='Provision the new service as a mirror of the existing AHA service.')
    pars.add_argument('svcname', help='The name of the service relative to the AHA network.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as aha:

            provinfo = {}

            if opts.cellyaml:
                provinfo['conf'] = s_common.yamlload(opts.cellyaml)

            provinfo.setdefault('conf', {})

            provinfo['mirror'] = opts.mirror
            provinfo['conf']['aha:user'] = opts.user

            provurl = await aha.addAhaSvcProv(opts.svcname, provinfo=provinfo)
            outp.printf(f'one-time use url: {provurl}')

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
