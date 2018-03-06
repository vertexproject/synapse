#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='synapse',
    version='0.0.46',
    description='Synapse Distributed Key-Value Hypergraph Analysis Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['*.tests',
                                    '*.tests.*',
                                    'scripts',
                                    ]),

    include_package_data=True,

    install_requires=[
        'tornado>=3.2.2,<5.0.0',
        'pyOpenSSL>=16.2.0,<18.0.0',
        'msgpack==0.5.1',
        'xxhash>=1.0.1,<2.0.0',
        'lmdb>=0.92,<1.0.0',
        'regex>=2017.9.23'
    ],

    classifiers=[
        'Development Status :: 4 - Beta',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',

        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
