#!/usr/bin/env python

# Execute ipython notebooks under ../docs/ to ensure they all execute properly

import os
import sys
import traceback
import subprocess

basepath = os.path.split(__file__)[0]
docspath = os.path.abspath(os.path.join(basepath, '../docs'))
tmplpath = os.path.join(docspath, 'vertex')

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

    return 0


if __name__ == '__main__':
    sys.exit(main())
