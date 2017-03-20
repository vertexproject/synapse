'''
The synapse distributed key-value hypergraph analysis framework.
'''
import os
import msgpack
import tornado
import logging

logger = logging.getLogger(__name__)

if msgpack.version < (0,4,2):
    raise Exception('synapse requires msgpack >= 0.4.2')

if tornado.version_info < (3,2,2):
    raise Exception('synapse requires tornado >= 3.2.2')

version = (0,0,12)
verstring = '.'.join([ str(x) for x in version ])

import synapse.lib.modules as s_modules

# load all the synapse builtin modules
s_modules.load('synapse.models.syn')
s_modules.load('synapse.models.dns')
s_modules.load('synapse.models.orgs')
s_modules.load('synapse.models.inet')
s_modules.load('synapse.models.mime')
s_modules.load('synapse.models.files')
s_modules.load('synapse.models.money')
s_modules.load('synapse.models.telco')
s_modules.load('synapse.models.crypto')
s_modules.load('synapse.models.geopol')
s_modules.load('synapse.models.person')
s_modules.load('synapse.models.temporal')
s_modules.load('synapse.models.geospace')
s_modules.load('synapse.models.av')

mods = os.getenv('SYN_MODULES')
if mods:
    for name in mods.split(','):
        try:
            s_modules.load(name)
        except Exception as e:
            logger.warning('SYN_MODULES failed: %s (%s)' % (name,e))
