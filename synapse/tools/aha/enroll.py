import os
import sys
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir

descr = '''
Use a one-time use key to initialize your AHA user enrivonment.

Examples:

    python -m synapse.tools.aha.register tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='provision', description=descr)
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
                os.path.unlink(capath)

            byts = await prov.getCaCert()
            capath = certdir.saveCaCertByts(byts)
            outp.printf(f'Saved CA certificate: {capath}')

            keypath = certdir.getUserKeyPath(username)
            if keypath is not None:
                os.path.unlink(keypath)

            crtpath = certdir.getUserCertPath(username)
            if crtpath is not None:
                os.path.unlink(keypath)

            xcsr = certdir.genUserCsr(username)
            byts = await prov.signUserCsr(xcsr)
            crtpath = certdir.saveUserCertByts(byts)
            outp.printf(f'Saved user certificate: {crtpath}')

            ahaurls = s_telepath.modurl(ahaurls, user=ahauser)
            if ahaurls not in teleyaml.get('aha:servers'):
                outp.printf('Updating known AHA servers')
                servers = list(teleyaml.get('aha:servers'))
                servers.append(ahaurls)
                teleyaml['aha:servers'] = servers
                s_common.yamlsave(teleyaml, yamlpath)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
