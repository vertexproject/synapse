import io
import os
import json
import logging

from typing import Any, BinaryIO, Callable, Iterator, Optional

from synapse.vendor.cpython.lib.json import detect_encoding

import yyjson

import synapse.exc as s_exc

logger = logging.getLogger(__name__)

def _fallback_loads(s: str | bytes) -> Any:

    try:
        return json.loads(s)
    except json.JSONDecodeError as exc:
        raise s_exc.BadJsonText(mesg=exc.args[0])

def loads(s: str | bytes) -> Any:
    '''
    Deserialize a JSON string.

    Similar to the standard library json.loads().

    Arguments:
        s (str | bytes): The JSON data to be deserialized.

    Returns:
        (object): The deserialized JSON data.

    Raises:
        synapse.exc.BadJsonText: This exception is raised when there is an error
            deserializing the provided data.
    '''
    try:
        return yyjson.Document(s, flags=yyjson.ReaderFlags.BIGNUM_AS_RAW).as_obj

    except (ValueError, TypeError) as exc:
        extra = {'synapse': {'fn': 'loads', 'reason': str(exc)}}
        logger.warning('Using fallback JSON deserialization. Please report this to Vertex.', extra=extra)
        return _fallback_loads(s)

def load(fp: BinaryIO) -> Any:
    '''
    Deserialize JSON data from a file.

    Similar to the standard library json.load().

    Arguments:
        fp (file): The python file pointer to read the data from.

    Returns:
        (object): The deserialized JSON data.

    Raises:
        synapse.exc.BadJsonText: This exception is raised when there is an error
            deserializing the provided data.
    '''
    return loads(fp.read())

def _fallback_dumps(obj: Any, sort_keys: bool = False, indent: bool = False, default: Optional[Callable] = None) -> bytes:
    indent = 2 if indent else None

    try:
        ret = json.dumps(obj, sort_keys=sort_keys, indent=indent, default=default)
        return ret.encode()
    except TypeError as exc:
        raise s_exc.MustBeJsonSafe(mesg=exc.args[0])

def _dumps(obj, sort_keys=False, indent=False, default=None, newline=False):
    rflags = 0
    wflags = 0

    if sort_keys:
        rflags |= yyjson.ReaderFlags.SORT_KEYS

    if indent:
        wflags |= yyjson.WriterFlags.PRETTY_TWO_SPACES

    if newline:
        wflags |= yyjson.WriterFlags.WRITE_NEWLINE_AT_END

    if isinstance(obj, bytes):
        mesg = 'Object of type bytes is not JSON serializable'
        raise s_exc.MustBeJsonSafe(mesg=mesg)

    if isinstance(obj, str) and obj not in ('null', 'true', 'false'):
        # Raw strings have to be double-quoted. This is because the default behavior for `yyjson.Document` is to attempt
        # to parse the string as a serialized JSON string into objects. Instead of trying to manually escape the string,
        # we wrap it in a list, serialize it, and then strip off the leading/trailing [] so we can get the JSON encoded
        # string as output.
        doc = yyjson.Document([obj], default=default, flags=rflags)
        return doc.dumps(flags=wflags)[1:-1].encode()

    doc = yyjson.Document(obj, default=default, flags=rflags)
    return doc.dumps(flags=wflags).encode()

def dumps(obj: Any, sort_keys: bool = False, indent: bool = False, default: Optional[Callable] = None, newline: bool = False) -> bytes:
    '''
    Serialize a python object to byte string.

    Similar to the standard library json.dumps().

    Arguments:
        obj (object): The python object to serialize.
        sort_keys (bool): Sort dictionary keys. Default: False.
        indent (bool): Include 2 spaces of indentation. Default: False.
        default (Optional[Callable]): Callback for serializing unknown object types. Default: None.
        newline (bool): Append a newline to the end of the serialized data. Default: False.

    Returns:
        (bytes): The JSON serialized python object.

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    try:
        return _dumps(obj, sort_keys=sort_keys, indent=indent, default=default, newline=newline)
    except UnicodeEncodeError as exc:
        extra = {'synapse': {'fn': 'dumps', 'reason': str(exc)}}
        logger.warning('Using fallback JSON serialization. Please report this to Vertex.', extra=extra)

        ret = _fallback_dumps(obj, sort_keys=sort_keys, indent=indent, default=default)

        if newline:
            ret += b'\n'

        return ret

    except (TypeError, ValueError) as exc:
        mesg = f'{exc.__class__.__name__}: {exc}'
        raise s_exc.MustBeJsonSafe(mesg=mesg)

def dump(obj: Any, fp: BinaryIO, sort_keys: bool = False, indent: bool = False, default: Optional[Callable] = None, newline: bool = False) -> None:
    '''
    Serialize a python object to a file-like object opened in binary mode.

    Similar to the standard library json.dump().

    Arguments:
        obj (object): The python object to serialize.
        fp (file): The python file pointer to write the serialized data to.
        sort_keys (bool): Sort dictionary keys. Default: False.
        indent (bool): Include 2 spaces of indentation. Default: False.
        default (Optional[Callable]): Callback for serializing unknown object types. Default: None.
        newline (bool): Append a newline to the end of the serialized data. Default: False.

    Returns: None

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    data = dumps(obj, sort_keys=sort_keys, indent=indent, default=default, newline=newline)
    fp.write(data)

def jsload(*paths: str) -> Any:
    '''
    Deserialize the JSON data at *paths.

    Arguments:
        *paths: The file path parts to load the data from.

    Returns:
        (object): The deserialized JSON data.

    Raises:
        synapse.exc.BadJsonText: This exception is raised when there is an error
            deserializing the provided data.
    '''
    import synapse.common as s_common # Avoid circular import
    with s_common.genfile(*paths) as fd:
        if os.fstat(fd.fileno()).st_size == 0:
            return None

        return load(fd)

def jslines(*paths: list[str]) -> Iterator[Any]:
    '''
    Deserialize the JSON lines data at *paths.

    Arguments:
        *paths: The file path parts to load the data from.

    Yields:
        (object): The deserialized JSON data from each line.

    Raises:
        synapse.exc.BadJsonText: This exception is raised when there is an error
            deserializing the provided data.
    '''
    import synapse.common as s_common # Avoid circular import
    with s_common.genfile(*paths) as fd:
        for line in fd:
            yield loads(line)

def jssave(js: Any, *paths: list[str]) -> None:
    '''
    Serialize the python object to a file.

    Arguments:
        js: The python object to serialize.
        *paths: The file path parts to save the data to.

    Returns: None

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python
        object cannot be serialized.
    '''
    import synapse.common as s_common # Avoid circular import
    path = s_common.genpath(*paths)
    with io.open(path, 'wb') as fd:
        dump(js, fd, sort_keys=True, indent=True)

def reqjsonsafe(item: Any, strict: bool = False) -> None:
    '''
    Check if a python object is safe to be serialized to JSON.

    Uses default type coercion from synapse.lib.json.dumps.

    Arguments:
        item (any): The python object to check.
        strict (bool): If specified, do not fallback to python json library which is
                more permissive of unicode strings. Default: False

    Returns: None if item is json serializable, otherwise raises an exception.

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when the item
        cannot be serialized.
    '''
    if strict:
        try:
            _dumps(item)

        except s_exc.MustBeJsonSafe:
            raise

        except UnicodeEncodeError as exc:
            mesg = str(exc)
            raise s_exc.MustBeJsonSafe(mesg=mesg)

        except Exception as exc:
            mesg = f'{exc.__class__.__name__}: {exc}'
            raise s_exc.MustBeJsonSafe(mesg=mesg)
    else:
        dumps(item)
