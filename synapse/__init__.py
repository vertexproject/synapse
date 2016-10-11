'''
The synapse distributed computing framework.
'''
import msgpack
import tornado

if msgpack.version < (0,4,2):
    raise Exception('synapse requires msgpack >= 0.4.2')

if tornado.version_info < (3,2):
    raise Exception('synapse requires tornado >= 3.2')

version = (0,0,7)

