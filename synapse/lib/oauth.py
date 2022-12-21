import copy
import heapq
import asyncio
import logging

import aiohttp

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

KEY_LEN = 32          # length of a provider/user iden in a key
REFRESH_WINDOW = 0.5  # refresh in REFRESH_WINDOW * expires_in
DEFAULT_TIMEOUT = 10  # secs

reqValidProvider = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'flow_type': {'type': 'string', 'default': 'authorization_code', 'enum': ['authorization_code']},
        'auth_scheme': {'type': 'string', 'default': 'basic', 'enum': ['basic']},
        'client_id': {'type': 'string'},
        'client_secret': {'type': 'string'},
        'scope': {'type': 'string'},
        'ssl_verify': {'type': 'boolean', 'default': True},
        'auth_uri': {'type': 'string'},
        'token_uri': {'type': 'string'},
        'redirect_uri': {'type': 'string'},
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
    'required': ['iden', 'name', 'client_id', 'client_secret', 'scope', 'auth_uri', 'token_uri', 'redirect_uri'],
})

reqValidTokenResponse = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'access_token': {'type': 'string'},
        'expires_in': {'type': 'number', 'exclusiveMinimum': 0},
    },
    'additionalProperties': True,
    'required': ['access_token', 'expires_in'],
})

def normOAuthTokenData(issued_at, data):
    '''
    Normalize timestamps to be in epoch millis and set expires_at/refresh_at.
    '''
    reqValidTokenResponse(data)
    expires_in = data['expires_in']
    return {
        'access_token': data['access_token'],
        'expires_in': expires_in,
        'expires_at': issued_at + expires_in * 1000,
        'refresh_at': issued_at + (expires_in * REFRESH_WINDOW) * 1000,
        'refresh_token': data.get('refresh_token'),
    }

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

                ok, data = await self._refreshOAuthAccessToken(providerconf, clientconf)
                if not ok:
                    logger.warning(f'OAuth V2 token refresh failed provider={provideriden} user={useriden} data={data}')

                await self._setOAuthTokenData(provideriden, useriden, data)
                self._oauth_sched_ran.set()

            self._oauth_sched_empty.set()
            await s_coro.event_wait(self._oauth_sched_wake)
            self._oauth_sched_wake.clear()

    async def _getOAuthAccessToken(self, providerconf, authcode, code_verifier=None):
        token_uri = providerconf['token_uri']
        ssl_verify = providerconf['ssl_verify']

        formdata = aiohttp.FormData()
        formdata.add_field('grant_type', 'authorization_code')
        formdata.add_field('scope', providerconf['scope'])
        formdata.add_field('redirect_uri', providerconf['redirect_uri'])
        formdata.add_field('code', authcode)
        if code_verifier is not None:
            formdata.add_field('code_verifier', code_verifier)

        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])
        return await self._fetchOAuthToken(token_uri, auth, formdata, ssl_verify=ssl_verify)

    async def _refreshOAuthAccessToken(self, providerconf, clientconf):
        token_uri = providerconf['token_uri']
        ssl_verify = providerconf['ssl_verify']
        refresh_token = clientconf['refresh_token']

        formdata = aiohttp.FormData()
        formdata.add_field('grant_type', 'refresh_token')
        formdata.add_field('refresh_token', refresh_token)

        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])
        ok, data = await self._fetchOAuthToken(token_uri, auth, formdata, ssl_verify=ssl_verify, retries=3)
        if ok and not data.get('refresh_token'):
            # if a refresh_token is not provided in the response persist the existing token
            data['refresh_token'] = refresh_token

        return ok, data

    async def _fetchOAuthToken(self, url, auth, formdata, ssl_verify=True, retries=1):

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        attempts = 0
        issued_at = s_common.now()

        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

        cadir = self.conf.get('tls:ca:dir')
        if ssl_verify is False:
            ssl = False
        elif cadir:
            ssl = s_common.getSslCtx(cadir)
        else:
            ssl = None

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
        conf = reqValidProvider(conf)

        iden = conf['iden']
        if self._getOAuthProvider(iden) is not None:
            raise s_exc.DupIden(mesg=f'Duplicate OAuth V2 client iden ({iden})', iden=iden)

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
            conf.pop('client_secret')
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
            conf.pop('client_secret')

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

        ok, data = await self._getOAuthAccessToken(providerconf, authcode, code_verifier=code_verifier)
        if not ok:
            raise s_exc.SynErr(mesg=f'Failed to get OAuth v2 token: {data["error"]}')

        await self._setOAuthTokenData(provideriden, useriden, data)

    @s_nexus.Pusher.onPushAuto('oauth:client:data:set')
    async def _setOAuthTokenData(self, provideriden, useriden, data):
        iden = provideriden + useriden
        self._oauth_clients.set(iden, data)
        self._scheduleOAuthItem(provideriden, useriden, data)
