import os
import copy
import heapq
import asyncio
import logging

import aiohttp

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.schemas as s_schemas
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

KEY_LEN = 32          # length of a provider/user iden in a key
REFRESH_WINDOW = 0.5  # refresh in REFRESH_WINDOW * expires_in
DEFAULT_TIMEOUT = 10  # secs

def normOAuthTokenData(issued_at, data):
    '''
    Normalize timestamps to be in epoch millis and set expires_at/refresh_at.
    '''
    s_schemas.reqValidOauth2TokenResponse(data)
    expires_in = data['expires_in']
    return {
        'access_token': data['access_token'],
        'expires_in': expires_in,
        'expires_at': issued_at + expires_in * 1000,
        'refresh_at': issued_at + (expires_in * REFRESH_WINDOW) * 1000,
        'refresh_token': data.get('refresh_token'),
    }

az_tfile_envar = 'AZURE_FEDERATED_TOKEN_FILE'
def _getAzureTokenFile() -> tuple[bool, str]:
    fp = os.getenv(az_tfile_envar, None)
    if fp is None:
        return False, f'{az_tfile_envar} environment variable is not set.'
    if os.path.exists(fp):
        with open(fp, 'r') as fd:
            assertion = fd.read()
            return True, assertion
    else:
        return False, f'{az_tfile_envar} file does not exist {fp}'

az_clientid_envar = 'AZURE_CLIENT_ID'
def _getAzureClientId() -> tuple[bool, str]:
    valu = os.getenv(az_clientid_envar, None)
    if valu is None:
        return False, f'{az_clientid_envar} environment variable is not set.'
    if valu:
        return True, valu
    else:
        return False, f'{az_clientid_envar} is set to an empty string.'


