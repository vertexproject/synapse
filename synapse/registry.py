'''
A run-time registry for synapse elements.
'''
import synapse.cortex as s_cortex
import synapse.lib.service as s_service

# service type names
services = {
    'echo': s_service.Service,
    'cortex': s_cortex.Cortex,
}

def addService(name, ctor):
    '''
    Add a service type constructor.
    '''
    services[name] = ctor

def getService(name):
    '''
    Get a service constructor by name.
    '''
    return self.services.get(name)
