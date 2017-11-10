#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - loadrows.py
Created on 7/26/17.

Load rows from a savefile (or a dumprows file) into a Cortex Storage object.
"""
# Stdlib
import sys
import gzip
import time
import logging
import argparse

# Custom Code
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# noinspection PyMissingOrEmptyDocstring
def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()
    parser = makeargpaser()
    opts = parser.parse_args(argv)

    if not opts.verbose:
        logging.disable(logging.DEBUG)

    # Check to see if we're working with a savefile or a dumprows file
    decompress = False
    discard_first_event = False
    with open(opts.input, 'rb') as fd:
        gen = s_msgpack.iterfd(fd)
        tufo0 = next(gen)
        if tufo0[0] == 'syn:cortex:rowdump:info':
            outp.printf('Restoring from a dumprows file.')
            discard_first_event = True
            decompress = tufo0[1].get('rows:compress')
            if decompress:
                outp.printf('Gzip row compression enabled.')
        else:
            outp.printf('Restoring from a savefile')
        # No longer need that generator around with the dangler to fd
        del gen

    storconf = {'rev:storage': False}
    if opts.revstorage:  # pragma: no cover
        storconf['rev:storage'] = True

    with open(opts.input, 'rb') as fd:
        gen = s_msgpack.iterfd(fd)
        if discard_first_event:
            next(gen)
        with s_cortex.openstore(opts.store, storconf=storconf) as store:
            outp.printf('Starting row level restore')
            tick = time.time()
            i = 0
            nrows = 0
            for event in gen:
                if decompress and 'rows' in event[1]:
                    event[1]['rows'] = s_msgpack.un(gzip.decompress(event[1].get('rows')))
                i += 1
                if i % 250 == 0:
                    outp.printf('Loaded {} events'.format(i))
                store.loadbus.dist(event)
                _nrows = len(event[1].get('rows', ()))
                nrows += _nrows
                if _nrows and i % 10 == 0:
                    logger.debug('Loaded %s rows', nrows)

            tock = time.time()
            outp.printf('Done loading events - took {} seconds.'.format(tock - tick))
    outp.printf('Fin')
    return 0

# noinspection PyMissingOrEmptyDocstring
def makeargpaser():  # pragma: no cover
    parser = argparse.ArgumentParser(description="Load a savefile into a Cortex.")
    parser.add_argument('-s', '--store', dest='store', required=True, type=str, action='store',
                        help='Cortex Storage URL to load data too.')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, action='store',
                        help='File to output the row data too')
    parser.add_argument('--enable-revstorage', dest='revstorage', default=False, action='store_true',
                        help='Set the rev:storage value to True - this will allow for storage layer '
                             'revisions to take place when creating the storage object.')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Enable verbose output')
    return parser

def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    _main()
