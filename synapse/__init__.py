'''
The synapse distributed key-value hypergraph analysis framework.
'''
import sys
import msgpack
import tornado
import logging
import multiprocessing

logger = logging.getLogger(__name__)

if (sys.version_info.major, sys.version_info.minor) < (3, 6):  # pragma: no cover
    raise Exception('synapse is not supported on Python versions < 3.6')

if msgpack.version < (0, 5, 0):  # pragma: no cover
    raise Exception('synapse requires msgpack >= 0.5.0')

if tornado.version_info < (3, 2, 2):  # pragma: no cover
    raise Exception('synapse requires tornado >= 3.2.2')

# setup glob here to avoid import loops...
import synapse.glob as s_glob
import synapse.lib.plex as s_plex
import synapse.lib.threads as s_threads

tmax = multiprocessing.cpu_count() * 8

s_glob.plex = s_plex.Plex()
s_glob.pool = s_threads.Pool(maxsize=tmax)
