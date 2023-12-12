import os
import hmac
import base64
import binascii
import hashlib
import logging

import synapse.exc as s_exc
import synapse.common as s_common

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
    if hashed is None:
        raise s_exc.CryptoErr(mesg='No hashed in pbdkf2 shadow')

    func_params = shadow.get('func_params')
    if func_params is None:
        raise s_exc.CryptoErr(mesg='No func_params in pbdkf2 shadow')

    hash_name = func_params.get('hash_name')
    if hash_name is None:
        raise s_exc.CryptoErr(mesg='Missing hash_name in pbdkf2 shadow')

    salt = func_params.get('salt')
    if salt is None:
        raise s_exc.CryptoErr(mesg='Missing salt in pbdkf2 shadow')

    iterations = func_params.get('iterations')
    if iterations is None:
        raise s_exc.CryptoErr(mesg='Missing iterations in pbdkf2 shadow')

    check = hashlib.pbkdf2_hmac(hash_name=hash_name, password=passwd.encode(),
                                salt=salt, iterations=iterations)
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
        raise s_exc.CryptoErr(mesg=f'type [{DEFAULT_PTYP}] does not map to a known function', valu=DEFAULT_PTYP)
    return await func(passwd=passwd)

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
        raise s_exc.CryptoErr(mesg=f'type [{ptyp}] does not map to a known function', valu=ptyp)
    return await func(passwd=passwd, shadow=shadow)

async def generateAccessToken(iden=None):
    if iden is None:
        iden = s_common.guid()
    secv = s_common.guid()
    valu = f'{iden}.{secv}'.encode('utf-8')
    if len(valu) != 65:
        raise s_exc.CryptoErr(mesg=f'Token size mismatch - invalid iden provided: {iden}')
    valu = base64.urlsafe_b64encode(valu + binascii.crc32(valu).to_bytes(4, byteorder='big'))
    token = f'syn_{valu.decode("utf-8")}'
    shadow = await getShadowV2(secv)
    return iden, token, shadow

def checkAccesToken(valu):
    prefix, tokn = valu.split('_', 1)
    if prefix != 'syn':
        return False, f'Incorrect prefix, got {prefix[:40]}'
    tokn = base64.urlsafe_b64decode(tokn)
    if len(tokn) != 69:
        return False, f'Incorrect length, got {len(tokn)}'
    tokn, csum = tokn[:-4], tokn[-4:]
    calc = binascii.crc32(tokn)
    if calc != int.from_bytes(csum, byteorder='big'):
        return False, 'Invalid checksum'
    iden, secv = tokn.decode('utf-8').split('.', 1)
    return True, (iden, secv)
