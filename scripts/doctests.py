#!/usr/bin/env python

# Ensure rstorm execute properly.
# Check the changelog files for valid yaml, no multiline scalars, schema validation

import os
import re
import sys
import traceback
import subprocess

import yaml

basepath = os.path.split(__file__)[0]
# Inject the synapse directory into sys.path
sys.path.append(basepath + '/../')
docspath = os.path.abspath(os.path.join(basepath, '../docs'))
tmplpath = os.path.join(docspath, 'vertex')

changlogpath = os.path.join(basepath, '../changes')

try:
    import synapse.lib.schemas as s_schemas
except ImportError:
    print('Failed to import synapse schemas module')
    s_schemas = None

def check_rstorm(dirn):
    env = {**os.environ, 'SYN_LOG_LEVEL': 'DEBUG'}

    for fdir, dirs, fns in os.walk(dirn):
        if '.ipynb_checkpoints' in dirs:
            dirs.remove('.ipynb_checkpoints')
        if '_build' in dirs:
            dirs.remove('_build')
        for fn in fns:
            if fn.endswith('.rstorm'):

                oname = fn.rsplit('.', 1)[0]
                oname = oname + '.rst'
                sfile = os.path.join(fdir, fn)
                ofile = os.path.join(fdir, oname)

                args = ['python', '-m', 'synapse.tools.rstorm', '--save', ofile, sfile]

                try:
                    supb = subprocess.run(args, capture_output=True, timeout=60, check=True, env=env)
                except Exception as e:
                    raise
                else:
                    print(f'Ran {ofile} successfully.')

def check_changelogs(dirn):
    # Ensure all changelog files are valid yaml and do not contain multiline scalars
    for fn in os.listdir(dirn):
        if not fn.endswith('.yaml'):
            continue
        fp = os.path.abspath(os.path.join(dirn, fn))
        print(f'Checking {fp}')
        with open(fp, 'rb') as fd:
            bytz = fd.read()
        # Do we have multi-line scalers?
        if re.findall(r'[a-z0-9]\:\s+\|\s*\n', bytz.decode('utf8'), flags=re.IGNORECASE):
            raise ValueError(f'multiline scaler detected in {fp}')
        # Just asserting we are valid yaml to start with.
        data = yaml.load(bytz, yaml.SafeLoader)
        # And validate the schema.
        if s_schemas is not None:
            s_schemas._reqChanglogSchema(data)

def main():

    try:
        check_rstorm(docspath)
    except subprocess.CalledProcessError as e:
        print(f'Error executing rstorm: {str(e)}')
        print(f'Stdout:\n{e.stdout.decode()}')
        print(f'Stderr:\n{e.stderr.decode()}')
        return 1
    except:
        traceback.print_exc()
        return 1

    try:
        check_changelogs(changlogpath)
    except Exception:
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
