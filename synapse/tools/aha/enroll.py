import os
import sys
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack

descr = '''
Use a one-time use key to initialize your AHA user enrivonment.

Examples:

    python -m synapse.tools.aha.enroll tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.enroll', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('onceurl', help='The one-time use AHA user enrollment URL.')
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        certpath = s_common.getSynDir('certs')
        yamlpath = s_common.getSynPath('telepath.yaml')

        teleyaml = s_common.yamlload(yamlpath)
        if teleyaml is None:
            teleyaml = {}

        teleyaml.setdefault('version', 1)
        teleyaml.setdefault('aha:servers', ())

        s_common.gendir(certpath)

        certdir = s_certdir.CertDir(path=certpath)

        async with await s_telepath.openurl(opts.onceurl) as prov:

            userinfo = await prov.getUserInfo()

            ahaurls = userinfo.get('aha:urls')
            ahauser = userinfo.get('aha:user')
            ahanetw = userinfo.get('aha:network')

            username = f'{ahauser}@{ahanetw}'

            capath = certdir.getCaCertPath(ahanetw)
            if capath is not None:
                os.unlink(capath)

            byts = await prov.getCaCert()
            capath = certdir.saveCaCertByts(byts)
            outp.printf(f'Saved CA certificate: {capath}')

            keypath = certdir.getUserKeyPath(username)
            if keypath is not None:
                os.unlink(keypath)

            crtpath = certdir.getUserCertPath(username)
            if crtpath is not None:
                os.unlink(crtpath)

            xcsr = certdir.genUserCsr(username)
            byts = await prov.signUserCsr(xcsr)
            crtpath = certdir.saveUserCertByts(byts)
            outp.printf(f'Saved user certificate: {crtpath}')

            if ahaurls is not None:
                if isinstance(ahaurls, str):
                    ahaurls = (ahaurls,)

                certname = f'{ahauser}@{ahanetw}'
                ahaurls = set(s_telepath.modurl(ahaurls, certname=certname))
                servers = teleyaml.get('aha:servers')

                # repack the servers so lists are tuplized like values
                # we may get over telepath
                servers = s_msgpack.deepcopy(servers)
                if isinstance(servers, str):
                    servers = [servers]
                else:
                    servers = list(servers)

                newurls = ahaurls - set(servers)
                if newurls:
                    outp.printf('Updating known AHA servers')
                    servers.extend(newurls)
                    teleyaml['aha:servers'] = servers
                    s_common.yamlsave(teleyaml, yamlpath)

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
