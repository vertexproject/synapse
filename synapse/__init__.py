'''
The synapse distributed computing framework.
'''
import msgpack
import tornado

if msgpack.version < (0,4,2):
    raise Exception('synapse requires msgpack >= 0.4.2')

if tornado.version_info < (3,2):
    raise Exception('synapse requires tornado >= 3.2')

version = (0,0,8)
verstring = '.'.join([ str(x) for x in version ])

import synapse.lib.modules as s_modules

# load all the synapse builtin modules
s_modules.load('synapse.models.syn')
s_modules.load('synapse.models.dns')
s_modules.load('synapse.models.orgs')
s_modules.load('synapse.models.inet')
s_modules.load('synapse.models.mime')
s_modules.load('synapse.models.telco')
s_modules.load('synapse.models.crypto')
s_modules.load('synapse.models.geopol')
s_modules.load('synapse.models.temporal')
s_modules.load('synapse.models.geospace')
