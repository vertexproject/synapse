import json
import asyncio
import aiohttp

import synapse.lib.httpapi as s_httpapi

import synapse.tests.utils as s_tests

class HttpApiTest(s_tests.SynTest):

    async def test_reqauth(self):

        class ReqAuthHandler(s_httpapi.Handler):
            async def get(self):
                if not await self.reqAuthAllowed(('syn:test', )):
                    return
                return self.sendRestRetn({'data': 'everything is awesome!'})

        async with self.getTestCore() as core:
            core.addHttpApi('/api/tests/test_reqauth', ReqAuthHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/tests/test_reqauth'
            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            user = await core.auth.addUser('user')
            await user.setPasswd('12345')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                async with sess.get(url) as resp:
                    self.eq(resp.status, 200)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'ok')
                    self.eq(retn.get('result'), {'data': 'everything is awesome!'})

            async with self.getHttpSess(auth=('user', '12345'), port=port) as sess:
                async with sess.get(url) as resp:
                    self.eq(resp.status, 200)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'err')
                    self.eq(retn.get('code'), 'AuthDeny')

                await user.addRule((True, ('syn:test',)))

                async with sess.get(url) as resp:
                    self.eq(resp.status, 200)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'ok')
                    self.eq(retn.get('result'), {'data': 'everything is awesome!'})

            async with aiohttp.ClientSession() as sess:
                burl = f'https://newp:newp@localhost:{port}/api/tests/test_reqauth'
                async with sess.get(burl, ssl=False) as resp:
                    self.eq(resp.status, 401)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'err')

    async def test_http_user_archived(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')
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

                self.true(newb.isLocked())

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

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            newb = await core.auth.addUser('bob')
            await newb.setPasswd('secret')

            bobs = await core.auth.addRole('bobs')

            await newb.grant(bobs.iden)

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
                    self.eq('SchemaViolation', item.get('code'))

                info = {'name': 'newp'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchRole', item.get('code'))

                self.len(2, newb.getRoles())
                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

            self.len(1, newb.getRoles())
            self.none(await core.auth.getRoleByName('bobs'))

    async def test_http_passwd(self):
        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            newb = await core.auth.addUser('newb')
            await newb.setPasswd('newb')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                url = f'https://localhost:{port}/api/v1/auth/password/{newb.iden}'
                # Admin can change the newb password
                async with sess.post(url, json={'passwd': 'words'}) as resp:
                    item = await resp.json()
                    self.eq(item.get('status'), 'ok')

                # must have content
                async with sess.post(url) as resp:
                    item = await resp.json()
                    self.eq(item.get('status'), 'err')
                    self.isin('Invalid JSON content.', (item.get('mesg')))

                # password must be valid
                async with sess.post(url, json={'passwd': ''}) as resp:
                    item = await resp.json()
                    self.eq(item.get('status'), 'err')
                    self.eq(item.get('code'), 'BadArg')

                url = f'https://localhost:{port}/api/v1/auth/password/1234'
                # User iden must be valid
                async with sess.post(url, json={'passwd': 'words'}) as resp:
                    item = await resp.json()
                    self.isin('User does not exist', (item.get('mesg')))

            async with self.getHttpSess(auth=('newb', 'words'), port=port) as sess:
                # newb can change their own password
                url = f'https://localhost:{port}/api/v1/auth/password/{newb.iden}'
                async with sess.post(url, json={'passwd': 'newb'}) as resp:
                    item = await resp.json()
                    self.eq(item.get('status'), 'ok')

                # non-admin newb cannot change someone elses password
                url = f'https://localhost:{port}/api/v1/auth/password/{root.iden}'
                async with sess.post(url, json={'passwd': 'newb'}) as resp:
                    item = await resp.json()
                    self.eq(item.get('status'), 'ok')

    async def test_http_auth(self):
        '''
        Test the HTTP api for cell auth.
        '''
        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            async with self.getHttpSess() as sess:

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                # Make the first user as root
                async with sess.post(f'https://root:root@localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    visiiden = item['result']['iden']

                info = {'name': 'noob', 'passwd': 'nooblet', 'email': 'nobody@nowhere.com'}
                # The visi user is an admin, so reuse it
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    self.eq('nobody@nowhere.com', item['result']['email'])
                    noobiden = item['result']['iden']

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupUser', item.get('code'))

                info = {'name': 'analysts'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    analystiden = item['result']['iden']

                info = {'name': 'analysts'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupRole', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/user/newp') as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/role/newp') as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/users') as resp:
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('visi', [u.get('name') for u in users])

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/roles') as resp:
                    item = await resp.json()
                    roles = item.get('result')
                    self.isin('analysts', [r.get('name') for r in roles])

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(2, roles)
                    self.isin(analystiden, roles)

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(1, roles)

            # lets try out session based login

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
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', data=b'asdf') as resp:
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                rules = [(True, ('node', 'add',))]
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
                    self.eq('SchemaViolation', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'derpuser', 'passwd': 'derpuser'}) as resp:
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

    async def test_http_impersonate(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')
            await visi.addRule((True, ('impersonate',)))

            opts = {'user': core.auth.rootuser.iden}

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                data = {'query': '[ inet:ipv4=1.2.3.4 ]', 'opts': opts}

                podes = []
                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=data) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        podes.append(json.loads(byts))

                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))

                msgs = []
                data = {'query': '[ inet:ipv4=5.5.5.5 ]', 'opts': opts}

                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=data) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        msgs.append(json.loads(byts))
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.eq(podes[0][0], ('inet:ipv4', 0x05050505))

    async def test_http_model(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                self.len(0, core.sessions)  # zero sessions..

                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                self.len(1, core.sessions)  # We have one session after login

                # Get a copy of the data model
                async with sess.get(f'https://localhost:{port}/api/v1/model') as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.isin('types', retn['result'])
                    self.isin('forms', retn['result'])

                self.len(1, core.sessions)  # We still have one session since the cookie was reused

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

    async def test_http_watch(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            # with no session user...
            async with self.getHttpSess() as sess:

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/watch') as sock:
                    await sock.send_json({'tags': ['test.visi']})
                    mesg = await sock.receive_json()
                    self.eq('errx', mesg['type'])
                    self.eq('AuthDeny', mesg['data']['code'])

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/watch') as sock:
                    await sock.send_json({'tags': ['test.visi']})
                    mesg = await sock.receive_json()
                    self.eq('errx', mesg['type'])
                    self.eq('AuthDeny', mesg['data']['code'])

                await visi.addRule((True, ('watch',)))

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/watch') as sock:

                    await sock.send_json({'tags': ['test.visi']})
                    mesg = await sock.receive_json()

                    self.eq('init', mesg['type'])

                    await core.nodes('[ test:str=woot +#test.visi ]')

                    mesg = await sock.receive_json()

                    self.eq('tag:add', mesg['type'])
                    self.eq('test.visi', mesg['data']['tag'])

    async def test_http_storm(self):

        async with self.getTestCore() as core:

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
                    self.eq('SchemaViolation', item.get('code'))

                node = None
                body = {'query': '[ inet:ipv4=1.2.3.4 ]'}

                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = json.loads(byts)

                        if mesg[0] == 'node':
                            node = mesg[1]

                    self.nn(node)
                    self.eq(0x01020304, node[0][1])

                async with sess.post(f'https://localhost:{port}/api/v1/storm', json=body) as resp:

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

                async with sess.post(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        node = json.loads(byts)

                    self.eq(0x01020304, node[0][1])

    async def test_healthcheck(self):
        async with self.getTestCore() as core:
            # Run http instead of https for this test
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            url = f'https://localhost:{port}/api/v1/healthcheck'
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                async with sess.get(url) as resp:
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')
                    snfo = result.get('result')
                    self.isinstance(snfo, dict)
                    self.eq(snfo.get('status'), 'nominal')

            user = await core.auth.addUser('user')
            await user.setPasswd('beep')
            async with self.getHttpSess(auth=('user', 'beep'), port=port) as sess:
                async with sess.get(url) as resp:
                    result = await resp.json()
                    self.eq(result.get('status'), 'err')
                await user.addRule((True, ('health',)))
                async with sess.get(url) as resp:
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')
