import copy
import hmac

import hashlib
import logging

import synapse.exc as s_exc
import synapse.lib.crypto.aws as s_crypt_aws
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerType
class AWSCredsHelper(s_stormtypes.Prim):
    _storm_typename = 'aws:creds'

    def __init__(self, provider, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.provider = provider
        self.gtors.update({
            'creds': self._getCreds,
        })

    async def _getCreds(self):
        return await self.provider.getCredentials()

@s_stormtypes.registry.registerType
class AWSSigner(s_stormtypes.Prim):
    _storm_typename = 'aws:signer'
    def __init__(self, service, region, provider, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.service = service
        self.region = region
        self.signer = s_crypt_aws.AWSSigv4Signer(service, region, provider)
        self.locls.update({
            'sign': self._methSignature,
        })

    async def _methSignature(self, meth, url, headers=None, payloadhash=None):
        meth = await s_stormtypes.tostr(meth)
        url = await s_stormtypes.tostr(url)
        headers = await s_stormtypes.toprim(headers)  # TODO validate dict || none
        payloadhash = await s_stormtypes.toprim(payloadhash)  # TODO validate str || none

        if headers is None:
            headers = {}
        else:
            headers = copy.deepcopy(headers)

        headers.update(
            await self.signer.signRequest(meth, url, headers, payloadhash=payloadhash)
        )

        return headers

@s_stormtypes.registry.registerLib
class LibAWS(s_stormtypes.Lib):
    _storm_lib_path = ('aws', )

    def getObjLocals(self):
        return {
            'creds': self._methAwsCreds,
            'signer': self._methAwsSigner,
        }

    async def _methAwsCreds(self):
        # TODO This should normally come from a Cortex API or runtime API...
        # TODO dictate parameters about the provider you want!
        provider = await s_crypt_aws.AWSEC2Provider.anit()
        self.runt.onfini(provider)
        return AWSCredsHelper(provider)

    async def _methAwsSigner(self, service, region, provider):
        region = await s_stormtypes.tostr(region)
        service = await s_stormtypes.tostr(service)
        # The provider needs to be a AWSCredsHelper
        if not isinstance(provider, AWSCredsHelper):
            raise s_exc.BadArg(mesg=f'provider must be an {AWSCredsHelper._storm_typename} instance.',
                               name='provider')
        return AWSSigner(service, region, provider.provider)
