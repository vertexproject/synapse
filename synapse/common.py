import io
import os
import ssl
import sys
import enum
import http
import stat
import time
import heapq
import types
import base64
import shutil
import struct
import typing
import asyncio
import decimal
import fnmatch
import hashlib
import logging
import binascii
import builtins
import tempfile
import warnings
import functools
import itertools
import threading
import traceback
import contextlib
import collections

import http.cookies
import tornado.escape

import yaml
import regex

import synapse.exc as s_exc
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.structlog as s_structlog

import synapse.vendor.cpython.lib.ipaddress as ipaddress
import synapse.vendor.cpython.lib.http.cookies as v_cookies


try:
    from yaml import CSafeLoader as Loader
    from yaml import CSafeDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as Loader
    from yaml import SafeDumper as Dumper

class NoValu:
    pass

major = sys.version_info.major
minor = sys.version_info.minor
micro = sys.version_info.micro

majmin = (major, minor)
version = (major, minor, micro)

guidre = regex.compile('^[0-9a-f]{32}$')
buidre = regex.compile('^[0-9a-f]{64}$')

novalu = NoValu()

logger = logging.getLogger(__name__)

if Loader == yaml.SafeLoader:  # pragma: no cover
    logger.warning('*****************************************************************************************************')
    logger.warning('* PyYAML is using the pure python fallback implementation. This will impact performance negatively. *')
    logger.warning('* See PyYAML docs (https://pyyaml.org/wiki/PyYAMLDocumentation) for tips on resolving this issue.   *')
    logger.warning('*****************************************************************************************************')

def now():
    '''
    Get the current epoch time in milliseconds.

    This relies on time.time_ns(), which is system-dependent in terms of resolution.

    Returns:
        int: Epoch time in milliseconds.
    '''
    return time.time_ns() // 1000000

def mononow():
    '''
    Get the current monotonic clock time in milliseconds.

    This relies on time.monotonic_ns(), which is a relative time.

    Returns:
        int: Monotonic clock time in milliseconds.
    '''
    return time.monotonic_ns() // 1000000

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
    return hashlib.md5(byts, usedforsecurity=False).hexdigest()

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

def flatten(item):
    '''
    Normalize a primitive object for cryptographic signing.

    Args:
        item: The python primitive object to normalize.

    Notes:
        Only None, bool, int, bytes, strings, lists, tuples and dictionaries are acceptable input.
        List objects will be converted to tuples.
        Dictionary objects must have keys which can be sorted.

    Returns:
        A new copy of the object.
    '''

    if item is None:
        return None

    if isinstance(item, (str, int, bytes)):
        return item

    if isinstance(item, (tuple, list)):
        return tuple([flatten(i) for i in item])

    if isinstance(item, dict):
        return {flatten(k): flatten(item[k]) for k in sorted(item.keys())}

    raise s_exc.BadDataValu(mesg=f'Unknown type: {type(item)}')

def ehex(byts):
    '''
    Encode a bytes variable to a string using binascii.hexlify.

    Args:
        byts (bytes): Bytes to encode.

    Returns:
        str: A string representing the bytes.
    '''
    return binascii.hexlify(byts).decode('utf8')

def uhex(text):
    '''
    Decode a hex string into bytes.

    Args:
        text (str): Text to decode.

    Returns:
        bytes: The decoded bytes.
    '''
    return binascii.unhexlify(text)

def isguid(text):
    return guidre.match(text) is not None

def isbuidhex(text):
    return buidre.match(text) is not None

def intify(x):
    '''
    Ensure ( or coerce ) a value into being an integer or None.

    Args:
        x (obj):    An object to intify

    Returns:
        (int):  The int value ( or None )
    '''
    if isinstance(x, int):
        return x

    try:
        return int(x, 0)
    except (TypeError, ValueError):
        return None

