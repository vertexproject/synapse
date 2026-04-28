import os
import errno
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
    try:
        usage = len(os.listdir(f'/dev/fd'))
    except OSError as err:
        if err.errno == errno.EMFILE:
            # We've hit the maximum allowed files and cannot list contents of /proc/;
            # so we set usage to soft_limit so the caller can know that we're exactly at the limit.
            usage = soft_limit
        else:
            raise
    ret = {'soft_limit': soft_limit, 'hard_limit': hard_limit, 'usage': usage}
    return ret
