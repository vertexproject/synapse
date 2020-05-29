import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

reqver = '>=0.2.0,<3.0.0'

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.hive.load',
                                   description='Load data into a remote hive from a previous hivesave.')

    pars.add_argument('--trim', default=False, action='store_true', help='Trim all other hive nodes (DANGER!)')
    pars.add_argument('--path', default=None, help='A hive path string to use as the root.')
    pars.add_argument('--yaml', default=False, action='store_true',
                      help='Parse the savefile as a YAML file (default: msgpack)')

    pars.add_argument('hiveurl', help='The telepath URL for the remote hive.')
    pars.add_argument('filepath', help='The local file path to load.')

    opts = pars.parse_args(argv)

    if opts.yaml:
        tree = s_common.yamlload(opts.filepath)
    else:
        tree = s_msgpack.loadfile(opts.filepath)

    path = ()
    if opts.path is not None:
        path = opts.path.split('/')

    async with await s_telepath.openurl(opts.hiveurl) as hive:
        classes = hive.sharinfo.get('classes', ())

        try:
            s_version.reqVersion(hive._getSynVers(), reqver)
            if 'synapse.lib.hive.HiveApi' in classes:
                await hive.loadHiveTree(tree, path=path, trim=opts.trim)
            else:
                todo = s_common.todo('loadHiveTree', tree, path=path, trim=opts.trim)
                await hive.dyncall('cell', todo)

        except s_exc.BadVersion as e:
            valu = s_version.fmtVersion(*e.get('valu'))
            outp.printf(f'Hive version {valu} is outside of the hive.load supported range ({reqver}).')
            outp.printf(
                f'Please use a version of Synapse which supports {valu}; current version is {s_version.verstring}.')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
