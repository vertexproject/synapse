import os
import logging
import resource

logger = logging.getLogger(__name__)

def initHostInfo():
    return {
        'format': 'macho',
        'platform': 'darwin',
        'hasopenfds': True,
    }

def getOpenFdInfo():
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    usage = len(os.listdir(f'/dev/fd'))
    ret = {'soft_limit': soft_limit, 'hard_limit': hard_limit, 'usage': usage}
    return ret
