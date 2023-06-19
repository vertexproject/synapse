#!/usr/bin/env python
import os
import sys
import subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install

VERSION = '2.139.0'

class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG', '')
        tag = tag.lstrip('v')

        if tag != VERSION:
            info = f"Git tag: {tag} does not match the version of this app: {VERSION}"
            sys.exit(info)

class ReplaceCommitVersion(install):
    description = 'Replace the embedded commit information with our current git commit'
    def run(self):
        try:
            ret = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                 capture_output=True,
                                 timeout=15,
                                 check=False,
                                 text=True,
                                 )
        except Exception as e:
            print(f'Error grabbing commit: {e}')
            return 1
        else:
            commit = ret.stdout.strip()
        fp = './synapse/lib/version.py'
        with open(fp, 'rb') as fd:
            buf = fd.read()
        content = buf.decode()
        new_content = content.replace("commit = ''", f"commit = '{commit}'")
        if content == new_content:
            print(f'Unable to insert commit into {fp}')
            return 1
        with open(fp, 'wb') as fd:
            _ = fd.write(new_content.encode())
        print(f'Inserted commit {commit} into {fp}')
        return 0

setup()
