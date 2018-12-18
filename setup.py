#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='synapse',
    version='0.1.0a2',
    description='Synapse Distributed Key-Value Hypergraph Analysis Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['scripts',
                                    ]),

    include_package_data=True,

    install_requires=[
        'pyOpenSSL>=16.2.0,<18.0.0',
        'msgpack>=0.5.1,<0.6.0',
        'xxhash>=1.0.1,<2.0.0',
        'lmdb>=0.94,<1.0.0',
        'tornado>=5.1,<6.0.0',
        'regex>=2017.9.23',
        'PyYAML>=3.13,<4.0',
    ],

    extras_require={
        'docs': [
            'sphinx>=1.8.2,<2.0.0',
            'jupyter>=1.0.0,<2.0.0',
            'hide-code>=0.5.2,<1.0.0',
            'nbstripout>=0.3.3,<1.0.0',
            'sphinx-rtd-theme>=0.4.2,<1.0.0',
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
