import os
import sys
import copy
import asyncio
import logging
import argparse
import contextlib

from OpenSSL import crypto

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.certdir as s_certdir
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

# FIXME - set the correct version prior to release.
# reqver = '>=2.26.0,<3.0.0'

from typing import List, Tuple

def readfile(fp):
    '''Read a filepath in rb mode'''
    with open(fp, 'rb') as fd:
        return fd.read()

async def addAhaUser(aha: s_aha.AhaCell, svcname: str, svcnetw: str) -> None:
    username = f'{svcname}@{svcnetw}'
    udef = await aha.getUserDefByName(username)
    if udef is None:
        await aha.addUser(username)
        udef = await aha.getUserDefByName(username)

    getrule = (True, ('aha', 'service', 'get', svcnetw))
    addrule = (True, ('aha', 'service', 'add', svcnetw, svcname))

    if getrule not in udef.get('rules'):
        await aha.addUserRule(udef['iden'], getrule)

    if addrule not in udef.get('rules'):
        await aha.addUserRule(udef['iden'], addrule)

async def genSvcCerts(aha, dirn, certdir: s_certdir.CertDir,
                      svcname: str, svcnetw: str) -> Tuple[Tuple[str, bytes], ...]:
    user = f'{svcname}@{svcnetw}'
    name = f'{svcname}.{svcnetw}'

    cacrt = s_common.genpath(dirn, 'certs', 'cas', f'{svcnetw}.crt')
    hostkey = s_common.genpath(dirn, 'certs', 'hosts', f'{name}.key')
    hostcrt = s_common.genpath(dirn, 'certs', 'hosts', f'{name}.crt')
    userkey = s_common.genpath(dirn, 'certs', 'users', f'{user}.key')
    usercrt = s_common.genpath(dirn, 'certs', 'users', f'{user}.crt')

    if not os.path.isfile(cacrt):
        byts = await aha.genCaCert(svcnetw)
        with open(cacrt, 'wb') as fd:
            fd.write(byts.encode())

    if not os.path.isfile(userkey):
        byts = certdir.genUserCsr(user)
        crtbyts = await aha.signUserCsr(byts.decode(), signas=svcnetw)
        with open(usercrt, 'wb') as fd:
            fd.write(crtbyts.encode())

    if not os.path.isfile(hostkey):
        byts = certdir.genHostCsr(name)
        crtbyts = await aha.signHostCsr(byts.decode(), signas=svcnetw)
        with open(hostcrt, 'wb') as fd:
            fd.write(crtbyts.encode())

    return (
        (f'certs/cas/{svcnetw}.crt', readfile(cacrt)),
        (f'certs/users/{user}.crt', readfile(usercrt)),
        (f'certs/users/{user}.key', readfile(userkey)),
        (f'certs/hosts/{name}.crt', readfile(hostcrt)),
        (f'certs/hosts/{name}.key', readfile(hostkey)),
    )

def getAhaRegistry(template: str, svcname: str) -> List[str]:
    ret = []

    info = s_telepath.chopurl(template)
    info['user'] = svcname
    url = s_telepath.zipurl(info)
    ret.append(url)
    return ret

