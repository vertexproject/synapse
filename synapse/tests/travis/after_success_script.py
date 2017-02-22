
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
    os.environ['REPO'] = 'vertexproject/synapse'
    env = os.environ

    build_cmds = (
        ['docker', 'build', '-f', 'synapse/docker/synapse_dockerfile', '-t', '$REPO:$COMMIT', '.'],
        ['docker', 'tag', '$REPO:$COMMIT', '$REPO:$TAG'],
        ['docker', 'push', '$REPO']
    )
    current_branch = os.getenv('TRAVIS_BRANCH')
    current_tag = os.getenv('TRAVIS_TAG')
    tags = []

    if current_branch == 'master':
        tags.append('latest')

    if current_tag:
        tags.append(current_tag.strip())
    print('tags', tags)

    if not tags:
        print('docker build not required')
        sys.exit(0)

    subprocess.check_call(['docker', 'login', '-e', '$DOCKER_EMAIL', '-u', '$DOCKER_USER', '-p', '$DOCKER_PASS'], env=env)
    for tag in tags:
        for cmd in build_cmds:
            print('run: %r' % cmd)
            subprocess.check_call(cmd, env=env)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
