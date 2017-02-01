
import os
import sys
import argparse
import subprocess

def parse_args(argv):
    parser = argparse.ArgumentParser()

    args = parser.parse_args(argv)

    return args

def main(argv):
    args = parse_args(argv)


    core = os.environ.get('SYN_TEST_CORE')
    if core == 'ram':
        cmds = [
            'docker exec core_ram /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
        ]
    elif core == 'sqlite':
        cmds = [
            'docker exec core_sqlite /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
        ]
    elif core == 'postgres':
        cmds = [
            'docker exec core_pg /bin/bash -c "SYN_TEST_PG_DB=syn_test SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
        ]
    else:
        cmds = [
            'nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse',
        ]

    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        if proc.returncode != 0:
            return proc.returncode

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

