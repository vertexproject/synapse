import json
import aiohttp

import synapse.tests.utils as s_tests

class HttpApiTest(s_tests.SynTest):

    async def test_http_port(self):
        async with self.getTestCore() as core:
            # Run http instead of https for this test
            host, port = await core.addHttpPort(0, host='127.0.0.1')

            root = core.auth.getUserByName('root')
            await root.setPasswd('secret')
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f'http://root:secret@localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('root', [u.get('name') for u in users])

    async def test_http_user_archived(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = core.auth.getUserByName('root')
            await root.setPasswd('secret')

            newb = await core.auth.addUser('newb')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('newb', [u.get('name') for u in users])

                info = {'archived': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{newb.iden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                self.true(newb.locked)

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.notin('newb', [u.get('name') for u in users])

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=asdf') as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('BadHttpParam', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=99') as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('BadHttpParam', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=0') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.notin('newb', [u.get('name') for u in users])

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=1') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('newb', [u.get('name') for u in users])

                info = {'archived': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{newb.iden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('newb', [u.get('name') for u in users])

    async def test_http_delrole(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = core.auth.getUserByName('root')
            await root.setPasswd('secret')

            newb = await core.auth.addUser('bob')
            await newb.setPasswd('secret')

            bobs = await core.auth.addRole('bobs')

            await newb.grant('bobs')

            async with self.getHttpSess() as sess:

                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

            async with self.getHttpSess(auth=('bob', 'secret'), port=port) as sess:

                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('AuthDeny', item.get('code'))

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                info = {}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('BadJson', item.get('code'))

                info = {'name': 'newp'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchRole', item.get('code'))

                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

            self.len(0, newb.getRoles())
            self.none(core.auth.getRoleByName('bobs'))

    async def test_http_auth(self):
        '''
        Test the HTTP api for cell auth.
        '''
        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            core.insecure = True

            async with self.getHttpSess() as sess:

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    visiiden = item['result']['iden']

                info = {'name': 'noob', 'passwd': 'nooblet', 'email': 'nobody@nowhere.com'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    self.eq('nobody@nowhere.com', item['result']['email'])
                    noobiden = item['result']['iden']

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

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

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

                info = {'user': 'hehe'}
                async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                    item = await resp.json()
                    self.eq('AuthDeny', item.get('code'))

            async with self.getHttpSess() as sess:

                info = {'user': 'visi', 'passwd': 'borked'}
                async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                    item = await resp.json()
                    self.eq('AuthDeny', item.get('code'))

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

                headers = {'Authorization': 'yermom'}
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

                headers = {'Authorization': 'Basic zzzz'}
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

            # work some authenticated as admin code paths
            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
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

                # check same-host cross-origin options
                origin = 'https://localhost:1/web/site'
                headers = {'origin': origin}
                async with sess.options(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    self.eq(origin, resp.headers.get('Access-Control-Allow-Origin'))
                    self.eq(204, resp.status)

                # use the authenticated session to do stuff...
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'locked': True, 'name': 'derpderp', 'email': 'noob@derp.com'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{noobiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(True, retn['result']['locked'])
                    self.eq('derpderp', retn['result']['name'])
                    self.eq('noob@derp.com', retn['result']['email'])
                    self.eq(noobiden, retn['result']['iden'])

                async with self.getHttpSess() as noobsess:
                    info = {'user': 'noob', 'passwd': 'nooblet'}
                    async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                        item = await resp.json()
                        self.eq('AuthDeny', item.get('code'))

                info = {'locked': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{noobiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.false(retn['result']['locked'])
                    self.eq('derpderp', retn['result']['name'])
                    self.eq(noobiden, retn['result']['iden'])

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json={}) as resp:
                    item = await resp.json()
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json={}) as resp:
                    item = await resp.json()
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

                rules = [(True, ('node:add',))]
                info = {'name': 'derpuser', 'passwd': 'derpuser', 'rules': rules}
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

                info = {'admin': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    self.false(user.get('admin'))

            # test some auth but not admin paths
            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', data=b'asdf') as resp:
                    retn = await resp.json()
                    self.eq('BadJson', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'derpuser', 'passwd': 'derpuser'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('derpuser', retn['result']['name'])

                info = {'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', json=info) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', json={}) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', json={}) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json={}) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json={}) as resp:
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

    async def test_http_model(self):

        async with self.getTestCore() as core:

            core.insecure = False

            visi = await core.auth.addUser('visi')

            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                # Get a copy of the data model
                async with sess.get(f'https://localhost:{port}/api/v1/model') as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.isin('types', retn['result'])
                    self.isin('forms', retn['result'])

                # Norm via GET
                body = {'prop': 'inet:ipv4', 'value': '1.2.3.4'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(0x01020304, retn['result']['norm'])
                    self.eq('unicast', retn['result']['info']['subs']['type'])

                body = {'prop': 'fake:prop', 'value': '1.2.3.4'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq('NoSuchProp', retn.get('code'))

                body = {'value': '1.2.3.4'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq('MissingField', retn.get('code'))

                # Norm via POST
                body = {'prop': 'inet:ipv4', 'value': '1.2.3.4'}
                async with sess.post(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(0x01020304, retn['result']['norm'])
                    self.eq('unicast', retn['result']['info']['subs']['type'])

            # Auth failures
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as sess:
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/model') as resp:
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))

                body = {'prop': 'inet:ipv4', 'value': '1.2.3.4'}
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))

    async def test_http_storm(self):

        async with self.getTestCore() as core:

            core.insecure = False

            visi = await core.auth.addUser('visi')

            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.get(f'https://localhost:{port}/api/v1/storm', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('BadJson', item.get('code'))

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
