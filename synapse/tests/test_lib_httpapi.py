import ssl
import http

import aiohttp
import aiohttp.client_exceptions as a_exc

import synapse.common as s_common
import synapse.tools.backup as s_backup

import synapse.exc as s_exc
import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.link as s_link
import synapse.lib.httpapi as s_httpapi
import synapse.lib.version as s_version

import synapse.tests.utils as s_tests
import synapse.tests.test_axon as s_t_axon

class HttpApiTest(s_tests.SynTest):

    async def test_reqauth(self):

        class ReqAuthHandler(s_httpapi.Handler):
            async def get(self):
                if not await self.allowed(('syn:test', )):
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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'ok')
                    self.eq(retn.get('result'), {'data': 'everything is awesome!'})

            async with self.getHttpSess(auth=('user', '12345'), port=port) as sess:
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'err')
                    self.eq(retn.get('code'), 'AuthDeny')

                await user.addRule((True, ('syn:test',)))

                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq(retn.get('status'), 'ok')
                    self.eq(retn.get('result'), {'data': 'everything is awesome!'})

            async with aiohttp.ClientSession() as sess:
                burl = f'https://newp:newp@localhost:{port}/api/tests/test_reqauth'
                async with sess.get(burl, ssl=False) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('newb', [u.get('name') for u in users])

                info = {'archived': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{newb.iden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                self.true(newb.isLocked())

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    users = item.get('result')
                    self.notin('newb', [u.get('name') for u in users])

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('BadHttpParam', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=99') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('BadHttpParam', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=0') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    users = item.get('result')
                    self.notin('newb', [u.get('name') for u in users])

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users?archived=1') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('newb', [u.get('name') for u in users])

                info = {'archived': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{newb.iden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
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
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

            async with self.getHttpSess(auth=('bob', 'secret'), port=port) as sess:

                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('AuthDeny', item.get('code'))

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                info = {}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('SchemaViolation', item.get('code'))

                info = {'name': 'newp'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchRole', item.get('code'))

                self.len(2, newb.getRoles())
                info = {'name': 'bobs'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/delrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq(item.get('status'), 'ok')

                # must have content
                async with sess.post(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq(item.get('status'), 'err')
                    self.isin('Invalid JSON content.', (item.get('mesg')))

                # password must be valid
                async with sess.post(url, json={'passwd': ''}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq(item.get('status'), 'err')
                    self.eq(item.get('code'), 'BadArg')

                url = f'https://localhost:{port}/api/v1/auth/password/1234'
                # User iden must be valid
                async with sess.post(url, json={'passwd': 'words'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.isin('User does not exist', (item.get('mesg')))

            async with self.getHttpSess(auth=('newb', 'words'), port=port) as sess:
                # newb can change their own password
                url = f'https://localhost:{port}/api/v1/auth/password/{newb.iden}'
                async with sess.post(url, json={'passwd': 'newb'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq(item.get('status'), 'ok')

                # non-admin newb cannot change someone elses password
                url = f'https://localhost:{port}/api/v1/auth/password/{root.iden}'
                async with sess.post(url, json={'passwd': 'newb'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    visiiden = item['result']['iden']

                info = {'name': 'noob', 'passwd': 'nooblet', 'email': 'nobody@nowhere.com'}
                # The visi user is an admin, so reuse it
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    self.eq('nobody@nowhere.com', item['result']['email'])
                    noobiden = item['result']['iden']

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/user/{noobiden}') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq(noobiden, item['result']['iden'])

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupUser', item.get('code'))

                info = {'name': 'analysts',
                        'rules': [
                            [True, ('foo', 'bar')],
                            [False, ('baz',)]
                        ]}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'))
                    self.eq(item.get('result').get('rules'), ((True, ('foo', 'bar')), (False, ('baz',))))
                    analystiden = item['result']['iden']

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/role/{analystiden}') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.nn(item.get('result').get('iden'), analystiden)

                info = {'name': 'analysts'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/addrole', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('DupRole', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/user/newp') as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/role/newp') as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    users = item.get('result')
                    self.isin('visi', [u.get('name') for u in users])

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/roles') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    roles = item.get('result')
                    self.isin('analysts', [r.get('name') for r in roles])

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                info = {'user': 'blah', 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchUser', item.get('code'))

                info = {'user': visiiden, 'role': 'blah'}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('NoSuchRole', item.get('code'))

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/grant', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(2, roles)
                    self.isin(analystiden, roles)

                info = {'user': visiiden, 'role': analystiden}
                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/revoke', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    roles = item['result']['roles']
                    self.len(1, roles)

                # Sad path coverage
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/auth/roles') as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/auth/user/{noobiden}') as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/auth/role/{analystiden}') as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/user/{s_common.guid()}') as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchUser', item.get('code'))

                async with sess.get(f'https://visi:secret@localhost:{port}/api/v1/auth/role/{s_common.guid()}') as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchRole', item.get('code'))

                async with sess.post(f'https://visi:secret@localhost:{port}/api/v1/auth/role/{s_common.guid()}') as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NoSuchRole', item.get('code'))

            # lets try out session based login

            # Sad path tests
            async with self.getHttpSess() as sess:
                async with sess.post(f'https://localhost:{port}/api/v1/login') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))
                async with sess.post(f'https://localhost:{port}/api/v1/login', json=['newp',]) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

            async with self.getHttpSess() as sess:

                info = {'user': 'hehe', 'passwd': 'newp'}
                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'No such user.') as stream:
                    async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                        self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                        item = await resp.json()
                        self.eq('AuthDeny', item.get('code'))
                        self.true(await  stream.wait(timeout=6))

            async with self.getHttpSess() as sess:
                info = {'user': 'visi', 'passwd': 'secret'}
                await core.setUserLocked(visiiden, True)
                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'User is locked.') as stream:
                    async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                        self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                        item = await resp.json()
                        self.eq('AuthDeny', item.get('code'))
                        self.true(await  stream.wait(timeout=6))
                await core.setUserLocked(visiiden, False)

            async with self.getHttpSess() as sess:

                info = {'user': 'visi', 'passwd': 'borked'}
                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'Incorrect password.') as stream:
                    async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                        self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                        item = await resp.json()
                        self.eq('AuthDeny', item.get('code'))
                        self.true(await stream.wait(timeout=6))

            async with self.getHttpSess() as sess:
                info = {'user': 'visi', 'passwd': 'secret'}
                async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                # make sure session works
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                # log out of said session
                async with sess.get(f'https://localhost:{port}/api/v1/logout') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))
                    newcookie = resp.headers.get('Set-Cookie')
                    self.isin('sess=""', newcookie)

                # session no longer works
                data = {'query': '[ inet:ipv4=1.2.3.4 ]'}
                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=data) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

                heheauth = aiohttp.BasicAuth('hehe', 'haha')
                visiauth = aiohttp.BasicAuth('visi', 'secret')
                newpauth = aiohttp.BasicAuth('visi', 'newp')

                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=visiauth) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'No such user.') as stream:
                    async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=heheauth) as resp:
                        self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                        item = await resp.json()
                        self.eq('NotAuthenticated', item.get('code'))
                        self.true(await stream.wait(timeout=12))

                await core.setUserLocked(visiiden, True)
                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'User is locked.') as stream:
                    async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=visiauth) as resp:
                        self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                        item = await resp.json()
                        self.eq('NotAuthenticated', item.get('code'))
                        self.true(await stream.wait(timeout=12))
                await core.setUserLocked(visiiden, False)

                with self.getAsyncLoggerStream('synapse.lib.httpapi', 'Incorrect password.') as stream:
                    async with sess.get(f'https://localhost:{port}/api/v1/auth/users', auth=newpauth) as resp:
                        self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                        item = await resp.json()
                        self.eq('NotAuthenticated', item.get('code'))
                        self.true(await stream.wait(timeout=12))

                headers = {'Authorization': 'yermom'}
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    item = await resp.json()
                    self.eq('NotAuthenticated', item.get('code'))

                headers = {'Authorization': 'Basic zzzz'}
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq(origin, resp.headers.get('Access-Control-Allow-Origin'))
                    self.eq('ok', retn.get('status'))

                # check same-host cross-origin options
                origin = 'https://localhost:1/web/site'
                headers = {'origin': origin}
                async with sess.options(f'https://localhost:{port}/api/v1/auth/users', headers=headers) as resp:
                    self.eq(origin, resp.headers.get('Access-Control-Allow-Origin'))
                    self.eq(resp.status, http.HTTPStatus.NO_CONTENT)

                # use the authenticated session to do stuff...
                async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                info = {'locked': True, 'name': 'derpderp', 'email': 'noob@derp.com'}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{noobiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(True, retn['result']['locked'])
                    self.eq('derpderp', retn['result']['name'])
                    self.eq('noob@derp.com', retn['result']['email'])
                    self.eq(noobiden, retn['result']['iden'])

                async with self.getHttpSess() as noobsess:
                    info = {'user': 'noob', 'passwd': 'nooblet'}
                    async with noobsess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                        item = await resp.json()
                        self.eq('AuthDeny', item.get('code'))

                info = {'locked': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{noobiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.false(retn['result']['locked'])
                    self.eq('derpderp', retn['result']['name'])
                    self.eq(noobiden, retn['result']['iden'])

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('MissingField', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{visiiden}', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                rules = [(True, ('node', 'add',))]
                info = {'name': 'derpuser', 'passwd': 'derpuser', 'rules': rules}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    derpiden = user.get('iden')
                    self.eq('derpuser', user.get('name'))
                    self.len(1, user.get('rules'))
                    self.false(user.get('admin'))

                info = {'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    self.true(user.get('admin'))

                info = {'admin': False}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    user = retn.get('result')
                    self.false(user.get('admin'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{s_common.guid()}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))
                    self.eq('NoSuchUser', retn.get('code'))

            # test some auth but not admin paths
            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    retn = await resp.json()
                    self.eq('SchemaViolation', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'derpuser', 'passwd': 'derpuser'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('derpuser', retn['result']['name'])

                info = {'admin': True}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/user/{derpiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                info = {'rules': ()}
                async with sess.post(f'https://localhost:{port}/api/v1/auth/role/{analystiden}', json=info) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/grant', json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/revoke', json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/adduser', json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    retn = await resp.json()
                    self.eq('AuthDeny', retn.get('code'))

                async with sess.post(f'https://localhost:{port}/api/v1/auth/addrole', json={}) as resp:
                    retn = await resp.json()
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    self.eq('AuthDeny', retn.get('code'))

    async def test_http_impersonate(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            visi = await core.auth.addUser('visi')
            newpuser = s_common.guid()

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
                    self.eq(resp.status, http.HTTPStatus.OK)

                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        podes.append(s_json.loads(byts))

                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))

                # NoSuchUser precondition failure
                data = {'query': '.created', 'opts': {'user': newpuser}}
                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=data) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    data = await resp.json()
                    self.eq(data, {'status': 'err', 'code': 'NoSuchUser',
                                   'mesg': f'No user found with iden: {newpuser}'})

                msgs = []
                data = {'query': '[ inet:ipv4=5.5.5.5 ]', 'opts': opts}

                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=data) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        msgs.append(s_json.loads(byts))
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.eq(podes[0][0], ('inet:ipv4', 0x05050505))

                # NoSuchUser precondition failure
                opts['user'] = newpuser
                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=data) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    data = await resp.json()
                    self.eq(data, {'status': 'err', 'code': 'NoSuchUser',
                                   'mesg': f'No user found with iden: {newpuser}'})

    async def test_http_coreinfo(self):
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.get(f'https://localhost:{port}/api/v1/core/info') as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    coreinfo = retn.get('result')

                self.eq(coreinfo.get('version'), s_version.version)

                self.nn(coreinfo.get('modeldict'))

                docs = coreinfo.get('stormdocs')
                self.isin('types', docs)
                self.isin('libraries', docs)

            # Auth failures
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as sess:
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/core/info') as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))

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
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(0x01020304, retn['result']['norm'])
                    self.eq('unicast', retn['result']['info']['subs']['type'])

                body = {'prop': 'fake:prop', 'value': '1.2.3.4'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                    retn = await resp.json()
                    self.eq('NoSuchProp', retn.get('code'))

                body = {'prop': 'test:int', 'value': 'newp'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    retn = await resp.json()
                    self.eq('BadTypeValu', retn.get('code'))

                body = {'value': '1.2.3.4'}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    retn = await resp.json()
                    self.eq('MissingField', retn.get('code'))

                body = {'prop': 'test:comp', 'value': '3^foobar', 'typeopts': {'sepr': '^'}}
                async with sess.get(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq([3, 'foobar'], retn['result']['norm'])

                # Norm via POST
                body = {'prop': 'inet:ipv4', 'value': '1.2.3.4'}
                async with sess.post(f'https://localhost:{port}/api/v1/model/norm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(0x01020304, retn['result']['norm'])
                    self.eq('unicast', retn['result']['info']['subs']['type'])

            # Auth failures
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as sess:
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/model') as resp:
                    retn = await resp.json()
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    self.eq('err', retn.get('status'))

                body = {'prop': 'inet:ipv4', 'value': '1.2.3.4'}
                async with sess.get(f'https://visi:newp@localhost:{port}/api/v1/model/norm', json=body) as resp:
                    retn = await resp.json()
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    self.eq('err', retn.get('status'))

    async def test_http_beholder(self):
        self.skipIfNexusReplay()
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/behold') as sock:
                    await sock.send_json({'type': 'call:init'})
                    mesg = await sock.receive_json()
                    self.eq('errx', mesg['type'])
                    self.eq('AuthDeny', mesg['data']['code'])

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/behold') as sock:
                    await sock.send_json({'type': 'call:init'})
                    mesg = await sock.receive_json()
                    self.eq('errx', mesg['type'])
                    self.eq('AuthDeny', mesg['data']['code'])

                await visi.setAdmin(True)
                userrole = await core.auth.addRole('fancy.role')
                await core.addUserRole(visi.iden, userrole.iden)

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/behold') as sock:
                    await sock.send_json({'type': 'bleep blorp'})
                    mesg = await sock.receive_json()
                    self.eq('errx', mesg['type'])
                    self.eq('BadMesgFormat', mesg['data']['code'])

                ssvc = {'iden': s_common.guid(), 'name': 'dups', 'url': 'tcp://127.0.0.1:1/'}
                spkg = {
                    'name': 'testy',
                    'version': (0, 0, 1),
                    'synapse_version': '>=2.50.0,<3.0.0',
                    'modules': (
                        {'name': 'testy.ingest', 'storm': 'function punch(x, y) { return (($x + $y)) }'},
                    ),
                    'commands': (
                        {
                            'name': 'testy.dostuff',
                            'storm': '$ingest = $lib.import("test.ingest") $punch.punch(40, 20)'
                        },
                    ),
                    'perms': (
                        {
                            'perm': ('test', 'testy', 'permission'),
                            'gate': 'cortex',
                            'desc': 'a test gate',
                        },
                    ),
                }

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/behold') as sock:
                    root = await core.auth.getUserByName('root')
                    await sock.send_json({'type': 'call:init'})
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'init')

                    base = 0
                    layr, view = await core.callStorm('''
                        $view = $lib.view.get().fork()
                        return(($view.layers.0.iden, $view.iden))
                    ''')
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.len(1, data['gates'])
                    self.eq(data['event'], 'layer:add')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    info = data['info']
                    self.eq(info['creator'], root.iden)
                    self.eq(info['iden'], layr)

                    gate = data['gates'][0]
                    self.eq(gate['iden'], layr)
                    self.eq(gate['type'], 'layer')
                    self.len(1, gate['users'])

                    user = gate['users'][0]
                    self.eq(user['iden'], root.iden)
                    self.true(user['admin'])

                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    info = data['info']
                    self.eq(data['event'], 'view:add')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    self.eq(info['creator'], root.iden)
                    self.eq(info['iden'], view)

                    cdef = await core.callStorm('return($lib.cron.add(query="{meta:note=*}", hourly=30).pack())')
                    layr = await core.callStorm('return($lib.layer.add().iden)')

                    opts = {'vars': {'view': view, 'cron': cdef['iden'], 'layr': layr}}
                    await core.callStorm('$lib.view.get($view).set(name, "a really okay view")', opts=opts)
                    await core.callStorm('$lib.layer.get($layr).set(name, "some kinda layer")', opts=opts)
                    await core.callStorm('cron.move $cron $view', opts=opts)
                    await core.callStorm('cron.mod $cron {[test:guid=*]}', opts=opts)
                    await core.callStorm('cron.disable $cron', opts=opts)
                    await core.callStorm('cron.enable $cron', opts=opts)
                    await core.callStorm('$c = $lib.cron.get($cron) $c.set("name", "neato cron")', opts=opts)
                    await core.callStorm('$c = $lib.cron.get($cron) $c.set("doc", "some docs")', opts=opts)
                    await core.callStorm('cron.del $cron', opts=opts)

                    await core.addStormPkg(spkg)
                    await core.addStormPkg(spkg)
                    await core.addStormSvc(ssvc)

                    await core.delStormSvc(ssvc['iden'])
                    await core.delStormPkg(spkg['name'])

                    newlayr = await core.callStorm('return($lib.layer.add().iden)')
                    topts = {'vars': {'layr': newlayr}}
                    newview = await core.callStorm('return($lib.view.add(($layr,)).iden)', opts=topts)
                    topts['vars']['view'] = newview
                    await core.callStorm('$lib.view.get($view).set(layers, ($layr,))', opts=topts)

                    tview = core.getView(newview)
                    await tview.addLayer(layr)
                    await core.delView(tview.iden)

                    events = [
                        'cron:add',
                        'layer:add',
                        'view:set',
                        'layer:set',
                        'cron:move',
                        'cron:edit:query',
                        'cron:disable',
                        'cron:enable',
                        'cron:edit:name',
                        'cron:edit:doc',
                        'cron:del',
                        'pkg:add',
                        'svc:add',
                        'svc:del',
                        'pkg:del',
                        'layer:add',
                        'view:add',
                        'view:setlayers',
                        'view:addlayer',
                        'view:del'
                    ]

                    mesgs = []
                    for event in events:
                        m = await sock.receive_json()
                        self.eq(m['type'], 'iter')
                        data = m.get('data')
                        self.nn(data)
                        self.nn(data['info'])
                        self.ge(len(data['info']), 1)
                        self.eq(event, data['event'])

                        if not event.startswith('svc'):
                            self.nn(data['gates'])
                            self.ge(len(data['gates']), 1)

                        if event.startswith('pkg'):
                            self.nn(data['perms'])

                        # offset always goes up
                        self.gt(data['offset'], base)
                        base = data['offset']
                        mesgs.append(data)

                    role = await core.callStorm('return($lib.auth.roles.add("beholder.role").iden)')
                    await core.callStorm('$lib.auth.users.byname("visi").grant($role)', opts={'vars': {'role': role}})
                    # role add
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'role:add')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    self.eq(data['info']['iden'], role)
                    self.eq(data['info']['name'], 'beholder.role')
                    self.eq(data['info']['rules'], [])
                    self.eq(data['info']['authgates'], {})

                    # role grant
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    self.eq(data['info']['name'], 'role:grant')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['role']['iden'], role)
                    self.eq(data['info']['role']['type'], 'role')
                    self.eq(data['info']['role']['name'], 'beholder.role')
                    self.eq(data['info']['role']['rules'], [])
                    self.eq(data['info']['role']['authgates'], {})

                    # give a user view read perms
                    gate = await core.callStorm('''
                        $usr = $lib.auth.users.byname("visi")
                        $rule = $lib.auth.ruleFromText(view.read)
                        $usr.addRule($rule, $view)
                        return($lib.auth.gates.get($view))
                    ''', opts={'vars': {'view': view}})
                    mesg = await sock.receive_json()
                    self.eq(m['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.gt(data['offset'], base)
                    base = data['offset']
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'rule:add')
                    self.eq(data['info']['valu'], [True, ['view', 'read']])

                    # delete view
                    await core.callStorm('view.del $view', opts=opts)
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'view:del')
                    self.gt(data['offset'], base)
                    self.len(1, data['gates'])
                    self.eq(data['info']['iden'], view)
                    base = data['offset']

                    # delete layer
                    await core.callStorm('$lib.layer.del($layr)', opts=opts)
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'layer:del')
                    self.gt(data['offset'], base)
                    self.len(1, data['gates'])
                    self.eq(data['info']['iden'], layr)

                    # set admin
                    await visi.setAdmin(False)
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.gt(data['offset'], base)
                    base = data['offset']
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'admin')
                    self.eq(data['info']['valu'], False)

                    # lock a user
                    await core.callStorm('$lib.auth.users.byname("visi").setLocked($lib.true)')
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.gt(data['offset'], base)
                    base = data['offset']
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'locked')
                    self.eq(data['info']['valu'], True)

                    # rule grant to a role
                    await core.callStorm('auth.role.addrule all power-ups.foo.bar')
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'role:info')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    rall = await core.auth.getRoleByName('all')
                    self.eq(data['info']['iden'], rall.iden)
                    self.eq(data['info']['name'], 'rule:add')
                    self.eq(data['info']['valu'], [True, ['power-ups', 'foo', 'bar']])

                    # rule deny to a role
                    await core.callStorm('auth.role.addrule all "!power-ups.foo.bar"')
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'iter')
                    data = mesg['data']
                    self.eq(data['event'], 'role:info')
                    self.eq(data['info']['iden'], rall.iden)
                    self.eq(data['info']['name'], 'rule:add')
                    self.eq(data['info']['valu'], [False, ['power-ups', 'foo', 'bar']])
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # rule del from a role
                    await core.callStorm('''
                        $rule = $lib.auth.ruleFromText("power-ups.foo.bar")
                        $lib.auth.roles.byname(all).delRule($rule)
                    ''')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'role:info')
                    self.eq(data['info']['iden'], rall.iden)
                    self.eq(data['info']['name'], 'rule:del')
                    self.eq(data['info']['valu'], [True, ['power-ups', 'foo', 'bar']])
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # rule add to a user
                    await core.callStorm('auth.user.addrule visi "!power-ups.foo.bar" --gate cortex')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'rule:add')
                    self.eq(data['info']['valu'], [False, ['power-ups', 'foo', 'bar']])
                    self.len(1, data['gates'])
                    self.eq(data['gates'][0]['iden'], 'cortex')

                    # rule del from a user
                    mesgs = await core.callStorm('''
                        $rule = $lib.auth.ruleFromText("!power-ups.foo.bar")
                        $lib.auth.users.byname(visi).delRule($rule, gateiden=cortex)
                    ''')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'rule:del')
                    self.eq(data['info']['valu'], [False, ['power-ups', 'foo', 'bar']])
                    self.len(1, data['gates'])
                    self.eq(data['gates'][0]['iden'], 'cortex')

                    deflayr, defview = await core.callStorm('''
                        $view = $lib.view.get()
                        return(($view.layers.0.iden, $view.iden))
                    ''')

                    # user add. couple of messages fall out from it
                    await core.callStorm('auth.user.add beep --email beep@vertex.link')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:add')
                    self.eq(data['info']['name'], 'beep')
                    self.eq(data['info']['email'], None)
                    self.eq(data['info']['type'], 'user')
                    self.gt(data['offset'], base)
                    beepiden = data['info']['iden']
                    base = data['offset']

                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['name'], 'role:grant')
                    self.eq(data['info']['iden'], beepiden)
                    self.eq(data['info']['role']['iden'], rall.iden)
                    self.eq(data['info']['role']['name'], 'all')
                    self.eq(data['info']['role']['type'], 'role')
                    self.eq(data['info']['role']['authgates'][deflayr], {'rules': [[True, ['layer', 'read']]]})
                    self.eq(data['info']['role']['authgates'][defview], {'rules': [[True, ['view', 'read']]]})
                    self.eq(data['info']['role']['rules'], [[False, ['power-ups', 'foo', 'bar']]])
                    self.gt(data['offset'], base)
                    base = data['offset']

                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['name'], 'email')
                    self.eq(data['info']['valu'], 'beep@vertex.link')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # set password
                    await core.callStorm('$lib.auth.users.byname("beep").setPasswd("plzdontdothis")')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['iden'], beepiden)
                    self.gt(data['offset'], base)
                    base = data['offset']
                    self.notin('valu', data)
                    self.notin('valu', data['info'])

                    # set user name
                    await visi.setName('invisig0th')
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:name')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['valu'], 'invisig0th')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # set role name
                    rolename = 'some fancy new role name'
                    await userrole.setName(rolename)
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'role:name')
                    self.eq(data['info']['iden'], userrole.iden)
                    self.eq(data['info']['valu'], rolename)
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # role del
                    await core.delRole(role)
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'role:del')
                    self.eq(data['info']['iden'], role)
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # revoke
                    allroles = [x.iden for x in visi.getRoles()]
                    self.len(2, allroles)
                    await visi.revoke(userrole.iden)
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['name'], 'role:revoke')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['role']['iden'], userrole.iden)
                    self.eq(data['info']['role']['name'], 'some fancy new role name')
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # set roles
                    await visi.setRoles([rall.iden, userrole.iden])
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['name'], 'role:set')
                    self.eq(data['info']['iden'], visi.iden)
                    roles = [x['iden'] for x in data['info']['roles']]
                    self.isin(rall.iden, roles)
                    self.isin(userrole.iden, roles)

                    # archive
                    await visi.setArchived(True)
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'archived')
                    self.eq(data['info']['valu'], True)
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # archive also sets locked
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:info')
                    self.eq(data['info']['iden'], visi.iden)
                    self.eq(data['info']['name'], 'locked')
                    self.eq(data['info']['valu'], True)
                    self.gt(data['offset'], base)
                    base = data['offset']

                    # user del
                    await core.delUser(beepiden)
                    mesg = await sock.receive_json()
                    data = mesg['data']
                    self.eq(data['event'], 'user:del')
                    self.eq(data['info']['iden'], beepiden)
                    self.gt(data['offset'], base)
                    base = data['offset']

    async def test_http_storm(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess(port=port) as sess:
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm')
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                item = await resp.json()
                self.eq('NotAuthenticated', item.get('code'))

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                body = {'query': 'inet:ipv4', 'opts': {'user': core.auth.rootuser.iden}}
                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    item = await resp.json()
                    self.eq('AuthDeny', item.get('code'))

                body = {'query': 'inet:ipv4', 'opts': {'user': core.auth.rootuser.iden}}
                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    item = await resp.json()
                    self.eq('AuthDeny', item.get('code'))

                await visi.setAdmin(True)

                async with sess.get(f'https://localhost:{port}/api/v1/storm', data=b'asdf') as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    item = await resp.json()
                    self.eq('SchemaViolation', item.get('code'))

                node = None
                body = {'query': '[ inet:ipv4=1.2.3.4 ]'}

                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = s_json.loads(byts)

                        if mesg[0] == 'node':
                            node = mesg[1]

                    self.nn(node)
                    self.eq(0x01020304, node[0][1])

                async with sess.post(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = s_json.loads(byts)

                        if mesg[0] == 'node':
                            node = mesg[1]

                    self.eq(0x01020304, node[0][1])

                node = None
                body = {'query': '[ inet:ipv4=1.2.3.4 ]'}

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        node = s_json.loads(byts)

                    self.eq(0x01020304, node[0][1])

                async with sess.post(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        node = s_json.loads(byts)

                    self.eq(0x01020304, node[0][1])

                body['stream'] = 'jsonlines'

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    bufr = b''
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        bufr += byts
                        for jstr in bufr.split(b'\n'):
                            if not jstr:
                                bufr = b''
                                break

                            try:
                                node = s_json.loads(byts)
                            except s_exc.BadJsonText:
                                bufr = jstr
                                break

                    self.eq(0x01020304, node[0][1])

                async with sess.post(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    bufr = b''
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        bufr += byts
                        for jstr in bufr.split(b'\n'):
                            if not jstr:
                                bufr = b''
                                break

                            try:
                                mesg = s_json.loads(byts)
                            except s_exc.BadJsonText:
                                bufr = jstr
                                break

                            if mesg[0] == 'node':
                                node = mesg[1]

                    self.eq(0x01020304, node[0][1])

                # Task cancellation during long running storm queries works as intended
                body = {'query': '.created | sleep 10'}
                task = None
                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = s_json.loads(byts)
                        if mesg[0] == 'node':
                            task = core.boss.tasks.get(list(core.boss.tasks.keys())[0])
                            self.eq(core.view.iden, task.info.get('view'))
                            break

                self.nn(task)
                self.true(await task.waitfini(6))
                self.len(0, core.boss.tasks)

                task = None
                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes', json=body) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    async for byts, x in resp.content.iter_chunks():

                        if not byts:
                            break

                        mesg = s_json.loads(byts)
                        self.len(2, mesg)  # Is if roughly shaped like a node?
                        task = core.boss.tasks.get(list(core.boss.tasks.keys())[0])
                        break

                self.nn(task)
                self.true(await task.waitfini(6))
                self.len(0, core.boss.tasks)

                fork = await core.callStorm('return($lib.view.get().fork().iden)')
                lowuser = await core.auth.addUser('lowuser')

                async with sess.get(f'https://localhost:{port}/api/v1/storm/nodes',
                                    json={'query': '.created', 'opts': {'view': s_common.guid()}}) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)

                async with sess.get(f'https://localhost:{port}/api/v1/storm',
                                    json={'query': '.created', 'opts': {'view': s_common.guid()}}) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)

                async with sess.get(f'https://localhost:{port}/api/v1/storm',
                                    json={'query': '.created', 'opts': {'user': lowuser.iden, 'view': fork}}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)

                # check reqvalidstorm with various queries
                tvs = (
                    ('test:str=test', {}, 'ok'),
                    ('1.2.3.4 | spin', {'mode': 'lookup'}, 'ok'),
                    ('1.2.3.4 | spin', {'mode': 'autoadd'}, 'ok'),
                    ('1.2.3.4', {}, 'err'),
                    ('| 1.2.3.4 ', {'mode': 'lookup'}, 'err'),
                    ('| 1.2.3.4', {'mode': 'autoadd'}, 'err'),
                )
                url = f'https://localhost:{port}/api/v1/reqvalidstorm'
                for (query, opts, rcode) in tvs:
                    body = {'query': query, 'opts': opts}
                    async with sess.post(url, json=body) as resp:
                        if rcode == 'ok':
                            self.eq(resp.status, http.HTTPStatus.OK)
                        else:
                            self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                        data = await resp.json()
                        self.eq(data.get('status'), rcode)
                # Sad path
                async with aiohttp.client.ClientSession() as bad_sess:
                    async with bad_sess.post(url, ssl=False) as resp:
                        data = await resp.json()
                        self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                        self.eq(data.get('status'), 'err')
                        self.eq(data.get('code'), 'NotAuthenticated')

    async def test_tls_ciphers(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            with self.raises(ssl.SSLError):
                sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
                link = await s_link.connect('127.0.0.1', port=port, ssl=sslctx)

            with self.raises(ssl.SSLError):
                sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_1)
                link = await s_link.connect('127.0.0.1', port=port, ssl=sslctx)

            with self.raises(ssl.SSLError):
                sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
                sslctx.set_ciphers('ADH-AES256-SHA')
                link = await s_link.connect('127.0.0.1', port=port, ssl=sslctx)

            with self.raises(ssl.SSLError):
                sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
                sslctx.set_ciphers('AES256-GCM-SHA384')
                link = await s_link.connect('127.0.0.1', port=port, ssl=sslctx)

            with self.raises(ssl.SSLError):
                sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
                sslctx.set_ciphers('DHE-RSA-AES256-SHA256')
                link = await s_link.connect('127.0.0.1', port=port, ssl=sslctx)

    async def test_healthcheck(self):
        conf = {
            'https:headers': {
                'X-Hehe-Haha': 'wootwoot!',
            }
        }
        async with self.getTestCore(conf=conf) as core:
            # Run http instead of https for this test
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')

            async with self.getHttpSess(auth=None, port=port) as sess:

                url = f'https://localhost:{port}/robots.txt'
                async with sess.get(url) as resp:
                    self.eq('User-agent: *\nDisallow: /\n', await resp.text())

                url = f'https://localhost:{port}/api/v1/active'
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    self.none(resp.headers.get('server'))
                    self.eq('wootwoot!', resp.headers.get('x-hehe-haha'))
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')
                    self.true(result['result']['active'])
                    self.eq('nosniff', resp.headers.get('x-content-type-options'))

            await root.setPasswd('secret')

            url = f'https://localhost:{port}/api/v1/healthcheck'
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')
                    snfo = result.get('result')
                    self.isinstance(snfo, dict)
                    self.eq(snfo.get('status'), 'nominal')

            user = await core.auth.addUser('user')
            await user.setPasswd('beep')
            async with self.getHttpSess(auth=('user', 'beep'), port=port) as sess:
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    result = await resp.json()
                    self.eq(result.get('status'), 'err')
                await user.addRule((True, ('health',)))
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')

    async def test_streamhandler(self):

        class SadHandler(s_httpapi.StreamHandler):
            '''
            data_received must be implemented
            '''
            async def post(self):
                self.sendRestRetn('foo')
                return

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/sad', SadHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            url = f'https://localhost:{port}/api/v1/sad'
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                with self.raises(a_exc.ServerDisconnectedError):
                    async with sess.post(url, data=b'foo') as resp:
                        pass

    async def test_http_storm_vars(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = core.auth.rootuser
            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/set')
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('SchemaViolation', (await resp.json())['code'])

                resp = await sess.get(f'https://localhost:{port}/api/v1/storm/vars/get')
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('SchemaViolation', (await resp.json())['code'])

                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/pop')
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('SchemaViolation', (await resp.json())['code'])

                body = {'name': 'hehe'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/set', json=body)
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('BadArg', (await resp.json())['code'])

                body = {'name': 'hehe', 'value': 'haha'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/set', json=body)
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq({'status': 'ok', 'result': True}, await resp.json())

                body = {'name': 'hehe', 'default': 'lolz'}
                resp = await sess.get(f'https://localhost:{port}/api/v1/storm/vars/get', json=body)
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq({'status': 'ok', 'result': 'haha'}, await resp.json())

                body = {'name': 'hehe', 'default': 'lolz'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/pop', json=body)
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq({'status': 'ok', 'result': 'haha'}, await resp.json())

            async with self.getHttpSess(auth=('visi', 'secret'), port=port) as sess:

                body = {'name': 'hehe', 'value': 'haha'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/set', json=body)
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                self.eq('AuthDeny', (await resp.json())['code'])

                body = {'name': 'hehe', 'default': 'lolz'}
                resp = await sess.get(f'https://localhost:{port}/api/v1/storm/vars/get', json=body)
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                self.eq('AuthDeny', (await resp.json())['code'])

                body = {'name': 'hehe', 'default': 'lolz'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/storm/vars/pop', json=body)
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                self.eq('AuthDeny', (await resp.json())['code'])

    async def test_http_feed(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = core.auth.rootuser
            visi = await core.auth.addUser('visi')

            await visi.setPasswd('secret')
            await root.setPasswd('secret')

            async with self.getHttpSess(port=port) as sess:
                body = {'items': [(('inet:ipv4', 0x05050505), {})]}
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed', json=body)
                self.eq('NotAuthenticated', (await resp.json())['code'])

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed')
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('SchemaViolation', (await resp.json())['code'])

                body = {'view': 'asdf'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed', json=body)
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                self.eq('NoSuchView', (await resp.json())['code'])

                body = {'name': 'asdf'}
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed', json=body)
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('NoSuchFunc', (await resp.json())['code'])

                body = {'items': [(('inet:ipv4', 0x05050505), {'tags': {'hehe': (None, None)}})]}
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed', json=body)
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq('ok', (await resp.json())['status'])
                self.len(1, await core.nodes('inet:ipv4=5.5.5.5 +#hehe'))

            async with self.getHttpSess(auth=('visi', 'secret'), port=port) as sess:
                body = {'items': [(('inet:ipv4', 0x01020304), {})]}
                resp = await sess.post(f'https://localhost:{port}/api/v1/feed', json=body)
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                self.eq('AuthDeny', (await resp.json())['code'])
                self.len(0, await core.nodes('inet:ipv4=1.2.3.4'))

    async def test_http_sess_mirror(self):

        with self.getTestDir() as dirn:

            core00dirn = s_common.gendir(dirn, 'core00')
            core01dirn = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=core00dirn, conf={'nexslog:en': True}) as core00:
                pass

            s_backup.backup(core00dirn, core01dirn)

            async with self.getTestCore(dirn=core00dirn, conf={'nexslog:en': True}) as core00:

                conf = {'mirror': core00.getLocalUrl()}
                async with self.getTestCore(dirn=core01dirn, conf=conf) as core01:

                    iden = s_common.guid()
                    self.false(await core00.hasHttpSess(iden))
                    sess00 = await core00.genHttpSess(iden)
                    self.true(await core00.hasHttpSess(iden))
                    await sess00.set('foo', 'bar')
                    self.eq('bar', sess00.info.get('foo'))

                    await core01.sync()

                    sess01 = await core01.genHttpSess(iden)
                    self.eq('bar', sess01.info.get('foo'))

                    self.nn(core00.sessions.get(iden))
                    self.nn(core01.sessions.get(iden))

                    await core00.delHttpSess(iden)

                    await core01.sync()

                    self.none(await core00.getHttpSessDict(iden))
                    self.none(await core01.getHttpSessDict(iden))
                    self.false(await core00.hasHttpSess(iden))

                    self.none(core00.sessions.get(iden))
                    self.none(core01.sessions.get(iden))

                    self.eq(sess00.info, {})
                    self.eq(sess01.info, {})
                    self.true(sess00.isfini)
                    self.true(sess01.isfini)

    async def test_request_logging(self):

        def get_mesg(stream: s_tests.AsyncStreamEvent) -> dict:
            msgs = stream.jsonlines()
            self.len(1, msgs)
            return msgs[0]

        async with self.getTestCore() as core:

            # structlog tests

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            async with self.getHttpSess() as sess:

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                logname = 'tornado.access'

                # Basic-auth

                with self.getStructuredAsyncLoggerStream(logname, 'api/v1/auth/adduser') as stream:

                    headers = {
                        'X-Forwarded-For': '1.2.3.4',
                        'User-Agent': 'test_request_logging',
                    }
                    async with sess.post(f'https://root:root@localhost:{port}/api/v1/auth/adduser',
                                         json=info, headers=headers) as resp:
                        item = await resp.json()
                        self.nn(item.get('result').get('iden'))
                        visiiden = item['result']['iden']
                        self.eq(resp.status, http.HTTPStatus.OK)
                        self.true(await stream.wait(6))

                mesg = get_mesg(stream)
                self.eq(mesg.get('uri'), '/api/v1/auth/adduser')
                self.eq(mesg.get('username'), 'root')
                self.eq(mesg.get('user'), core.auth.rootuser.iden)
                self.isin('headers', mesg)
                self.eq(mesg['headers'].get('user-agent'), 'test_request_logging')
                self.isin('remoteip', mesg)
                self.isin('(root)', mesg.get('message'))
                self.isin('200 POST /api/v1/auth/adduser', mesg.get('message'))
                self.notin('1.2.3.4', mesg.get('message'))

                # No auth provided
                with self.getStructuredAsyncLoggerStream(logname, 'api/v1/active') as stream:
                    async with sess.get(f'https://root:root@localhost:{port}/api/v1/active', skip_auto_headers=['User-Agent']) as resp:
                        self.eq(resp.status, http.HTTPStatus.OK)
                        self.true(await stream.wait(6))

                mesg = get_mesg(stream)
                self.eq(mesg.get('uri'), '/api/v1/active')
                self.notin('headers', mesg)
                self.notin('username', mesg)
                self.notin('user', mesg)
                self.isin('remoteip', mesg)
                self.isin('200 GET /api/v1/active', mesg.get('message'))

                # Sessions populate the data too
                async with self.getHttpSess() as sess:

                    # api/v1/login populates the data
                    with self.getStructuredAsyncLoggerStream(logname, 'api/v1/login') as stream:
                        async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                            self.eq(resp.status, http.HTTPStatus.OK)
                            self.true(await stream.wait(6))

                    mesg = get_mesg(stream)
                    self.eq(mesg.get('uri'), '/api/v1/login')
                    self.eq(mesg.get('username'), 'visi')
                    self.eq(mesg.get('user'), visiiden)

                    # session cookie loging populates the data upon reuse
                    with self.getStructuredAsyncLoggerStream(logname, 'api/v1/auth/users') as stream:
                        async with sess.get(f'https://localhost:{port}/api/v1/auth/users') as resp:
                            self.eq(resp.status, http.HTTPStatus.OK)
                            self.true(await stream.wait(6))

                    mesg = get_mesg(stream)
                    self.eq(mesg.get('uri'), '/api/v1/auth/users')
                    self.eq(mesg.get('username'), 'visi')
                    self.eq(mesg.get('user'), visiiden)

        async with self.getTestCore(conf={'https:parse:proxy:remoteip': True}) as core:

            # structlog tests

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            async with self.getHttpSess() as sess:

                info = {'name': 'visi', 'passwd': 'secret', 'admin': True}
                logname = 'tornado.access'

                # Basic-auth

                with self.getStructuredAsyncLoggerStream(logname, 'api/v1/auth/adduser') as stream:

                    async with sess.post(f'https://root:root@localhost:{port}/api/v1/auth/adduser',
                                         json=info, headers={'X-Forwarded-For': '1.2.3.4'}) as resp:
                        item = await resp.json()
                        self.nn(item.get('result').get('iden'))
                        self.eq(resp.status, http.HTTPStatus.OK)
                        self.true(await stream.wait(6))

                mesg = get_mesg(stream)
                self.eq(mesg.get('uri'), '/api/v1/auth/adduser')
                self.eq(mesg.get('username'), 'root')
                self.eq(mesg.get('user'), core.auth.rootuser.iden)
                self.eq(mesg.get('remoteip'), '1.2.3.4')
                self.isin('(root)', mesg.get('message'))
                self.isin('200 POST /api/v1/auth/adduser', mesg.get('message'))

                info = {'name': 'charles', 'passwd': 'secret', 'admin': True}
                with self.getStructuredAsyncLoggerStream(logname, 'api/v1/auth/adduser') as stream:

                    async with sess.post(f'https://root:root@localhost:{port}/api/v1/auth/adduser',
                                         json=info, headers={'X-Real-Ip': '8.8.8.8'}) as resp:
                        item = await resp.json()
                        self.nn(item.get('result').get('iden'))
                        self.eq(resp.status, http.HTTPStatus.OK)
                        self.true(await stream.wait(6))

                mesg = get_mesg(stream)
                self.eq(mesg.get('uri'), '/api/v1/auth/adduser')
                self.eq(mesg.get('username'), 'root')
                self.eq(mesg.get('user'), core.auth.rootuser.iden)
                self.eq(mesg.get('remoteip'), '8.8.8.8')
                self.isin('(root)', mesg.get('message'))
                self.isin('200 POST /api/v1/auth/adduser', mesg.get('message'))

    async def test_core_local_axon_http(self):
        async with self.getTestCore() as core:
            await s_t_axon.AxonTest.runAxonTestHttp(self, core, realaxon=core.axon)

    async def test_core_remote_axon_http(self):
        timeout = aiohttp.ClientTimeout(total=1)

        async with self.getTestAxon() as axon:
            conf = {
                'axon': axon.getLocalUrl(),
            }

            async with self.getTestCore(conf=conf) as core:
                self.true(await s_coro.event_wait(core.axready, timeout=1))

                # await s_t_axon.AxonTest.runAxonTestHttp(self, core, realaxon=core.axon)

                # additional test for axon down

                host, port = await core.addHttpsPort(0, host='127.0.0.1')

                async with self.getHttpSess() as sess:
                    await axon.fini()

                    with self.raises(TimeoutError):
                        sha256 = s_common.ehex(s_t_axon.asdfhash)
                        url = f'https://localhost:{port}/api/v1/axon/files/has/sha256/{sha256}'
                        async with sess.get(url, timeout=timeout) as resp:
                            pass

    async def test_http_login_broken(self):
        async with self.getTestCore() as core:

            lowuser = await core.addUser('lowuser', passwd='secret')
            ninjas = await core.addRole('ninjas')
            await core.addUserRole(lowuser.get('iden'), ninjas.get('iden'))

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess() as sess:

                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'lowuser', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    roles = set([r.get('name') for r in retn.get('result', {}).get('roles')])
                    self.eq(roles, {'all', 'ninjas'})

            # Remove the role from the Auth subsystem.
            core.auth.roledefs.delete(ninjas.get('iden'))
            core.auth.roleidenbyname.delete('ninjas')
            core.auth.rolebyidencache.pop(ninjas.get('iden'))
            core.auth.roleidenbynamecache.pop('ninjas')

            async with self.getHttpSess() as sess:
                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'lowuser', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    roles = set([r.get('name') for r in retn.get('result', {}).get('roles')])
                    self.eq(roles, {'all'})

    async def test_http_sess_setvals(self):

        class ValsHandler(s_httpapi.StreamHandler):

            async def get(self):

                iden = await self.useriden()
                if iden is None or self._web_sess is None:  # pragma: no cover
                    self.sendRestErr('NoSuchUser', 'User must login with a valid sess')
                    return

                throw = bool(int(self.request.headers.get('throw', 0)))
                code = int(self.request.headers.get('code', 200))

                if throw:
                    vals = {'hehe': 'haha', 'omg': {'hehe', 'haha'}}
                    code = None
                else:
                    vals = {'now': s_common.now(), 'lastip': self.request.connection.context.remote_ip}

                await self._web_sess.update(vals)

                self.sendRestRetn({'iden': s_common.ehex(self._web_sess.iden), 'info': self._web_sess.info},
                                  status_code=code)
                return

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/vals', ValsHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            url = f'https://localhost:{port}/api/v1/vals'

            async with self.getHttpSess() as sess:
                info = {'user': 'root', 'passwd': 'secret'}
                async with sess.post(f'https://localhost:{port}/api/v1/login', json=info) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    data = await resp.json()
                    result = data.get('result')
                    iden = s_common.uhex(result.get('iden'))
                    info = result.get('info')
                    self.isin('now', info)
                    self.isin('lastip', info)
                    self.isin('user', info)
                    self.isin('username', info)

                cell_sess = core.sessions.get(iden)
                self.eq(cell_sess.info, result.get('info'))

                async with sess.get(url, headers={'throw': '1'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.INTERNAL_SERVER_ERROR)

                # No change with the bad data
                self.eq(cell_sess.info, result.get('info'))

                # Coverage for sendRestRetn status_code
                async with sess.get(url, headers={'code': '418'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.IM_A_TEAPOT)

    async def test_http_locked_admin(self):
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setAdmin(True)
            await visi.setPasswd('secret123')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            root = f'https://localhost:{port}'

            async with self.getHttpSess() as sess:
                resp = await sess.post(f'{root}/api/v1/login', json={'user': 'visi', 'passwd': 'secret123'})
                self.eq(resp.status, http.HTTPStatus.OK)

                resp = await sess.get(f'{root}/api/v1/auth/users')
                self.eq(resp.status, http.HTTPStatus.OK)

                data = {'query': '[ inet:ipv4=1.2.3.4 ]', 'opts': {'user': visi.iden}}
                async with sess.get(f'{root}/api/v1/storm/call', json=data) as resp:
                    item = await resp.json()
                    self.eq('ok', item.get('status'))

                with self.getAsyncLoggerStream('synapse.lib.cell',
                                               'Invalidated HTTP session for locked user visi') as stream:
                    await core.setUserLocked(visi.iden, True)
                    self.true(await stream.wait(timeout=2))

                resp = await sess.get(f'{root}/api/v1/auth/users')
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

                data = {'query': '[ inet:ipv4=5.6.7.8 ]', 'opts': {'user': visi.iden}}
                async with sess.get(f'{root}/api/v1/storm/call', json=data) as resp:
                    item = await resp.json()
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                    self.eq('err', item.get('status'))
                    self.eq('NotAuthenticated', item.get('code'))

                resp = await sess.post(f'{root}/api/v1/login', json={'user': 'visi', 'passwd': 'secret123'})
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                retn = await resp.json()
                self.eq(retn.get('status'), 'err')
                self.eq(retn.get('code'), 'AuthDeny')
                self.isin('User is locked.', retn.get('mesg'))
