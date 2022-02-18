import os
import sys
import copy
import shutil
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

import synapse.tools.backup as s_t_backup

logger = logging.getLogger(__name__)

# FIXME - set the correct version prior to release.
# reqver = '>=2.26.0,<3.0.0'

from typing import List, Tuple

def readfile(fp):
    '''Read a filepath in rb mode'''
    with open(fp, 'rb') as fd:
        return fd.read()

async def genSvcCerts(aha, dirn, certdir: s_certdir.CertDir,
                      svcname: str, svcnetw: str) -> Tuple[Tuple[str, bytes], ...]:
    user = f'{svcname}@{svcnetw}'
    name = f'{svcname}.{svcnetw}'

    cacrt = s_common.genpath(dirn, 'cas', f'{svcnetw}.crt')
    hostkey = s_common.genpath(dirn, 'hosts', f'{name}.key')
    hostcrt = s_common.genpath(dirn, 'hosts', f'{name}.crt')
    userkey = s_common.genpath(dirn, 'users', f'{user}.key')
    usercrt = s_common.genpath(dirn, 'users', f'{user}.crt')

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

def prep_certdir(dirn):
    s_common.gendir(dirn, 'certs', 'cas')
    s_common.gendir(dirn, 'certs', 'hosts')
    s_common.gendir(dirn, 'certs', 'users')

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

    certdirn = s_common.genpath(output_path, '_certs')
    certdir = s_certdir.CertDir(path=certdirn)

    ahainfo = definition.get('aha')

    ahanetwork = ahainfo['network']
    ahaname = ahainfo.get('aha:name', 'aha')
    ahaname = f'{ahaname}.{ahanetwork}'
    ahaadmin_raw = ahainfo.get('aha:admin', 'root')
    ahaadmin = f'{ahaadmin_raw}@{ahanetwork}'

    ahalisten = ahainfo.get('aha:listen', '0.0.0.0')
    ahaport = ahainfo.get('aha:port', 27492)

    ahadmonlisten = f'ssl://{ahalisten}:{ahaport}/?hostname={ahaname}&ca={ahanetwork}'
    aharegistry = [f'ssl://{ahaadmin_raw}@{ahaname}:{ahaport}/', ]

    ahaconf = {
        'https:port': None,
        'aha:admin': ahaadmin,
        'aha:name': ahaname,
        'aha:network': ahanetwork,
        'dmon:listen': ahadmonlisten,
        'backup:dir': '/vertex/backups'
    }

    aharoot = s_common.gendir(output_path, 'aha')
    ahasvcdir = s_common.gendir(aharoot, 'storage')
    ahadc = {
        'services': {
            'aha': {
                'environment': {
                    'SYN_LOG_LEVEL': 'DEBUG',
                    'SYN_LOG_STRUCT': '1',
                },
                'image': 'vertexproject/synapse-aha:v2.x.x',
                'logging': {'driver': 'json-file',
                            'options': {'max-file': '1',
                                        'max-size': '100m'}},
                'network_mode': 'host',
                'volumes': ['./storage:/vertex/storage',
                            './backups:/vertex/backups']}},
        'version': '3.3',
    }
    s_common.yamlsave(ahadc, aharoot, 'docker-compose.yaml')
    s_common.yamlsave(ahaconf, ahasvcdir, 'cell.yaml')
    prep_certdir(ahasvcdir)

    cakey, cacert = certdir.genCaCert(ahanetwork)
    ahakey, ahacert = certdir.genHostCert(ahaname, signas=ahanetwork)
    ahaadminkey, ahaadmincert = certdir.genUserCert(ahaadmin, signas=ahanetwork)

    #
    # with s_common.genfile(ahasvcdir, 'certs', 'ca', f'{ahanetwork}.key') as fd:
    #     fd.write(certdir._pkeyToByts(cakey))
    # with s_common.genfile(ahasvcdir, 'certs', 'ca', f'{ahanetwork}.crt') as fd:
    #     fd.write(certdir._certToByts(cacert))
    #
    # with s_common.genfile(ahasvcdir, 'certs', 'ca', f'{ahanetwork}.key') as fd:
    #     fd.write(certdir._pkeyToByts(cakey))
    # with s_common.genfile(ahasvcdir, 'certs', 'ca', f'{ahanetwork}.crt') as fd:
    #     fd.write(certdir._certToByts(cacert))
    #

    svc2ahaconnect = {}

    for svcinfo in definition.get('svcs', ()):  # type: dict
        svcname = svcinfo.get('name')
        svcroot = s_common.gendir(output_path, svcname)
        svcstorage = s_common.gendir(svcroot, 'storage')
        prep_certdir(svcstorage)

        svcfull = f'{svcname}.{ahanetwork}'
        svcuser = f'{svcname}@{ahanetwork}'

        svchkey, svchcrt = certdir.genHostCert(svcfull, signas=ahanetwork)
        svcukey, svcucrt = certdir.genUserCert(svcuser, signas=ahanetwork)

        with s_common.genfile(svcstorage, 'certs', 'cas', f'{ahanetwork}.crt') as fd:
            fd.write(certdir._certToByts(cacert))
        with s_common.genfile(svcstorage, 'certs', 'hosts', f'{svcfull}.key') as fd:
            fd.write(certdir._pkeyToByts(svchkey))
        with s_common.genfile(svcstorage, 'certs', 'hosts', f'{svcfull}.crt') as fd:
            fd.write(certdir._certToByts(svchcrt))
        with s_common.genfile(svcstorage, 'certs', 'users', f'{svcuser}.key') as fd:
            fd.write(certdir._pkeyToByts(svcukey))
        with s_common.genfile(svcstorage, 'certs', 'users', f'{svcuser}.crt') as fd:
            fd.write(certdir._certToByts(svcucrt))
        with s_common.genfile(svcstorage, 'certs', 'users', f'{ahaadmin}.key') as fd:
            fd.write(certdir._pkeyToByts(ahaadminkey))
        with s_common.genfile(svcstorage, 'certs', 'users', f'{ahaadmin}.crt') as fd:
            fd.write(certdir._certToByts(ahaadmincert))

        svcport = svcinfo.get('svcport', '0')
        svclistn = svcinfo.get('svclisten', '0.0.0.0')
        svc_dmon_listen = f'ssl://{svclistn}:{svcport}/?hostname={svcfull}&ca={ahanetwork}'
        svc_aha_connect = f'aha://{ahaadmin_raw}@{svcfull}/'
        svc2ahaconnect[svcname] = svc_aha_connect

        # Generate svcconf
        conf = svcinfo.get('cellconf', {})  # type: dict
        conf = copy.deepcopy(conf)
        # Mandatory values
        conf.setdefault('backup:dir', '/vertex/backups')
        conf.setdefault('aha:name', svcname)
        conf.setdefault('aha:network', ahanetwork)
        conf.setdefault('aha:registry', aharegistry)
        conf.setdefault('aha:admin', ahaadmin)
        conf.setdefault('https:port', None)
        conf.setdefault('dmon:listen', svc_dmon_listen)

        # Check if items require interpolation
        for k, v in list(conf.items()):
            if isinstance(v, str) and v.startswith('GENAHAURL_'):
                target_svc = v.split('_', 1)[1]
                url = svc2ahaconnect[target_svc]
                conf[k] = url

        s_common.yamlsave(conf, svcstorage, 'cell.yaml')

        # Generate docker-compose file

        env = svcinfo.get('environment', {})
        env.setdefault('SYN_LOG_LEVEL', 'DEBUG')
        env.setdefault('SYN_LOG_STRUCT', '1')

        svcdc = {'services': {svcfull: {'environment': env,
                                        'image': svcinfo['image'],
                                        'logging': {'driver': 'json-file',
                                                    'options': {'max-file': '1',
                                                                'max-size': '100m'}},
                                        'network_mode': 'host',
                                        'restart': 'unless-stopped',
                                        'volumes': ['./storage:/vertex/storage',
                                                    './backups:/vertex/backups']}},
                 'version': '3.3'}
        s_common.yamlsave(svcdc, svcroot, 'docker-compose.yaml')

    shutil.copytree(certdirn, ahasvcdir)

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
