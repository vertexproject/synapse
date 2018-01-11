import logging
import msgpack
import msgpack.fallback as m_fallback

logger = logging.getLogger(__name__)

# Single Packer object which is reused for performance
pakr = msgpack.Packer(use_bin_type=True, encoding='utf8', unicode_errors='surrogatepass')
if isinstance(pakr, m_fallback.Packer):  # pragma: no cover
    logger.warning('msgpack is using the pure python fallback implementation. This will impact performance negatively.')
    pakr = None

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
    if pakr is None:  # pragma: no cover
        return msgpack.packb(item, use_bin_type=True, encoding='utf8',
                             unicode_errors='surrogatepass')
    try:
        return pakr.pack(item)
    except Exception as e:
        pakr.reset()
        raise

def un(byts):
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
    return msgpack.loads(byts, use_list=False, encoding='utf8',
                         unicode_errors='surrogatepass')

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
    unpk = msgpack.Unpacker(fd, use_list=False, encoding='utf8',
                            unicode_errors='surrogatepass')
    for mesg in unpk:
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
        self.unpk = msgpack.Unpacker(use_list=False, encoding='utf8',
                                     unicode_errors='surrogatepass')

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
