import copy

import yarl
import aiohttp
from oauthlib import oauth1

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.config as s_config
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

class FakeClients:

    clients = dict()

    reqValidCdef = s_config.getJsValidator({
        'type': 'object',
        'properties': {
            'iden': {'type': 'string'},
            'client_id': {'type': 'string'},
            'client_secret': {'type': 'string'},
            'scope': {'type': 'string'},
            'response_type': {'type': 'string', 'enum': ['code']},
            'auth_uri': {'type': 'string'},
            'token_uri': {'type': 'string'},
            'redirect_uri': {'type': 'string'},
            'state': {
                'type': 'object',
                'properties': {
                    'auth_code': {'type': ['string', 'null']},
                    'expires_in': {'type': ['string', 'null']},
                    'expires_at': {'type': ['string', 'null']},
                    'access_token': {'type': ['string', 'null']},
                    'refresh_token': {'type': ['string', 'null']},
                    'code_verifier': {'type': ['string', 'null']}, # used w/optional pkce
                },
                'additionalProperties': False,
            },
            'extensions': {
                'type': 'object',
                'properties': {
                    'pkce': {'type': 'boolean'},
                },
                'additionalProperties': False,
            },
            'extra_auth_params': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
            },
        },
        'additionalProperties': False,
        'required': ['iden', 'client_id', 'client_secret', 'scope', 'response_type', 'auth_uri', 'token_uri'],
    })

    @classmethod
    async def addClient(cls, cdef):
        iden = cdef['iden']
        if iden in cls.clients:
            raise s_exc.DupIden(mesg=f'Duplicate OAuth V2 client iden ({iden})', iden=iden)

        cdef['response_type'] = 'code'

        cdef['state'] = {
            'auth_code': None,
            'expires_in': None,
            'expires_at': None,
            'access_token': None,
            'refresh_token': None,
            'code_verifier': None,
        }

        if cdef.get('extensions') is None:
            cdef['extensions'] = {}

        if cdef.get('extra_auth_params') is None:
            cdef['extra_auth_params'] = {}

        cls.reqValidCdef(cdef)

        cls.clients[iden] = copy.deepcopy(cdef)
        return copy.deepcopy(cdef)

    @classmethod
    async def getClient(cls, iden):
        cdef = cls.clients.get(iden)
        if cdef is not None:
            return copy.deepcopy(cdef)

    @classmethod
    async def getClients(cls):
        return [copy.deepcopy(cdef) for cdef in cls.clients.values()]

    @classmethod
    async def delClient(cls, iden):
        if iden not in cls.clients:
            raise s_exc.BadArg(mesg=f'Provided iden does not match any OAuth V2 clients ({iden})', iden=iden)
        del cls.clients[iden]

    @classmethod
    async def getToken(cls, iden):
        cdef = cls.clients.get(iden)
        if cdef is None:
            raise s_exc.BadArg(mesg=f'Provided iden does not match any OAuth V2 clients ({iden})', iden=iden)

        state = cdef['state']

        if state['auth_code'] is None:
            raise s_exc.NeedAuthCode(mesg=f'OAuth V2 client needs an authorization code ({iden})', iden=iden)

        if state['access_token'] is None:

            now = s_common.now()
            ok, data = await cls._token(cdef)
            if not ok:
                raise s_exc.StormRuntimeError(mesg=f'OAuth V2 client failed to get token ({iden}): {data}', iden=iden)

            token = data['access_token']
            state['access_token'] = token
            state['refresh_token'] = data['refresh_token']

            expires_in = data['expires_in']
            state['expires_in'] = expires_in
            state['expires_at'] = expires_in * 1000 + now

        return state['access_token']

    @classmethod
    async def refreshToken(cls, iden):
        cdef = cls.clients.get(iden)
        if cdef is None:
            raise s_exc.BadArg(mesg=f'Provided iden does not match any OAuth V2 clients ({iden})', iden=iden)

        state = cdef['state']

        if state['auth_code'] is None:
            raise s_exc.NeedAuthCode(mesg=f'OAuth V2 client needs an authorization code ({iden})', iden=iden)

        refresh_token = state['refresh_token']
        now = s_common.now()

        if refresh_token is None:
            ok, data = await cls._token(cdef)
            if not ok:
                raise s_exc.StormRuntimeError(mesg=f'OAuth V2 client failed to get token ({iden}): {data}', iden=iden)

            token = data['access_token']
            state['access_token'] = token
            state['refresh_token'] = data.get('refresh_token')

            expires_in = data['expires_in']
            state['expires_in'] = expires_in
            state['expires_at'] = expires_in * 1000 + now

        else:
            now = s_common.now()
            ok, data = await cls._refresh(cdef)
            if not ok:
                raise s_exc.StormRuntimeError(mesg=f'OAuth V2 client failed to refresh token ({iden}): {data}', iden=iden)

            token = data['access_token']
            state['access_token'] = token

            if data.get('refresh_token') is not None:  # this may or may not be changed
                state['refresh_token'] = data.get('refresh_token')

            expires_in = data['expires_in']
            state['expires_in'] = expires_in
            state['expires_at'] = expires_in * 1000 + now

        return True, None

    @staticmethod
    async def _token(cdef):
        '''
       "access_token":"2YotnFZFEjr1zCsicMWpAA",
       "token_type":"example",
       "expires_in":3600,
       "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
       "example_parameter":"example_value"
        '''

        url = cdef['token_uri']

        payload = aiohttp.FormData()
        payload.add_field('grant_type', 'authorization_code')
        payload.add_field('scope', cdef['scope'])
        payload.add_field('redirect_uri', cdef['redirect_uri'])
        payload.add_field('code', cdef['state']['auth_code'])

        code_verifier = cdef['state'].get('code_verifier')
        if code_verifier is not None:
            payload.add_field('code_verifier', code_verifier)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        # cadir = self.conf.get('tls:ca:dir')
        # ssl = None
        # if cadir is not None:
        #     ssl = s_common.getSslCtx(cadir)
        ssl = False

        auth = aiohttp.BasicAuth(cdef['client_id'], password=cdef['client_secret'])
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as sess:
            try:
                async with sess.post(url, auth=auth, headers=headers, data=payload, ssl=ssl) as resp:

                    data = await resp.json()  # fixme: try/exc on this
                    print(data)

                    if resp.status == 200:
                        return True, data

                    errmesg = data.get('error', 'error')
                    if 'error_description' in data:
                        errmesg += f': {data["error_description"]}'

                    return False, errmesg

            except Exception as e:
                # logger.exception(f'Error during http {meth} @ {url}')
                return False, str(e)

    @staticmethod
    async def _refresh(cdef):
        '''
       "access_token":"2YotnFZFEjr1zCsicMWpAA",
       "token_type":"example",
       "expires_in":3600,
       "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
       "example_parameter":"example_value"
        '''

        url = cdef['token_uri']

        payload = aiohttp.FormData()
        payload.add_field('grant_type', 'refresh_token')
        payload.add_field('refresh_token', cdef['state']['refresh_token'])

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        # cadir = self.conf.get('tls:ca:dir')
        # ssl = None
        # if cadir is not None:
        #     ssl = s_common.getSslCtx(cadir)
        ssl = False

        auth = aiohttp.BasicAuth(cdef['client_id'], password=cdef['client_secret'])
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as sess:
            try:
                async with sess.post(url, auth=auth, headers=headers, data=payload, ssl=ssl) as resp:

                    data = await resp.json()  # fixme: try/exc on this

                    if resp.status == 200:
                        return True, data

                    errmesg = data.get('error', 'error')
                    if 'error_description' in data:
                        errmesg += f': {data["error_description"]}'

                    return False, errmesg

            except Exception as e:
                # logger.exception(f'Error during http {meth} @ {url}')
                return False, str(e)

    @classmethod
    async def setAuthCode(cls, iden, code, code_verifier=None):
        cdef = cls.clients.get(iden)
        if cdef is None:
            raise s_exc.BadArg(mesg=f'Provided iden does not match any OAuth V2 clients ({iden})', iden=iden)
        cdef['state']['auth_code'] = code
        if code_verifier is not None:
            cdef['state']['code_verifier'] = code_verifier
        # todo: this would then trigger entering the background refresh loop if it wasn't set
        # todo: if it was set should probably clear out access/refresh tokens?
        # todo: should this try to get the token *right away*?

