import logging
import msgpack
import msgpack.fallback as m_fallback

logger = logging.getLogger(__name__)

# Single Packer object which is reused for performance
pakr = msgpack.Packer(use_bin_type=True, encoding='utf8')
if isinstance(pakr, m_fallback.Packer):  # pragma: no cover
    logger.warning('msgpack is using the pure python fallback implementation. This will impact performance negatively.')
    pakr = None

def en(item):
    '''
    Use msgpack to serialize a compatible python object.

    Args:
        item (obj): The object to serialize

    Returns:
        bytes: The serialized bytes
    '''
    if pakr is None:  # pragma: no cover
        return msgpack.packb(item, use_bin_type=True, encoding='utf8')
    return pakr.pack(item)

def un(byts):
    '''
    Use msgpack to de-serialize a python object.

    Args:
        byts (bytes): The bytes to de-serialize

    Returns:
        obj: The de-serialized object
    '''
    return msgpack.loads(byts, use_list=False, encoding='utf8')

def iterfd(fd):
    '''
    Generator which unpacks a file object of msgpacked content.

    Args:
        fd: File object to consume data from.

    Yields:
        Objects from a msgpack stream.
    '''
    unpk = msgpack.Unpacker(fd, use_list=False, encoding='utf8')
    for mesg in unpk:
        yield mesg

class Unpk:
    '''
    An extension of the msgpack streaming Unpacker which reports sizes.
    '''
    def __init__(self):
        self.size = 0
        self.unpk = msgpack.Unpacker(use_list=0, encoding='utf8')

    def feed(self, byts):
        '''
        Feed bytes to the unpacker and return completed objects.
        '''
        self.unpk.feed(byts)

        def sizeof(b):
            self.size += len(b)

        retn = []

        while True:

            try:
                item = self.unpk.unpack(write_bytes=sizeof)
                retn.append((self.size, item))
                self.size = 0

            except msgpack.exceptions.OutOfData:
                break

        return retn
