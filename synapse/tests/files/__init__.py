# -*- coding: utf-8 -*-
# Stdlib
import os
import json
import logging

log = logging.getLogger(__name__)

ASSETS = os.path.split(__file__)[0]

def getAssetPath(fn):
    '''
    Get a asset file path.

    Args:
        fn (str): Asset to ask for.

    Returns:
        str: Path to asset file.

    Raises:
        ValueError: If path escaping detected or the path does not exist.
    '''
    fp = os.path.join(ASSETS, fn)
    absfp = os.path.abspath(fp)
    if not absfp.startswith(ASSETS):
        log.error('{} is not in {}'.format(fn, ASSETS))
        raise ValueError('Path escaping detected')
    if not os.path.isfile(absfp):
        log.error('{} does not exist'.format(absfp))
        raise ValueError('Asset does not exist')
    return absfp

def getAssetBytes(fn):
    '''
    Get the bytes for an assets file.

    Args:
        fn (str): File to get the bytes for.

    Returns:
        bytes: The bytes for the file.

    Raises:
        ValueError: If get_asset_path goes boom
    '''
    fp = getAssetPath(fn=fn)
    with open(fp, 'rb') as f:
        return f.read()

def getAssetStr(fn):
    '''
    Get the decoded string for an asset file.

    Args:
        fn (str): File to get and decode.

    Returns:
        str: The decoded string.
    '''
    byts = getAssetBytes(fn)
    return byts.decode()

def getAssets():
    '''
    Get a list of asset names.

    Returns:
        list: A list of file names in the assets.
    '''
    ret = []
    for fdir, fdirs, fns in os.walk(ASSETS):
        if '__pycache__' in fdir:
            continue
        for fn in fns:
            if fn in ['__init__.py']:
                continue
            fp = os.path.join(fdir, fn)
            relpath = os.path.relpath(fp, ASSETS)
            ret.append(relpath)
    return ret
