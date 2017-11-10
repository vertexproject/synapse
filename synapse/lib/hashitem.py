import types
import hashlib

import synapse.lib.msgpack as s_msgpack

def hashitem(item):
    '''
    Generate a uniq hash for the JSON compatible primitive data structure.
    '''
    norm = normitem(item)
    byts = s_msgpack.en(norm)
    return hashlib.md5(byts).hexdigest()

def normitem(item):
    normer = normers.get(type(item))
    if normer:
        return normer(item)

    return item

def normdict(item):
    return list(sorted([(normitem(key), normitem(val)) for key, val in item.items() if val is not None]))

def normiter(item):
    return list([normitem(i) for i in item if i is not None])

normers = {
    dict: normdict,
    list: normiter,
    tuple: normiter,
    types.GeneratorType: normiter,
}
