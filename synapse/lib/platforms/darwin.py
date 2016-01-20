import platform

if platform.system().lower() == 'darwin':
    # darwin only code goes here...
    pass

def _initHostInfo(ret):
    ret['format'] = 'macho'
    ret['platform'] = 'darwin'
