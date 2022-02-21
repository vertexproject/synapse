import os
import sys
import copy
import shutil
import asyncio
import logging
import argparse

import synapse.common as s_common

import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir

logger = logging.getLogger(__name__)

def prep_certdir(dirn):
    s_common.gendir(dirn, 'certs', 'cas')
    s_common.gendir(dirn, 'certs', 'hosts')
    s_common.gendir(dirn, 'certs', 'users')

_supported_versions = '>=0.1.0,<=0.2.0'

DEFAULT_DOCKER_LOGGING = {'driver': 'json-file',
                          'options': {'max-file': '1',
                                      'max-size': '100m'}}

DEFAULT_DOCKER_NETWORK_MODE = 'host'
DEFAULT_DOCKER_RESTART = 'unless-stopped'

DOCKER_COMPOSE_DEFAULTS = {
    'logging': DEFAULT_DOCKER_LOGGING,
    'network_mode': DEFAULT_DOCKER_NETWORK_MODE,
    'restart': DEFAULT_DOCKER_RESTART,
    'labels': {},
}

infraschema = {
    'definitions': {
        'ahaSvc': {
            'type': 'object',
            'properties': {
                'aha:network': {'type': 'string'},
                'aha:name': {'type': 'string', 'default': 'aha'},
                'aha:admin': {'type': 'string', 'default': 'root'},
                'aha:listen': {'type': 'string', 'default': '0.0.0.0'},
                'aha:port': {'type': 'integer', 'default': 27492},
                'docker': {
                    'type': 'object',
                    'properties': {
                        'image': {'type': 'string',
                                  'default': 'vertexproject/synapse-aha:v2.x.x'},
                        'environment': {'type': 'object', 'default': {}},
                        'labels': {'type': 'object', 'default': {}},
                    },
                    'default': {
                        'image': 'vertexproject/synapse-aha:v2.x.x',
                        'environment': {},
                        'labels': {},
                    }
                }
            },
            'required': [
                'aha:network',
            ]
        },
        'genericSvc': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'svcport': {'type': 'integer',
                            'default': 0},
                'svclisten': {'type': 'string',
                              'default': '0.0.0.0'},
                'cellconf': {
                    'type': 'object',
                },
                'docker': {
                    'type': 'object',
                    'properties': {
                        'image': {'type': 'string'},
                        'environment': {'type': 'object', 'default': {}},
                        'labels': {'type': 'object', 'default': {}},
                    },
                    'rquired': [
                        'image',
                    ]
                }
            },
            'required': [
                'name',
                'docker',
            ]
        },
        'dockerComposeDefaults': {
            'type': 'object',
            'properties': {
                'logging': {'type': 'object', 'default': DEFAULT_DOCKER_LOGGING, },
                'network_mode': {'type': 'string',
                                 'default': DEFAULT_DOCKER_NETWORK_MODE},
                'restart': {'type': 'string',
                            'default': DEFAULT_DOCKER_RESTART},
                'labels': {'type': 'object', 'default': {}},
            },
        }
    },
    'type': 'object',
    'properties': {
        'aha': {
            '$ref': '#/definitions/ahaSvc',
        },
        'svcs': {
            'type': 'array',
            'items': {'$ref': '#/definitions/genericSvc'}
        },
        'docker': {
            '$ref': '#/definitions/dockerComposeDefaults',
            'default': DOCKER_COMPOSE_DEFAULTS,
        },
        'version': {
            'type': 'string',
            'pattern': '^[0-9]+\\.[0-9]+\\.[0-9]+$',
        }
    },
    'required': [
        'aha',
        'svcs',
        'version',
    ],
}

reqValidInfra = s_config.getJsValidator(infraschema)

