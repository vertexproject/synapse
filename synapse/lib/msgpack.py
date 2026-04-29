import io
import logging
import msgpack
import msgpack.fallback as m_fallback

import synapse.exc as s_exc

logger = logging.getLogger(__name__)

def _ext_un(code, byts):
    if code == 0:
        return int.from_bytes(byts, 'big')
    elif code == 1:
        return int.from_bytes(byts, 'big', signed=True)
    else:  # pragma: no cover
        mesg = f'Invalid msgpack ext code: {code} ({repr(byts)[:20]})'
        raise s_exc.SynErr(mesg=mesg)

def _ext_en(item):
    if isinstance(item, int):
        if item > 0xffffffffffffffff:
            size = (item.bit_length() + 7) // 8
            return msgpack.ExtType(0, item.to_bytes(size, 'big'))
        if item < -0x8000000000000000:
            size = (item.bit_length() // 8) + 1
            return msgpack.ExtType(1, item.to_bytes(size, 'big', signed=True))
    return item

_packer_kwargs = {
    'use_bin_type': True,
    'default': _ext_en,
}
if msgpack.version >= (1, 1, 0):
    _packer_kwargs['buf_size'] = 1024 * 1024

# Single Packer object which is reused for performance
pakr = msgpack.Packer(**_packer_kwargs)
if isinstance(pakr, m_fallback.Packer):  # pragma: no cover
    logger.warning('******************************************************************************************************')
    logger.warning('* msgpack is using the pure python fallback implementation. This will impact performance negatively. *')
    logger.warning('* Check https://github.com/msgpack/msgpack-python for troubleshooting msgpack on your platform.      *')
    logger.warning('******************************************************************************************************')
    pakr = None

# synapse.lib.msgpack.un uses a hardcoded subset of these arguments for speed
unpacker_kwargs = {
    'raw': False,
    'use_list': False,
    'strict_map_key': False,
    'ext_hook': _ext_un,
    'max_buffer_size': 2**32 - 1,
    'unicode_errors': 'replace',
}

unpacker_kwargs_strict = {
    'raw': False,
    'use_list': False,
    'strict_map_key': False,
    'ext_hook': _ext_un,
    'max_buffer_size': 2**32 - 1,
}

def en(item):
    '''
    Use msgpack to serialize a compatible python object.

    Args:
        item (obj): The object to serialize

    Notes:
        String objects are encoded using utf8 encoding.

    Returns:
        bytes: The serialized bytes in msgpack format.
    '''
    try:
        return pakr.pack(item)
    except TypeError as e:
        pakr.reset()
        mesg = f'{e.args[0]}: {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e
    except Exception as e:
        pakr.reset()
        mesg = f'Cannot serialize: {repr(e)}:  {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e

def _fallback_en(item):
    '''
    Use msgpack to serialize a compatible python object.

    Args:
        item (obj): The object to serialize

    Notes:
        String objects are encoded using utf8 encoding.

    Returns:
        bytes: The serialized bytes in msgpack format.
    '''
    try:
        return msgpack.packb(item, **_packer_kwargs)
    except TypeError as e:
        mesg = f'{e.args[0]}: {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e
    except Exception as e:
        mesg = f'Cannot serialize: {repr(e)}:  {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e

# Redefine the en() function if we're in fallback mode.
if pakr is None:  # pragma: no cover
    en = _fallback_en

def un(byts, use_list=False, strict=False):
    '''
    Use msgpack to de-serialize a python object.

    Args:
        byts (bytes): The bytes to de-serialize
        use_list (boolean): Decode arrays as lists rather than tuples.
        strict (boolean): Whether to require strings are valid utf8.

    Notes:
        String objects are decoded using utf8 encoding.

    Returns:
        obj: The de-serialized object
    '''
    # This uses a subset of unpacker_kwargs
    if not strict:
        return msgpack.loads(byts, use_list=use_list, raw=False, strict_map_key=False,
                             unicode_errors='replace', ext_hook=_ext_un)

    try:
        return msgpack.loads(byts, use_list=use_list, raw=False, strict_map_key=False, ext_hook=_ext_un)
    except UnicodeDecodeError as exc:
        mesg = 'Error decoding string in msgpack data.'
        raise s_exc.BadMsgpackData(mesg=mesg) from exc

def isok(item):
    '''
    Returns True if the item can be msgpacked (by testing packing).
    '''
    try:
        en(item)
        return True
    except Exception:
        return False

def iterfd(fd, strict=False):
    '''
    Generator which unpacks a file object of msgpacked content.

    Args:
        fd: File object to consume data from.
        strict (boolean): Whether to require strings are valid utf8.

    Notes:
        String objects are decoded using utf8 encoding.

    Yields:
        Objects from a msgpack stream.
    '''
    kwargs = unpacker_kwargs_strict if strict else unpacker_kwargs
    unpk = msgpack.Unpacker(fd, **kwargs)

    try:
        for mesg in unpk:
            yield mesg
    except UnicodeDecodeError as exc:
        mesg = 'Error decoding string in msgpack data.'
        raise s_exc.BadMsgpackData(mesg=mesg) from exc

def iterfile(path, since=-1, strict=False):
    '''
    Generator which yields msgpack objects from a file path.

    Args:
        path: File path to open and consume data from.
        strict (boolean): Whether to require strings are valid utf8.

    Notes:
        String objects are decoded using utf8 encoding.

    Yields:
        Objects from a msgpack stream.
    '''
    with io.open(path, 'rb') as fd:

        kwargs = unpacker_kwargs_strict if strict else unpacker_kwargs
        unpk = msgpack.Unpacker(fd, **kwargs)

        try:
            for i, mesg in enumerate(unpk):
                if i <= since:
                    continue

                yield mesg

        except UnicodeDecodeError as exc:
            mesg = 'Error decoding string in msgpack data.'
            raise s_exc.BadMsgpackData(mesg=mesg) from exc

class Unpk:
    '''
    An extension of the msgpack streaming Unpacker which reports sizes.

    Notes:
        String objects are decoded using utf8 encoding. If initialized with strict=True, strings are
        required to be valid utf8.
    '''
    def __init__(self, strict=False):
        self.size = 0
        kwargs = unpacker_kwargs_strict if strict else unpacker_kwargs
        self.unpk = msgpack.Unpacker(**kwargs)

    def feed(self, byts):
        '''
        Feed bytes to the unpacker and return completed objects.

        Args:
            byts (bytes): Bytes to unpack.

        Notes:
            It is intended that this function is called multiple times with
            bytes from some sort of a stream, as it will unpack and return
            objects as they are available.

        Returns:
            list: List of tuples containing the item size and the unpacked item.
        '''
        self.unpk.feed(byts)

        retn = []

        while True:

            try:
                item = self.unpk.unpack()
                tell = self.unpk.tell()
                retn.append((tell - self.size, item))
                self.size = tell

            except msgpack.exceptions.OutOfData:
                break

            except UnicodeDecodeError as exc:
                mesg = 'Error decoding string in msgpack data.'
                raise s_exc.BadMsgpackData(mesg=mesg) from exc

        return retn

def loadfile(path):
    '''
    Load and upack the msgpack bytes from a file by path.

    Args:
        path (str): The file path to a message pack file.

    Raises:
        msgpack.exceptions.ExtraData: If the file contains multiple objects.

    Returns:
        (obj): The decoded python object.
    '''
    with io.open(path, 'rb') as fd:
        return un(fd.read())

def dumpfile(item, path):
    '''
    Dump an object to a file by path.

    Args:
        item (object): The object to serialize.
        path (str): The file path to save.

    Returns:
        None
    '''
    with io.open(path, 'wb') as fd:
        fd.write(en(item))

def deepcopy(item, use_list=False):
    '''
    Copy a msgpack serializable by packing then unpacking it.
    For complex primitives, this runs in about 1/3 the time of
    copy.deepcopy()
    '''
    return un(en(item), use_list=use_list)

def getvars(varz):
    items = []
    for item in varz.items():
        if not isok(item):
            continue
        items.append(item)
    return dict(items)
