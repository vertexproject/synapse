
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
        'docker ps | grep -q core_ram',
        'docker ps | grep -q core_sqlite',
        'docker ps | grep -q core_pg',
        'nc -v -w 4 127.0.0.1 47320',
        'nc -v -w 4 127.0.0.1 47321',
        'nc -v -w 8 127.0.0.1 47322',
    ]
    for cmd in cmds:
        print('run: %r' % (cmd,))
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

