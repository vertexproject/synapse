import os
import json
import hmac
import hashlib
import logging
import datetime

import urllib.parse as u_parse

import aiohttp


import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.time as s_time

import typing

logger = logging.getLogger(__name__)

class AwsCredentialError(s_exc.CryptoErr):
    '''
    An exception raised when unable to process AWS credentials
    '''
    pass

class AwsSigningError(s_exc.CryptoErr):
    '''
    An exception raised due to an error signing an AWS requests.
    '''

class AWSCredentialProvider(s_base.Base):

    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self.accesskeyid = None
        self.secretaccesskey = None
        self.token = None
        self.expiration = None
        self.lastupdated = None
        self.expires_after = None

    def getProvType(self):
        return self._getProvType()

    def _getProvType(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(mesg=f'_getProvType not implemented for {self.__class__.__name__}')

    async def getCredentials(self):
        return await self._getCredentials()

    async def _getCredentials(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(mesg=f'_getCredentials not implemented for {self.__class__.__name__}')

    async def updateCredentials(self):
        '''
        Refresh the credentials for a given provider.

        Generally uses should use getCredentials()
        '''
        return await self._updateCredentials()

    async def _updateCredentials(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(mesg=f'_updateCredentials not implemented for {self.__class__.__name__}')

class AWSEC2Provider(AWSCredentialProvider):
    # IDMS provider endpoint
    EC2_METADATA_ENDPOINT = 'http://169.254.169.254'

    async def __anit__(self, role: str =None):
        await AWSCredentialProvider.__anit__(self)
        self.role = role
        self._machinetokenlifetime = '21600'

    def _getProvType(self):
        return 'idms'

    async def _updateCredentials(self):
        '''
        Get credentials from the endpoint metadata service
        '''
        role = self.role
        async with aiohttp.ClientSession() as session:
            # Get machine token
            headers = {'X-aws-ec2-metadata-token-ttl-seconds': self._machinetokenlifetime}
            async with session.put(self.EC2_METADATA_ENDPOINT + '/latest/api/token', headers=headers) as resp:
                token = await resp.text()

            headers = {'X-aws-ec2-metadata-token': token}
            # XXX Check code
            if role is None:
                # Get the default EC2 instance role name
                async with session.get(self.EC2_METADATA_ENDPOINT + '/latest/meta-data/iam/info',
                                       headers=headers) as resp:
                    text = await resp.text()
                    metadata = json.loads(text)
                    arn = metadata.get('InstanceProfileArn')
                    role = arn.split('/', 1)[1]
                    logger.debug(f'Resolved role via metadata: {role}')

            async with session.get(self.EC2_METADATA_ENDPOINT + f'/latest/meta-data/iam/security-credentials/{role}',
                                   headers=headers) as resp:
                text = await resp.text()
                creds = json.loads(text)

        self.token = creds.get('Token')
        self.accesskeyid = creds.get('AccessKeyId')
        self.secretaccesskey = creds.get('SecretAccessKey')
        self.expiration = s_time.parse(creds.get('Expiration'))
        self.lastupdated = s_time.parse(creds.get('LastUpdated'))
        # Keep credentials alive for 80% of their lifetime before we'll attempt to get new credentials
        self.expires_after = self.lastupdated + int((self.expiration - self.lastupdated) * 0.8)

        return creds

    async def _getCredentials(self):
        if self.expiration is None:
            _creds = await self.updateCredentials()
        elif self.expires_after > s_common.now():
            _creds = await self.updateCredentials()
        ret = {
            'token': self.token,
            'accesskeyid': self.accesskeyid,
            'secretaccesskey': self.secretaccesskey,
        }
        return ret

class AWSEnvarProvider(AWSCredentialProvider):
    AWS_TOKEN_VARS = (
        'AWS_SECURITY_TOKEN',
        'AWS_SESSION_TOKEN',
    )
    async def __anit__(self, region='us-east-1', role=None):
        await AWSCredentialProvider.__anit__(self)
        self.role = None

    def _getProvType(self):
        return 'env'

    async def _getCredentials(self):
        # TODO: Support refreshableCredentials
        if self.accesskeyid is None:
            await self.updateCredentials()

        ret = {
            'token': self.token,
            'accesskeyid': self.accesskeyid,
            'secretaccesskey': self.secretaccesskey,
        }
        return ret

    async def _updateCredentials(self):
        self.accesskeyid = os.environ.get('AWS_ACCESS_KEY_ID')
        self.secretaccesskey = os.environ.get('AWS_SECRET_ACCESS_KEY')
        for envar in self.AWS_TOKEN_VARS:
            valu = os.environ.get(envar)
            if valu:
                self.token = valu
                break

class AWSSigv4Signer:
    METHODS_NO_BODY = {'DELETE', 'GET', 'HEAD'}
    EMPTY_SHA256_HASH = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    AWS4_REQUEST = 'aws4_request'
    AWS4_ALGORITHM = 'AWS4-HMAC-SHA256'
    TIMESTAMP_FMT = '%Y%m%dT%H%M%SZ'
    def __init__(self,
                 service: str,
                 region: str,
                 provider: AWSCredentialProvider,
                 ):
        self.service = service
        self.region = region
        self.provider = provider

    async def signRequest(self,
                          method: str,
                          url: str,
                          headers: typing.Optional[dict] = None,
                          payloadhash: typing.Optional[str] = None,
                          ):
        cnfo = await self.provider.getCredentials()
        token = cnfo.get('token')

        secret_key = cnfo.get('secretaccesskey')
        accesskeyid = cnfo.get('accesskeyid')

        method = method.upper()

        parsed_url = u_parse.urlsplit(url)

        if headers is None:
            headers = {}

        if payloadhash is None:
            if method in self.METHODS_NO_BODY:
                payloadhash = self.EMPTY_SHA256_HASH
            else:
                mesg = f'payload hash required when method [{method=}] not in {self.METHODS_NO_BODY}'
                raise AwsSigningError(mesg=mesg, method=method)

        now = datetime.datetime.utcnow().strftime(self.TIMESTAMP_FMT)
        additional_headers = {
            "x-amz-content-sha256": payloadhash,
            "x-amz-date": now
        }

        if token:
            additional_headers['x-amz-security-token'] = token

        canonical_headers = sorted(
            {
                'host': parsed_url.netloc,
                **{key.lower(): valu for key, valu in headers.items()},
                **{key.lower(): valu for key, valu in additional_headers.items()},
            }.items()
        )
        signed_headers = ';'.join([k for k, _ in canonical_headers])

        canonical_query = u_parse.urlencode(sorted(u_parse.parse_qsl(parsed_url.query)),
                                            quote_via=u_parse.quote)

        canonical_request = '\n'.join([
            method,
            parsed_url.path,
            canonical_query,
            '\n'.join('{}:{}'.format(key, valu) for key, valu in canonical_headers),
            "",
            signed_headers,
            payloadhash,
        ])

        string_to_sign = '\n'.join([
            self.AWS4_ALGORITHM,
            now,
            '/'.join((now[:8], self.region, self.service, self.AWS4_REQUEST)),
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])

        kdate = hmac.digest(f'AWS4{secret_key}'.encode(), now[:8].encode(), 'sha256')
        kregion = hmac.digest(kdate, self.region.encode(), 'sha256')
        kservice = hmac.digest(kregion, self.service.encode(), 'sha256')
        ksignature = hmac.digest(kservice, self.AWS4_REQUEST.encode(), 'sha256')

        signature = hmac.digest(ksignature, string_to_sign.encode(), 'sha256')
        signature = s_common.ehex(signature)

        credential = '/'.join((accesskeyid, now[:8], self.region, self.service, self.AWS4_REQUEST))

        auth_header = f'{self.AWS4_ALGORITHM} Credential={credential}, SignedHeaders={signed_headers},' \
                      f' Signature={signature}'

        return {**additional_headers, 'Authorization': auth_header}
