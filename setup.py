#!/usr/bin/env python
from setuptools import setup,find_packages


setup(
    name='synapse',
    version='0.0.18', # sync with synapse.version!
    description='Synapse Distributed Key-Value Hypergraph Analysis Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['*.tests','*.tests.*']),

    include_package_data=True,

    install_requires=[
        'tornado>=3.2.2',
        'cryptography>=1.7.2',
        'pyOpenSSL>=16.2.0',
        'msgpack-python>=0.4.2',
    ],

    classifiers=[
        'Development Status :: 4 - Beta',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
