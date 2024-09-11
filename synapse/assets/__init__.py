import os
import logging

import synapse.common as s_common

logger = logging.getLogger(__name__)
dirname = os.path.dirname(__file__)

def getStorm(*names):
    '''
    Return a storm file from the synapse storm folder.

    Example:

        text = storm.get('migrate.storm')
        await core.callStorm(text)

    Example #2:
        text = storm.get('migrations', 'model-0.2.28.storm')
        await core.callStorm(text)
    '''
    fp = getAssetPath('storm', *names)
    with open(fp, 'rb') as fd:
        text = fd.read()
    return text.decode('utf8')

def getAssetPath(*names):
    fp = s_common.genpath(dirname, *names)
    if not fp.startswith(dirname):
        logger.error(f'{fp} is not in {dirname}')
        raise ValueError(f'Path escaping detected for {names}')
    if not os.path.isfile(fp):
        logger.error('{} does not exist'.format(fp))
        raise ValueError(f'Asset does not exist for {names}')
    return fp
