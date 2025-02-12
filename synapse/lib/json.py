import io
import os
import mmap

import orjson

import synapse.exc as s_exc
import synapse.common as s_common

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
    except ValueError:
        mesg = 'Cannot read empty file.'
        raise s_exc.BadJsonText(mesg=mesg)

def dumps(obj, sort_keys=False, indent=False, default=None, asbytes=False, append_newline=False):
    '''
    Serialize a python object to a string.

    Similar to the standard library json.dumps().

    Arguments:
        obj (object): The python object to serialize.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        asbytes (Optional[bool]): Serialized data should be returned as bytes instead of a string. Default: False.
        append_newlines (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

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

    if append_newline:
        opts |= orjson.OPT_APPEND_NEWLINE

    try:
        ret = orjson.dumps(obj, option=opts, default=default)
        if not asbytes:
            ret = ret.decode()
        return ret
    except orjson.JSONEncodeError as exc:
        raise s_exc.MustBeJsonSafe(mesg=exc.args[0])

def dump(obj, fp, sort_keys=False, indent=False, default=None, append_newline=False):
    '''
    Serialize a python object to a string.

    Similar to the standard library json.dump().

    Note: This function attempts to automatically detect if the file was opened
    in text or binary mode by inspecting `fp.mode`.

    Arguments:
        obj (object): The python object to serialize.
        fp (file): The python file pointer to write the serialized data to.
        sort_keys (Optional[bool]): Sort dictionary keys. Default: False.
        indent (Optional[bool]): Include 2 spaces of indentation. Default: False.
        default (Optional[callable]): Callback for serializing unknown object types. Default: None.
        append_newlines (Optional[bool]): Append a newline to the end of the serialized data. Default: False.

    Returns: None

    Raises:
        synapse.exc.MustBeJsonSafe: This exception is raised when a python object cannot be serialized.
    '''
    asbytes = 'b' in fp.mode
    data = dumps(obj, sort_keys=sort_keys, indent=indent, default=default, asbytes=asbytes, append_newline=append_newline)
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
    path = s_common.genpath(*paths)
    with io.open(path, 'wb') as fd:
        dump(js, fd, sort_keys=True, indent=True)

def reqjsonsafe(item):
    '''
    Returns None if item is json serializable, otherwise raises an exception.
    Uses default type coercion from synapse.lib.json.dumps.
    '''
    dumps(item)
