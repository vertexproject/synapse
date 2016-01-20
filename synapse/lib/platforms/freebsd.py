import platform

if platform.system().lower() == 'freebsd':
    # freebsd only code goes here...
    pass

def _initHostInfo(ret):
    ret['format'] = 'elf'
    ret['platform'] = 'freebsd'
