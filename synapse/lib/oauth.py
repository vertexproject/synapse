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

reqValidProvider = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'flow_type': {'type': 'string', 'enum': ['authorization_code']},
        'client_id': {'type': 'string'},
        'client_secret': {'type': 'string'},
        'scope': {'type': 'string'},
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
    'required': ['iden', 'name', 'flow_type', 'client_id', 'client_secret',
                 'scope', 'auth_uri', 'token_uri', 'redirect_uri'],
})

class OAuthManager(s_nexus.Pusher):
    '''
    Organize and execute OAuth token refreshes.
    '''

    async def __anit__(self, cell, nexsroot=None):
        await s_nexus.Pusher.__anit__(self, 'oauth', nexsroot=nexsroot)

        self.cell = cell

        slab = self.cell.slab
        self.clients = s_lmdbslab.SlabDict(slab, db=slab.initdb('oauth:v2:clients'))
        self.providers = s_lmdbslab.SlabDict(slab, db=slab.initdb('oauth:v2:providers'))

        # self.enabled = True  # todo
        self.refresh_window = 0.5

        self.ssl = None
        cadir = self.cell.conf.get('tls:ca:dir')
        if cadir is not None:
            self.ssl = s_common.getSslCtx(cadir)

        self.timeout = aiohttp.ClientTimeout(total=10)

        self.schedule_run = None
        self.schedule_heap = []
        self.schedule_task = None
        self.schedule_wake = asyncio.Event()

        # For testing
        self._schedule_item_ran = asyncio.Event()

    async def initActive(self):
        self._loadSchedule()

    async def initPassive(self):
        self._clearSchedule()

    def _clearSchedule(self):
        if self.schedule_task is not None:
            self.schedule_task.cancel()
            self.schedule_task = None

        self.schedule_run = None
        self.schedule_heap.clear()
        self.schedule_wake.clear()

    def _loadSchedule(self):
        if not self.cell.isactive:
            return

        self._clearSchedule()

        for provideriden, useriden, clientconf in self.listClients():
            self._scheduleRefreshItem(provideriden, useriden, clientconf)

        self.schedule_task = self.schedCoro(self._refreshLoop())  # todo: make this an active coro?

    def _scheduleRefreshItem(self, provideriden, useriden, clientconf):
        # todo: could stuff other things into clientconf like enabled
        if not self.cell.isactive:
            return

        refresh_at = clientconf.get('refresh_at')
        if refresh_at is None or clientconf.get('refresh_token') is None:
            return

        if self.schedule_run is not None and refresh_at < self.schedule_run[0]:
            # this item should supersede the current item so reload the schedule
            self._loadSchedule()
            return

        # todo: this should prevent duplicating clients not just by refresh_at
        item = (refresh_at, provideriden, useriden)
        if item in self.schedule_heap:
            return

        heapq.heappush(self.schedule_heap, item)
        self.schedule_wake.set()

    async def _refreshLoop(self):

        while not self.isfini:

            while self.schedule_heap:

                self.schedule_run = heapq.heappop(self.schedule_heap)
                refresh_at, provideriden, useriden = self.schedule_run

                refresh_in = int(max(0, refresh_at - s_common.now()) / 1000)
                logger.debug(f'Waiting to refresh OAuth V2 token in {refresh_in}s for: {self.schedule_run}')

                if await self.waitfini(refresh_in):
                    break

                providerconf = self._getProvider(provideriden)
                if providerconf is None:
                    logger.warning(f'OAuth V2 provider does not exist ({provideriden})')
                    continue

                user = self.cell.auth.user(useriden)
                if user is None:
                    await self._setClientTokenData(provideriden, useriden, {'error': 'User does not exist'})
                    continue
                if user.isLocked():
                    await self._setClientTokenData(provideriden, useriden, {'error': 'User is locked'})
                    continue

                clientconf = self.clients.get(provideriden + useriden)
                if clientconf is None or clientconf.get('refresh_token') is None:
                    self._schedule_item_ran.set()
                    continue

                ok, data = await self._refreshAccessToken(providerconf, clientconf)
                if not ok:
                    logger.warning(f'Failed to refresh token for provider,user ({provideriden},{useriden}): {data}')

                await self._setClientTokenData(provideriden, useriden, data)

                self._schedule_item_ran.set()

            await s_coro.event_wait(self.schedule_wake)
            self.schedule_wake.clear()

    def _normTokenData(self, issued_at, data):
        expires_in = data.get('expires_in')
        return {
            'access_token': data.get('access_token'),
            'expires_in': expires_in,
            'expires_at': issued_at + expires_in * 1000,
            'refresh_at': issued_at + (expires_in * self.refresh_window) * 1000,
            'refresh_token': data.get('refresh_token'),
        }

    async def _getAccessToken(self, providerconf, authcode, code_verifier=None):
        formdata = aiohttp.FormData()
        formdata.add_field('grant_type', 'authorization_code')
        formdata.add_field('scope', providerconf['scope'])
        formdata.add_field('redirect_uri', providerconf['redirect_uri'])
        formdata.add_field('code', authcode)
        if code_verifier is not None:
            formdata.add_field('code_verifier', code_verifier)

        # todo: support a different type of auth-type?
        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])
        return await self._fetchToken(providerconf['token_uri'], auth, formdata)

    async def _refreshAccessToken(self, providerconf, clientconf):
        formdata = aiohttp.FormData()
        formdata.add_field('grant_type', 'refresh_token')
        formdata.add_field('refresh_token', clientconf['refresh_token'])

        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])
        return await self._fetchToken(providerconf['token_uri'], auth, formdata)

    async def _fetchToken(self, url, auth, formdata):

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        issued_at = s_common.now()

        async with aiohttp.ClientSession(timeout=self.timeout) as sess:

            try:
                async with sess.post(url, auth=auth, headers=headers, data=formdata, ssl=self.ssl) as resp:

                    data = await resp.json()

                    if resp.status == 200:
                        return True, self._normTokenData(issued_at, data)

                    errmesg = data.get('error', 'unknown error')
                    if 'error_description' in data:
                        errmesg += f': {data["error_description"]}'

                    return False, {'error': errmesg}

            except Exception as e:
                logger.exception('Error fetching token data')
                return False, {'error': str(e)}

    async def addProvider(self, conf):
        conf = reqValidProvider(conf)

        iden = conf['iden']
        if self._getProvider(iden) is not None:
            raise s_exc.DupIden(mesg=f'Duplicate OAuth V2 client iden ({iden})', iden=iden)

        await self._push('oauth:provider:add', conf)

    @s_nexus.Pusher.onPush('oauth:provider:add')
    async def _addProvider(self, conf):
        iden = conf['iden']
        if self._getProvider(iden) is None:
            self.providers.set(iden, conf)

    def _getProvider(self, iden):
        conf = self.providers.get(iden)
        if conf is not None:
            return copy.deepcopy(conf)

    async def getProvider(self, iden):
        conf = self._getProvider(iden)
        if conf is not None:
            conf.pop('client_secret')
        return conf

    async def listProviders(self):
        return [(iden, await self.getProvider(iden)) for iden in self.providers.keys()]

    async def delProvider(self, iden):
        if self._getProvider(iden) is not None:
            return await self._push('oauth:provider:del', iden)

    @s_nexus.Pusher.onPush('oauth:provider:del')
    async def _delProvider(self, iden):
        for clientiden in list(self.clients.keys()):
            if clientiden.startswith(iden):
                self.clients.pop(clientiden)
        return self.providers.pop(iden)

    async def getClient(self, provideriden, useriden):
        conf = self.clients.get(provideriden + useriden)
        if conf is not None:
            return copy.deepcopy(conf)
        return None

    def listClients(self):
        return [(iden[:32], iden[32:], copy.deepcopy(conf)) for iden, conf in self.clients.items()]

    async def getClientAccessToken(self, provideriden, useriden):

        if self._getProvider(provideriden) is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        clientconf = await self.getClient(provideriden, useriden)
        if clientconf is None:
            return None

        err = clientconf.get('error')
        if err is not None:
            raise s_exc.BadDataValu(mesg=f'Token unavailable due to to error: {err}', iden=provideriden, user=useriden)

        # never return an expired token
        if clientconf['expires_at'] < s_common.now():
            logger.debug(f'OAuth V2 token is expired for provider,user ({provideriden},{useriden})')
            return None

        return clientconf.get('access_token')

    async def clearClientAccessToken(self, provideriden, useriden):
        if self.clients.get(provideriden + useriden) is not None:
            return await self._push('oauth:client:data:clear', provideriden, useriden)

    @s_nexus.Pusher.onPush('oauth:client:data:clear')
    async def _clearClientAccessToken(self, provideriden, useriden):
        return self.clients.pop(provideriden + useriden)

    async def setClientAuthCode(self, provideriden, useriden, authcode, code_verifier=None):

        providerconf = self._getProvider(provideriden)
        if providerconf is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        await self.clearClientAccessToken(provideriden, useriden)

        # todo: should we delay this?
        ok, data = await self._getAccessToken(providerconf, authcode, code_verifier=code_verifier)
        if not ok:
            raise s_exc.SynErr(mesg=f'Failed to get OAuth v2 token: {data["error"]}')

        await self._setClientTokenData(provideriden, useriden, data)

    @s_nexus.Pusher.onPushAuto('oauth:client:data:set')
    async def _setClientTokenData(self, provideriden, useriden, data):
        iden = provideriden + useriden
        self.clients.set(iden, data)
        self._scheduleRefreshItem(provideriden, useriden, data)
