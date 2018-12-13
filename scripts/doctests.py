#!/usr/bin/env python

# Execute ipython notebooks under ../docs/ to ensure they all execute properly

import os
import sys
import traceback
import subprocess

basepath = os.path.split(__file__)[0]
docspath = os.path.abspath(os.path.join(basepath, '../docs'))
tmplpath = os.path.join(docspath, 'vertex.tpl')

def check_ipynb(dirn):
    for fdir, dirs, fns in os.walk(dirn):
        if '.ipynb_checkpoints' in dirs:
            dirs.remove('.ipynb_checkpoints')
        if '_build' in dirs:
            dirs.remove('_build')
        for fn in fns:
            if fn.endswith('.ipynb'):
                fp = os.path.join(fdir, fn)
                # base args
                args = ['jupyter', 'nbconvert', '--debug', '--execute', ]
                # output control
                args.extend(['--stdout', '--to', 'rst', '--template', tmplpath, ])
                # Our file
                args.extend([fp])
                print(f'executing: {" ".join(args)}')
                try:
                    subp = subprocess.run(args, capture_output=True, timeout=60, check=True)
                except Exception as e:
                    raise
                else:
                    print(f'Ran notebook successfully.')
    return 0

def main():
    try:
        return check_ipynb(docspath)
    except subprocess.CalledProcessError as e:
        print(f'Error executing notebook: {str(e)}')
        print(f'Stdout:\n{e.stdout.decode()}')
        print(f'Stderr:\n{e.stderr.decode()}')
        return 1
    except:
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