hugectx = decimal.Context(prec=49)
def hugenum(valu):
    '''
    Return a decimal.Decimal with proper precision for use as a synapse hugenum.
    '''
    if isinstance(valu, float):
        valu = str(valu)
    if isinstance(valu, str) and valu.startswith('0x'):
        valu = int(valu, 0)
    return decimal.Decimal(valu, context=hugectx)

def hugeadd(x, y):
    '''
    Add two decimal.Decimal with proper precision to support synapse hugenums.
    '''
    return hugectx.add(x, y)

def hugesub(x, y):
    '''
    Subtract two decimal.Decimal with proper precision to support synapse hugenums.
    '''
    return hugectx.subtract(x, y)

def hugemul(x, y):
    '''
    Multiply two decimal.Decimal with proper precision to support synapse hugenums.
    '''
    return hugectx.multiply(x, y)

def hugediv(x, y):
    '''
    Divide two decimal.Decimal with proper precision to support synapse hugenums.
    '''
    return hugectx.divide(x, y)

def hugepow(x, y):
    '''
    Return the first operand to the power of the second operand.
    '''
    return hugectx.power(x, y)

def hugescaleb(x, y):
    '''
    Return the first operand with its exponent adjusted by the second operand.
    '''
    return hugectx.scaleb(x, y)

hugeexp = decimal.Decimal('1E-24')
def hugeround(x):
    '''
    Round a decimal.Decimal with proper precision for synapse hugenums.
    '''
    return hugectx.quantize(x, hugeexp)

def hugemod(x, y):
    return hugectx.divmod(x, y)

def vertup(vstr):
    '''
    Convert a version string to a tuple.

    Example:

        ver = vertup('1.3.30')

    '''
    return tuple([int(x) for x in vstr.split('.')])

def todo(_todoname, *args, **kwargs):
    '''
    Construct and return a todo tuple of (name, args, kwargs).

    Note:  the odd name for the first parameter is to avoid collision with keys in kwargs.
    '''
    return (_todoname, args, kwargs)

def tuplify(obj):
    '''
    Convert a nested set of python primitives into tupleized forms via msgpack.
    '''
    return s_msgpack.un(s_msgpack.en(obj))

def genpath(*paths):
    '''
    Return an absolute path of the joining of the arguments as path elements

    Performs home directory(``~``) and environment variable expansion on the joined path

    Args:
        *paths ([str,...]): A list of path elements

    Note:
        All paths used by Synapse operations (i.e. everything but the data) shall use this function or one of its
        callers before storing as object properties.
    '''
    path = os.path.join(*paths)
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return os.path.abspath(path)

def switchext(*paths, ext):
    '''
    Return an absolute path of the joining of the arguments with the extension replaced.

    If an extension does not exist, it will be added.

    Args:
        *paths ([str,...]): A list of path elements
        ext (str):  A file extension (e.g. '.txt').  It should begin with a period.
    '''
    return os.path.splitext(genpath(*paths))[0] + ext

def reqpath(*paths):
    '''
    Return the absolute path of the joining of the arguments, raising an exception if a file doesn't exist at resulting
    path

    Args:
        *paths ([str,...]): A list of path elements
    '''
    path = genpath(*paths)
    if not os.path.isfile(path):
        raise s_exc.NoSuchFile(mesg=f'No such path {path}', path=path)
    return path

def reqfile(*paths, **opts):
    '''
    Return a file at the path resulting from joining of the arguments, raising an exception if the file does not
    exist.

    Args:
        *paths ([str,...]): A list of path elements
        **opts:  arguments as kwargs to io.open

    Returns:
        io.BufferedRandom: A file-object which can be read/written too.
    '''
    path = genpath(*paths)
    if not os.path.isfile(path):
        raise s_exc.NoSuchFile(mesg=f'No such file {path}', path=path)
    opts.setdefault('mode', 'rb')
    return io.open(path, **opts)

def getfile(*paths, **opts):
    '''
    Return a file at the path resulting from joining of the arguments, or None if the file does not exist.

    Args:
        *paths ([str,...]): A list of path elements
        **opts:  arguments as kwargs to io.open

    Returns:
        io.BufferedRandom: A file-object which can be read/written too.
    '''
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