async def _main(argv, outp):
    pars = getArgParser()
    opts = pars.parse_args(argv)

    definition = s_common.yamlload(opts.definition)
    reqValidInfra(definition)
    import synapse.lib.version as s_version
    s_version.reqVersion(definition.get('version').split('.'), _supported_versions)

    output_path = s_common.genpath(opts.output)
    os.makedirs(output_path)

    docker_defaults = definition.get('docker')
    docker_logging = docker_defaults.get('logging')
    default_docker_labels = docker_defaults.get('labels')
    docker_restart = docker_defaults.get('restart')
    docker_network_mode = docker_defaults.get('network_mode')

    syndir = s_common.gendir(output_path, '_syndir')
    certdirn = s_common.genpath(syndir, 'certs')
    logger.info(f'Prepping certdir @ {certdirn}')

    certdir = s_certdir.CertDir(path=certdirn)

    logger.info('Making aha dir')
    ahainfo = definition.get('aha')

    ahanetwork = ahainfo['aha:network']
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
    ahadnfo = ahainfo.get('docker')
    ahalabels = {k: v for k, v in default_docker_labels.items()}
    ahalabels.update(ahadnfo.get('labels'))
    ahaenv = ahadnfo.get('environment')
    ahaenv.setdefault('SYN_LOG_LEVEL', 'DEBUG')
    ahaenv.setdefault('SYN_LOG_STRUCT', '1')

    for k, v in ahadnfo.get('environment').items():
        ahaenv.setdefault(k, v)

    ahacomposesvc = {
                'environment': ahaenv,
                'image': ahadnfo.get('image'),
                'logging': docker_logging,
                'network_mode': docker_network_mode,
                'restart': docker_restart,
                'volumes': ['./storage:/vertex/storage',
                            './backups:/vertex/backups']}

    if ahalabels:
        ahacomposesvc['labels'] = ahalabels

    ahadc = {
        'services': {
            ahaname: ahacomposesvc
        },
        'version': '3.3',
    }
    s_common.yamlsave(ahadc, aharoot, 'docker-compose.yaml')
    s_common.yamlsave(ahaconf, ahasvcdir, 'cell.yaml')

    cakey, cacert = certdir.genCaCert(ahanetwork)
    ahakey, ahacert = certdir.genHostCert(ahaname, signas=ahanetwork)
    ahaadminkey, ahaadmincert = certdir.genUserCert(ahaadmin, signas=ahanetwork)

    svc2ahaconnect = {}

    stormsvcs = []

    for svcinfo in definition.get('svcs', ()):  # type: dict
        svcname = svcinfo.get('name')
        svcroot = s_common.gendir(output_path, svcname)
        svcstorage = s_common.gendir(svcroot, 'storage')
        prep_certdir(svcstorage)

        svcfull = f'{svcname}.{ahanetwork}'
        svcuser = f'{svcname}@{ahanetwork}'

        logger.info(f'Prepping dir for {svcfull}')

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
                logger.info(f'Replaced {k}={v} with {url}')
                conf[k] = url
                continue

            if isinstance(v, str) and v.startswith('GENFQDN_'):
                prefix = v.split('_', 1)[1]
                fqdn = f'{prefix}.{ahanetwork}'
                logger.info(f'Replaced {k}={v} with {fqdn}')
                conf[k] = fqdn
                continue

        s_common.yamlsave(conf, svcstorage, 'cell.yaml')

        # Generate docker-compose file

        svcdnfo = svcinfo.get('docker')

        svcenv = svcdnfo.get('environment')
        svcenv.setdefault('SYN_LOG_LEVEL', 'DEBUG')
        svcenv.setdefault('SYN_LOG_STRUCT', '1')

        svclabels = {k: v for k, v in default_docker_labels.items()}
        svclabels.update(svcdnfo.get('labels'))
        svccompose = {'environment': svcenv,
                      'image': svcdnfo['image'],
                      'logging': docker_logging,
                      'network_mode': docker_network_mode,
                      'restart': docker_restart,
                      'volumes': ['./storage:/vertex/storage',
                                  './backups:/vertex/backups']}
        if svclabels:
            svccompose['labels'] = svclabels

        svcdc = {
            'services': {
                svcfull: svccompose,
            },
            'version': '3.3'}
        s_common.yamlsave(svcdc, svcroot, 'docker-compose.yaml')

        if svcinfo.get('stormsvc', False):
            stormstr = f'service.add {svcname} {svc_aha_connect}'
            stormsvcs.append(stormstr)

    logger.info('Copying certdir to ahasvcdir')
    shutil.copytree(certdirn, s_common.genpath(ahasvcdir, 'certs'), dirs_exist_ok=True)

    telefp = s_common.genpath(syndir, 'telepath.yaml')
    logger.info(f'Creating telepath.yaml at {telefp}')
    tnfo = {
        'version': 1,
        'aha:servers': [
            aharegistry,
        ]
    }
    s_common.yamlsave(tnfo, telefp)

    if stormsvcs:
        stormfp = s_common.genpath(output_path, 'storm_services.storm')
        logger.info(f'Saving stormservice config to {stormfp}')

        storm = ' | '.join(stormsvcs)
        with s_common.genfile(stormfp) as fd:
            fd.write(storm.encode())

    return 0

def getArgParser():
    desc = 'CLI tool to generate TLS deployments with docker-compose.'
    pars = argparse.ArgumentParser(prog='synapse.tools.infra.gentls', description=desc)

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
