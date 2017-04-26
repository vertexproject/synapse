#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - hashset.py
Created on 4/26/17.

Generate the hashsets and guid (superhash) for a file.
"""
# Stdlib
import argparse
import json
import logging
import os
import sys
# Custom Code
import synapse.axon as s_axon


log = logging.getLogger(__name__)


# noinspection PyMissingOrEmptyDocstring
def main(options):  # pragma: no cover

    hs = s_axon.HashSet()
    with open(options.input, 'rb') as f:
        guid, hashd = hs.eatfd(fd=f)

    if options.ingest:
        hashd['name'] = os.path.basename(options.input)
        d = {"props": hashd}
        l = [guid, d]
        print(json.dumps(l, sort_keys=True, indent=2))
    else:
        hashd['guid'] = guid
        keys = list(hashd.keys())
        keys.sort()
        for key in keys:
            value = hashd.get(key)
            print('{}\t{}'.format(key, value))

    sys.exit(0)


# noinspection PyMissingOrEmptyDocstring
def makeargpaser():  # pragma: no cover
    parser = argparse.ArgumentParser(description="Compute the guid and hashes for a file.")
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, action='store',
                        help='Input file to process')
    parser.add_argument('--ingest', dest='ingest', default=False, action='store_true',
                        help='Display the data in a format that can be placed into a ingest definition.')
    return parser


def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    p = makeargpaser()
    opts = p.parse_args()
    main(opts)


if __name__ == '__main__':  # pragma: no cover
    _main()
