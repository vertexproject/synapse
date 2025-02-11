import io
import os
import mmap

import orjson

import synapse.exc as s_exc
import synapse.common as s_common

def loads(s):
    # Decode json string s
    try:
        return orjson.loads(s)
    except orjson.JSONDecodeError as exc:
        raise s_exc.BadJsonText(mesg=exc.args[0])

def load(fp):
    # Decode json in fp
    try:
        with mmap.mmap(fp.fileno(), 0, prot=mmap.PROT_READ) as mm:
            with memoryview(mm) as mv:
                return loads(mv)
    except ValueError:
        mesg = 'Cannot read empty file.'
        raise s_exc.BadJsonText(mesg=mesg)

def dumps(obj, sort_keys=False, indent=False, default=None, asbytes=False, append_newline=False):
    # Encode obj as a json string
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
    # Encode obj as json into fp
    asbytes = 'b' in fp.mode
    data = dumps(obj, sort_keys=sort_keys, indent=indent, default=default, asbytes=asbytes, append_newline=append_newline)
    fp.write(data)

def jsload(*paths):
    with s_common.genfile(*paths) as fd:
        if os.fstat(fd).st_size == 0:
            return None

        return load(fd)

def jslines(*paths):
    with s_common.genfile(*paths) as fd:
        for line in fd:
            yield loads(line)

def jssave(js, *paths):
    path = s_common.genpath(*paths)
    with io.open(path, 'wb') as fd:
        dump(js, fd, sort_keys=True, indent=2)

def reqjsonsafe(item):
    '''
    Returns None if item is json serializable, otherwise raises an exception.
    Uses default type coercion from built-in json.dumps.
    '''
    dumps(item)
