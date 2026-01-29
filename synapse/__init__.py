'''
The synapse intelligence analysis framework.
'''

import sys
if (sys.version_info.major, sys.version_info.minor) < (3, 11):  # pragma: no cover
    raise Exception('synapse is not supported on Python versions < 3.11')

# checking maximum *signed* integer size to determine the interpreter arch
if sys.maxsize < 9223372036854775807:  # pragma: no cover
    raise Exception('synapse is only supported on 64 bit architectures')

# Checking if the interpreter is running with -OO - if so, this breaks
# behavior which relies on __doc__ being set.  Warn the user of this
# degraded behavior.  Could affect Cli, Cmdr, Cortex, and other components.
if sys.flags.optimize >= 2:
    import warnings
    mesg = '''Synapse components may experience degraded capabilities with sys.flags.optimize >=2.'''
    warnings.warn(mesg, RuntimeWarning)

import lmdb
if tuple([int(x) for x in lmdb.__version__.split('.')]) < (1, 0, 0):  # pragma: no cover
    raise Exception('synapse is only supported on version >= 1.0.0 of the lmdb python module')

from synapse.lib.version import version, verstring
# Friendly __version__ string alias
__version__ = verstring