def genfile(*paths) -> typing.BinaryIO:
    '''
    Create or open (for read/write) a file path join.

    Args:
        *paths: A list of paths to join together to make the file.

    Notes:
        If the file already exists, the fd returned is opened in ``r+b`` mode.
        Otherwise, the fd is opened in ``w+b`` mode.

        The file position is set to the start of the file.  The user is
        responsible for truncating (``fd.truncate()``) if the existing file
        contents are not desired, or seeking to the end (``fd.seek(0, 2)``)
        to append.

    Returns:
        A file-object which can be read/written too.
    '''
    path = genpath(*paths)
    gendir(os.path.dirname(path))
    if not os.path.isfile(path):
        return io.open(path, 'w+b')
    return io.open(path, 'r+b')

@contextlib.contextmanager
def getTempDir(dirn=None):
    tempdir = tempfile.mkdtemp(dir=dirn)

    try:
        yield tempdir

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

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
    '''
    Return the absolute path of the joining of the arguments, creating a directory at the resulting path if one does
    not exist.

    Performs home directory(~) and environment variable expansion.

    Args:
        *paths ([str,...]): A list of path elements
        **opts:  arguments as kwargs to os.makedirs
    '''
    mode = opts.get('mode', 0o700)
    path = genpath(*paths)

    if os.path.islink(path):
        path = os.readlink(path)

    if not os.path.isdir(path):
        os.makedirs(path, mode=mode, exist_ok=True)

    return path

def reqdir(*paths):
    '''
    Return the absolute path of the joining of the arguments, raising an exception if a directory does not exist at
    the resulting path.

    Performs home directory(~) and environment variable expansion.

    Args:
        *paths ([str,...]): A list of path elements
    '''
    path = genpath(*paths)
    if not os.path.isdir(path):
        raise s_exc.NoSuchDir(path=path)
    return path

def getDirSize(*paths):
    '''
    Get the size of a directory.

    Args:
        *paths (str): A list of path elements.

    Returns:
        tuple: Tuple of total real and total apparent size of all normal files and directories underneath
        ``*paths`` plus ``*paths`` itself.
    '''
    def getsize(path):
        try:
            status = os.lstat(path)
        except OSError:  # pragma: no cover
            return 0, 0

        mode = status.st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            return 0, 0

        return status.st_blocks * 512, status.st_size

    realsum, apprsum = getsize(genpath(*paths))

    for fpath, dirnames, fnames in os.walk(reqdir(*paths)):
        for fname in itertools.chain(fnames, dirnames):
            fp = genpath(fpath, fname)
            real, appr = getsize(fp)
            realsum += real
            apprsum += appr

    return realsum, apprsum

def yamlloads(data):
    return yaml.load(data, Loader)

def yamlload(*paths):

    path = genpath(*paths)
    if not os.path.isfile(path):
        return None

    with io.open(path, 'rb') as fd:
        return yamlloads(fd)

def yamldump(obj, stream: typing.Optional[typing.BinaryIO] =None) -> bytes:
    '''
    Dump a object to yaml.

    Args:
        obj: The object to serialize.
        stream: The optional stream to write the stream too.

    Returns:
        The raw yaml bytes if stream is not provided.
    '''
    return yaml.dump(obj, allow_unicode=True, default_flow_style=False,
                     default_style='', explicit_start=True, explicit_end=True,
                     encoding='utf8', stream=stream, Dumper=Dumper)

def yamlsave(obj, *paths):
    path = genpath(*paths)
    with genfile(path) as fd:
        fd.truncate(0)
        yamldump(obj, stream=fd)

def yamlmod(obj, *paths):
    '''
    Combines/creates a yaml file and combines with obj.  obj and file must be maps/dict or empty.
    '''
    oldobj = yamlload(*paths)
    if obj is not None:
        if oldobj:
            yamlsave({**oldobj, **obj}, *paths)
        else:
            yamlsave(obj, *paths)

