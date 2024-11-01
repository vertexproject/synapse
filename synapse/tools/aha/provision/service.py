import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
A tool to prepare provisioning entries in the AHA server.

Examples:

    # provision a new serivce named 00.axon from within the AHA container.
    python -m synapse.tools.aha.provision.service 00.axon

    # provision a new serivce named 01.cortex as a mirror from within the AHA container.
    python -m synapse.tools.aha.provision.service 01.cortex --mirror 00.cortex

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.provision.service', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--user', help='Provision the new service with the username.')
    pars.add_argument('--cellyaml', help='Specify the path to a YAML file containing config options for the service.')
    pars.add_argument('--mirror', help='Provision the new service as a mirror of the existing AHA service.')
    pars.add_argument('--dmon-port', help='Provision the services SSL listener on a given port.', type=int)
    pars.add_argument('--https-port', help='Provision the services HTTPS listener on a given port.', type=int)
    pars.add_argument('--only-url', help='Only output the URL upon successful execution',
                      action='store_true', default=False)
    pars.add_argument('svcname', help='The name of the service relative to the AHA network.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:
            async with await s_telepath.openurl(opts.url) as aha:

                provinfo = {}

                if opts.cellyaml:
                    provinfo['conf'] = s_common.yamlload(opts.cellyaml)

                provinfo.setdefault('conf', {})

                provinfo['mirror'] = opts.mirror

                if opts.user is not None:
                    provinfo['conf']['aha:user'] = opts.user

                if opts.dmon_port is not None:
                    if not 0 <= opts.dmon_port < 65535:
                        outp.printf(f'ERROR: Invalid dmon port: {opts.dmon_port}')
                        return 1
                    provinfo['dmon:port'] = opts.dmon_port

                if opts.https_port is not None:
                    if not 0 <= opts.https_port < 65535:
                        outp.printf(f'ERROR: Invalid HTTPS port: {opts.https_port}')
                        return 1
                    provinfo['https:port'] = opts.https_port

                provurl = await aha.addAhaSvcProv(opts.svcname, provinfo=provinfo)
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
