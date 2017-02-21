#!/usr/bin/env python
from setuptools import setup,find_packages

# For Testing:
#
# python setup.py bdist_wheel upload -r https://testpypi.python.org/pypi
# python -m pip install synapse -i https://testpypi.python.org/pypi
#
# For Realz:
#
# python setup.py bdist_wheel upload
# python -m pip install synapse

setup(
    name='synapse',
    version='0.0.10', # sync with synapse.version!
    description='Synapse Distributed Computing Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vertexproject/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['*.tests','*.tests.*']),

    install_requires=[
        'tornado>=3.2',
        'cryptography>=1.1.2',
        'pyOpenSSL>=16.2.0',
        'msgpack-python>=0.4.2',
    ],

    classifiers=[
        'Development Status :: 4 - Beta',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',
    ],

)
