import io
import logging
import msgpack
import msgpack.fallback as m_fallback

import synapse.exc as s_exc

logger = logging.getLogger(__name__)

# Single Packer object which is reused for performance
pakr = msgpack.Packer(use_bin_type=True, unicode_errors='surrogatepass')
if isinstance(pakr, m_fallback.Packer):  # pragma: no cover
    logger.warning('msgpack is using the pure python fallback implementation. This will impact performance negatively.')
    pakr = None

# synapse.lib.msgpack.un uses a hardcoded subset of these arguments for speed
unpacker_kwargs = {
    'raw': False,
    'use_list': False,
    'strict_map_key': False,
    'max_buffer_size': 2**32 - 1,
    'unicode_errors': 'surrogatepass'
}

def en(item):
    '''
    Use msgpack to serialize a compatible python object.

    Args:
        item (obj): The object to serialize

    Notes:
        String objects are encoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow encoding bad input strings.

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
        String objects are encoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow encoding bad input strings.

    Returns:
        bytes: The serialized bytes in msgpack format.
    '''
    try:
        return msgpack.packb(item, use_bin_type=True, unicode_errors='surrogatepass')
    except TypeError as e:
        mesg = f'{e.args[0]}: {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e
    except Exception as e:
        mesg = f'Cannot serialize: {repr(e)}:  {repr(item)[:20]}'
        raise s_exc.NotMsgpackSafe(mesg=mesg) from e

# Redefine the en() function if we're in fallback mode.
if pakr is None:  # pragma: no cover
    en = _fallback_en

def un(byts, use_list=False):
    '''
    Use msgpack to de-serialize a python object.

    Args:
        byts (bytes): The bytes to de-serialize

    Notes:
        String objects are decoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow decoding bad input strings.

    Returns:
        obj: The de-serialized object
    '''
    # This uses a subset of unpacker_kwargs
    return msgpack.loads(byts, use_list=use_list, raw=False, strict_map_key=False, unicode_errors='surrogatepass')

def isok(item):
    '''
    Returns True if the item can be msgpacked (by testing packing).
    '''
    try:
        en(item)
        return True
    except Exception:
        return False

def iterfd(fd):
    '''
    Generator which unpacks a file object of msgpacked content.

    Args:
        fd: File object to consume data from.

    Notes:
        String objects are decoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow decoding bad input strings.

    Yields:
        Objects from a msgpack stream.
    '''
    unpk = msgpack.Unpacker(fd, **unpacker_kwargs)
    for mesg in unpk:
        yield mesg

def iterfile(path, since=-1):
    '''
    Generator which yields msgpack objects from a file path.

    Args:
        path: File path to open and consume data from.

    Notes:
        String objects are decoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow decoding bad input strings.

    Yields:
        Objects from a msgpack stream.
    '''
    with io.open(path, 'rb') as fd:

        unpk = msgpack.Unpacker(fd, **unpacker_kwargs)

        for i, mesg in enumerate(unpk):
            if i <= since:
                continue

            yield mesg

class Unpk:
    '''
    An extension of the msgpack streaming Unpacker which reports sizes.

    Notes:
        String objects are decoded using utf8 encoding.  In order to handle
        potentially malformed input, ``unicode_errors='surrogatepass'`` is set
        to allow decoding bad input strings.
    '''
    def __init__(self):
        self.size = 0
        self.unpk = msgpack.Unpacker(**unpacker_kwargs)

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