class OAuthMixin(s_nexus.Pusher):
    '''
    Mixin for Cells to organize and execute OAuth token refreshes.
    '''

    async def _initOAuthManager(self):

        slab = self.slab
        self._oauth_clients = s_lmdbslab.SlabDict(slab, db=slab.initdb('oauth:v2:clients'))     # key=<provider><user>
        self._oauth_providers = s_lmdbslab.SlabDict(slab, db=slab.initdb('oauth:v2:providers')) # key=<provider>

        self._oauth_sched_map = {}
        self._oauth_sched_heap = []
        self._oauth_sched_wake = asyncio.Event()
        self.onfini(self._oauth_sched_wake.set)

        self._oauth_actviden = self.addActiveCoro(self._runOAuthRefreshLoop)

        # For testing
        self._oauth_sched_ran = asyncio.Event()
        self._oauth_sched_empty = asyncio.Event()

    async def _runOAuthRefreshLoop(self):
        self._oauth_sched_map.clear()
        self._oauth_sched_heap.clear()
        self._oauth_sched_wake.clear()

        for provideriden, useriden, clientconf in self.listOAuthClients():
            self._scheduleOAuthItem(provideriden, useriden, clientconf)

        await self._oauthRefreshLoop()

    def _scheduleOAuthItem(self, provideriden, useriden, clientconf):
        if not self.isactive:
            return

        if clientconf.get('error'):
            return

        if not clientconf.get('refresh_token'):
            logger.warning(f'OAuth V2 client missing token to schedule refresh provider={provideriden} user={useriden}')
            return

        refresh_at = clientconf['refresh_at']

        newitem = (refresh_at, provideriden, useriden)

        old_refresh_at = self._oauth_sched_map.get(newitem[1:])
        if old_refresh_at == refresh_at:
            return

        if old_refresh_at is not None:
            # there's an old item for this client in the refresh queue to remove
            self._oauth_sched_heap.remove((old_refresh_at, *newitem[1:]))
            heapq.heapify(self._oauth_sched_heap)

        self._oauth_sched_map[newitem[1:]] = refresh_at
        heapq.heappush(self._oauth_sched_heap, newitem)

        if self._oauth_sched_heap[0] == newitem:
            # the new item is at the front of the line so wake up the loop if its waiting
            self._oauth_sched_wake.set()

    async def _oauthRefreshLoop(self):

        while not self.isfini:

            while self._oauth_sched_heap:

                refresh_at, provideriden, useriden = self._oauth_sched_heap[0]
                refresh_in = int(max(0, refresh_at - s_common.now()) / 1000)

                if await s_coro.event_wait(self._oauth_sched_wake, timeout=refresh_in):
                    self._oauth_sched_wake.clear()
                    continue

                if self.isfini:  # pragma: no cover
                    break

                _, provideriden, useriden = heapq.heappop(self._oauth_sched_heap)
                self._oauth_sched_map.pop((provideriden, useriden), None)

                logger.debug(f'Refreshing OAuth V2 token for provider={provideriden} user={useriden}')

                providerconf = self._getOAuthProvider(provideriden)
                if providerconf is None:
                    logger.debug(f'OAuth V2 provider does not exist for provider={provideriden}')
                    continue

                user = self.auth.user(useriden)
                if user is None:
                    await self._setOAuthTokenData(provideriden, useriden, {'error': 'User does not exist'})
                    continue
                if user.isLocked():
                    await self._setOAuthTokenData(provideriden, useriden, {'error': 'User is locked'})
                    continue

                clientconf = self._oauth_clients.get(provideriden + useriden)
                if clientconf is None:
                    logger.debug(f'OAuth V2 client does not exist for provider={provideriden} user={useriden}')
                    continue

                ok, data = await self._refreshOAuthAccessToken(providerconf, clientconf, useriden)
                if not ok:
                    logger.warning(f'OAuth V2 token refresh failed provider={provideriden} user={useriden} data={data}')

                await self._setOAuthTokenData(provideriden, useriden, data)
                self._oauth_sched_ran.set()

            self._oauth_sched_empty.set()
            await s_coro.event_wait(self._oauth_sched_wake)
            self._oauth_sched_wake.clear()
            self._oauth_sched_ran.clear()

    async def _getOAuthAccessToken(self, providerconf, useriden, authcode, code_verifier=None):

        ok, data = await self._getAuthData(providerconf, useriden)
        if not ok:
            return ok, data

        token_uri = providerconf['token_uri']
        ssl_verify = providerconf['ssl_verify']

        auth, formdata = self._unpackAuthData(data)

        formdata.add_field('grant_type', 'authorization_code')
        formdata.add_field('scope', providerconf['scope'])
        formdata.add_field('redirect_uri', providerconf['redirect_uri'])
        formdata.add_field('code', authcode)
        if code_verifier is not None:
            formdata.add_field('code_verifier', code_verifier)

        return await self._fetchOAuthToken(token_uri, auth, formdata, ssl_verify=ssl_verify)

    async def _refreshOAuthAccessToken(self, providerconf, clientconf, useriden):

        ok, data = await self._getAuthData(providerconf, useriden)
        if not ok:
            return ok, data

        token_uri = providerconf['token_uri']
        ssl_verify = providerconf['ssl_verify']
        refresh_token = clientconf['refresh_token']

        auth, formdata = self._unpackAuthData(data)

        formdata.add_field('grant_type', 'refresh_token')
        formdata.add_field('refresh_token', refresh_token)

        ok, data = await self._fetchOAuthToken(token_uri, auth, formdata, ssl_verify=ssl_verify, retries=3)
        if ok and not data.get('refresh_token'):
            # if a refresh_token is not provided in the response persist the existing token
            data['refresh_token'] = refresh_token

        return ok, data

    async def _getAuthData(self, providerconf, useriden):
        isok = False
        ret = {}
        auth_scheme = providerconf['auth_scheme']

        if auth_scheme == 'basic':
            ret['auth'] = {'login': providerconf['client_id'], 'password': providerconf['client_secret']}
            ret['formdata'] = {}
            isok = True

        elif auth_scheme == 'client_assertion':
            assertion = None
            client_id = providerconf.get('client_id', None)
            client_assertion = providerconf['client_assertion']

            if (info := client_assertion.get('cortex:callstorm')):
                opts = {
                    'view': info['view'],
                    'vars': info.get('vars', {}),
                    'user': useriden,
                }
                try:
                    ok, info = await self.callStorm(info['query'], opts=opts)
                except Exception as e:
                    isok = False
                    ret['error'] = f'Error executing callStorm: {e}'
                else:
                    if not ok:
                        return ok, info
                    assertion = info.get('token')

            elif (info := client_assertion.get('msft:azure:workloadidentity')):
                ok, valu = _getAzureTokenFile()
                if not ok:
                    return ok, {'error': valu}
                assertion = valu
                if info.get('client_id'):
                    ok, valu = _getAzureClientId()
                    if not ok:
                        return ok, {'error': valu}
                    client_id = valu

            else:
                isok = False
                ret['error'] = f'Unknown client_assertions data: {client_assertion}'

            if assertion:
                formdata = {
                    'client_id': client_id,
                    'client_assertion': assertion,
                    'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                }
                ret['formdata'] = formdata
                isok = True

        else:
            isok = False
            ret['error'] = f'Unknown authorization scheme: {auth_scheme}'

        return isok, ret

    @staticmethod
    def _unpackAuthData(data: dict) -> tuple[aiohttp.BasicAuth | None, aiohttp.FormData]:
        auth = data.get('auth', None)  # type: dict | None
        if auth:
            auth = aiohttp.BasicAuth(auth.get('login'), password=auth.get('password'))
        formdata = aiohttp.FormData()
        for k, v in data.get('formdata', {}).items():
            formdata.add_field(k, v)
        return auth, formdata

    async def _fetchOAuthToken(self, url, auth, formdata, ssl_verify=True, retries=1):

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        attempts = 0
        issued_at = s_common.now()

        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

        ssl = self.getCachedSslCtx(verify=ssl_verify)

        async with aiohttp.ClientSession(timeout=timeout) as sess:

            while True:
                attempts += 1

                try:
                    async with sess.post(url, auth=auth, headers=headers, data=formdata, ssl=ssl) as resp:

                        if resp.status == 200:
                            data = await resp.json()
                            return True, normOAuthTokenData(issued_at, data)

                        if resp.status < 500:
                            data = await resp.json()

                            errmesg = data.get('error', 'unknown error')
                            if 'error_description' in data:
                                errmesg += f': {data["error_description"]}'

                            return False, {'error': errmesg + f' (HTTP code {resp.status})'}

                        retn = False, {'error': f'Token API returned HTTP code {resp.status}'}

                except asyncio.TimeoutError:
                    retn = False, {'error': f'Token API request timed out'}

                except Exception as e:
                    logger.exception(f'Error fetching token data from {url}')
                    return False, {'error': str(e)}

                if attempts <= retries:
                    await self.waitfini(2 ** (attempts - 1))
                    continue

                return retn

    async def addOAuthProvider(self, conf):

        conf = s_schemas.reqValidOauth2Provider(conf)
        iden = conf['iden']
        if self._getOAuthProvider(iden) is not None:
            raise s_exc.DupIden(mesg=f'Duplicate OAuth V2 client iden ({iden})', iden=iden)

        # N.B. The schema ensures that the possible values in the conf are valid
        # when they are provided. Since writing multi-path schemas in draft07 is
        # overly complicated, some of the mutual exclusion values and logical
        # "is this meaningful?" type checks are made here before pushing the
        # nexus event to create the provider.

        client_secret = conf.get('client_secret')
        client_assertion = conf.get('client_assertion', {})

        if client_assertion and client_secret:
            mesg = 'client_assertion and client_secret provided. These are mutually exclusive options.'
            raise s_exc.BadArg(mesg=mesg)
        if not client_assertion and not client_secret:
            mesg = 'client_assertion and client_secret missing. These are mutually exclusive options and one must be provided.'
            raise s_exc.BadArg(mesg=mesg)

        auth_scheme = conf.get('auth_scheme')
        client_id = conf.get('client_id')
        if auth_scheme == 'basic':
            if not client_id:
                raise s_exc.BadArg(mesg='Must provide client_id for auth_scheme=basic')
            if not client_secret:
                raise s_exc.BadArg(mesg='Must provide client_secret for auth_scheme=basic')

        elif auth_scheme == 'client_assertion':
            if (info := client_assertion.get('cortex:callstorm')) is not None:
                if not hasattr(self, 'callStorm'):
                    mesg = f'cortex:callstorm client assertion not supported by {self.__class__.__name__}'
                    raise s_exc.BadArg(mesg=mesg)

                if not client_id:
                    raise s_exc.BadArg(mesg='Must provide client_id for with cortex:callstorm provider.')

                text = info['query']
                # Validate the query text
                try:
                    await self.reqValidStorm(text)
                except s_exc.BadSyntax as e:
                    raise s_exc.BadArg(mesg=f'Bad storm query: {e.get("mesg")}') from None
                view = self.getView(info['view'])
                if view is None:
                    raise s_exc.BadArg(mesg=f'View {info["view"]} does not exist.')
            elif (info := client_assertion.get('msft:azure:workloadidentity')) is not None:
                if not info.get('token'):
                    raise s_exc.BadArg(mesg='msft:azure:workloadidentity token key must be true')
                ok, tknkvalu = _getAzureTokenFile()
                if not ok:
                    raise s_exc.BadArg(mesg=f'Failed to get the client_assertion data: {tknkvalu}')
                if info.get('client_id'):
                    if client_id:
                        raise s_exc.BadArg(mesg='Cannot specify a fixed client_id and a dynamic client_id value.')
                    ok, idvalu = _getAzureClientId()
                    if not ok:
                        raise s_exc.BadArg(mesg=f'Failed to get the client_id data: {idvalu}')
        else:  # pragma: no cover
            raise s_exc.BadArg(mesg=f'Unknown auth_scheme={auth_scheme}')

        await self._push('oauth:provider:add', conf)

    @s_nexus.Pusher.onPush('oauth:provider:add')
    async def _addOAuthProvider(self, conf):
        iden = conf['iden']
        if self._getOAuthProvider(iden) is None:
            self._oauth_providers.set(iden, conf)

    def _getOAuthProvider(self, iden):
        conf = self._oauth_providers.get(iden)
        if conf is not None:
            return copy.deepcopy(conf)

    async def getOAuthProvider(self, iden):
        conf = self._getOAuthProvider(iden)
        if conf is not None:
            conf.pop('client_secret', None)
        return conf

    async def listOAuthProviders(self):
        return [(iden, await self.getOAuthProvider(iden)) for iden in self._oauth_providers.keys()]

    async def delOAuthProvider(self, iden):
        if self._getOAuthProvider(iden) is not None:
            return await self._push('oauth:provider:del', iden)

    @s_nexus.Pusher.onPush('oauth:provider:del')
    async def _delOAuthProvider(self, iden):
        for clientiden in list(self._oauth_clients.keys()):
            if clientiden.startswith(iden):
                self._oauth_clients.pop(clientiden)

        conf = self._oauth_providers.pop(iden)
        if conf is not None:
            conf.pop('client_secret', None)

        return conf

    async def getOAuthClient(self, provideriden, useriden):
        conf = self._oauth_clients.get(provideriden + useriden)
        if conf is not None:
            return copy.deepcopy(conf)
        return None

    def listOAuthClients(self):
        '''
        Returns:
            list: List of (provideriden, useriden, conf) for each client.
        '''
        return [(iden[:KEY_LEN], iden[KEY_LEN:], copy.deepcopy(conf)) for iden, conf in self._oauth_clients.items()]

    async def getOAuthAccessToken(self, provideriden, useriden):

        if self._getOAuthProvider(provideriden) is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        clientconf = await self.getOAuthClient(provideriden, useriden)
        if clientconf is None:
            return False, 'Auth code has not been set'

        # if the client has an error return None so caller can start oauth flow again
        err = clientconf.get('error')
        if err is not None:
            logger.debug(f'OAuth V2 client token unavailable provider={provideriden} user={useriden} err={err}')
            return False, err

        # never return an expired token
        expires_at = clientconf['expires_at']
        if expires_at < s_common.now():
            logger.debug(f'OAuth V2 token is expired ({expires_at}) for provider={provideriden} user={useriden}')
            return False, 'Token is expired'

        return True, clientconf.get('access_token')

    async def clearOAuthAccessToken(self, provideriden, useriden):
        '''
        Remove a client access token by clearing the configuration.
        This will prevent further refreshes (if scheduled),
        and a new auth code will be required the next time an access token is requested.
        '''
        if self._oauth_clients.get(provideriden + useriden) is not None:
            return await self._push('oauth:client:data:clear', provideriden, useriden)

    @s_nexus.Pusher.onPush('oauth:client:data:clear')
    async def _clearOAuthAccessToken(self, provideriden, useriden):
        return self._oauth_clients.pop(provideriden + useriden)

    async def setOAuthAuthCode(self, provideriden, useriden, authcode, code_verifier=None):
        '''
        Typically set as the end result of a successful OAuth flow.
        An initial access token and refresh token will be immediately requested,
        and the client will be loaded into the schedule to be background refreshed.
        '''
        providerconf = self._getOAuthProvider(provideriden)
        if providerconf is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        await self.clearOAuthAccessToken(provideriden, useriden)

        ok, data = await self._getOAuthAccessToken(providerconf, useriden, authcode, code_verifier=code_verifier)
        if not ok:
            raise s_exc.SynErr(mesg=f'Failed to get OAuth v2 token: {data["error"]}')
        await self._setOAuthTokenData(provideriden, useriden, data)

    @s_nexus.Pusher.onPushAuto('oauth:client:data:set')
    async def _setOAuthTokenData(self, provideriden, useriden, data):
        iden = provideriden + useriden
        self._oauth_clients.set(iden, data)
        self._scheduleOAuthItem(provideriden, useriden, data)