def yamlpop(key, *paths):
    '''
    Pop a key out of a yaml file.

    Args:
        key (str): Name of the key to remove.
        *paths: Path to a yaml file. The file must be a map / dictionary.

    Returns:
        None
    '''
    obj = yamlload(*paths)
    if obj is not None:
        obj.pop(key, None)
        yamlsave(obj, *paths)

def verstr(vtup):
    '''
    Convert a version tuple to a string.
    '''
    return '.'.join([str(v) for v in vtup])

def excinfo(e):
    '''
    Populate err,errmsg,errtrace info from exc.
    '''
    tb = e.__traceback__
    path, line, name, sorc = traceback.extract_tb(tb)[-1]
    ret = {
        'err': e.__class__.__name__,
        'errmsg': str(e),
        'errfile': path,
        'errline': line,
    }

    if isinstance(e, s_exc.SynErr):
        ret['errinfo'] = e.errinfo

    return ret

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
        then be exhausted. This behavior is intended to allow the yielding of
        contents of a zero byte file.

    Yields:
        bytes: Bytes from the file descriptor.
    '''
    fd.seek(0)
    byts = fd.read(size)
    # Fast path to yield b''
    if len(byts) == 0:
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

async def aspin(genr):
    '''
    Async version of spin
    '''
    async for _ in genr:
        pass

async def agen(*items):
    for item in items:
        yield item

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
    thr = threading.Thread(target=meth, args=args, kwargs=kwargs, daemon=True)
    thr.start()
    return thr

sockerrs = (builtins.ConnectionError, builtins.FileNotFoundError)

_Int64be = struct.Struct('>Q')

def int64en(i):
    '''
    Encode an unsigned 64-bit int into 8 byte big-endian bytes
    '''
    return _Int64be.pack(i)

def int64un(b):
    '''
    Decode an unsigned 64-bit int from 8 byte big-endian
    '''
    return _Int64be.unpack(b)[0]

_SignedInt64be = struct.Struct('>q')

def signedint64en(i):
    '''
    Encode a signed 64-bit int into 8 byte big-endian bytes
    '''
    return _SignedInt64be.pack(i)

def signedint64un(b):
    '''
    Decode a signed 64-bit int from 8 byte big-endian
    '''
    return _SignedInt64be.unpack(b)[0]

def enbase64(b):
    return base64.b64encode(b).decode('utf8')

def debase64(b):
    return base64.b64decode(b.encode('utf8'))

def makedirs(path, mode=0o777):
    os.makedirs(path, mode=mode, exist_ok=True)

def iterzip(*args, fillvalue=None):
    return itertools.zip_longest(*args, fillvalue=fillvalue)

def _getLogConfFromEnv(defval=None, structlog=None, datefmt=None):
    if structlog:
        structlog = 'true'
    else:
        structlog = 'false'
    defval = os.getenv('SYN_LOG_LEVEL', defval)
    datefmt = os.getenv('SYN_LOG_DATEFORMAT', datefmt)
    structlog = envbool('SYN_LOG_STRUCT', structlog)
    ret = {'defval': defval, 'structlog': structlog, 'datefmt': datefmt}
    return ret

def normLogLevel(valu):
    '''
    Norm a log level value to a integer.

    Args:
        valu: The value to norm ( a string or integer ).

    Returns:
        int: A valid Logging log level.
    '''
    if isinstance(valu, int):
        if valu not in s_const.LOG_LEVEL_INVERSE_CHOICES:
            raise s_exc.BadArg(mesg=f'Invalid log level provided: {valu}', valu=valu)
        return valu
    if isinstance(valu, str):
        valu = valu.strip()
        try:
            valu = int(valu)
        except ValueError:
            valu = valu.upper()
            ret = s_const.LOG_LEVEL_CHOICES.get(valu)
            if ret is None:
                raise s_exc.BadArg(mesg=f'Invalid log level provided: {valu}', valu=valu) from None
            return ret
        else:
            return normLogLevel(valu)
    raise s_exc.BadArg(mesg=f'Unknown log level type: {type(valu)} {valu}', valu=valu)

def setlogging(mlogger, defval=None, structlog=None, log_setup=True, datefmt=None):
    '''
    Configure synapse logging.

    Args:
        mlogger (logging.Logger): Reference to a logging.Logger()
        defval (str): Default log level. May be an integer.
        structlog (bool): Enabled structured (jsonl) logging output.
        datefmt (str): Optional strftime format string.

    Notes:
        This calls logging.basicConfig and should only be called once per process.

    Returns:
        None
    '''
    ret = _getLogConfFromEnv(defval, structlog, datefmt)

    datefmt = ret.get('datefmt')
    log_level = ret.get('defval')
    log_struct = ret.get('structlog')

    if log_level:  # pragma: no cover

        log_level = normLogLevel(log_level)

        if log_struct:
            handler = logging.StreamHandler()
            formatter = s_structlog.JsonFormatter(datefmt=datefmt)
            handler.setFormatter(formatter)
            logging.basicConfig(level=log_level, handlers=(handler,))
        else:
            logging.basicConfig(level=log_level, format=s_const.LOG_FORMAT, datefmt=datefmt)
        if log_setup:
            mlogger.info('log level set to %s', s_const.LOG_LEVEL_INVERSE_CHOICES.get(log_level))

    return ret

syndir_default = '~/.syn'
syndir = os.getenv('SYN_DIR')
if syndir is None:
    syndir = syndir_default

def envbool(name, defval='false'):
    '''
    Resolve an environment variable to a boolean value.

    Args:
        name (str): Environment variable to resolve.
        defval (str): Default string value to resolve as.

    Notes:
        False values will be consider strings "0" or "false" after lower casing.

    Returns:
        boolean: True if the envar is set, false if it is set to a false value.
    '''
    return os.getenv(name, defval).lower() not in ('0', 'false')

def getSynPath(*paths):
    return genpath(syndir, *paths)

def getSynDir(*paths):
    return gendir(syndir, *paths)

def result(retn):
    '''
    Return a value or raise an exception from a retn tuple.
    '''
    ok, valu = retn

    if ok:
        return valu

    name, info = valu

    ctor = getattr(s_exc, name, None)
    if ctor is not None:
        raise ctor(**info)

    info['errx'] = name
    raise s_exc.SynErr(**info)

def err(e, fulltb=False):
    name = e.__class__.__name__
    info = {}

    tb = sys.exc_info()[2]
    tbinfo = traceback.extract_tb(tb)
    if tbinfo:
        path, line, tbname, src = tbinfo[-1]
        path = os.path.basename(path)
        info = {
            'efile': path,
            'eline': line,
            'esrc': src,
            'ename': tbname,
        }

    if isinstance(e, s_exc.SynErr):
        info.update(e.items())
    else:
        info['mesg'] = str(e)

    if fulltb:
        s = traceback.format_exc()
        if s[-1:] == "\n":
            s = s[:-1]
        info['etb'] = s

    return (name, info)

def retnexc(e):
    '''
    Construct a retn tuple for the given exception.
    '''
    return (False, err(e))

def config(conf, confdefs):
    '''
    Initialize a config dict using the given confdef tuples.
    '''
    conf = conf.copy()

    # for now just populate defval
    for name, info in confdefs:
        conf.setdefault(name, info.get('defval'))

    return conf

def deprecated(name, curv='2.x', eolv='3.0.0'):
    mesg = f'"{name}" is deprecated in {curv} and will be removed in {eolv}'
    warnings.warn(mesg, DeprecationWarning)
    return mesg

def deprdate(name, date):  # pragma: no cover
    mesg = f'{name} is deprecated and will be removed on {date}.'
    warnings.warn(mesg, DeprecationWarning)

def jsonsafe_nodeedits(nodeedits):
    '''
    Hexlify the buid of each node:edits
    '''
    retn = []
    for nodeedit in nodeedits:
        newedit = (ehex(nodeedit[0]), *nodeedit[1:])
        retn.append(newedit)

    return retn

def unjsonsafe_nodeedits(nodeedits):
    retn = []
    for nodeedit in nodeedits:
        buid = nodeedit[0]
        if isinstance(buid, str):
            newedit = (uhex(buid), *nodeedit[1:])
        else:
            newedit = nodeedit
        retn.append(newedit)

    return retn

def reprauthrule(rule):
    text = '.'.join(rule[1])
    if not rule[0]:
        text = '!' + text
    return text

async def merggenr(genrs, cmprkey):
    '''
    Iterate multiple sorted async generators and yield their results in order.

    Args:
        genrs (Sequence[AsyncGenerator[T]]):  a sequence of async generator that each yield sorted items
        cmprkey(Callable[T, T, bool]):  a comparison function over the items yielded

    Note:
        If the genrs yield increasing items, cmprkey should return True if the first parameter is less
        than the second parameter, e.g lambda x, y: x < y.
    '''

    size = len(genrs)
    genrs = list(genrs)

    indxs = list(range(size))

    async def genrnext(g):
        try:
            ret = await g.__anext__()
            return ret
        except StopAsyncIteration:
            return novalu

    curvs = [await genrnext(g) for g in genrs]

    while True:

        nextindx = None
        nextvalu = novalu
        toremove = []

        for i in indxs:

            curv = curvs[i]
            if curv is novalu:
                toremove.append(i)
                continue

            # in the case where we're the first, initialize...
            if nextvalu is novalu:
                nextindx = i
                nextvalu = curv
                continue

            if cmprkey(curv, nextvalu):
                nextindx = i
                nextvalu = curv

        # check if we're done
        if nextvalu is novalu:
            return

        # Remove spent genrs
        for i in toremove:
            indxs.remove(i)

        yield nextvalu

        curvs[nextindx] = await genrnext(genrs[nextindx])

async def merggenr2(genrs, cmprkey=None, reverse=False):
    '''
    Optimized version of merggenr based on heapq.merge
    '''
    h = []
    h_append = h.append

    if reverse:
        _heapify = heapq._heapify_max
        _heappop = heapq._heappop_max
        _heapreplace = heapq._heapreplace_max
        direction = -1
    else:
        _heapify = heapq.heapify
        _heappop = heapq.heappop
        _heapreplace = heapq.heapreplace
        direction = 1

    if cmprkey is None:
        for order, genr in enumerate(genrs):
            try:
                nxt = genr.__anext__
                h_append([await nxt(), order * direction, nxt])
            except StopAsyncIteration:
                pass

        _heapify(h)

        while len(h) > 1:
            try:
                while True:
                    valu, _, nxt = s = h[0]
                    yield valu
                    s[0] = await nxt()
                    _heapreplace(h, s)
            except StopAsyncIteration:
                _heappop(h)

        if h:
            valu, order, _ = h[0]
            yield valu
            async for valu in genrs[abs(order)]:
                yield valu
        return

    for order, genr in enumerate(genrs):
        try:
            nxt = genr.__anext__
            valu = await nxt()
            h_append([cmprkey(valu), order * direction, valu, nxt])
        except StopAsyncIteration:
            pass

    _heapify(h)

    while len(h) > 1:
        try:
            while True:
                _, _, valu, nxt = s = h[0]
                yield valu
                valu = await nxt()
                s[0] = cmprkey(valu)
                s[2] = valu
                _heapreplace(h, s)
        except StopAsyncIteration:
            _heappop(h)

    if h:
        _, order, valu, _ = h[0]
        yield valu
        async for valu in genrs[abs(order)]:
            yield valu

def getSslCtx(cadir, purpose=ssl.Purpose.SERVER_AUTH):
    '''
    Create as SSL Context and load certificates from a given directory.

    Args:
        cadir (str): Path to load certificates from.
        purpose: SSLContext purposes flags.

    Returns:
        ssl.SSLContext: A SSL Context object.
    '''
    sslctx = ssl.create_default_context(purpose=purpose)
    for name in os.listdir(cadir):
        certpath = os.path.join(cadir, name)
        if not os.path.isfile(certpath):
            continue
        try:
            sslctx.load_verify_locations(cafile=certpath)
        except Exception:  # pragma: no cover
            logger.exception(f'Error loading {certpath}')
    return sslctx

def httpcodereason(code):
    '''
    Get the reason for an HTTP status code.

    Args:
        code (int): The code.

    Note:
        If the status code is unknown, a string indicating it is unknown is returned.

    Returns:
        str: A string describing the status code.
    '''
    try:
        return http.HTTPStatus(code).phrase
    except ValueError:
        return f'Unknown HTTP status code {code}'

def trimText(text: str, n: int = 256, placeholder: str = '...') -> str:
    '''
    Trim a text string larger than n characters and add a placeholder at the end.

    Args:
        text: String to trim.
        n: Number of characters to allow.
        placeholder: Placeholder text.

    Returns:
        The original string or the trimmed string.
    '''
    if len(text) <= n:
        return text
    plen = len(placeholder)
    mlen = n - plen
    assert plen > 0
    assert n > plen
    return f'{text[:mlen]}{placeholder}'

def queryhash(text):
    return hashlib.md5(text.encode(errors='surrogatepass'), usedforsecurity=False).hexdigest()

def _patch_http_cookies():
    '''
    Patch stdlib http.cookies._unquote from the 3.11.10 implementation if
    the interpreter we are using is not patched for CVE-2024-7592.
    '''
    if not hasattr(http.cookies, '_QuotePatt'):
        return
    http.cookies._unquote = v_cookies._unquote

def _patch_tornado_json():
    import synapse.lib.json as s_json

    if hasattr(tornado.escape, 'json_encode'):
        # This exists for a specific reason. See the following URL for explanation:
        # https://github.com/tornadoweb/tornado/blob/d5ac65c1f1453c2aeddd089d8e68c159645c13e1/tornado/escape.py#L83-L96
        # https://github.com/tornadoweb/tornado/pull/706
        def _tornado_json_encode(value):
            return s_json.dumps(value).replace(b'</', br'<\/').decode()

        tornado.escape.json_encode = _tornado_json_encode

    if hasattr(tornado.escape, 'json_decode'):
        tornado.escape.json_decode = s_json.loads

_patch_http_cookies()
_patch_tornado_json()

# TODO:  Switch back to using asyncio.wait_for when we are using py 3.12+
# This is a workaround for a race where asyncio.wait_for can end up
# ignoring cancellation https://github.com/python/cpython/issues/86296
async def wait_for(fut, timeout):

    if timeout is not None and timeout <= 0:
        fut = asyncio.ensure_future(fut)

        if fut.done():
            return fut.result()

        await _cancel_and_wait(fut)
        try:
            return fut.result()
        except asyncio.CancelledError as exc:
            raise TimeoutError from exc

    async with _timeout(timeout):
        return await fut

def _release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)

async def _cancel_and_wait(fut):
    """Cancel the *fut* future or task and wait until it completes."""

    loop = asyncio.get_running_loop()
    waiter = loop.create_future()
    cb = functools.partial(_release_waiter, waiter)
    fut.add_done_callback(cb)

    try:
        fut.cancel()
        # We cannot wait on *fut* directly to make
        # sure _cancel_and_wait itself is reliably cancellable.
        await waiter
    finally:
        fut.remove_done_callback(cb)


class _State(enum.Enum):
    CREATED = "created"
    ENTERED = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    EXITED = "finished"

class _Timeout:
    """Asynchronous context manager for cancelling overdue coroutines.
    Use `timeout()` or `timeout_at()` rather than instantiating this class directly.
    """

    def __init__(self, when):
        """Schedule a timeout that will trigger at a given loop time.
        - If `when` is `None`, the timeout will never trigger.
        - If `when < loop.time()`, the timeout will trigger on the next
          iteration of the event loop.
        """
        self._state = _State.CREATED
        self._timeout_handler = None
        self._task = None
        self._when = when

    def when(self):  # pragma: no cover
        """Return the current deadline."""
        return self._when

    def reschedule(self, when):
        """Reschedule the timeout."""
        assert self._state is not _State.CREATED
        if self._state is not _State.ENTERED:  # pragma: no cover
            raise RuntimeError(
                f"Cannot change state of {self._state.value} Timeout",
            )
        self._when = when
        if self._timeout_handler is not None:  # pragma: no cover
            self._timeout_handler.cancel()
        if when is None:
            self._timeout_handler = None
        else:
            loop = asyncio.get_running_loop()
            if when <= loop.time():  # pragma: no cover
                self._timeout_handler = loop.call_soon(self._on_timeout)
            else:
                self._timeout_handler = loop.call_at(when, self._on_timeout)

    def expired(self):  # pragma: no cover
        """Is timeout expired during execution?"""
        return self._state in (_State.EXPIRING, _State.EXPIRED)

    def __repr__(self):  # pragma: no cover
        info = ['']
        if self._state is _State.ENTERED:
            when = round(self._when, 3) if self._when is not None else None
            info.append(f"when={when}")
        info_str = ' '.join(info)
        return f"<Timeout [{self._state.value}]{info_str}>"

    async def __aenter__(self):
        self._state = _State.ENTERED
        self._task = asyncio.current_task()
        self._cancelling = self._task.cancelling()
        if self._task is None:  # pragma: no cover
            raise RuntimeError("Timeout should be used inside a task")
        self.reschedule(self._when)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._state in (_State.ENTERED, _State.EXPIRING)
        if self._timeout_handler is not None:
            self._timeout_handler.cancel()
            self._timeout_handler = None
        if self._state is _State.EXPIRING:
            self._state = _State.EXPIRED

            if self._task.uncancel() <= self._cancelling and exc_type is asyncio.CancelledError:
                # Since there are no new cancel requests, we're
                # handling this.
                raise TimeoutError from exc_val
        elif self._state is _State.ENTERED:
            self._state = _State.EXITED

        return None

    def _on_timeout(self):
        assert self._state is _State.ENTERED
        self._task.cancel()
        self._state = _State.EXPIRING
        # drop the reference early
        self._timeout_handler = None

def _timeout(delay):
    """Timeout async context manager.

    Useful in cases when you want to apply timeout logic around block
    of code or in cases when asyncio.wait_for is not suitable. For example:

    >>> async with asyncio.timeout(10):  # 10 seconds timeout
    ...     await long_running_task()


    delay - value in seconds or None to disable timeout logic

    long_running_task() is interrupted by raising asyncio.CancelledError,
    the top-most affected timeout() context manager converts CancelledError
    into TimeoutError.
    """
    loop = asyncio.get_running_loop()
    return _Timeout(loop.time() + delay if delay is not None else None)
# End - Vendored Code from Python 3.12+

async def waitretn(futu, timeout):
    try:
        valu = await wait_for(futu, timeout)
        return (True, valu)
    except Exception as e:
        return (False, excinfo(e))

async def waitgenr(genr, timeout):

    async with contextlib.aclosing(genr.__aiter__()) as genr:

        while True:
            retn = await waitretn(genr.__anext__(), timeout)

            if not retn[0] and retn[1]['err'] == 'StopAsyncIteration':
                return

            yield retn

            if not retn[0]:
                return

def format(text, **kwargs):
    '''
    Similar to python str.format() but treats tokens as opaque.
    '''
    for name, valu in kwargs.items():
        tokn = '{' + name + '}'
        text = text.replace(tokn, valu)
    return text
