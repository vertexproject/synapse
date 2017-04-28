#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - superhash.py
Created on 4/26/17.

Generate the hashsets and guid (superhash) for a file.
"""
# Stdlib
import os
import sys
import json
import logging
import argparse
# Custom Code
import synapse.axon as s_axon
import synapse.lib.output as s_output

log = logging.getLogger(__name__)


def compute_hashes(fp):
    """
    Compute the superhash information for a file path
    :param fp: Path to compute
    :return: Tuple containing the superhash (guid) and other hashes for the file.
    """
    hs = s_axon.HashSet()
    with open(fp, 'rb') as f:
        guid, hashd = hs.eatfd(fd=f)
    return guid, hashd


def main(argv, outp=None):
    if outp == None:  # pragma: no cover
        outp = s_output.OutPut()

    p = makeargpaser()
    opts = p.parse_args(args=argv)

    results = []
    for fp in opts.input:
        try:
            guid, hashd = compute_hashes(fp=fp)
        except:
            outp.printf('Failed to compute superhash for {}'.format(fp))
        else:
            results.append((fp, guid, hashd))

    if opts.ingest:
        l = []
        for fp, guid, hashd in results:
            hashd['name'] = os.path.basename(fp)
            d = {"props": hashd}
            hl = [guid, d]
            l.append(hl)
        if len(l) == 1:
            l = l[0]
        outp.printf(json.dumps(l, sort_keys=True, indent=2))
    else:
        for fp, guid, hashd in results:
            outp.printf('Superhash for: {}'.format(fp))
            hashd['guid'] = guid
            keys = list(hashd.keys())
            keys.sort()
            for key in keys:
                value = hashd.get(key)
                outp.printf('{}\t{}'.format(key, value))

    return 0


def makeargpaser():
    parser = argparse.ArgumentParser(description="Compute the guid and hashes for a file.")
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, action='append',
                        help='Input file to process. May be specified multple times.')
    parser.add_argument('--ingest', dest='ingest', default=False, action='store_true',
                        help='Display the data in a format that can be placed into a ingest definition.')
    return parser


def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    main(sys.argv[1:])


if __name__ == '__main__':  # pragma: no cover
    _main()
