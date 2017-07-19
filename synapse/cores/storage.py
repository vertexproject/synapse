#!/usr/bin/env python
# -*- coding: utf-8 -*-
# XXX Update Docstring
"""
synapse - storage.py
Created on 7/19/17.


"""
# Stdlib
import argparse
import json
import logging
import os
import sys

# Third Party Code
# Custom Code

import synapse.common as s_common
import syanpse.compat as s_compat

import synapse.lib.config as s_config

logger = logging.getLogger(__name__)


# XXX
# This is the base class for a cortex Storage object which storage layers must
# implement
class Storage(s_config.Config):
    '''
    Base class for storage layer backends for a Synapse Cortex.

    It is intended that storage layer implementations may override many of the functions provided here.
    '''
    def __init__(self, **conf):
        s_config.Config.__init__(self)

    def _getStoreType(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_getStoreType', mesg='Store does not implement getCoreType')

    def _getBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _getBlobValu', name='_getBlobValu')
        return None

    def _setBlobValu(self, key, valu):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _setBlobValu', name='_setBlobValu')
        return None

    def _hasBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _hasBlobValue', name='_hasBlobValue')
        return None

    def _delBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _delBlobValu', name='_delBlobValu')
        return None

    def _getBlobKeys(self):
        self.log(logging.ERROR, mesg='Store does not implement _getBlobKeys', name='_getBlobKeys')
        return None

    # Blobstore interface isn't clean to seperate
    def _revCorVers(self, revs):
        '''
        Update a the storage layer with a list of (vers,func) tuples.

        Args:
            revs ([(int,function)]):  List of (vers,func) revision tuples.

        Returns:
            (None)

        Each specified function is expected to update the storage layer including data migration.
        '''
        if not revs:
            return
        vsn_str = 'syn:core:{}:version'.format(self._getCoreType())
        curv = self.getBlobValu(vsn_str, -1)

        maxver = revs[-1][0]
        if maxver == curv:
            return

        if not self.getConfOpt('rev:storage'):
            raise s_common.NoRevAllow(name='rev:storage',
                                      mesg='add rev:storage=1 to cortex url to allow storage updates')

        for vers, func in sorted(revs):

            if vers <= curv:
                continue

            # allow the revision function to optionally return the
            # revision he jumped to ( to allow initial override )
            mesg = 'Warning - storage layer update occurring. Do not interrupt. [{}] => [{}]'.format(curv, vers)
            logger.warning(mesg)
            retn = func()
            logger.warning('Storage layer update completed.')
            if retn is not None:
                vers = retn

            curv = self.setBlobValu(vsn_str, vers)


# noinspection PyMissingOrEmptyDocstring
def main(options):  # pragma: no cover
    if not options.verbose:
        logging.disable(logging.DEBUG)

    sys.exit(0)

# noinspection PyMissingOrEmptyDocstring
def makeargpaser():  # pragma: no cover
    # XXX Fill in description
    parser = argparse.ArgumentParser(description="Description.")
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, action='store',
                        help='Input file to process')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Enable verbose output')
    return parser

def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    p = makeargpaser()
    opts = p.parse_args()
    main(opts)

if __name__ == '__main__':  # pragma: no cover
    _main()
