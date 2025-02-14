import io
import os
import mmap

import orjson

import synapse.exc as s_exc

def loads(s):
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
    if isinstance(s, str):
        s = s.encode('utf8', errors='backslashreplace')

    try:
        return orjson.loads(s)
    except orjson.JSONDecodeError as exc:
        raise s_exc.BadJsonText(mesg=exc.args[0])

def load(fp):
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
    try:
        with mmap.mmap(fp.fileno(), 0, prot=mmap.PROT_READ) as mm:
            with memoryview(mm) as mv:
                return loads(mv)

    except (AttributeError, io.UnsupportedOperation):
        # This block need to be first because io.UnsupportedOperation is a subclass of ValueError.
        # The file pointer will raise UnsupportedOperation if fileno() fails because the file isn't
        # backed by a file descriptor but mmap will raise ValueError if the (real) file is empty. So
        # ordering matters. *sigh*
        return loads(fp.read())

    except ValueError:
        mesg = 'Cannot read empty file.'
        raise s_exc.BadJsonText(mesg=mesg)

def dumpsb(obj, sort_keys=False, indent=False, default=None, newline=False):
    '''
    Serialize a python object to byte string.

    Similar to the standard library json.dumps().

    Arguments:
        obj (object): The python object to serialize.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        newline (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

    Returns:
        (str | bytes): The JSON serialized python object.

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    opts = 0

    if indent:
        opts |= orjson.OPT_INDENT_2

    if sort_keys:
        opts |= orjson.OPT_SORT_KEYS

    if newline:
        opts |= orjson.OPT_APPEND_NEWLINE

    try:
        return orjson.dumps(obj, option=opts, default=default)
    except orjson.JSONEncodeError as exc:
        raise s_exc.MustBeJsonSafe(mesg=exc.args[0])

def dumps(obj, sort_keys=False, indent=False, default=None, asbytes=False, newline=False):
    '''
    Serialize a python object to a string.

    Similar to the standard library json.dumps().

    Arguments:
        obj (object): The python object to serialize.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        newline (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

    Returns:
        (str | bytes): The JSON serialized python object.

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    data = dumpsb(obj, sort_keys=sort_keys, indent=indent, default=default, newline=newline)
    return data.decode('utf8', errors='surrogatepass')

def dumpb(obj, fp, sort_keys=False, indent=False, default=None, newline=False):
    '''
    Serialize a python object to a file-like object opened in binary mode.

    Similar to the standard library json.dump().

    Arguments:
        obj (object): The python object to serialize.
        fp (file): The python file pointer to write the serialized data to.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        newline (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

    Returns: None

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    data = dumpsb(obj, sort_keys=sort_keys, indent=indent, default=default, newline=newline)
    fp.write(data)

def dump(obj, fp, sort_keys=False, indent=False, default=None, newline=False):
    '''
    Serialize a python object to a file-like object opened in text mode.

    Similar to the standard library json.dump().

    Arguments:
        obj (object): The python object to serialize.
        fp (file): The python file pointer to write the serialized data to.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        newline (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

    Returns: None

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    data = dumps(obj, sort_keys=sort_keys, indent=indent, default=default, newline=newline)
    fp.write(data)

def jsload(*paths):
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

def jslines(*paths):
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

def jssave(js, *paths):
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
        dumpb(js, fd, sort_keys=True, indent=True)

def reqjsonsafe(item):
    '''
    Returns None if item is json serializable, otherwise raises an exception.
    Uses default type coercion from synapse.lib.json.dumps.
    '''
    dumps(item)
