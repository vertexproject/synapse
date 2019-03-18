#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='synapse',
    version='0.1.0',
    description='Synapse Hypergraph Analysis Framework',
    author='The Vertex Project LLC',
    author_email='synapse@vertex.link',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['scripts',
                                    ]),

    include_package_data=True,

    install_requires=[
        'pyOpenSSL>=16.2.0,<20.0.0',
        'msgpack>=0.6.1,<0.7.0',
        'xxhash>=1.0.1,<2.0.0',
        'lmdb>=0.94,<1.0.0',
        'tornado>=5.1,<6.0.0',
        'regex>=2017.9.23',
        'PyYAML>=5.1,<6.0',
        'aiohttp>=3.5.4,<4.0',
        'prompt-toolkit>=2.0.7,<2.1.0',
    ],

    extras_require={
        'docs': [
            'sphinx>=1.8.2,<2.0.0',
            'jupyter>=1.0.0,<2.0.0',
            'hide-code>=0.5.2,<1.0.0',
            'nbstripout>=0.3.3,<1.0.0',
            'sphinx-rtd-theme>=0.4.2,<1.0.0',
        ],
        'dev': [
            'pytest>=4.0.0,<5.0.0',
            'autopep8>=1.4.3,<2.0.0',
            'pytest-cov>=2.6.0,<3.0.0',
            'pycodestyle>=2.4.0,<3.0.0',
            'pytest-xdist>=1.25.0,<2.0.0',
        ],
    },

    classifiers=[
        'Development Status :: 4 - Beta',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',

        'Programming Language :: Python :: 3.7',
    ],
)
