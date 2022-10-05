import os
import hmac
import hashlib
import logging

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.const as s_const

from typing import AnyStr, ByteString, Dict, Tuple

logger = logging.getLogger(__name__)


PBKDF2 = 'pbkdf2'
SCRYPT = 'scrypt'
DEFAULT_PTYP = PBKDF2


def _getScrypt(passwd: AnyStr,
               n: int =2**16,
               r: int =8,
               p: int =1,
               maxmem: int = s_const.megabyte * 128) -> Dict:
    salt = os.urandom(16)
    params = {
        'n': n,
        'p': p,
        'r': r,
        'salt': salt,
        'maxmem': maxmem,
    }

    hashed = hashlib.scrypt(passwd.encode(), **params)
    params['type'] = SCRYPT
    params['hashed'] = hashed
    return params

def _verifyScrypt(passwd: AnyStr, params: Dict) -> bool:
    hashed = params.pop('hashed')
    check = hashlib.scrypt(passwd.encode(), **params)
    # Constant time comparison
    return hmac.compare_digest(hashed, check)

async def getScrypt(passwd: AnyStr) -> Dict:
    return await s_coro.executor(_getScrypt, passwd=passwd)

async def verifyScrypt(passwd: AnyStr, params: Dict) -> bool:
    return await s_coro.executor(_verifyScrypt, passwd=passwd, params=params)

def _getPcrypt(passwd):
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
    return await s_coro.executor(_getPcrypt, passwd=passwd)

async def verifyPbkdf2(passwd: AnyStr, params: Dict) -> bool:
    return await s_coro.executor(_verifyPbkdf2, passwd=passwd, params=params)

efuncs = {
    PBKDF2: getPbkdf2,
    SCRYPT: getScrypt,
}

vfuncs = {
    PBKDF2: verifyPbkdf2,
    SCRYPT: verifyScrypt,
}

assert set(efuncs.keys()) == set(vfuncs.keys())

async def getShadowV2(passwd: AnyStr, ptyp: AnyStr =DEFAULT_PTYP) -> Dict:
    '''
    Get the shadow dictionary for a given password.

    Args:
        passwd (str): Password to hash.
        ptyp (str): The password hash type.

    Returns:
        dict: A dictionary containing shadowed password information.
    '''
    func = efuncs.get(ptyp)
    if func is None:
        raise s_exc.BadArg(mesg='ptyp does not map to a known function', valu=ptyp)
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
    func = vfuncs.get(ptyp)
    if func is None:
        raise s_exc.BadArg(mesg='ptyp does not map to a known function', valu=ptyp)
    return await func(passwd=passwd, params=params)
