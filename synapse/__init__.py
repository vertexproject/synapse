'''
The synapse distributed key-value hypergraph analysis framework.
'''

import sys
if (sys.version_info.major, sys.version_info.minor) < (3, 7):  # pragma: no cover
    raise Exception('synapse is not supported on Python versions < 3.7')

# checking maximum *signed* integer size to determine the interpreter arch
if sys.maxsize < 9223372036854775807:  # pragma: no cover
    raise Exception('synapse is only supported on 64 bit architectures')

import lmdb
if tuple([int(x) for x in lmdb.__version__.split('.')]) < (0, 94): # pragma: no cover
    raise Exception('synapse is only supported on version >= 0.94 of the lmdb python module')

from synapse.lib.version import version, verstring
