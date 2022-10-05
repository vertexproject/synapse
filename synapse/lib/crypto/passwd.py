import os
import hmac
import hashlib
import logging

import synapse.exc as s_exc

import synapse.lib.coro as s_coro

from typing import AnyStr, Dict

logger = logging.getLogger(__name__)

PBKDF2 = 'pbkdf2'
PBKDF2_HASH = 'sha256'
PBKDF2_ITERATIONS = 310_000  # OWASP recommended value 20221004

DEFAULT_PTYP = PBKDF2

def _getPbkdf2(passwd):
    salt = os.urandom(32)
    func_params = {'salt': salt,
                   'iterations': PBKDF2_ITERATIONS,
                   'hash_name': PBKDF2_HASH,
                   }
    hashed = hashlib.pbkdf2_hmac(password=passwd.encode(), **func_params)
    shadow = {'type': PBKDF2,
              'hashed': hashed,
              'func_params': func_params
              }
    return shadow

def _verifyPbkdf2(passwd: AnyStr, shadow: Dict) -> bool:
    hashed = shadow.get('hashed')
    func_params = shadow.get('func_params', None)
    check = hashlib.pbkdf2_hmac(password=passwd.encode(), **func_params)
    return hmac.compare_digest(hashed, check)

async def getPbkdf2(passwd: AnyStr) -> Dict:
    return await s_coro.executor(_getPbkdf2, passwd=passwd)

async def verifyPbkdf2(passwd: AnyStr, shadow: Dict) -> bool:
    return await s_coro.executor(_verifyPbkdf2, passwd=passwd, shadow=shadow)

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
        raise s_exc.CryptoErr(mesg='type does not map to a known function', valu=DEFAULT_PTYP)
    return await func(passwd)

async def checkShadowV2(passwd: AnyStr, shadow: Dict) -> bool:
    '''
    Check a password against a shadow dictionary.

    Args:
        passwd (str): Password to check.
        shadow (dict): Data to check the password against.

    Returns:
        bool: True if the password is valid, false otherwise.
    '''
    ptyp = shadow.get('type')
    func = _vfuncs.get(ptyp)
    if func is None:
        raise s_exc.CryptoErr(mesg='type does not map to a known function', valu=ptyp)
    return await func(passwd=passwd, shadow=shadow)
