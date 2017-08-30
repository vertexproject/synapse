import logging

logger = logging.getLogger(__name__)

def initHostInfo():
    return {
        'format': 'macho',
        'platform': 'darwin',
    }
