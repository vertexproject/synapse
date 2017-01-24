
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

    if not syn_docker:
        return

    cmds = [
        'docker build -t vertexproject/synapse -f synapse/docker/synapse_dockerfile .',
        'docker build -t vertexproject/core_ram -f synapse/docker/cortex/ram_dockerfile .',
        'docker build -t vertexproject/core_sqlite -f synapse/docker/cortex/sqlite_dockerfile .',
        'docker build -t vertexproject/core_pg -f synapse/docker/cortex/postgres_9.5_dockerfile .',
        'docker build -t vertexproject/synapse_27 -f synapse/docker/synapse_dockerfile_py27 .',
        'docker build -t vertexproject/synapse_35 -f synapse/docker/synapse_dockerfile_py35 .',
        'docker build -t vertexproject/synapse_36 -f synapse/docker/synapse_dockerfile_py36 .',
        'docker run -d -p 127.0.0.1:47000:47322 --name core_ram vertexproject/core_ram',
        'docker run -d -p 127.0.0.1:47001:47322 --name core_sqlite vertexproject/core_sqlite',
        'docker run -d -p 127.0.0.1:47002:47322 --name core_pg vertexproject/core_pg',
        'docker run -d -p 127.0.0.1:47003:47322 --name synapse_27 vertexproject/synapse_27',
        'docker run -d -p 127.0.0.1:47004:47322 --name synapse_35 vertexproject/synapse_35',
        'docker run -d -p 127.0.0.1:47005:47322 --name synapse_36 vertexproject/synapse_36',
        'docker exec core_ram python3 -m pip install nose coverage coveralls',
        'docker exec core_sqlite python3 -m pip install nose coverage coveralls',
        'docker exec core_pg python3 -m pip install nose coverage coveralls',
        'docker exec synapse_27 python -m pip install nose coverage coveralls',
        'docker exec synapse_35 python -m pip install nose coverage coveralls',
        'docker exec synapse_36 python -m pip install nose coverage coveralls',
    ]
    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

