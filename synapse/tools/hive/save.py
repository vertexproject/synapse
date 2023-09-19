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

    pars = argparse.ArgumentParser(prog='synapse.tools.hive.save',
                                   description='Save tree data from a remote hive to file.')

    pars.add_argument('--path', default=None, help='A hive path string to use as the root.')
    pars.add_argument('--yaml', default=False, action='store_true', help='Parse the savefile as a YAML file (default: msgpack)')

    pars.add_argument('hiveurl', help='The telepath URL for the remote hive.')
    pars.add_argument('filepath', help='The local file path to save.')

    opts = pars.parse_args(argv)

    path = ()
    if opts.path is not None:
        path = opts.path.split('/')

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.hiveurl) as hive:
            try:
                s_version.reqVersion(hive._getSynVers(), reqver)
            except s_exc.BadVersion as e:
                valu = s_version.fmtVersion(*e.get('valu'))
                outp.printf(f'Hive version {valu} is outside of the hive.save supported range ({reqver}).')
                outp.printf(f'Please use a version of Synapse which supports {valu}; current version is {s_version.verstring}.')
                return 1

            tree = await hive.saveHiveTree(path=path)

    if opts.yaml:
        s_common.yamlsave(tree, opts.filepath)
    else:
        s_msgpack.dumpfile(tree, opts.filepath)

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
