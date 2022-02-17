import os
import sys
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
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

# FIXME - set the correct version prior to release.
# reqver = '>=2.26.0,<3.0.0'

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
    aharegistry_template = f'ssl://{{name}}@{ahadnsname}:{ahaport}/'

    ahaconf = {
        'https:port': None,
        'aha:admin': ahaadmin,
        'aha:network': ahanetwork,
        'dmon:listen': ahadmonlisten,
        'nexslog:en': ahanexuslog
    }

    aharoot = s_common.genpath(output_path, 'aha')
    ahasvcdir = s_common.genpath(aharoot, 'svcdata', 'aha')

    ahadc = {'services': {'aha': {'environment': ['SYN_LOG_LEVEL=DEBUG',
                                                  'SYN_LOG_STRUCT=1'],
                                  'image': 'vertexproject/synapse-aha:v2.x.x',
                                  'logging': {'driver': 'json-file',
                                              'options': {'max-file': '1',
                                                          'max-size': '100m'}},
                                  'network_mode': 'host',
                                  'volumes': ['./svcdata/aha:/vertex/storage',
                                              './backups/aha:/vertex/backups']}},
             'version': '3.3'}
    s_common.yamlsave(ahadc, aharoot, 'docker-compose.yaml')
    s_common.yamlsave(ahaconf, ahasvcdir, 'cell.yaml')

    _tempconf = {
        'dmon:listen': None
    }
    # We'll end up using the backup tool to
    with s_common.getTempDir() as dirn:
        async with await s_aha.AhaCell.anit(dirn=ahasvcdir,
                                            conf=_tempconf) as aha:  # type: s_aha.AhaCell
            # Smash the svcdir in directly
            ahaconf['backup:dir'] = '/vertex/storage'
            s_common.yamlsave(ahaconf, ahasvcdir, 'cell.yaml')

            for svc in definition.get('svcs', ()):


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
