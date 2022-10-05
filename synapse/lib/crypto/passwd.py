import os
import hmac
import hashlib
import logging

import synapse.exc as s_exc

import synapse.lib.coro as s_coro

from typing import AnyStr, Dict

logger = logging.getLogger(__name__)

PBKDF2 = 'pbkdf2'
DEFAULT_PTYP = PBKDF2

def _getPbkdf2(passwd):
    salt = os.urandom(32)
    hash_name = 'sha256'
    params = {'salt': salt,
              'iterations': 310_000  # OWASP recommended value 20221004
              }
    hashed = hashlib.pbkdf2_hmac(hash_name=hash_name, password=passwd.encode(), **params)
    params['hash_name'] = hash_name
    params['type'] = PBKDF2
    params['hashed'] = hashed
    return params

def _verifyPbkdf2(passwd: AnyStr, params: Dict) -> bool:
    hashed = params.pop('hashed')
    hash_name = params.pop('hash_name', None)
    check = hashlib.pbkdf2_hmac(hash_name=hash_name, password=passwd.encode(), **params)
    return hmac.compare_digest(hashed, check)

async def getPbkdf2(passwd: AnyStr) -> Dict:
    return await s_coro.executor(_getPbkdf2, passwd=passwd)

async def verifyPbkdf2(passwd: AnyStr, params: Dict) -> bool:
    return await s_coro.executor(_verifyPbkdf2, passwd=passwd, params=params)

_efuncs = {
    PBKDF2: getPbkdf2,
}

_vfuncs = {
    PBKDF2: verifyPbkdf2,
}

assert set(_efuncs.keys()) == set(_vfuncs.keys())

async def getShadowV2(passwd: AnyStr) -> Dict:
    '''
    Get the shadow dictionary for a given password.

    Args:
        passwd (str): Password to hash.
        ptyp (str): The password hash type.

    Returns:
        dict: A dictionary containing shadowed password information.
    '''
    func = _efuncs.get(DEFAULT_PTYP)
    if func is None:
        raise s_exc.CryptoErr(mesg='ptyp does not map to a known function', valu=DEFAULT_PTYP)
    return await func(passwd)

async def checkShadowV2(passwd: AnyStr, params: Dict) -> bool:
    '''
    Check a password against a shadow dictionary.

    Args:
        passwd (str): Password to check.
        params (dict): Data to check the password against.

    Returns:
        bool: True if the password is valid, false otherwise.
    '''
    params = dict(params)  # Shallow copy so we can pop values out of it
    ptyp = params.pop('type')
    func = _vfuncs.get(ptyp)
    if func is None:
        raise s_exc.CryptoErr(mesg='ptyp does not map to a known function', valu=ptyp)
    return await func(passwd=passwd, params=params)