async def _main(argv, outp):
    pars = getArgParser()
    opts = pars.parse_args(argv)

    definition = s_common.yamlload(opts.definition)
    from pprint import pprint
    pprint(definition)
    # return 0
    assert bool(definition), f'invalid definition {definition=}'

    output_path = s_common.genpath(opts.output)
    os.makedirs(output_path)

    ahanetwork = definition.get('aha:network')
    ahaname = definition.get('aha:name')
    ahadnsname = definition.get('aha:dns:name')
    ahaadmin = definition.get('aha:admin')
    ahanexuslog = definition.get('aha:nexus', True)

    ahaadmin = f'{ahaadmin}@{ahanetwork}'

    ahalisten = definition.get('aha:listen', '0.0.0.0')
    ahaport = definition.get('aha:port', 27492),

    ahadmonlisten = f'ssl://{ahalisten}:{ahaport}/?hostname={ahaname}&ca={ahanetwork}'

    # This is a format() friendly string
    aharegistry_template = f'ssl://USER@{ahadnsname}:{ahaport}/'

    ahaconf = {
        'https:port': None,
        'aha:admin': ahaadmin,
        'aha:network': ahanetwork,
        'dmon:listen': ahadmonlisten,
        'nexslog:en': ahanexuslog
    }

    aharoot = s_common.genpath(output_path, 'aha')
    ahasvcdir = s_common.genpath(aharoot, 'storage')

    ahadc = {'services': {'aha': {'environment': {'SYN_LOG_LEVEL': 'DEBUG',
                                                  'SYN_LOG_STRUCT': '1'},
                                  'image': 'vertexproject/synapse-aha:v2.x.x',
                                  'logging': {'driver': 'json-file',
                                              'options': {'max-file': '1',
                                                          'max-size': '100m'}},
                                  'network_mode': 'host',
                                  'volumes': ['./storage:/vertex/storage',
                                              './backups:/vertex/backups']}},
             'version': '3.3'}
    s_common.yamlsave(ahadc, aharoot, 'docker-compose.yaml')
    # s_common.yamlsave(ahaconf, ahasvcdir, 'cell.yaml')

    _tempconf = {
        'dmon:listen': None
    }

    svc2ahatemplate = {}  # Put listen urls here keyed to the service?

    # We'll end up using the backup tool to
    with s_common.getTempDir() as dirn:
        tmpcertdir = s_common.genpath(dirn, 'certs')
        certdir = s_certdir.CertDir(tmpcertdir)
        tmpahadirn = s_common.genpath(dirn, 'aha')
        s_common.yamlsave(ahaconf, tmpahadirn, 'cell.yaml')
        async with await s_aha.AhaCell.anit(dirn=ahasvcdir,
                                            conf=_tempconf) as aha:  # type: s_aha.AhaCell

            # Smash the backup:dir into the aha cell.yaml
            ahaconf['backup:dir'] = '/vertex/storage'
            s_common.yamlsave(ahaconf, tmpahadirn, 'cell.yaml')

            for svc in definition.get('svcs', ()):
                svcname = svc.get('name')
                svcroot = s_common.genpath(output_path, svcname)
                svcstorage = s_common.genpath(svcroot, 'storage')

                svcfull = f'{svcname}.{ahanetwork}'

                # Add the aha user
                await addAhaUser(aha, svcname, ahanetwork)

                # Generate certs
                certinfo = await genSvcCerts(aha, dirn, certdir, svcname, ahanetwork)
                for (certpath, byts) in certinfo:
                    fp = s_common.genpath(svcstorage, certpath)
                    with s_common.genfile(fp) as fd:
                        fd.write(byts)

                svc_dmon_listen = f'ssl://0.0.0.0:0?hostname={svcfull}&ca={ahanetwork}'
                svc_aha_connect = f'aha://{{name}}@{svcfull}/'
                svc2ahatemplate[svcname] = svc_aha_connect

                # Generate svcconf
                conf = svc.get('cellconf', {})  # type: dict
                conf = copy.deepcopy(conf)
                # Mandatory values
                conf.setdefault('backup:dir', '/vertex/storage')
                conf.setdefault('aha:name', svcname)
                conf.setdefault('aha:network', ahanetwork)
                conf.setdefault('aha:registry', getAhaRegistry(aharegistry_template, svcname))
                conf.setdefault('aha:admin', ahaadmin)
                conf.setdefault('https:port', None)
                conf.setdefault('dmon:listen', svc_dmon_listen)

                # Check if items require interpolation
                for k, v in list(conf.items()):
                    if isinstance(v, str) and v.startswith('GENINFRAURL_'):
                        target_svc = v.split('_', 1)[1]
                        template = svc2ahatemplate[target_svc]
                        url = template.format(name=svcname)
                        conf[k] = url

                s_common.yamlsave(conf, svcstorage, 'cell.yaml')

                # Generate docker-compose file

                env = svc.get('environment', {})
                env.setdefault('SYN_LOG_LEVEL', 'DEBUG')
                env.setdefault('SYN_LOG_STRUCT', '1')

                svcdc = {'services': {svcfull: {'environment': env,
                                                'image': svc['image'],
                                                'logging': {'driver': 'json-file',
                                                            'options': {'max-file': '1',
                                                                        'max-size': '100m'}},
                                                'network_mode': 'host',
                                                'restart': 'unless-stopped',
                                                'volumes': ['./storage:/vertex/storage',
                                                            './backups:/vertex/backups']}},
                         'version': '3.3'}
                s_common.yamlsave(svcdc, svcroot, 'docker-compose.yaml')

def getArgParser():
    desc = 'CLI tool to generate simple x509 certificates from an Aha server.'
    pars = argparse.ArgumentParser(prog='aha.easycert', description=desc)

    pars.add_argument('-d', '--definition', required=True, type=str,
                      help='Infrastructure definition')
    pars.add_argument('-o', '--output', required=True, type=str,
                      help='Output directory')

    return pars

async def main(argv, outp=None):  # pragma: no cover

    if outp is None:
        outp = s_output.stdout

    s_common.setlogging(logger, 'DEBUG')

    ret = await _main(argv, outp)

    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
