
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

    syn_docker = os.environ.get('SYN_DOCKER')

    cmds = [
        #'nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse',
    ]
    if syn_docker:
        cmds = [
            #'docker exec core_ram /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
            #'docker exec core_sqlite /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
            #'docker exec core_pg /bin/bash -c "SYN_TEST_PG_DB=syn_test SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
            #'docker exec synapse_27 /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
            #'docker exec synapse_35 /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
            'docker exec synapse_36 /bin/bash -c "SYN_DOCKER=1 nosetests --verbosity=3 --with-coverage --cover-erase --cover-package=synapse"',
        ]
    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        if proc.returncode != 0:
            return proc.returncode

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

