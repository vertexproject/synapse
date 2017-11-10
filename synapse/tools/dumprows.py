#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - dumprows.py
Created on 7/24/17.

Dump all of the rows from a cortex storage instance.
"""
# Stdlib
import os
import sys
import gzip
import json
import time
import logging
import argparse

# Third Party Code
# Custom Code
import synapse
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.tufo as s_tufo
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

def gen_backup_tufo(options):
    d = {'rows:compress': options.compress,
         'synapse:version': synapse.version,
         'synapse:rows:output': options.output,
         'synapse:cortex:input': options.store,
         'synapse:cortex:blob_store': options.dump_blobstore,
         'synapse:cortex:revstore': options.revstorage,
         'time:created': s_common.now(),
         'python:version': s_common.version
         }
    tufo = s_tufo.tufo('syn:cortex:rowdump:info', **d)
    return tufo

preset_args = {
    'sqlite': {'slicebytes': 4,
               'incvalu': 20}
}
DUMP_MEGS = 4

def dump_rows(outp, fd, store, compress=False, genrows_kwargs=None):
    outp.printf('Starting row dump')
    if not genrows_kwargs:
        genrows_kwargs = {}
    i = 0
    j = 0
    cur_bytes = 0
    bufs = []
    kwargs = preset_args.get(store.getStoreType(), {})
    kwargs.update(genrows_kwargs)
    tick = time.time()

    for rows in store.genStoreRows(**kwargs):
        j += len(rows)
        i += len(rows)
        tufo = s_tufo.tufo('core:save:add:rows', rows=rows)
        if compress:
            tufo[1]['rows'] = gzip.compress(s_msgpack.en(rows), 9)
        byts = s_msgpack.en(tufo)
        bufs.append(byts)
        cur_bytes += len(byts)
        if cur_bytes > s_axon.megabyte * DUMP_MEGS:
            fd.write(b''.join([byts for byts in bufs]))
            outp.printf('Stored {} rows, total {} rows'.format(j, i))
            bufs = []
            cur_bytes = 0
            j = 0
    # There still may be rows we need too write out.
    if bufs:
        fd.write(b''.join([byts for byts in bufs]))
        outp.printf('Stored {} rows, total {} rows'.format(j, i))
        bufs = []
    tock = time.time()
    outp.printf('Done dumping rows - took {} seconds.'.format(tock - tick))
    outp.printf('Dumped {} rows'.format(i))

def dump_blobs(outp, fd, store):
    i = 0
    outp.printf('Dumping blobstore')
    for key in store.getBlobKeys():
        valu = store.getBlobValu(key)
        tufo = s_tufo.tufo('syn:core:blob:set', key=key, valu=s_msgpack.en(valu))
        byts = s_msgpack.en(tufo)
        fd.write(byts)
        i += 1
    outp.printf('Done dumping {} keys from blobstore.'.format(i))

def dump_store(outp, fd, store,
               compress=False,
               dump_blobstore=False,
               genrows_kwargs=None):
    outp.printf('Starting data dump from storage object.')
    dump_rows(outp, fd, store, compress=compress, genrows_kwargs=genrows_kwargs)
    if dump_blobstore:
        dump_blobs(outp, fd, store)
    outp.printf('Done dumping data from the store.')

# noinspection PyMissingOrEmptyDocstring
def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()
    parser = makeargpaser()
    opts = parser.parse_args(argv)

    if not opts.verbose:
        logging.disable(logging.DEBUG)

    if os.path.isfile(opts.output) and not opts.force:
        outp.printf('Cannot overwrite a backup.')
        return 1

    genrows_kwargs = {}
    if opts.extra_args:
        with open(opts.extra_args, 'rb') as fd:
            genrows_kwargs = json.loads(fd.read().decode())

    storconf = {'rev:storage': False}
    if opts.revstorage:
        storconf['rev:storage'] = True

    backup_tufo = gen_backup_tufo(opts)

    with open(opts.output, 'wb') as fd:
        fd.write(s_msgpack.en(backup_tufo))
        with s_cortex.openstore(opts.store, storconf=storconf) as store:
            dump_store(outp, fd, store,
                       compress=opts.compress,
                       dump_blobstore=opts.dump_blobstore,
                       genrows_kwargs=genrows_kwargs)

    outp.printf('Fin')
    return 0

# noinspection PyMissingOrEmptyDocstring
def makeargpaser():
    parser = argparse.ArgumentParser(description="Dump the rows of a cortex into a file in savefile format.")
    parser.add_argument('-s', '--store', dest='store', required=True, type=str, action='store',
                        help='Cortex Storage URL to dump.')
    parser.add_argument('-o', '--output', dest='output', required=True, type=str, action='store',
                        help='File to output the row data too')
    parser.add_argument('--compress', dest='compress', default=False, action='store_true',
                        help='Compress the stored rows using gzip encoding. Takes longer to '
                             'store/restore from but reduces file size.')
    parser.add_argument('--enable-revstorage', dest='revstorage', default=False, action='store_true',
                        help='Set the rev:storage value to True - this will allow for storage layer '
                             'revisions to take place when creating the storage object.')
    parser.add_argument('--dump-blobstore', dest='dump_blobstore', default=False, action='store_true',
                        help='Dump the blob store in the backup as well.')
    parser.add_argument('-f', '--force', dest='force', default=False, action='store_true',
                        help='Allow overwriting the backup file.')
    parser.add_argument('-e', '--extra-storeargs', dest='extra_args', default=None, type=str,
                        help='JSON file containing kwargs which are passed to genStoreRows. '
                             'These may override any presets present in the dumprows tools. '
                             'May be provided for performance tuning purposes.')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Enable verbose output')
    return parser

def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    _main()
