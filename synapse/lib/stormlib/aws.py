import hmac

import hashlib
import logging

import synapse.exc as s_exc
import synapse.lib.crypto.aws as s_crypt_aws
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerType
class CredsHelper(s_stormtypes.Prim):
    _storm_typename = 'aws:creds'

    def __init__(self, provider, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.provider = provider
        self.gtors.update({
            'creds': self._getCreds,
        })

    async def _getCreds(self):
        return await self.provider.getCredentials()

    # AWS V4 Signing logic goes here?

@s_stormtypes.registry.registerLib
class LibAWS(s_stormtypes.Lib):
    _storm_lib_path = ('aws', )

    def getObjLocals(self):
        return {
            'creds': self._awscreds,
        }

    async def _awscreds(self):
        # TODO This should normally come from a Cortex API or runtime API...
        provider = await s_crypt_aws.AWSEC2Provider.anit()
        self.runt.onfini(provider)
        return CredsHelper(provider)
