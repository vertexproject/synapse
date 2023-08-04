import hmac
import hashlib
import logging

import aiohttp


import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.time as s_time


logger = logging.getLogger(__name__)

class AwsCredentialError(s_exc.CryptoErr):
    '''
    An exception raised when unable to process AWS credentials
    '''
    pass

class AWSProvider(s_base.Base):
    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self.accesskeyid = None
        self.secretkeyid = None
        self.token = None
        self.expiration = None
        self.lastupdated = None
        self.expires_after = None

    def storeCredentials(self, creds: dict):
        self.token = creds.get('Token')
        self.accesskeyid = creds.get('AccessKeyId')
        self.secretkeyid = creds.get('SecretKeyId')
        self.expiration = s_time.parse(creds.get('Expiration'))
        self.lastupdated = s_time.parse(creds.get('LastUpdated'))
        # Keep credentials alive for 80% of their lifetime before we'll attempt to get new credentials
        self.expires_after = self.lastupdated + int ((self.expiration - self.lastupdated) * 0.8)

class AWSEC2Provider(AWSProvider):
    EC2_METADATA_ENDPOINT = 'http://169.254.169.254'

    async def __anit__(self, role=None):
        await AWSProvider.__anit__(self)
        self.role = None

    async def updateCredentials(self):
        '''
        Get credentials from the endpoint metadata service
        '''
        role = self.role
        async with aiohttp.ClientSession() as session:
            # XXX Check code
            if role is None:
                # Get the default EC2 instance role name
                async with session.get(self.EC2_METADATA_ENDPOINT + '/latest/meta-data/iam/info') as resp:
                    metadata = await resp.json()
                    arn = metadata.get('InstanceProfileArn')
                    role = arn.split('/', 1)[1]
                    logger.debug(f'Resolved role via metadata: {role}')

            async with session.get(self.EC2_METADATA_ENDPOINT + f'/latest/iam/security-credentials/{role}') as resp:
                creds = await resp.json()

        return creds

    async def getCredentials(self, role=None):
        if self.expiration is None:
            logger.debug(f'Retrieving initial credentials for {self.role}')
            _creds = await self.updateCredentials()
            self.storeCredentials(_creds)
        elif self.expires_after > s_common.now():
            # TODO Use ioloop monotonic clock?
            logger.debug(f'Getting updated credentials for {self.role}')
            _creds = await self.updateCredentials()
            self.storeCredentials(_creds)
        ret = {
            'token': self.token,
            'accesskeyid': self.accesskeyid,
            'secretkeyid': self.secretkeyid,
        }

        return ret
