import os
import logging

logger = logging.getLogger(__name__)

def initHostInfo():
    return {
        'format': 'elf',
        'platform': 'linux',
    }


def getMappedAddress(filename):
    '''
    Return the address and length of a particular file memory mapped into this process
    '''
    # /proc/<pid>/maps has a bunch of entries that look like this:
    # 7fb5195fc000-7fb519ffc000 r--s 00000000 fd:01 5245137                    /tmp/foo.lmdb/data.mdb

    filename = str(filename)
    with open(f'/proc/{os.getpid()}/maps') as smaps:
        for line in smaps:
            if len(line) < 50:
                continue
            if line.rstrip().endswith(filename):
                addrs = line.split(' ', 1)[0]
                start, end = addrs.split('-')
                start_addr = int(start, 16)
                end_addr = int(end, 16)
                return start_addr, end_addr - start_addr
    return None, None
