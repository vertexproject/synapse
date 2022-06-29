import yarl
from oauthlib import oauth1

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class OAuthV1Lib(s_stormtypes.Lib):
    '''
    A Storm library to handle oauth v1 authentication.
    '''
    _storm_locals = (
        {
            'name': 'client',
            'desc': '''
                Initialize an OAuthV1 Client to use for signing/authentication.
            ''',
            'type': {
                'type': 'function', '_funcname': '_methClient',
                'args': (
                    {'name': 'ckey', 'type': 'str',
                     'desc': 'The OAuthV1 Consumer Key to store and use for signing requests.'},
                    {'name': 'csecret', 'type': 'str',
                     'desc': 'The OAuthV1 Consumer Secret used to sign requests.'},
                    {'name': 'atoken', 'type': 'str',
                     'desc': 'The OAuthV1 Access Token (or resource owner key) to use to sign requests.)'},
                    {'name': 'asecret', 'type': 'str',
                     'desc': 'The OAuthV1 Access Token Secret (or resource owner secret) to use to sign requests.'},
                    {'name': 'sigtype', 'type': 'str', 'default': oauth1.SIGNATURE_TYPE_QUERY,
                     'desc': 'Where to populate the signature (in the HTTP body, in the query parameters, or in the header)'},
                ),
                'returns': {
                    'type': 'storm:oauth:v1:client',
                    'desc': 'An OAuthV1 client to be used to sign requests.',
                }
            },
        },
    )

    _storm_lib_path = ('inet', 'http', 'oauth', 'v1',)

    def getObjLocals(self):
        return {
            'client': self._methClient,
            'SIG_BODY': oauth1.SIGNATURE_TYPE_BODY,
            'SIG_QUERY': oauth1.SIGNATURE_TYPE_QUERY,
            'SIG_HEADER': oauth1.SIGNATURE_TYPE_AUTH_HEADER,
        }

    async def _methClient(self, ckey, csecret, atoken, asecret, sigtype=oauth1.SIGNATURE_TYPE_QUERY):
        return OAuthV1Client(self.runt, ckey, csecret, atoken, asecret, sigtype)

@s_stormtypes.registry.registerType
class OAuthV1Client(s_stormtypes.StormType):
    '''
    A client for doing OAuth Authentication from Storm.
    '''
    _storm_locals = (
        {
            'name': 'sign',
            'desc': ''',
                Sign an OAuth request to a particular URL.
            ''',
            'type': {
                'type': 'function', '_funcname': '_methSign',
                'args': (
                    {'name': 'baseurl', 'type': 'str', 'desc': 'The base url to sign and query.'},
                    {'name': 'method', 'type': 'dict', 'default': 'GET',
                     'desc': 'The HTTP Method to use as part of signing.'},
                    {'name': 'headers', 'type': 'dict', 'default': None,
                     'desc': 'Optional headers used for signing. Can override the "Content-Type" header if the signature type is set to SIG_BODY'},
                    {'name': 'params', 'type': 'dict', 'default': None,
                     'desc': 'Optional query parameters to pass to url construction and/or signing.'},
                    {'name': 'body', 'type': 'bytes', 'default': None,
                     'desc': 'Optional HTTP body to pass to request signing.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'A 3-element tuple of ($url, $headers, $body). The OAuth signature elements will be embedded in the element specified when constructing the client.'
                },
            },
        },
    )
    _storm_typename = 'storm:oauth:v1:client'

    def __init__(self, runt, ckey, csecret, atoken, asecret, sigtype, path=None):
        s_stormtypes.StormType.__init__(self, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.sigtype = sigtype
        self.client = oauth1.Client(
            ckey,
            client_secret=csecret,
            resource_owner_key=atoken,
            resource_owner_secret=asecret,
            signature_type=sigtype
        )

    def getObjLocals(self):
        return {
            'sign': self._methSign,
        }

    async def _methSign(self, baseurl, method='GET', headers=None, params=None, body=None):
        url = yarl.URL(baseurl).with_query(await s_stormtypes.toprim(params))
        headers = await s_stormtypes.toprim(headers)
        body = await s_stormtypes.toprim(body)
        if self.sigtype == oauth1.SIGNATURE_TYPE_BODY:
            if not headers:
                headers = {'Content-Type': oauth1.rfc5849.CONTENT_TYPE_FORM_URLENCODED}
            else:
                headers['Content-Type'] = oauth1.rfc5849.CONTENT_TYPE_FORM_URLENCODED
        try:
            return self.client.sign(str(url), http_method=method, headers=headers, body=body)
        except ValueError as e:
            mesg = f'Request signing failed ({str(e)})'
            raise s_exc.StormRuntimeError(mesg=mesg) from None
