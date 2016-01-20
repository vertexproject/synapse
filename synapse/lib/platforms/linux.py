import platform

if platform.system().lower() == 'linux':
    # linux only code goes here...
    pass

def _initHostInfo(ret):
    ret['format'] = 'elf'
    ret['platform'] = 'linux'
