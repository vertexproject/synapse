import os

import synapse.common as s_common

dirname = os.path.dirname(__file__)

def get(name):
    '''
    Return a storm file from the synapse storm folder.

    Example:

        text = storm.get('migrate.storm')
        await core.callStorm(text)
    '''
    with s_common.genfile(dirname, name) as fp:
        text = fp.read()
    return text.decode('utf8')
