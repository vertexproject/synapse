import json

import aiohttp

import synapse.common as s_common
import synapse.exc as s_exc

import synapse.tests.utils as s_test

from pprint import pprint

class CortexLibTest(s_test.SynTest):

    async def test_libcortex_httpapi_methods(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define a handler. Add storm for each METHOD we support
            q = '''
            $api = $lib.cortex.httpapi.add(testpath00)
            $api.methods.get = ${
$data = ({'method': 'get'})
$headers = ({'Secret-Header': 'OhBoy!'})
$request.reply(200, headers=$headers, body=$data)
            }
            $api.methods.post = ${
$data = ({'method': 'post'})
$headers = ({'Secret-Header': 'OhBoy!'})
$request.reply(201, headers=$headers, body=$data)
            }
            $api.methods.put = ${
$data = ({'method': 'put'})
$headers = ({'Secret-Header': 'OhBoy!'})
$request.reply(202, headers=$headers, body=$data)
            }
            $api.methods.patch = ${
$data = ({'method': 'patch'})
$headers = ({'Secret-Header': 'OhBoy!'})
$request.reply(203, headers=$headers, body=$data)
            }
            $api.methods.options = ${
$headers = ({'Secret-Header': 'Options', 'Content-Type': 'application/json'})
$request.reply(204, headers=$headers)
            }
            $api.methods.delete = ${
$data = ({'method': 'delete'})
$headers = ({'Secret-Header': 'OhBoy!'})
$request.reply(205, headers=$headers, body=$data)
            }
            $api.methods.head = ${
$headers = ({'Secret-Header': 'Head'})
$request.reply(206, headers=$headers, body=({"no":"body"}))
            }

            return ( $api.iden )
            '''
            testpath00 = await core.callStorm(q)

            info = await core.callStorm('return( $lib.cortex.httpapi.get($iden).pack() )',
                                        opts={'vars': {'iden': testpath00}})
            self.eq(info.get('iden'), testpath00)

            with self.raises(s_exc.BadSyntax):
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.get = "| | | "'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})

            with self.raises(s_exc.NoSuchName):
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.trace = ${}'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})

            with self.raises(s_exc.NoSuchName):
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.connect = ${}'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})

            with self.raises(s_exc.NoSuchName):
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.wildycustomverb = ${}'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:  # type: aiohttp.ClientSession
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('method'), 'get')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 201)
                data = await resp.json()
                self.eq(data.get('method'), 'post')

                resp = await sess.put(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 202)
                data = await resp.json()
                self.eq(data.get('method'), 'put')

                resp = await sess.patch(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 203)
                data = await resp.json()
                self.eq(data.get('method'), 'patch')

                resp = await sess.options(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 204)
                self.eq(resp.headers.get('Secret-Header'), 'Options')
                # HTTP 204 code has no response content per rfc9110
                self.eq(await resp.read(), b'')

                resp = await sess.delete(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 205)
                data = await resp.json()
                self.eq(data.get('method'), 'delete')

                resp = await sess.head(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 206)
                self.eq(resp.headers.get('Secret-Header'), 'Head')
                self.eq(resp.headers.get('Content-Length'), '14')
                # HEAD had no body in its response
                self.eq(await resp.read(), b'')

                # exercise _gtors
                q = '''$api = $lib.cortex.httpapi.get($iden)
                $ret = ({
                    "get": $api.methods.get,
                    "put": $api.methods.put,
                    "head": $api.methods.head,
                    "post": $api.methods.post,
                    "patch": $api.methods.patch,
                    "delete": $api.methods.delete,
                    "options": $api.methods.options,
                })
                return ($ret)
                '''
                queries = await core.callStorm(q, opts={'vars': {'iden': testpath00}})
                self.len(7, queries)

                # Stat the api to enumerate all its method _gtors
                msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': testpath00}})
                self.stormIsInPrint('Method: GET', msgs)
                self.stormIsInPrint('Method: PUT', msgs)
                self.stormIsInPrint('Method: POST', msgs)
                self.stormIsInPrint('Method: PATCH', msgs)
                self.stormIsInPrint('Method: OPTIONS', msgs)
                self.stormIsInPrint('Method: DELETE', msgs)
                self.stormIsInPrint('Method: HEAD', msgs)

                # Unset a method and try to use it
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.post = $lib.undef'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})
                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('mesg'), f'Extended HTTP API {testpath00} has no method for POST')

                # Unsetting a HEAD method and calling it yields a 500
                # but still has no body in the response.
                q = '$api = $lib.cortex.httpapi.get($iden) $api.methods.head = $lib.undef'
                await core.callStorm(q, opts={'vars': {'iden': testpath00}})
                resp = await sess.head(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 500)
                self.eq(await resp.read(), b'')

                msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': testpath00}})
                self.stormNotInPrint('Method: POST', msgs)
                self.stormNotInPrint('Method: HEAD', msgs)
                self.stormIsInPrint('Method: GET', msgs)
                self.stormIsInPrint('Method: PUT', msgs)
                self.stormIsInPrint('Method: PATCH', msgs)
                self.stormIsInPrint('Method: OPTIONS', msgs)
                self.stormIsInPrint('Method: DELETE', msgs)

                q = '''$api = $lib.cortex.httpapi.add(testpath01)
                $api.methods.get = ${ $request.reply(200, body=({"hehe": "haha"})) }
                return ( $api.iden )'''
                testpath01 = await core.callStorm(q)
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath01')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('hehe'), 'haha')

                q = '$lib.cortex.httpapi.del($iden)'
                msgs = await core.stormlist(q, opts={'vars': {'iden': testpath01}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath01')
                self.eq(resp.status, 404)
                data = await resp.json()
                self.eq(data.get('code'), 'NoSuchPath')
                self.eq(data.get('mesg'), 'No Extended HTTP API endpoint matches testpath01')

                # Test method reply types
                q = '''$api = $lib.cortex.httpapi.add(testreply)
                            $api.methods.post = ${ $request.reply(200, body=$request.json.data) }
                            return ( $api.iden )'''
                testreply = await core.callStorm(q)
                edata = ('hello',
                         31337,
                         ['a', 2],
                         {'key': 'valu', 'hehe': [1, '2']},
                         None,
                         )
                for valu in edata:
                    resp = await sess.post(f'https://localhost:{hport}/api/ext/testreply',
                                           json={'data': valu}
                                           )
                    self.eq(resp.status, 200)
                    data = await resp.json()
                    self.eq(data, valu)

                # Echo handler returns the request data.
                # This also shows some flattening of request data we do.

                q = '''$api = $lib.cortex.httpapi.add('echo/(.*)/([a-zA-Z0-9]*)?')
                $api.methods.get = ${
                $data = ({
                    "echo": $lib.true,
                    "method": $request.method,
                    "headers": $request.headers,
                    "params": $request.params,
                    "uri": $request.uri,
                    "path": $request.path,
                    "remote_ip": $request.remote_ip,
                    "args": $request.args,
                })
                try {
                    $data.json = $request.json
                } catch StormRuntimeError as err {
                    $data.json = "err"
                }
                $headers = ({'Echo': 'hehe!'})
                $request.reply(200, headers=$headers, body=$data)
                }
                return ( $api.iden )
                '''
                echoiden = await core.callStorm(q)

                url = f'https://lowuser:secret@localhost:{hport}/api/ext/echo/sup/?echo=test&giggle=haha&echo=eggs'
                resp = await sess.get(url, headers=(('hehe', 'haha'), ('apikey', 'secret'), ('hehe', 'badjoke')),
                                      json={'look': 'at this!'},
                                      )
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('args'), ['sup', ''])
                self.eq(data.get('echo'), True)
                self.eq(data.get('headers').get('hehe'), 'haha')
                self.eq(data.get('headers').get('apikey'), 'secret')
                self.eq(data.get('json'), {'look': 'at this!'})
                self.eq(data.get('method'), 'GET')
                self.eq(data.get('params'), {'echo': 'test', 'giggle': 'haha'})
                self.eq(data.get('path'), 'echo/sup/')
                self.isin('remote_ip', data)
                self.eq(data.get('uri'), '/api/ext/echo/sup/?echo=test&giggle=haha&echo=eggs')

                url = f'https://lowuser:secret@localhost:{hport}/api/ext/echo/words/wOw'
                resp = await sess.get(url, headers=(('hehe', 'haha'), ('apikey', 'secret'), ('hehe', 'badjoke')),
                                      data=b'hehe',
                                      )
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('args'), ['words', 'wOw'])
                self.eq(data.get('json'), 'err')
                self.eq(data.get('path'), 'echo/words/wOw')

                # Sad paths on the $request methods
                q = '''$api = $lib.cortex.httpapi.add(testpath02)
                $api.methods.get = ${ $request.sendcode(200) $request.sendheaders('beep beep') }
                return ( $api.iden )'''
                testpath02 = await core.callStorm(q)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath02')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'BadArg')
                self.eq(data.get('mesg'), 'HTTP Response headers must be a dictionary, got str.')

                q = '''$api = $lib.cortex.httpapi.add(testpath03)
                $api.methods.get = ${ $request.sendcode(200) $request.sendbody('beep beep') }
                return ( $api.iden )'''
                testpath03 = await core.callStorm(q)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath03')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'BadArg')
                self.eq(data.get('mesg'), 'HTTP Response body must be bytes, got str.')

                q = '''$api = $lib.cortex.httpapi.add(testpath04)
                $api.methods.get = ${ $request.reply(200, body=({"hehe": "yes!"})) $request.reply(201, body=({"hehe":" newp"})) }
                return ( $api.iden )'''
                test04 = await core.callStorm(q)

                emsg = f'Error executing custom HTTP API {test04}: BadArg Response.reply() has already been called.'
                with self.getAsyncLoggerStream('synapse.lib.httpapi', emsg) as stream:
                    resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath04')
                    self.eq(resp.status, 200)
                    self.eq(await resp.json(), {'hehe': 'yes!'})

    async def test_libcortex_httpapi_runas_owner(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$api = $lib.cortex.httpapi.add(testpath00)
            $api.methods.get = ${
                $view = $lib.view.get()
                $request.reply(200, body=({'view': $view.iden, "username": $lib.user.name()}) )
            }
            return ( ($api.iden, $api.owner.name) )
            '''
            iden, uname = await core.callStorm(q)
            self.eq(uname, 'root')

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:  # type: aiohttp.ClientSession
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')

                q = '''$api=$lib.cortex.httpapi.get($http_iden)
                $user=$lib.auth.users.byname(lowuser) $api.owner = $user
                return ($api.owner.name)'''
                name = await core.callStorm(q, opts={'vars': {'http_iden': iden}})
                self.eq(name, 'lowuser')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'lowuser')

                q = '''
                $api=$lib.cortex.httpapi.get($http_iden)
                $api.runas = user
                return ($api.runas)'''
                name = await core.callStorm(q, opts={'vars': {'http_iden': iden}})
                self.eq(name, 'user')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')

            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:  # type: aiohttp.ClientSession
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath00')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'lowuser')

            # Set the user by iden
            q = '''$api=$lib.cortex.httpapi.get($http_iden)
            $user=$lib.auth.users.byname(root) $api.owner = $user.iden
            return ($api.owner.name)'''
            name = await core.callStorm(q, opts={'vars': {'http_iden': iden}})
            self.eq(name, 'root')

    async def test_libcortex_httpapi_order_stat(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define a few handlers
            q = '''
            $api = $lib.cortex.httpapi.add('hehe/([a-z0-9]*)')
            $api.methods.get = ${ $request.reply(200, headers=({"yup": "wildcard"}), body=({"path": $request.path})) }
            $api.methods.head = ${ $request.replay(200, headers=({"yup": "wildcard"}) ) }
            $api.name = 'the hehe wildcard handler'
            $api.desc = 'wildcard words'
            $api.runas = owner
            return ( $api.iden )
            '''
            iden0 = await core.callStorm(q)

            q = '''
            $api = $lib.cortex.httpapi.add('hehe/haha')
            $api.methods.get = ${ $request.reply(200, headers=({"yup": "hehe/haha"}), body=({"path": $request.path})) }
            $api.methods.head = ${ $request.replay(200, headers=({"yup": "hehe/haha"}) ) }
            $api.name = 'the hehe/haha handler'
            $api.desc = 'beep boop zoop robot captain'
            $api.runas = user
            $api.perms = (
                ({"perm": ["hehe", "haha"]}),
                ({"perm": ["some", "thing"], "default": $lib.true}),
            )
            return ( $api.iden )
            '''
            iden1 = await core.callStorm(q)

            q = '''
            $api = $lib.cortex.httpapi.add('hehe')
            $api.methods.get = ${ $request.reply(200, headers=({"yup": "hehe"}), body=({"path": $request.path})) }
            $api.methods.head = ${ $request.replay(200, headers=({"yup": "hehe"})) }
            $api.authenticated = $lib.false
            $api.owner = $lowuser
            return ( $api.iden )
            '''
            iden2 = await core.callStorm(q, opts={'vars': {'lowuser': lowuser}})

            q = '''
            $api = $lib.cortex.httpapi.add('wow')
            $api.methods.get = ${ $request.reply(200, body=({"path": $request.path})) }
            $api.authenticated = $lib.false
            $api.vars.hehe = wow
            $api.vars.items = (1, 2, (3) )
            return ( $api.iden )
            '''
            iden3 = await core.callStorm(q)

            msgs = await core.stormlist('cortex.httpapi.list')
            self.stormIsInPrint(f'0     {iden0}', msgs)
            self.stormIsInPrint(f'1     {iden1}', msgs)
            self.stormIsInPrint(f'2     {iden2}', msgs)
            self.stormIsInPrint(f'3     {iden3}', msgs)

            # Order matters. The hehe/haha path occurs after the wildcard.
            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/haha')
                self.eq(resp.headers.get('yup'), 'wildcard')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/ohmy1234')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/ohmy1234')
                self.eq(resp.headers.get('yup'), 'wildcard')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe')
                self.eq(resp.headers.get('yup'), 'hehe')

            # Move the wildcard handler after the more specific handler
            msgs = await core.stormlist('cortex.httpapi.index $iden 1', opts={'vars': {'iden': iden0}})
            self.stormIsInPrint(f'Set HTTP API {iden0} to index 1', msgs)

            msgs = await core.stormlist('cortex.httpapi.list')
            self.stormIsInPrint(f'0     {iden1}', msgs)
            self.stormIsInPrint(f'1     {iden0}', msgs)
            self.stormIsInPrint(f'2     {iden2}', msgs)
            self.stormIsInPrint(f'3     {iden3}', msgs)

            # The wildcard handler does not match the more specific request as a result of the new order
            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/haha')
                self.eq(resp.headers.get('yup'), 'hehe/haha')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/ohmy1234')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/ohmy1234')
                self.eq(resp.headers.get('yup'), 'wildcard')

                # The paths are matched in case sensitive manner. The current regex fails to match.
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/OhMy1234')
                self.eq(resp.status, 404)

                q = "$api=$lib.cortex.httpapi.get($iden) $api.path='hehe/([A-Za-z0-9]*)' "
                await core.callStorm(q, opts={'vars': {'iden': iden0}})

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/OhMy1234')
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/OhMy1234')
                self.eq(resp.headers.get('yup'), 'wildcard')

            # We can move the endpoint to the end of the list too. An arbitrary high
            # index will place it at the end.
            msgs = await core.stormlist('cortex.httpapi.index $iden 100', opts={'vars': {'iden': iden0}})
            self.stormIsInPrint(f'Set HTTP API {iden0} to index 3', msgs)

            msgs = await core.stormlist('cortex.httpapi.list')
            self.stormIsInPrint(f'0     {iden1}', msgs)
            self.stormIsInPrint(f'1     {iden2}', msgs)
            self.stormIsInPrint(f'2     {iden3}', msgs)
            self.stormIsInPrint(f'3     {iden0}', msgs)

            # Show detailed information for a given api
            msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': iden0}})
            self.stormIsInPrint(f'Iden: {iden0}', msgs)
            self.stormIsInPrint('Owner: root', msgs)
            self.stormIsInPrint('Runas: owner', msgs)
            self.stormIsInPrint('Readonly: false', msgs)
            self.stormIsInPrint('Authenticated: true', msgs)
            self.stormIsInPrint('Name: the hehe wildcard handler', msgs)
            self.stormIsInPrint('Description: wildcard words', msgs)
            self.stormIsInPrint('No user permissions are required to run this HTTP API endpoint.', msgs)
            self.stormIsInPrint('Method: GET', msgs)
            self.stormIsInPrint('$request.reply(200, headers=({"yup": "wildcard"}), body=({"path": $request.path}))',
                                msgs)
            self.stormIsInPrint(f'Method: HEAD', msgs)
            self.stormIsInPrint('$request.replay(200, headers=({"yup": "wildcard"}) )', msgs)
            self.stormIsInPrint('No vars are set for the handler.', msgs)

            msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': iden1}})
            self.stormIsInPrint(f'Iden: {iden1}', msgs)
            self.stormIsInPrint('Owner: root', msgs)
            self.stormIsInPrint('Runas: user', msgs)
            self.stormIsInPrint('Readonly: false', msgs)
            self.stormIsInPrint('Authenticated: true', msgs)
            self.stormIsInPrint('Name: the hehe/haha handler', msgs)
            self.stormIsInPrint('Description: beep boop zoop robot captain', msgs)
            self.stormIsInPrint('The following user permissions are required to run this HTTP API endpoint:',
                                msgs)
            self.stormIsInPrint('hehe.haha', msgs)
            self.stormIsInPrint('some.thing, default: true', msgs)

            msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': iden3}})
            self.stormIsInPrint(f'Iden: {iden3}', msgs)
            self.stormIsInPrint('The handler has the following runtime variables set:', msgs)
            self.stormIsInPrint('hehe             => wow', msgs)
            self.stormIsInPrint("items            => ('1', '2', 3)", msgs)

            # Remove a user + view and stat the handler
            badview = await core.callStorm('''$view=$lib.view.get().fork() $lib.auth.users.del($user)
                                        $api=$lib.cortex.httpapi.get($iden)
                                        $api.view=$view.iden
                                        $lib.view.del($view.iden)
                                        return ( $view.iden )
                                        ''',
                                        opts={'vars': {'user': lowuser, 'iden': iden2}})

            msgs = await core.stormlist('cortex.httpapi.stat $iden', opts={'vars': {'iden': iden2}})
            self.stormIsInPrint(f'Iden: {iden2}', msgs)
            self.stormIsInPrint(f'No user found ({lowuser})', msgs)
            self.stormIsInPrint(f'No view found ({badview})', msgs)

    async def test_libcortex_httpapi_auth(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            root = core.auth.rootuser.iden
            await core.setUserPasswd(root, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$api = $lib.cortex.httpapi.add('auth')
            $api.methods.get = ${
                $request.reply(200, body=({"username": $lib.user.name(), "user": $request.user}) )
            }
            return ( $api.iden )
            '''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')
                self.eq(data.get('user'), root)

            async with self.getHttpSess() as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 401)
                data = await resp.json()
                self.eq(data.get('code'), 'NotAuthenticated')

                q = '$api = $lib.cortex.httpapi.get($iden) $api.authenticated=$lib.false'
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')
                self.eq(data.get('user'), None)

                # authenticated = false + runas = user -> runs as owner
                q = '$api = $lib.cortex.httpapi.get($iden) $api.runas=user'
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')
                self.eq(data.get('user'), None)

            # The user value is populated for authenticated requests which
            # indicates who the requester's user iden is.
            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')
                self.eq(data.get('user'), None)

                q = '$api = $lib.cortex.httpapi.get($iden) $api.authenticated=$lib.true'
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'lowuser')
                self.eq(data.get('user'), lowuser)

                q = '$api = $lib.cortex.httpapi.get($iden) $api.runas=owner'
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/auth')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('username'), 'root')
                self.eq(data.get('user'), lowuser)

    async def test_libcortex_httpapi_raw(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define a handler that makes its own response headers, bytes, body.
            q = '''
            $api = $lib.cortex.httpapi.add('raw')
            $api.methods.get = ${
$data = ({'oh': 'my'})
$body = $lib.json.save($data).encode()
$headers = ({'Secret-Header': 'OhBoy!'})
$headers."Content-Type" = "application/json"
$headers."Content-Length" = $lib.len($body)
$request.reply(200, headers=$headers, body=$body)
            }
            return ( $api.iden )
            '''
            await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/raw')
                self.eq(resp.status, 200)
                self.eq(resp.headers.get('Content-Type'), 'application/json')
                self.eq(resp.headers.get('Content-Length'), '12')
                self.eq(resp.headers.get('Secret-Header'), 'OhBoy!')

                buf = await resp.read()
                self.len(12, buf)
                self.eq(json.loads(buf), {'oh': 'my'})

    async def test_libcortex_httpapi_jsonlines(self):
        async with self.getTestCore() as core:
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            addr, hport = await core.addHttpsPort(0)

            # Example which uses the sendcode / sendheaders / sendbody
            # methods in order to implement a streaming API endpoint

            q = '''$api = $lib.cortex.httpapi.add('jsonlines')
            $api.methods.get = ${
$request.sendcode(200)
$request.sendheaders(({"Secret-Header": "OhBoy!", "Content-Type": "text/plain; charset=utf8"}))
$values = ((1), (2), (3))
for $i in $values {
    $body=`{$lib.json.save(({'oh': $i}))}\\n`
    $request.sendbody($body.encode())
}
            }
            return ( $api.iden )
            '''
            iden00 = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/jsonlines')
                self.eq(resp.status, 200)
                self.eq(resp.headers.get('Content-Type'), 'text/plain; charset=utf8')

                msgs = []
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
                            mesg = json.loads(byts)
                        except json.JSONDecodeError:
                            bufr = jstr
                            break
                        else:
                            msgs.append(mesg)

                self.eq(msgs, ({'oh': 1}, {'oh': 2}, {'oh': 3}))

    async def test_libcortex_httpapi_perms(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Set a handler which requires a single permission

            q = '''
            $api = $lib.cortex.httpapi.add('hehe/haha')
            $api.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $api.methods.head = ${
                $request.replay(200, ({"yup": "it exists"}) )
            }
            $api.name = 'the hehe/haha handler'
            $api.desc = 'beep boop zoop robot captain'
            $api.runas = user
            $api.perms = (foocorp.http.user, )
            return ( $api.iden )
            '''
            iden0 = await core.callStorm(q)

            # Set a handler which has a few permissions, using perm
            # defs to require there is a default=true permission
            q = '''$api = $lib.cortex.httpapi.add('weee')
            $api.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $api.perms = ( ({'perm': ['foocorp', 'http', 'user']}), ({'perm': ['apiuser'], 'default': $lib.true}) )
            $api.runas = user
            return ( $api.iden )
            '''
            iden1 = await core.callStorm(q)

            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                self.eq(resp.status, 403)
                data = await resp.json()
                self.eq(data.get('mesg'), 'User (lowuser) must have permission foocorp.http.user')

                await core.stormlist('auth.user.addrule lowuser foocorp.http.user')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('path'), 'hehe/haha')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/weee')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data.get('path'), 'weee')

                # Add a deny rule for this user
                await core.stormlist('auth.user.addrule lowuser "!apiuser"')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/weee')
                self.eq(resp.status, 403)
                data = await resp.json()
                self.eq(data.get('mesg'), 'User (lowuser) is denied the permission apiuser')

            # Defining perms as !foo.bar.baz does not work
            with self.raises(s_exc.BadArg):
                q = "$api=$lib.cortex.httpapi.get($iden) $api.perms=('!foo.bar.baz',)"
                await core.callStorm(q, opts={'vars': {'iden': iden0}})

    async def test_libcortex_httpapi_view(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            def_view = await core.callStorm('return ( $lib.view.get().iden )')

            q = '$lyr=$lib.layer.add() $view=$lib.view.add(($lyr.iden,), name="iso view") return ( $view.iden )'
            view = await core.callStorm(q)

            q = '''$api = $lib.cortex.httpapi.add(testpath)
            $api.methods.get = ${
                $view = $lib.view.get()
                $request.reply(200, body=({'view': $view.iden}) )
            }
            return ( $api.iden )
            '''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                data = await resp.json()
                self.eq(data.get('view'), def_view)

                # Change the view the endpoint uses
                q = '$api=$lib.cortex.httpapi.get($http_iden) $api.view = $lib.view.get($view_iden)'
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden, 'view_iden': view}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                data = await resp.json()
                self.eq(data.get('view'), view)

                # Our gtor gives a heavy view object
                name = await core.callStorm('$api=$lib.cortex.httpapi.get($http_iden) return ($api.view.get(name))',
                                            opts={'vars': {'http_iden': iden}})
                self.eq(name, 'iso view')

                # If the view is deleted out from under the object, it has no knowledge of that
                msgs = await core.stormlist('$lib.view.del($iden)', opts={'vars': {'iden': view}})
                self.stormHasNoWarnErr(msgs)

                # The gtor throws
                with self.raises(s_exc.NoSuchView):
                    await core.callStorm('$api=$lib.cortex.httpapi.get($http_iden) return ($api.view.get(name))',
                                         opts={'vars': {'http_iden': iden}})

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'NoSuchView')

                # Change the view back to the original view by iden
                q = '$api=$lib.cortex.httpapi.get($http_iden) $api.view = $view_iden'
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden, 'view_iden': def_view}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                data = await resp.json()
                self.eq(data.get('view'), def_view)

    async def test_libcortex_httpapi_headers_params(self):

        # Test around case sensitivity of request headers and parameters

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$api = $lib.cortex.httpapi.add(testpath)
            $api.methods.get = ${
                $data = ({
                    "Secret-Key": $request.headers."Secret-Key",
                    "secret-key": $request.headers."secret-key",
                    "aaa": $request.headers.AAA,
                    "hehe": $request.params.hehe,
                    "HeHe": $request.params.HeHe,
                })
                $request.reply(200, body=$data )
            }
            // Cannot modify request headers
            $api.methods.post = ${
                $request.headers.newp = haha
            }
            return ( ($api.iden, $api.owner.name) )
            '''
            iden, uname = await core.callStorm(q)
            self.eq(uname, 'root')

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',
                                      headers=(('secret-KEY', 'myluggagecombination'), ('aaa', 'zzz'), ('aaa', 'wtaf')),
                                      params=(('hehe', 'haha'), ('wow', 'words'), ('hehe', 'badjoke'), ('HeHe', ':)'))
                                      )
                self.eq(resp.status, 200)
                data = await resp.json()

                # Params are flattened and case-sensitive upon access
                self.eq(data.get('hehe'), 'haha')
                self.eq(data.get('HeHe'), ':)')

                # Headers are flattened and NOT case-sensitive upon access
                self.eq(data.get('aaa'), 'zzz')
                self.eq(data.get('Secret-Key'), 'myluggagecombination')
                self.eq(data.get('secret-key'), 'myluggagecombination')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'StormRuntimeError')
                self.eq(data.get('mesg'), 'http:request:headers may not be modified by the runtime')

    async def test_libcortex_httpapi_vars(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$api = $lib.cortex.httpapi.add(testpath)
            $api.methods.get =  ${ $data = ({"hehe": $hehe }) $request.reply(200, body=$data) }
            $api.methods.post = ${ $data = ({"sup": $sup })   $request.reply(200, body=$data) }
            $api.vars.hehe = haha
            $api.vars.sup = dawg
            return ( ($api.iden) )
            '''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',)
                data = await resp.json()
                self.eq(data.get('hehe'), 'haha')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                data = await resp.json()
                self.eq(data.get('sup'), 'dawg')

                q = '''$api=$lib.cortex.httpapi.get($http_iden)
                $api.vars = ({ "hehe": "yup", "sup": "word"})
                '''
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',)
                data = await resp.json()
                self.eq(data.get('hehe'), 'yup')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                data = await resp.json()
                self.eq(data.get('sup'), 'word')

                # Cause a NoSuchVar error due to a missing var in the handler
                q = '$api=$lib.cortex.httpapi.get($iden) $api.vars.sup = $lib.undef'
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)
                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'NoSuchVar')
                self.eq(data.get('mesg'), 'Missing variable: sup')

            q = '''$api = $lib.cortex.httpapi.get($iden)

            $api = $lib.cortex.httpapi.get($iden)

            $vars = $api.vars  // _ctor to make a thin object
            $vars.hehe = haha // set and persist hehe=haha

            $lib.print('pre _stor')
            for ($k, $v) in $vars {
                $lib.print(`{$k} -> {$v}`)
            }

            // Use a _stor to set new vars in place
            $api.vars = ({"hehe": "i am silly", "why": "why not"})

            $lib.print('post _stor')
            for ($k, $v) in $vars {
                $lib.print(`{$k} -> {$v}`)
            }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hehe -> haha', msgs)
            self.stormIsInPrint('hehe -> i am silly', msgs)
            self.stormIsInPrint('why -> why not', msgs)

    async def test_libcortex_httpapi_readonly(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # nothing
            q = '''$api = $lib.cortex.httpapi.add(testpath)
            $api.methods.get = ${ [inet:asn=$request.params.asn ] $request.reply(200, body=$node.value())}
            return ( ($api.iden) )'''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath?asn=0')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data, 0)

                msgs = await core.stormlist('$api=$lib.cortex.httpapi.get($iden) $api.readonly = $lib.true',
                                            opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath?asn=1')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'IsReadOnly')

                q = '''$api=$lib.cortex.httpapi.get($iden)
                $api.methods.get = ${ inet:asn=$request.params.asn $request.reply(200, body=$node.value()) }'''
                msgs = await core.stormlist(q, opts={'vars': {'iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath?asn=0')
                self.eq(resp.status, 200)
                data = await resp.json()
                self.eq(data, 0)

    async def test_libcortex_httpapi_fsm_sadpath(self):

        # Test to exercise sad paths of the state machine for the ExtHttpApi handler
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # nothing
            q = '''$api = $lib.cortex.httpapi.add(bad00)
            $api.methods.get =  ${ }
            return ( ($api.iden) )'''
            iden00 = await core.callStorm(q)

            # no status code
            q = '''$api = $lib.cortex.httpapi.add(bad01)
            $api.methods.get =  ${ $request.sendheaders( ({"oh":"my"}) ) }
            return ( ($api.iden) )'''
            iden01 = await core.callStorm(q)

            # no status code and a body being sent
            q = '''$api = $lib.cortex.httpapi.add(bad02)
            $api.methods.get = ${ $request.sendheaders(({"oh":"my"})) $data='text' $request.sendbody($data.encode()) }
            return ( ($api.iden) )'''
            iden02 = await core.callStorm(q)

            # code after body has been sent
            q = '''$api = $lib.cortex.httpapi.add(bad03)
            $api.methods.get = ${ $data='text' $request.reply(201, body=$data.encode()) $request.sendcode(403) }
            return ( ($api.iden) )'''
            iden03 = await core.callStorm(q)

            # headers after body has been sent
            q = '''$api = $lib.cortex.httpapi.add(bad04)
            $api.methods.get = ${$d='text' $request.reply(200, body=$d.encode()) $request.sendheaders(({"oh": "hi"}))}
            return ( ($api.iden) )'''
            iden04 = await core.callStorm(q)

            # storm error
            q = '''$api = $lib.cortex.httpapi.add(bad05)
            $api.methods.get = ${ [test:int = notAnInt ] }
            return ( ($api.iden) )'''
            iden05 = await core.callStorm(q)

            # storm error AFTER body has been sent
            q = '''$api = $lib.cortex.httpapi.add(bad06)
            $api.methods.get = ${ $request.reply(201, body=({})) [test:int = notAnInt ] }
            return ( ($api.iden) )'''
            iden06 = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/bad00')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'StormRuntimeError')
                self.eq(data.get('mesg'), f'Extended HTTP API {iden00} never set status code.')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/bad01')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.notin('oh', resp.headers)
                self.eq(data.get('code'), 'StormRuntimeError')
                self.eq(data.get('mesg'), f'Extended HTTP API {iden01} never set status code.')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/bad02')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.notin('oh', resp.headers)
                self.eq(data.get('code'), 'StormRuntimeError')
                self.eq(data.get('mesg'), f'Extended HTTP API {iden02} must set status code before sending body.')

                with self.getAsyncLoggerStream('synapse.lib.httpapi',
                                               f'Extended HTTP API {iden03} tried to set code after sending body.') as stream:

                    resp = await sess.get(f'https://localhost:{hport}/api/ext/bad03')
                    self.true(await stream.wait(timeout=6))
                    self.eq(resp.status, 201)
                    self.eq(await resp.read(), b'text')

                with self.getAsyncLoggerStream('synapse.lib.httpapi',
                                               f'Extended HTTP API {iden04} tried to set headers after sending body.') as stream:
                    resp = await sess.get(f'https://localhost:{hport}/api/ext/bad04')
                    self.true(await stream.wait(timeout=6))
                    self.eq(resp.status, 200)
                    self.eq(await resp.read(), b'text')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/bad05')
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('code'), 'BadTypeValu')
                self.eq(data.get('mesg'), "invalid literal for int() with base 0: 'notAnInt'")

                with self.getAsyncLoggerStream('synapse.lib.httpapi',
                                               f'Error executing Extended HTTP API {iden06}: BadTypeValu') as stream:
                    resp = await sess.get(f'https://localhost:{hport}/api/ext/bad06')
                    self.true(await stream.wait(timeout=6))
                    self.eq(resp.status, 201)
                    self.eq(await resp.json(), {})

    async def test_cortex_httpapi_dynamic(self):

        # API endpoints can be dynamic. Use at your own risk.

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$api = $lib.cortex.httpapi.add(dyn00)
            $api.methods.get =  ${
                $api = $request.api
                if $n {
                    $part = `redir0{$n}`
                    $redir = `/api/ext/{$part}`
                    $headers = ({"Location": $redir})
                    $api.vars.n = ($n - (1) )
                    $api.path = $part
                    $request.reply(301, headers=$headers)
                } else {
                    $api.vars.n = (3)
                    $api.vars.melt = $lib.true
                    $api.path = dyn00
                    $request.reply(200, body=({"end": "youMadeIt", "melt": $melt}) )
                    if $melt {
                        $lib.cortex.httpapi.del($api.iden)
                    }
                }
            }
            $api.vars.n = (3)
            $api.vars.melt = $lib.false
            return ( ($api.iden) )'''
            iden00 = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/dyn00')  # type: aiohttp.ClientResponse
                self.eq(resp.status, 200)
                self.eq(resp.url.path, '/api/ext/redir01')
                self.len(3, resp.history)
                data = await resp.json()
                self.eq(data, {'end': 'youMadeIt', 'melt': False})

                resp = await sess.get(f'https://localhost:{hport}/api/ext/dyn00')  # type: aiohttp.ClientResponse
                self.eq(resp.status, 200)
                self.len(3, resp.history)
                data = await resp.json()
                self.eq(data, {'end': 'youMadeIt', 'melt': True})

                resp = await sess.get(f'https://localhost:{hport}/api/ext/dyn00')  # type: aiohttp.ClientResponse
                self.eq(resp.status, 404)
                data = await resp.json()
                self.eq(data.get('code'), 'NoSuchPath')