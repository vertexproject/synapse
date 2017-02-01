
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
            'docker build -t vertexproject/synapse -f synapse/docker/synapse_dockerfile .',
            'docker build -t vertexproject/core_ram -f synapse/docker/cortex/ram_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_ram vertexproject/core_ram',
            'docker exec core_ram python -m pip install nose coverage coveralls',
        ]
    elif core == 'sqlite':
        cmds = [
            'docker build -t vertexproject/synapse -f synapse/docker/synapse_dockerfile .',
            'docker build -t vertexproject/core_sqlite -f synapse/docker/cortex/sqlite_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_sqlite vertexproject/core_sqlite',
            'docker exec core_sqlite python -m pip install nose coverage coveralls',
        ]
    elif core == 'postgres':
        cmds = [
            'docker build -t vertexproject/core_pg -f synapse/docker/cortex/postgres_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_pg vertexproject/core_pg',
            'docker exec core_pg python3 -m pip install nose coverage coveralls',
        ]

    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

