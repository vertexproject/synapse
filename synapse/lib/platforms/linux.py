import os
import logging
import resource
import contextlib
import ctypes as c

import synapse.exc as s_exc

logger = logging.getLogger(__name__)
import synapse.lib.platforms.common as s_pcommon

def initHostInfo():
    return {
        'format': 'elf',
        'platform': 'linux',
        'hasmemlocking': True  # has mlock, and all the below related functions
    }

def getFileMappedRegion(filename):
    '''
    Return a tuple of address and length of a particular file memory mapped into this process
    '''
    # /proc/<pid>/maps has a bunch of entries that look like this:
    # 7fb5195fc000-7fb519ffc000 r--s 00000000 fd:01 5245137                    /tmp/foo.lmdb/data.mdb

    filename = str(filename)
    largest = None
    with open(f'/proc/{os.getpid()}/maps') as maps:
        for line in maps:
            if len(line) < 50:
                continue
            if line.rstrip().endswith(filename):
                addrs = line.split(' ', 1)[0]
                start, end = addrs.split('-')
                start_addr = int(start, 16)
                end_addr = int(end, 16)
                memlen = end_addr - start_addr

                if largest is None or memlen > largest[1]:
                    largest = (start_addr, memlen)

    if largest is None:
        raise s_exc.NoSuchFile(f'{filename} is not mapped into current process')
    return largest

def getTotalMemory():
    '''
    Get the total amount of memory in the system
    '''
    # Unlike /proc/meminfo, this gives a correct value when running inside a memory-limited container
    with open(f'/sys/fs/cgroup/memory/memory.limit_in_bytes') as f:
        return int(f.read())

def getAvailableMemory():
    '''
    Returns the available memory of the system
    '''
    # Prefer MemAvailable over MemFree.  (MemAvailable is not available on older kernels)

    with open(f'/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemFree'):
                free = int(line.split()[1]) * 1024

            elif line.startswith('MemAvailable'):
                return int(line.split()[1]) * 1024

    return free

def getMaxLockedMemory():
    '''
    Returns the maximum amount of memory this process can lock
    '''
    # TODO: consider CAP_IPC_LOCK capability
    _, hard = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    if hard == resource.RLIM_INFINITY:
        return 2**64 - 1
    return hard

def getCurrentLockedMemory():
    '''
    Return the amount of memory this process has locked
    '''
    # Look for lines like: 'Locked:                400 kB' and add them up
    sum = 0
    with open(f'/proc/{os.getpid()}/smaps') as smaps:
        for line in smaps:
            if line.startswith('Locked:'):
                kb = int(line.split()[1])
                sum += kb * 1024

    return sum

def maximizeMaxLockedMemory():
    '''
    Remove any discretionary (i.e. soft) limits
    '''
    soft, hard = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    if soft != hard:
        resource.setrlimit(resource.RLIMIT_MEMLOCK, (hard, hard))

libc = s_pcommon.getLibC()

# int mlock(const void *addr, size_t len);
_mlock = libc.mlock
_mlock.restype = c.c_int
_mlock.argtypes = [c.c_void_p, c.c_size_t]

def mlock(address, length):
    '''
    Lock a chunk of memory to prevent it from being swapped out, raising an OSError on error
    '''
    retn = _mlock(address, length)
    if not retn:
        return
    err = c.get_errno()
    raise OSError(err, os.strerror(err))

# int munlock(const void *addr, size_t len);
_munlock = libc.munlock
_munlock.restype = c.c_int
_munlock.argtypes = [c.c_void_p, c.c_size_t]

def munlock(address, length):
    '''
    Unlock a chunk of memory, raising an OSError on error
    '''
    retn = _munlock(address, length)
    if not retn:
        return
    err = c.get_errno()
    raise OSError(err, os.strerror(err))

# void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
_mmap = libc.mmap
_mmap.restype = c.c_void_p
_mmap.argtypes = [c.c_void_p, c.c_size_t, c.c_int, c.c_int, c.c_int, c.c_ulonglong]

# int munmap(void *addr, size_t length);
_munmap = libc.munmap
_munmap.restype = c.c_int
_munmap.argtypes = [c.c_void_p, c.c_size_t]

@contextlib.contextmanager
def mmap(address, length, prot, flags, fd, offset):
    '''
    A simple mmap context manager that releases the GIL while mapping and unmapping.  It raises an OSError on error
    '''
    baseaddr = _mmap(address, length, prot, flags, fd, offset)
    if baseaddr == -1:
        err = c.get_errno()
        raise OSError(err, os.strerror(err))

    try:
        yield baseaddr
    finally:
        _munmap(baseaddr, length)
