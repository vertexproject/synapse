from __future__ import absolute_import,unicode_literals

import logging

logger = logging.getLogger(__name__)

def setProcName(name):
    '''
    Set the process title/name for process listing.
    '''
    logger.info('setProcName: %s' % (name,))

def initHostInfo():
    return {}
