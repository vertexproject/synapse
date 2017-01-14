from __future__ import absolute_import,unicode_literals

import types
import hashlib

import synapse.common as s_common

def hashitem(item):
    '''
    Generate a uniq hash for the JSON compatible primitve data structure.
    '''
    norm = normitem(item)
    byts = s_common.msgenpack(norm)
    return hashlib.md5(byts).hexdigest()

def normitem(item):
    normer = normers.get( type(item) )
    if normer:
        return normer(item)

    return item

def normdict(item):
    return list( sorted( [ (normitem(key),normitem(val)) for key,val in item.items() if val != None ] ) )

def normiter(item):
    return list( [ normitem(i) for i in item if i != None ] )

normers = {
    dict:normdict,
    list:normiter,
    tuple:normiter,
    types.GeneratorType:normiter,
}

