import io
import os
import sys
import json
import time
import fcntl
import types
import base64
import fnmatch
import hashlib
import logging
import binascii
import builtins
import functools
import itertools
import threading
import traceback
import contextlib
import collections

import regex

import synapse.exc as s_exc

from synapse.exc import *

import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

major = sys.version_info.major
minor = sys.version_info.minor
micro = sys.version_info.micro

majmin = (major, minor)
version = (major, minor, micro)

class NoValu: pass

novalu = NoValu()

def now():
    '''
    Get the current epoch time in milliseconds.

    This relies on time.time(), which is system-dependent in terms of resolution.

    Examples:
        Get the current time and make a row for a Cortex::

            tick = now()
            row = (someiden, 'foo:prop', 1, tick)
            core.addRows([row])

    Returns:
        int: Epoch time in milliseconds.
    '''
    return int(time.time() * 1000)

def guid(valu=None):
    '''
    Get a 16 byte guid value.

    By default, this is a random guid value.

    Args:
        valu: Object used to construct the guid valu from.  This must be able
            to be msgpack'd.

    Returns:
        str: 32 character, lowercase ascii string.
    '''
    if valu is None:
        return binascii.hexlify(os.urandom(16)).decode('utf8')
    # Generate a "stable" guid from the given item
    byts = s_msgpack.en(valu)
    return hashlib.md5(byts).hexdigest()

def buid(valu=None):
    '''
    A binary GUID like sequence of 32 bytes.

    Args:
        valu (object): Optional, if provided, the hash of the msgpack
        encoded form of the object is returned. This can be used to
        create stable buids.

    Notes:
        By default, this returns a random 32 byte value.

    Returns:
        bytes: A 32 byte value.
    '''
    if valu is None:
        return os.urandom(32)

    byts = s_msgpack.en(valu)
    return hashlib.sha256(byts).digest()

def ehex(byts):
    '''
    Encode a set of bytes to a string using binascii.hexlify.

    Args:
        byts (bytes): Bytes to encode.

    Returns:
        str: A string representing the bytes.
    '''
    return binascii.hexlify(byts).decode('utf8')

def uhex(text):
    '''
    Decode bytes to a string using binascii.unhexlify.
    Args:
        text (str): Text to decode.

    Returns:
        bytes: The decoded bytes.
    '''
    return binascii.unhexlify(text)

guidre = regex.compile('^[0-9a-f]{32}$')
def isguid(text):
    return guidre.match(text) is not None

def intify(x):
    '''
    Ensure ( or coerce ) a value into being an integer or None.

    Args:
        x (obj):    An object to intify

    Returns:
        (int):  The int value ( or None )
    '''
    try:
        return int(x)
    except (TypeError, ValueError) as e:
        return None

def addpref(pref, info):
    '''
    Add the given prefix to all elements in the info dict.
    '''
    return {'%s:%s' % (pref, k): v for (k, v) in info.items()}

def tufo(typ, **kwargs):
    return (typ, kwargs)

def vertup(vstr):
    '''
    Convert a version string to a tuple.

    Example:

        ver = vertup('1.3.30')

    '''
    return tuple([int(x) for x in vstr.split('.')])

def genpath(*paths):
    path = os.path.join(*paths)
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return os.path.abspath(path)

def reqpath(*paths):
    path = genpath(*paths)
    if not os.path.isfile(path):
        raise NoSuchFile(path)
    return path

def reqfile(*paths, **opts):
    path = genpath(*paths)
    if not os.path.isfile(path):
        raise NoSuchFile(path)
    opts.setdefault('mode', 'rb')
    return io.open(path, **opts)

def reqlines(*paths, **opts):
    '''
    Open a file and yield lines of text.

    Example:

        for line in reqlines('foo.txt'):
            dostuff(line)

    NOTE: This API is used as a performance optimization
          over the standard fd line iteration mechanism.
    '''
    opts.setdefault('mode', 'r')
    opts.setdefault('encoding', 'utf8')

    rem = None
    with reqfile(*paths, **opts) as fd:

        bufr = fd.read(10000000)
        while bufr:

            if rem is not None:
                bufr = rem + bufr

            lines = bufr.split('\n')
            rem = lines[-1]

            for line in lines[:-1]:
                yield line.strip()

            bufr = fd.read(10000000)

            if rem is not None:
                bufr = rem + bufr

def getfile(*paths, **opts):
    path = genpath(*paths)
    if not os.path.isfile(path):
        return None
    opts.setdefault('mode', 'rb')
    return io.open(path, **opts)

