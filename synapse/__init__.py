'''
The synapse distributed key-value hypergraph analysis framework.
'''

import sys
if (sys.version_info.major, sys.version_info.minor) < (3, 6):  # pragma: no cover
    raise Exception('synapse is not supported on Python versions < 3.6')

# checking maximum *signed* integer size to determine the interpreter arch
if sys.maxsize < 9223372036854775807:  # pragma: no cover
    raise Exception('synapse is only supported on 64 bit architectures')

import lmdb
if tuple([int(x) for x in lmdb.__version__.split('.')]) < (0, 94): # pragma: no cover
    raise Exception('synapse is only supported on version 0.94 of the lmdb python module')

import multiprocessing

import msgpack
if msgpack.version != (0, 5, 1):  # pragma: no cover
    raise Exception('synapse requires msgpack == 0.5.1')

import synapse.glob as s_glob  # setup glob here to avoid import loops...
import synapse.lib.plex as s_plex
import synapse.lib.threads as s_threads

tmax = multiprocessing.cpu_count() * 8

s_glob.plex = s_plex.Plex()
s_glob.pool = s_threads.Pool(maxsize=tmax)
