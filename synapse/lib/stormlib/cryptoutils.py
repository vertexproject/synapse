import cryptography.exceptions as c_exc

import synapse.exc as s_exc

import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.stormtypes as s_stormtypes

# cryptography key-loading can raise any of these; the Storm boundary treats them all as bad
# input so no raw cryptography/Python exception escapes into the runtime.
_loaderrors = (ValueError, TypeError, c_exc.UnsupportedAlgorithm, c_exc.InvalidKey)

class CryptoKey(s_stormtypes.Prim):
    '''
    Base class for the ``crypto:rsa:key`` and ``crypto:ecc:key`` Storm objects.

    The object wraps a backend ``PriKey`` or ``PubKey`` and, when converted to a
    primitive, yields the PEM encoded key as a string.
    '''
    def __init__(self, runt, key, isprivate):
        s_stormtypes.Prim.__init__(self, None)
        self.runt = runt
        self.key = key
        self.isprivate = isprivate

        self.locls.update({
            'isPrivate': isprivate,
            'pubkey': self._methPubkey,
            'encode': self._methEncode,
            'sign': self._methSign,
            'verify': self._methVerify,
        })

    def value(self):
        return self.key.dump(fmt='pem').decode()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPubkey(self):
        if not self.isprivate:
            raise s_exc.BadArg(mesg=f'The {self._storm_typename} is already public-only.')

        return type(self)(self.runt, self.key.public(), False)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methEncode(self, fmt='pem'):
        fmt = await s_stormtypes.tostr(fmt)
        byts = self.key.dump(fmt=fmt)
        if fmt.lower() == 'pem':
            return byts.decode()

        return byts

def reqPadding(padding):
    padding = padding.lower()
    if padding not in ('pkcs1v15', 'pss'):
        raise s_exc.BadArg(mesg=f'Invalid padding scheme: {padding}', padding=padding)

    return padding

async def reqBytes(valu, name):
    valu = await s_stormtypes.toprim(valu)
    if not isinstance(valu, bytes):
        raise s_exc.BadArg(mesg=f'{name} must be bytes.', name=name)

    return valu

async def reqKey(valu, name):
    valu = await s_stormtypes.toprim(valu)
    if isinstance(valu, str):
        valu = valu.encode()

    if not isinstance(valu, bytes):
        raise s_exc.BadArg(mesg=f'{name} must be bytes or str.', name=name)

    return valu

def loadRsaPriv(byts):
    try:
        return s_rsa.PriKey.load(byts, fmt='pem')
    except _loaderrors as e:
        raise s_exc.BadArg(mesg=f'Invalid RSA private key: {e}') from None

def loadRsaPub(byts):
    try:
        return s_rsa.PubKey.load(byts, fmt='pem')
    except _loaderrors as e:
        raise s_exc.BadArg(mesg=f'Invalid RSA public key: {e}') from None
