import os
import json
import urllib
import logging
import functools

import fastjsonschema

import synapse.common as s_common
import synapse.lib.datfile as s_datfile
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

def get(name, defval=None):
    '''
    Return an object from the embedded synapse data folder.

    Example:

        for tld in synapse.data.get('iana.tlds'):
            dostuff(tld)

    NOTE: Files are named synapse/data/<name>.mpk
    '''
    with s_datfile.openDatFile(f'synapse.data/{name}.mpk') as fd:
        return s_msgpack.un(fd.read())

def getJSON(name):
    with s_datfile.openDatFile(f'synapse.data/{name}.json') as fd:
        return json.loads(fd.read())

def path(*names):
    return s_common.genpath(dirname, *names)

def refHandler(func):
    '''
    Simple decorator for jsonschema ref handlers to allow for an automatic
    default behavior of fetching the schema if the custom ref handlers returns
    None.
    '''

    @functools.wraps(func)
    def wrapper(uri):
        ret = func(uri)
        if ret is None:
            if __debug__:
                logger.warning('Fetching remote JSON schema: %s. Consider caching to disk.', uri)
            return fastjsonschema.ref_resolver.resolve_remote(uri, {})
        return ret

    return wrapper

@refHandler
def localSchemaRefHandler(uri):
    '''
    This function parses the given URI to get the path component and then tries
    to resolve the referenced schema from the 'jsonschemas' directory of
    synapse.data.
    '''
    try:
        parts = urllib.parse.urlparse(uri)
    except ValueError:
        return None

    filename = path('jsonschemas', *parts.path.split('/'))
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return None

    # Check for path traversal. Unlikely, but still check
    if not filename.startswith(path('jsonschemas')):
        return None

    with open(filename, 'r') as fp:
        return json.load(fp)

# This default_schema_ref_handlers dictionary can be used by any jsonschema
# validator to attempt to resolve schema '$ref' values locally from disk first,
# and then fallback to downloading from the internet.
default_schema_ref_handlers = {
    'http': localSchemaRefHandler,
    'https': localSchemaRefHandler,
}