def getbytes(*paths, **opts):
    fd = getfile(*paths, **opts)
    if fd is None:
        return None

    with fd:
        return fd.read()

def reqbytes(*paths):
    with reqfile(*paths) as fd:
        return fd.read()

def genfile(*paths):
    '''
    Create or open ( for read/write ) a file path join.

    Args:
        *paths: A list of paths to join together to make the file.

    Notes:
        If the file already exists, the fd returned is opened in ``r+b`` mode.
        Otherwise, the fd is opened in ``w+b`` mode.

    Returns:
        io.BufferedRandom: A file-object which can be read/written too.
    '''
    path = genpath(*paths)
    gendir(os.path.dirname(path))
    if not os.path.isfile(path):
        return io.open(path, 'w+b')
    return io.open(path, 'r+b')

@contextlib.contextmanager
def lockfile(path):
    '''
    A file lock with-block helper.

    Args:
        path (str): A path to a lock file.

    Examples:
        Get the lock on a file and dostuff while having the lock:

            path = '/hehe/haha.lock'
            with lockfile(path):
                dostuff()

    Notes:
        This is curently based on fcntl.lockf(), and as such, it is purely
        advisory locking. If multiple processes are attempting to obtain a
        lock on the same file, this will block until the process which has
        the current lock releases it.

    Yields:
        None
    '''
    with genfile(path) as fd:
        fcntl.lockf(fd, fcntl.LOCK_EX)
        yield None

def listdir(*paths, glob=None):
    '''
    List the (optionally glob filtered) full paths from a dir.

    Args:
        *paths ([str,...]): A list of path elements
        glob (str): An optional fnmatch glob str
    '''
    path = genpath(*paths)

    names = os.listdir(path)
    if glob is not None:
        names = fnmatch.filter(names, glob)

    retn = [os.path.join(path, name) for name in names]
    return retn

def gendir(*paths, **opts):
    mode = opts.get('mode', 0o700)
    path = genpath(*paths)
    if not os.path.isdir(path):
        os.makedirs(path, mode=mode, exist_ok=True)
    return path

def reqdir(*paths):
    path = genpath(*paths)
    if not os.path.isdir(path):
        raise NoSuchDir(path=path)
    return path

def jsload(*paths):
    with genfile(*paths) as fd:
        byts = fd.read()
        if not byts:
            return None

        return json.loads(byts.decode('utf8'))

def gentask(func, *args, **kwargs):
    return (func, args, kwargs)

def jssave(js, *paths):
    path = genpath(*paths)
    with io.open(path, 'wb') as fd:
        fd.write(json.dumps(js, sort_keys=True, indent=2).encode('utf8'))

def verstr(vtup):
    '''
    Convert a version tuple to a string.
    '''
    return '.'.join([str(v) for v in vtup])

def getexcfo(e):
    '''
    Get an err tufo from an exception.

    Args:
        e (Exception): An Exception (or Exception subclass).

    Notes:
        This can be called outside of the context of an exception handler,
        however details such as file, line, function name and source may be
        missing.

    Returns:
        ((str, dict)):
    '''
    tb = sys.exc_info()[2]
    tbinfo = traceback.extract_tb(tb)
    path, line, name, src = '', '', '', None
    if tbinfo:
        path, line, name, sorc = tbinfo[-1]
    retd = {
        'msg': str(e),
        'file': path,
        'line': line,
        'name': name,
        'src': src
    }

    if isinstance(e, SynErr):
        retd['syn:err'] = e.errinfo

    return (e.__class__.__name__, retd)

def reqok(ok, retn):
    '''
    Raise exception from retn if not ok.
    '''
    if not ok:
        raise RetnErr(retn)
    return retn

def excinfo(e):
    '''
    Populate err,errmsg,errtrace info from exc.
    '''
    tb = sys.exc_info()[2]
    path, line, name, sorc = traceback.extract_tb(tb)[-1]
    ret = {
        'err': e.__class__.__name__,
        'errmsg': str(e),
        'errfile': path,
        'errline': line,
    }

    if isinstance(e, SynErr):
        ret['errinfo'] = e.errinfo

    return ret

def synerr(excname, **info):
    '''
    Return a SynErr exception.  If the given name
    is not known, fall back on the base class.
    '''
    info['excname'] = excname
    cls = getattr(s_exc, excname, s_exc.SynErr)
    return cls(**info)

def errinfo(name, mesg):
    return {
        'err': name,
        'errmsg': mesg,
    }

