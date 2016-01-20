import ctypes

if getattr(ctypes,'windll',None):
    # windows specific code may live in here...
    pass

def _initHostInfo(ret):
    ret['format'] = 'pe'
    ret['platform'] = 'windows'
