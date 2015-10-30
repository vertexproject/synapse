#!/usr/bin/env python
#from distutils.core import setup
from setuptools import setup,find_packages

# For Testing:
#
# python3.4 setup.py register -r https://testpypi.python.org/pypi
# python3.4 setup.py bdist_wheel upload -r https://testpypi.python.org/pypi
# python3.4 -m pip install -i https://testpypi.python.org/pypi
#
# For Realz:
#
# python3.4 setup.py register
# python3.4 setup.py bdist_wheel upload
# python3.4 -m pip install
import synapse
import synapse.common as s_common

setup(
    name='viv-synapse',
    version=s_common.verstr( synapse.version ),
    description='Synapse Distributed Computing Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vivisect/synapse',
    license='Apache License 2.0',

    packages=find_packages(exclude=['*.tests','*.tests.*']),

    install_requires=[
        'tornado',
        'requests',
        'pycrypto>=2.6.1',
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