def chunks(item, size):
    '''
    Divide an iterable into chunks.

    Args:
        item: Item to slice
        size (int): Maximum chunk size.

    Notes:
        This supports Generator objects and objects which support calling
        the __getitem__() method with a slice object.

    Yields:
        Slices of the item containing up to "size" number of items.
    '''
    # use islice if it's a generator
    if isinstance(item, types.GeneratorType):

        while True:

            chunk = tuple(itertools.islice(item, size))
            if not chunk:
                return

            yield chunk

    # The sequence item is empty, yield a empty slice from it.
    # This will also catch mapping objects since a slice should
    # be an unhashable type for a mapping and the __getitem__
    # method would not be present on a set object
    if not item:
        yield item[0:0]
        return

    # otherwise, use normal slicing
    off = 0

    while True:

        chunk = item[off:off + size]
        if not chunk:
            return

        yield chunk

        off += size

def iterfd(fd, size=10000000):
    '''
    Generator which yields bytes from a file descriptor.

    Args:
        fd (file): A file-like object to read bytes from.
        size (int): Size, in bytes, of the number of bytes to read from the
        fd at a given time.

    Notes:
        If the first read call on the file descriptor is a empty bytestring,
        that zero length bytestring will be yielded and the generator will
        then be exhuasted. This behavior is intended to allow the yielding of
        contents of a zero byte file.

    Yields:
        bytes: Bytes from the file descriptor.
    '''
    fd.seek(0)
    byts = fd.read(size)
    # Fast path to yield b''
    if len(byts) is 0:
        yield byts
        return
    while byts:
        yield byts
        byts = fd.read(size)

def spin(genr):
    '''
    Crank through a generator but discard the yielded values.

    Args:
        genr: Any generator or iterable valu.

    Notes:
        This generator is exhausted via the ``collections.dequeue()``
        constructor with a ``maxlen=0``, which will quickly exhaust an
        iterator staying in C code as much as possible.

    Returns:
        None
    '''
    collections.deque(genr, 0)

def reqStorDict(x):
    '''
    Raises BadStorValu if any value in the dict is not compatible
    with being stored in a cortex.
    '''
    for k, v in x.items():
        if not canstor(v):
            raise BadStorValu(name=k, valu=v)

def firethread(f):
    '''
    A decorator for making a function fire a thread.
    '''

    @functools.wraps(f)
    def callmeth(*args, **kwargs):
        thr = worker(f, *args, **kwargs)
        return thr

    return callmeth

def worker(meth, *args, **kwargs):
    thr = threading.Thread(target=meth, args=args, kwargs=kwargs)
    thr.setDaemon(True)
    thr.start()
    return thr

def reqstor(name, valu):
    '''
    Check to see if a value can be stored in a Cortex.

    Args:
        name (str): Property name.
        valu: Value to check.

    Returns:
        The valu is returned if it can be stored in a Cortex.

    Raises:
        BadPropValu if the value is not Cortex storable.
    '''
    if not canstor(valu):
        raise BadPropValu(name=name, valu=valu)
    return valu

def rowstotufos(rows):
    '''
    Convert rows into tufos.

    Args:
        rows (list): List of rows containing (i, p, v, t) tuples.

    Returns:
        list: List of tufos.
    '''
    res = collections.defaultdict(dict)
    [res[i].__setitem__(p, v) for (i, p, v, t) in rows]
    return list(res.items())

sockerrs = (builtins.ConnectionError, builtins.FileNotFoundError)

def to_bytes(valu, size):
    return valu.to_bytes(size, byteorder='little')

def to_int(byts):
    return int.from_bytes(byts, 'little')

def enbase64(b):
    return base64.b64encode(b).decode('utf8')

def debase64(b):
    return base64.b64decode(b.encode('utf8'))

def canstor(s):
    return type(s) in (int, str)

def makedirs(path, mode=0o777):
    os.makedirs(path, mode=mode, exist_ok=True)

def iterzip(*args):
    return itertools.zip_longest(*args)

def setlogging(mlogger, defval=None):
    '''
    Configure synapse logging.

    Args:
        mlogger (logging.Logger): Reference to a logging.Logger()
        defval (str): Default log level

    Notes:
        This calls logging.basicConfig and should only be called once per process.

    Returns:
        None
    '''
    log_level = os.getenv('SYN_DMON_LOG_LEVEL',
                          defval)
    if log_level:  # pragma: no cover
        log_level = log_level.upper()
        if log_level not in s_const.LOG_LEVEL_CHOICES:
            raise ValueError('Invalid log level provided: {}'.format(log_level))
        logging.basicConfig(level=log_level, format=s_const.LOG_FORMAT)
        mlogger.info('log level set to %s', log_level)
