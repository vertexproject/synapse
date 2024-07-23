import os

import synapse.common as s_common

dirname = os.path.dirname(__file__)

def getStorm(*names):
    '''
    Return a storm file from the synapse storm folder.

    Example:

        text = storm.get('migrate.storm')
        await core.callStorm(text)

    Example #2:
        text = storm.get('migrations', 'model-0.2.27.storm')
        await core.callStorm(text)
    '''
    with s_common.genfile(dirname, 'storm', *names) as fp:
        text = fp.read()
    return text.decode('utf8')
