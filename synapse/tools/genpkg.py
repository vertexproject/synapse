import os
import sys
import json
import base64
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

def chopSemVer(vers):
    return tuple([int(x) for x in vers.split('.')])

def loadOpticFiles(pkgdef, path):

    pkgfiles = pkgdef['optic']['files']

    abspath = s_common.genpath(path)
    for root, dirs, files, in os.walk(path):

        for name in files:

            if name.startswith('.'): # pragma: no cover
                continue

            fullname = s_common.genpath(root, name)
            if not os.path.isfile(fullname): # pragma: no cover
                continue

            pkgfname = fullname[len(abspath) + 1:]

            with open(fullname, 'rb') as fd:
                pkgfiles[pkgfname] = {
                    'file': base64.b64encode(fd.read()).decode(),
                }

def loadPkgProto(path, opticdir=None):

    full = s_common.genpath(path)
    pkgdef = s_common.yamlload(full)

    if isinstance(pkgdef['version'], str):
        pkgdef['version'] = chopSemVer(pkgdef['version'])

    protodir = os.path.dirname(full)

    for mod in pkgdef.get('modules', ()):
        name = mod.get('name')
        with s_common.genfile(protodir, 'storm', 'modules', name) as fd:
            mod['storm'] = fd.read().decode()

    for cmd in pkgdef.get('commands', ()):
        name = cmd.get('name')
        with s_common.genfile(protodir, 'storm', 'commands', name) as fd:
            cmd['storm'] = fd.read().decode()

    if opticdir is None:
        opticdir = s_common.genpath(protodir, 'optic')

    if os.path.isdir(opticdir):
        pkgdef.setdefault('optic', {})
        pkgdef['optic'].setdefault('files', {})
        loadOpticFiles(pkgdef, opticdir)

    return pkgdef


prog = 'synapse.tools.genpkg'
desc = 'A tool for generating/pushing storm packages from YAML prototypes.'

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser()
    pars.add_argument('--push', metavar='<url>', help='A telepath URL of a Cortex or PkgRepo.')
    pars.add_argument('--save', metavar='<path>', help='Save the completed package JSON to a file.')
    pars.add_argument('--optic', metavar='<path>', help='Load Optic module files from a directory.')
    pars.add_argument('pkgfile', metavar='<pkgfile>', help='Path to a storm package prototype yml file.')

    opts = pars.parse_args(argv)

    pkgdef = loadPkgProto(opts.pkgfile, opticdir=opts.optic)

    if opts.save:
        with s_common.genfile(opts.save) as fd:
            fd.write(json.dumps(pkgdef).encode())

    if opts.push:

        path = s_common.genpath('~/.syn/telepath.yaml')
        fini = await s_telepath.loadTeleEnv(path)

        async with await s_telepath.openurl(opts.push) as core:
            await core.addStormPkg(pkgdef)

        if fini is not None: # pragma: no cover
            await fini()

if __name__ == '__main__': # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
