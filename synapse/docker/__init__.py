import os

from synapse.cortex import openurl


def getSyncCore():
    core_url = os.getenv('SYN_UPSTREAM_CORE')
    if core_url:
        return openurl(core_url)
