
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

    if os.environ.get('SYN_PY27'):
        cmds = [
            'docker build -t vertexproject/synapse_27 -f synapse/docker/synapse_dockerfile_py27 .',
            'docker run -d -p 127.0.0.1:47322:47322 --name synapse_27 vertexproject/synapse_27',
            'docker exec synapse_27 python -m pip install nose coverage coveralls',
        ]
    if os.environ.get('SYN_PY35'):
        cmds = [
            'docker build -t vertexproject/synapse_35 -f synapse/docker/synapse_dockerfile_py35 .',
            'docker run -d -p 127.0.0.1:47322:47322 --name synapse_35 vertexproject/synapse_35',
            'docker exec synapse_35 python -m pip install nose coverage coveralls',
        ]
    if os.environ.get('SYN_PY36'):
        cmds = [
            'docker build -t vertexproject/synapse_36 -f synapse/docker/synapse_dockerfile_py36 .',
            'docker run -d -p 127.0.0.1:47322:47322 --name synapse_36 vertexproject/synapse_36',
            'docker exec synapse_36 python -m pip install nose coverage coveralls',
        ]
    if os.environ.get('SYN_CORE_RAM'):
        cmds = [
            'docker build -t vertexproject/core_ram -f synapse/docker/cortex/ram_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_ram vertexproject/core_ram',
            'docker exec core_ram python -m pip install nose coverage coveralls',
        ]
    if os.environ.get('SYN_CORE_SQLITE'):
        cmds = [
            'docker build -t vertexproject/core_sqlite -f synapse/docker/cortex/sqlite_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_sqlite vertexproject/core_sqlite',
            'docker exec core_sqlite python -m pip install nose coverage coveralls',
        ]
    if os.environ.get('SYN_CORE_PG95'):
        cmds = [
            'docker build -t vertexproject/core_pg95 -f synapse/docker/cortex/postgres_9.5_dockerfile .',
            'docker run -d -p 127.0.0.1:47322:47322 --name core_pg95 vertexproject/core_pg95',
            'docker exec core_pg95 python3 -m pip install nose coverage coveralls',
        ]

    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

