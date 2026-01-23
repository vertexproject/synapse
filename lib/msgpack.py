'''
Msgpack serialization utilities for for_lexicon.
'''
import logging
import msgpack
import msgpack.fallback as m_fallback

import for_lexicon.exc as s_exc

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
    'unicode_errors': 'surrogatepass',
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
