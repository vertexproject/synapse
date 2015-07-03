#!/usr/bin/env python
#from distutils.core import setup
from setuptools import setup

# For Testing
# python3.4 setup.py register -r https://testpypi.python.org/pypi
# python3.4 setup.py upload -r https://testpypi.python.org/pypi

setup(
    name='viv-synapse-py34',
    version='0.0.1',
    description='Synapse Distributed Computing Framework',
    author='Invisigoth Kenshoto',
    author_email='invisigoth.kenshoto@gmail.com',
    url='https://github.com/vivisect/synapse',

    packages=[
        'synapse',
        'synapse.links',
        'synapse.tools',
        'synapse.bridges',
    ],

    install_requires=[
    #requires=[
        #'python>=3.4',
        'pycrypto>=2.6.2',
        'msgpack-python>=0.4.2',
    ],

    classifiers=[
    ],

)
