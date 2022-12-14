import yarl
from oauthlib import oauth1

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class OAuthV1Lib(s_stormtypes.Lib):
    '''
    A Storm library to handle OAuth v1 authentication.
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
    A client for doing OAuth V1 Authentication from Storm.
    '''
    _storm_locals = (
        {
            'name': 'sign',
            'desc': '''
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

@s_stormtypes.registry.registerLib
class OAuthV2Lib(s_stormtypes.Lib):
    '''
    A Storm library for managing OAuth V2 clients.
    '''
    _storm_lib_path = ('inet', 'http', 'oauth', 'v2')
    _storm_locals = (
        {
            'name': 'addProvider',
            'desc': '''
                Add a new provider configuration.

                Example:
                    Add a new provider which uses the authorization code flow::

                        $iden = $lib.guid(example, provider, oauth)
                        $conf = ({
                            "iden": $iden,
                            "name": "example_provider",
                            "client_id": "yourclientid",
                            "client_secret": "yourclientsecret",
                            "scope": "first_scope second_scope",
                            "auth_uri": "https://provider.com/auth",
                            "token_uri": "https://provider.com/token",
                            "redirect_uri": "https://local.redirect.com/oauth",
                        })

                        // Optionally enable PKCE
                        $conf.extensions = ({"pkce": $lib.true})

                        // Optionally disable SSL verification
                        $conf.ssl_verify = $lib.false

                        // Optionally provide additional key-val parameters
                        // to include when calling the auth URI
                        $conf.extra_auth_params = ({"customparam": "foo"})

                        $lib.inet.http.oauth.v2.addProvider($conf)
            ''',
            'type': {
                'type': 'function', '_funcname': '_addProvider',
                'args': (
                    {'name': 'conf', 'type': 'dict', 'desc': 'A provider configuration.'},
                ),
                'returns': {'type': 'null'},
            },
        },
        {
            'name': 'delProvider',
            'desc': 'Delete a provider configuration.',
            'type': {
                'type': 'function', '_funcname': '_delProvider',
                'args': (
                    {'name': 'iden', 'type': 'str', 'desc': 'The provider iden.'},
                ),
                'returns': {'type': 'dict', 'desc': 'The deleted provider configuration or None if it does not exist.'}
            },
        },
        {
            'name': 'getProvider',
            'desc': 'Get a provider configuration',
            'type': {
                'type': 'function', '_funcname': '_getProvider',
                'args': (
                    {'name': 'iden', 'type': 'str', 'desc': 'The provider iden.'},
                ),
                'returns': {'type': 'dict', 'desc': 'The provider configuration or None if it does not exist.'}
            },
        },
        {
            'name': 'listProviders',
            'desc': 'List provider configurations',
            'type': {
                'type': 'function', '_funcname': '_listProviders',
                'returns': {'type': 'list', 'desc': 'List of (iden, conf) tuples.'},
            },
        },
        {
            'name': 'setUserAuthCode',
            'desc': 'Set the auth code for the current user.',
            'type': {
                'type': 'function', '_funcname': '_setUserAuthCode',
                'args': (
                    {'name': 'iden', 'type': 'str', 'desc': 'The provider iden.'},
                    {'name': 'authcode', 'type': 'str', 'desc': 'The auth code for the user.'},
                    {'name': 'code_verifier', 'type': 'str', 'default': None, 'desc': 'Optional PKCE code verifier.'},
                ),
                'returns': {'type': 'null'}
            },
        },
        {
            'name': 'getUserAccessToken',
            'desc': '''
                Get the provider access token for the current user.

                Example:

                    Retrieve the token and handle needing an auth code::

                        $provideriden = $lib.globals.get("oauth:myprovider")

                        ($ok, $data) = $lib.inet.http.oauth.v2.getUserAccessToken($provideriden)

                        if $ok {
                            // $data is the token to be used in a request
                        else {
                            // $data is a message stating why the token is not available
                            // caller should now handle retrieving a new auth code for the user
                        }
            ''',
            'type': {
                'type': 'function', '_funcname': '_getUserAccessToken',
                'args': (
                    {'name': 'iden', 'type': 'str', 'desc': 'The provider iden.'},
                ),
                'returns': {'type': 'list', 'desc': 'List of (<bool>, <token/mesg>) for status and data.'},
            },
        },
        {
            'name': 'clearUserAccessToken',
            'desc': 'Clear the stored refresh data for the current user\'s provider access token.',
            'type': {
                'type': 'function', '_funcname': '_clearUserAccessToken',
                'args': (
                    {'name': 'iden', 'type': 'str', 'desc': 'The provider iden.'},
                ),
                'returns': {'type': 'dict', 'desc': 'The existing token state data or None if it did not exist.'},
            },
        }
    )

    def getObjLocals(self):
        return {
            'addProvider': self._addProvider,
            'delProvider': self._delProvider,
            'getProvider': self._getProvider,
            'listProviders': self._listProviders,
            'setUserAuthCode': self._setUserAuthCode,
            'getUserAccessToken': self._getUserAccessToken,
            'clearUserAccessToken': self._clearUserAccessToken,
        }

    async def _addProvider(self, conf):
        if not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg='addProvider() requires admin privs.')
        conf = await s_stormtypes.toprim(conf)
        await self.runt.snap.core.addOAuthProvider(conf)

    async def _delProvider(self, iden):
        if not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg='delProvider() requires admin privs.')
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.core.delOAuthProvider(iden)

    async def _getProvider(self, iden):
        if not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg='getProvider() requires admin privs.')
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.core.getOAuthProvider(iden)

    async def _listProviders(self):
        if not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg='listProviders() requires admin privs.')
        return await self.runt.snap.core.listOAuthProviders()

    async def _setUserAuthCode(self, iden, authcode, code_verifier=None):
        iden = await s_stormtypes.tostr(iden)
        authcode = await s_stormtypes.tostr(authcode)
        code_verifier = await s_stormtypes.tostr(code_verifier, True)

        useriden = self.runt.user.iden
        await self.runt.snap.core.setOAuthAuthCode(iden, useriden, authcode, code_verifier=code_verifier)

    async def _getUserAccessToken(self, iden):
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.core.getOAuthAccessToken(iden, self.runt.user.iden)

    async def _clearUserAccessToken(self, iden):
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.core.clearOAuthAccessToken(iden, self.runt.user.iden)
