'''
The synapse distributed computing framework.
'''
import msgpack
if msgpack.version < (0,4,2):
    raise Exception('synapse requires msgpack >= 0.4.2')

version = (0,0,5)

