
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
    cmds = []

    core = os.environ.get('SYN_TEST_CORE')
    if core == 'ram':
        cmds = [
            'docker ps | grep -q core_ram',
            'nc -v -w 4 127.0.0.1 47322',
        ]
    elif core == 'sqlite':
        cmds = [
            'docker ps | grep -q core_sqlite',
            'nc -v -w 4 127.0.0.1 47322',
        ]
    elif core == 'postgres':
        cmds = [
            'docker ps | grep -q core_pg',
            'nc -v -w 8 127.0.0.1 47322',
            '''docker exec core_pg /bin/bash -c "psql -c 'create database syn_test;' -U postgres"''',
            '''docker exec core_pg /bin/bash -c "psql -c 'create user root;' -U postgres"''',
        ]

    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