@s_stormtypes.registry.registerLib
class OAuthV2Lib(s_stormtypes.Lib):
    '''
    A Storm library to manage OAuth v2 clients.
    '''
    _storm_lib_path = ('inet', 'http', 'oauth', 'v2')
    _storm_locals = (
        {
            'name': 'add',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methAdd',
                'args': (
                    {'name': 'iden', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'client_id', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'client_secret', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'scope', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'auth_uri', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'token_uri', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'redirect_uri', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'pkce', 'type': 'boolean', 'default': True,
                     'desc': 'todo'},
                    {'name': 'params', 'type': 'dict', 'default': None,
                     'desc': 'todo'},
                ),
                'returns': {'type': 'storm:oauth:v2:client', 'desc': 'The ``storm:oauth:v2:client`` object.'},
            },
        },
        {
            'name': 'del',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methDel',
                'args': (
                    {'name': 'iden', 'type': 'str',
                     'desc': 'todo'},
                ),
                'returns': {'type': 'null', 'desc': 'todo'},
            },
        },
        {
            'name': 'get',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methAdd',
                'args': (
                    {'name': 'iden', 'type': 'str',
                     'desc': 'todo'},
                ),
                'returns': {'type': 'storm:oauth:v2:client',
                            'desc': 'The ``storm:oauth:v2:client`` object or None if it does exist.'}
            },
        },
        {
            'name': 'list',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methList',
                'returns': {'type': 'list', 'desc': 'todo'},
            },
        },
    )

    def getObjLocals(self):
        return {
            'add': self._methAdd,
            'del': self._methDel,
            'get': self._methGet,
            'list': self._methList,
        }

    async def _methAdd(self, iden, client_id, client_secret, scope, auth_uri, token_uri, redirect_uri, pkce=True, params=None):
        # todo: must add a state param on auth request (see 4.1.1 in RFC)
        # todo: stormpkgs should be able to get redirect_uri
        cdef = {
            'iden': await s_stormtypes.tostr(iden),
            'client_id': await s_stormtypes.tostr(client_id),
            'client_secret': await s_stormtypes.tostr(client_secret),
            'scope': await s_stormtypes.tostr(scope),
            'auth_uri': await s_stormtypes.tostr(auth_uri),
            'token_uri': await s_stormtypes.tostr(token_uri),
            'redirect_uri': await s_stormtypes.tostr(redirect_uri),
            'extensions': {
                'pkce': await s_stormtypes.tobool(pkce),
            },
            'extra_auth_params': await s_stormtypes.toprim(params),
        }
        # cdef = await self.runt.snap.core.addOAuthV2Client(cdef)
        cdef = await FakeClients.addClient(cdef)
        return OAuthV2Client(self.runt, cdef['iden'])

    async def _methDel(self, iden):
        iden = await s_stormtypes.tostr(iden)
        await FakeClients.delClient(iden)

    async def _methGet(self, iden):
        iden = await s_stormtypes.tostr(iden)
        # cdef = await self.runt.snap.core.getOAuthV2Client(iden)
        cdef = await FakeClients.getClient(iden)
        if cdef is not None:
            return OAuthV2Client(self.runt, cdef['iden'])

    async def _methList(self):
        return [OAuthV2Client(self.runt, cdef['iden']) for cdef in await FakeClients.getClients()]

