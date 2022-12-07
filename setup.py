#!/usr/bin/env python
import os
import sys
import subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install

VERSION = '2.115.1'

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


long_description_content_type = None
long_description = None
readme = './README.rst'
if os.path.exists(readme):

    print(f'Adding {readme} contents as the long description.')

    with open('./README.rst', 'rb') as fd:
        buf = fd.read()
    long_description = buf.decode()
    long_description_content_type = 'text/x-rst'

setup(
    name='synapse',
    version=VERSION,
    description='Synapse Intelligence Analysis Framework',
    long_description=long_description,
    long_description_content_type=long_description_content_type,
    author='The Vertex Project LLC',
    author_email='synapse@vertex.link',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['scripts',
                                    ]),

    include_package_data=True,

    install_requires=[
        'pyOpenSSL>=21.0.0,<23.0.0',
        'cryptography>=36.0.0,<39.0.0',
        'msgpack>=1.0.2,<1.1.0',
        'xxhash>=1.4.4,<3.1.0',
        'lmdb>=1.2.1,<1.4.0',
        'tornado>=6.1.0,<7.0.0',
        'regex>=2022.9.11',
        'PyYAML>=5.4,<6.1.0',
        'aiohttp>=3.8.1,<4.0',
        'aiohttp-socks>=0.6.1,<0.7.0',
        'aioimaplib>=1.0.1,<1.1.0',
        'aiosmtplib>=1.1.7,<2.0',
        'prompt-toolkit>=3.0.4,<3.1.0',
        'lark==1.1.2',
        'Pygments>=2.7.4,<2.13.0',
        'packaging>=20.0,<22.0',
        'fastjsonschema>=2.15.3,<2.16',
        'stix2-validator>=3.0.0,<4.0.0',
        'vcrpy>=4.1.1,<4.2.0',
        'base58>=2.1.0,<2.2.0',
        'python-bitcoinlib==0.11.0',
        'pycryptodome>=3.11.0,<3.17.0',
        'typing-extensions>=3.7.4,<5.0.0',  # synapse.vendor.xrpl req
        'scalecodec>=1.0.2,<1.0.38',  # synapse.vendor.substrateinterface req
        'cbor2>=5.4.1,<5.4.6',
        'bech32==1.2.0',
        'oauthlib>=3.2.1,<4.0.0',
        'idna==3.3',
        'python-dateutil>=2.8,<3.0',
        'pytz>=2021.3,<2022.2',
        'beautifulsoup4[html5lib]>=4.11.1,<5.0',
    ],

    extras_require={
        'docs': [
            'nbconvert==5.6.1',
            'jupyter-client<=6.1.12',
            'jupyter>=1.0.0,<2.0.0',
            'hide-code>=0.5.2,<0.5.3',
            'nbstripout>=0.3.3,<1.0.0',
            'sphinx>=4.2.0,<5.0.0',
            'sphinx-rtd-theme>=1.0.0,<2.0.0',
            'sphinx-notfound-page==0.8',
            'jinja2<3.1.0',
        ],
        'dev': [
            'pytest>=7.2.0,<8.0.0',
            'autopep8>=1.5.4,<2.0.0',
            'pytest-cov>=4.0.0,<5.0.0',
            'pycodestyle>=2.8.0,<3.0.0',
            'bump2version>=1.0.1,<1.1.0',
            'pytest-xdist>=3.0.2,<4.0.0',
            'coverage>=6.5.0,<7.0.0',
        ],
    },

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',

        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    cmdclass={
        'verify': VerifyVersionCommand,
        'setcommit': ReplaceCommitVersion,
    },
)
