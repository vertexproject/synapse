import msgpack

pakr = msgpack.Packer(use_bin_type=True, encoding='utf8')

def en(item):
    '''
    Use msgpack to serialize a compatible python object.

    Args:
        item (obj): The object to serialize

    Returns:
        (bytes): The serialized bytes
    '''
    return pakr.pack(item)

def un(byts):
    '''
    Use msgpack to de-serialize a python object.

    Args:
        byts (bytes): The bytes to de-serialize

    Returns:
        (obj): The de-serialized object
    '''
    return msgpack.loads(byts, use_list=False, encoding='utf8')

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
