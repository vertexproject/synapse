import copy
import heapq
import asyncio

import aiohttp

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.lmdbslab as s_lmdbslab

reqValidProvider = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
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
    'required': ['iden', 'name', 'client_id', 'client_secret', 'scope', 'auth_uri', 'token_uri', 'redirect_uri'],
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

        self.ssl = None
        cadir = self.cell.conf.get('tls:ca:dir')
        if cadir is not None:
            self.ssl = s_common.getSslCtx(cadir)

        self.timeout = aiohttp.ClientTimeout(total=10)

        self.schedule_run = None
        self.schedule_heap = []
        self.schedule_task = None
        self.schedule_wake = asyncio.Event()

    async def initActive(self):

        async for provideriden, useriden, clientconf in self.listClients():

            # todo: enabled, etc

            expires_at = clientconf.get('expires_at')
            if expires_at is None or clientconf.get('refresh_token') is None:
                continue

            item = (expires_at, provideriden, useriden)
            heapq.heappush(self.schedule_heap, item)

        self.schedule_task = self.schedCoro(self._refreshLoop())  # todo: make this an active coro?

    async def initPassive(self):
        if self.schedule_task is not None:
            self.schedule_task.cancel()

        self.schedule_run = None
        self.schedule_task = None
        self.schedule_heap.clear()
        self.schedule_wake.clear()

    async def _refreshLoop(self):

        while not self.isfini:

            while self.schedule_heap:

                self.schedule_run = heapq.heappop(self.schedule_heap)

                # todo: do stuff

            await s_coro.event_wait(self.schedule_wake)
            self.schedule_wake.clear()

    async def _getAccessToken(self, providerconf, authcode, code_verifier=None):
        '''
       "access_token":"2YotnFZFEjr1zCsicMWpAA",
       "token_type":"example",
       "expires_in":3600,
       "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
       "example_parameter":"example_value"
        '''

        url = providerconf['token_uri']

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])

        payload = aiohttp.FormData()
        payload.add_field('grant_type', 'authorization_code')
        payload.add_field('scope', providerconf['scope'])
        payload.add_field('redirect_uri', providerconf['redirect_uri'])
        payload.add_field('code', authcode)

        if code_verifier is not None:
            payload.add_field('code_verifier', code_verifier)

        async with aiohttp.ClientSession(timeout=self.timeout) as sess:

            try:
                async with sess.post(url, auth=auth, headers=headers, data=payload, ssl=self.ssl) as resp:

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

    async def _refreshAccessToken(self, providerconf, authconf):

        url = providerconf['token_uri']

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        auth = aiohttp.BasicAuth(providerconf['client_id'], password=providerconf['client_secret'])

        payload = aiohttp.FormData()
        payload.add_field('grant_type', 'refresh_token')
        payload.add_field('refresh_token', authconf['refresh_token'])

        async with aiohttp.ClientSession(timeout=self.timeout) as sess:

            try:
                async with sess.post(url, auth=auth, headers=headers, data=payload, ssl=self.ssl) as resp:

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

    async def addProvider(self, conf):

        conf = reqValidProvider(conf)

        iden = conf['iden']

        if self.providers.get(iden) is not None:
            raise s_exc.DupIden(mesg=f'Duplicate OAuth V2 client iden ({iden})', iden=iden)

        await self._push('oauth:provider:add', conf)

    @s_nexus.Pusher.onPush('oauth:provider:add')
    async def _addProvider(self, conf):
        iden = conf['iden']
        if self.providers.get(iden) is None:
            self.providers.set(iden, conf)

    async def getProvider(self, iden):
        conf = self.providers.get(iden)
        if conf is not None:
            return copy.deepcopy(conf)
        return None

    async def listProviders(self):
        return copy.deepcopy(self.providers.items())

    # async def updateProvider(self, iden, conf): ...

    async def delProvider(self, iden):
        if self.providers.get(iden) is not None:
            return await self._push('oauth:provider:del', iden)

    @s_nexus.Pusher.onPush('oauth:provider:del')
    async def _delProvider(self, iden):
        for clientiden in list(self.clients.keys()):
            if clientiden.startswith(iden):
                # todo: more to do here to cancel if running (and maybe remove from the schedule?)
                self.clients.pop(clientiden)

        return self.providers.pop(iden)

    # async def addClient(self, provideriden, useriden, clientconf): ...

    async def getClient(self, provideriden, useriden):
        conf = self.clients.get(provideriden + useriden)
        if conf is not None:
            return copy.deepcopy(conf)
        return None

    async def listClients(self):
        for iden, clientconf in self.clients.items():
            provideriden, useriden = iden[:32], iden[32:]
            yield provideriden, useriden, clientconf

    async def delClient(self, provideriden, useriden): ...

    async def getClientAccessToken(self, provideriden, useriden):
        if self.providers.get(provideriden) is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        clientconf = await self.getClient(provideriden, useriden)
        if clientconf is None:
            return None

        # todo: if its expired try to refresh it right now

        return clientconf.get('access_token')

    async def setClientAuthCode(self, provideriden, useriden, authcode, code_verifier=None):

        providerconf = await self.getProvider(provideriden)
        if providerconf is None:
            raise s_exc.BadArg(mesg=f'OAuth V2 provider has not been configured ({provideriden})', iden=provideriden)

        # todo: should we try to make this call right away? (also not persisting authcode)
        # todo: should validate the data so normalized when it comes back
        ok, data = await self._getAccessToken(providerconf, authcode, code_verifier=code_verifier)
        if not ok:
            raise s_exc.SynErr(mesg=f'Failed to get OAuth v2 token: {data}')

        await self._setClientTokenData(provideriden, useriden, data)

    @s_nexus.Pusher.onPushAuto('oauth:client:token:set')
    async def _setClientTokenData(self, provideriden, useriden, data):

        iden = provideriden + useriden
        clientconf = self.clients.set(iden, data)

        # todo: if we got a refresh token add it to the loop