@s_stormtypes.registry.registerType
class OAuthV2Client(s_stormtypes.Prim):
    '''
    Implements the Storm API for an OAuth V2 client instance.
    '''
    _storm_typename = 'storm:oauth:v2:client'
    _storm_locals = (
        {
            'name': 'getToken',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methGetToken',
                'returns': {'type': 'str', 'desc': 'todo'},
            },
        },
        {
            'name': 'setAuthCode',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methSetAuthCode',
                'args': (
                    {'name': 'code', 'type': 'str',
                     'desc': 'todo'},
                    {'name': 'code_verifier', 'type': 'str', 'default': None,
                     'desc': 'todo'},
                ),
                'returns': {'type': 'str', 'desc': 'todo'},
            },
        },
        {
            'name': 'refreshToken',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methRefreshToken',
                'returns': {'type': 'list', 'desc': 'todo: ok,mesg'}
            }
        },
        {
            'name': 'pack',
            'desc': 'todo',
            'type': {
                'type': 'function', '_funcname': '_methPack',
                'returns': {'type': 'dict', 'desc': 'todo'},
            },
        },
        # todo: disable, enable, reset?
    )

    def __init__(self, runt, iden, path=None):
        s_stormtypes.Prim.__init__(self, iden, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu

    def getObjLocals(self):
        return {
            'pack': self._methPack,
            'getToken': self._methGetToken,
            'setAuthCode': self._methSetAuthCode,
            'refreshToken': self._methRefreshToken,
        }

    async def value(self):
        return await FakeClients.getClient(self.valu)

    async def _methGetToken(self):
        return await FakeClients.getToken(self.valu)

    async def _methRefreshToken(self):
        return await FakeClients.refreshToken(self.valu)

    async def _methSetAuthCode(self, code, code_verifier=None):
        code = await s_stormtypes.tostr(code)
        code_verifier = await s_stormtypes.tostr(code_verifier, True)
        await FakeClients.setAuthCode(self.valu, code, code_verifier=code_verifier)

    async def _methPack(self):
        return await self.value()
