import json
import aiohttp
import contextlib

import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

class EchoAuthApi(s_cell.CellApi):

    def isadmin(self):
        return self.user.admin

    def allowed(self, perm):
        return self.user.allowed(perm)

class EchoAuth(s_cell.Cell):
    cellapi = EchoAuthApi

s_cells.add('echoauth', EchoAuth)

class CellTest(s_t_utils.SynTest):

    async def test_cell_auth(self):

        # test out built in cell auth
        async with self.getTestDmon(mirror='cellauth') as dmon:

            echo = dmon.shared.get('echo00')
            self.nn(echo)

            host, port = dmon.addr

            url = f'tcp://{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://fake@{host}:{port}/echo00'
            await self.asyncraises(s_exc.NoSuchUser, s_telepath.openurl(url))

            url = f'tcp://root@{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://root:newpnewp@{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://root:secretsauce@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:
                self.true(await proxy.isadmin())
                self.true(await proxy.allowed(('hehe', 'haha')))

            user = await echo.auth.addUser('visi')
            await user.setPasswd('foo')
            await user.addRule((True, ('foo', 'bar')))

            url = f'tcp://visi:foo@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:
                self.true(await proxy.allowed(('foo', 'bar')))
                self.false(await proxy.isadmin())
                self.false(await proxy.allowed(('hehe', 'haha')))

    async def test_cell_hive(self):

        # test out built in cell auth
        async with self.getTestDmon(mirror='cellauth') as dmon:
            host, port = dmon.addr
            url = f'tcp://root:secretsauce@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:

                await proxy.setHiveKey(('foo', 'bar'), [1, 2, 3, 4])
                self.eq([1, 2, 3, 4], await proxy.getHiveKey(('foo', 'bar')))
                self.isin('foo', await proxy.listHiveKey())
                self.eq(['bar'], await proxy.listHiveKey(('foo', )))
                await proxy.popHiveKey(('foo', 'bar'))
                self.eq([], await proxy.listHiveKey(('foo', )))

    async def test_cell_unix_sock(self):
        async with self.getTestCore() as core:
            self.true(core.insecure)  # No remote auth on this cortex is currently enabled
            # This directs the connection through the cell:// handler.
            async with core.getLocalProxy() as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))

        # Explicit use of the unix:// handler
        async with self.getTestCore() as core:
            dirn = core.dirn
            url = f'unix://{dirn}/sock:cortex'
            async with await s_telepath.openurl(url) as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))
                iden = await prox.getCellIden()

            url = f'unix://{dirn}/sock:*'
            async with await s_telepath.openurl(url) as prox:
                self.eq(iden, await prox.getCellIden())

    async def test_cell_nonstandard_admin(self):
        boot = {
            'auth:admin': 'pennywise:cottoncandy',
            'type': 'echoauth',
        }
        pconf = {'user': 'pennywise', 'passwd': 'cottoncandy'}

        with self.getTestDir('cellauth') as dirn:
            s_common.yamlsave(boot, dirn, 'cells', 'echo00', 'boot.yaml')
            async with await s_daemon.Daemon.anit(dirn) as dmon:
                item = dmon.shared.get('echo00')
                self.false(item.insecure)

                async with await self.getTestProxy(dmon, 'echo00', **pconf) as proxy:
                    self.true(await proxy.isadmin())
                    self.true(await proxy.allowed(('hehe', 'haha')))

                host, port = dmon.addr
                url = f'tcp://root@{host}:{port}/echo00'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

        # Ensure the cell and its auth have been fini'd
        self.true(item.isfini)
        self.true(item.auth.isfini)
        self.true(item.auth.getUserByName('root').isfini)
        self.true(item.auth.getUserByName('pennywise').isfini)

    async def getHttpJson(self, url):
        async with self.getHttpSess() as sess:
            async with sess.get(url) as resp:
                return await resp.json()

    async def postHttpJson(self, url, data):
        async with self.getHttpSess() as sess:
            async with sess.post(url, json=data) as resp:
                return await resp.json()

    @contextlib.asynccontextmanager
    async def getHttpSess(self):
        jar = aiohttp.CookieJar(unsafe=True)
        conn = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(cookie_jar=jar, connector=conn) as sess:
            yield sess

    async def test_cell_http_auth(self):
        '''
        Test the HTTP api for cell auth.
        '''
        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    visiiden = item['result']['iden']

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupUser', item.get('code'))

                info = {'name': 'analysts'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    analystiden = item['result']['iden']

                info = {'name': 'analysts'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupRole', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/user/newp') as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/role/newp') as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('visi', [u.get('name') for u in users])

                async with sess.get(f'https://localhost:{port}/api/v1/auth/roles') as resp:
                    item = await resp.json()
                    roles = item.get('result')
                    self.isin('analysts', [r.get('name') for r in roles])

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(1, roles)
                    self.eq(analystiden, roles[0])

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(0, roles)

            # lets try out session based login
            core.insecure = False

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

                visiauth = aiohttp.BasicAuth('visi', 'secret')
                newpauth = aiohttp.BasicAuth('visi', 'newp')

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=visiauth) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=newpauth) as resp:
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

            # work some authenticated as admin code paths
            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                # check same-host cross-origin behavior
                origin = 'https://localhost:1/web/site'
                headers = {'origin': origin}
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    retn = await resp.json()
                    self.eq(origin, resp.headers.get('Access-Control-Allow-Origin'))
                    self.eq('ok', retn.get('status'))

                # use the authenticated session to do stuff...
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                rules = [(True, ('node:add',))]
                info = {'name': 'derpuser', 'rules': rules}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    derpiden = user.get('iden')
                    self.eq('derpuser', user.get('name'))
                    self.len(1, user.get('rules'))
                    self.false(user.get('admin'))

                info = {'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    self.true(user.get('admin'))

                node = None
                body = {'query': '[ inet:ipv4=1.2.3.4 ]'}

                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = json.loads(byts)

                        if mesg[0] == 'node':
                            node = mesg[1]

                    self.eq(0x01020304, node[0][1])

                node = None
                body = {'query': '[ inet:ipv4=1.2.3.4 ]'}

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        node = json.loads(byts)

                    self.eq(0x01020304, node[0][1])
