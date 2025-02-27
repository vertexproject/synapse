import os
import sys
import argparse

import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

def getArgParser():
    pars = argparse.ArgumentParser(description='Convert files from json lines to msgpack')
    pars.add_argument('--rm', action='store_true', help='Remove json files once the conversion is complete')
    pars.add_argument('paths', nargs='+', help='json files or directories full of json files')
    return pars

def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = getArgParser()
    opts = pars.parse_args(argv)

    for path in opts.paths:

        if not path.endswith('.json'):
            outp.printf('skip: %s (not .json extension)' % (path,))
            continue

        if not os.path.isfile(path):
            outp.printf('skip: %s (not a file)' % (path,))
            continue

        base = path[:-5]
        newp = base + '.mpk'

        outp.printf('converting: %s -> .mpk' % (path,))
        with open(path, 'r', encoding='utf8') as fd:
            with open(newp, 'wb') as pk:
                for line in fd:
                    item = s_json.loads(line)
                    pk.write(s_msgpack.en(item))

        if opts.rm:
            os.unlink(path)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
