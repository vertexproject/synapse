import asyncio

from unittest import mock

import aioimaplib

import synapse.common as s_common

import synapse.tests.utils as s_test

from pprint import pprint

class CortexLibTest(s_test.SynTest):
    async def test_libcortex_httpapi_simple(self):
        async with self.getTestCore() as core:

            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
                $obj = $lib.cortex.httpapi.add('hehe/haha')
                $obj.methods.get = ${
    $data = ({'oh': 'my'})
    $headers = ({'Secret-Header': 'OhBoy!'})
    $request.reply(200, headers=$headers, body=$data)
                }
                '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            q = '''
                $obj = $lib.cortex.httpapi.add('hehe/haha/(.*)/(.*)')
    $obj.methods.get = ${
    $data = ({'oh': 'we got a wildcard match!'})
    $headers = ({'Secret-Header': 'ItsWildcarded!'})
    $request.reply(200, headers=$headers, body=$data)
    }
                            '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            q = '''$obj = $lib.cortex.httpapi.add('echo/(.*)')
                $obj.methods.get = ${
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
                                        '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha',
                                      headers=(('Hi', 'George'), ('Sup', 'Buddy'), ('Hi', 'Alice')))
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://lowuser:secret@localhost:{hport}/api/ext/hehe/haha/haha/wow?sup=dude')
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://lowuser:secret@localhost:{hport}/api/ext/echo/sup?echo=test')
                print(resp)
                buf = await resp.json()
                pprint(buf)

                resp = await sess.get(f'https://lowuser:secret@localhost:{hport}/api/ext/echo/sup?echo=test&giggle=haha&echo=eggs',
                                      headers=(('hehe', 'haha'), ('apikey', 'secret'), ('hehe', 'badjoke')),
                                      json={'look': 'at this!'})
                buf = await resp.json()
                pprint(buf)

                resp = await sess.get(f'https://lowuser:secret@localhost:{hport}/api/ext/echo/sup?echo=test',
                                      data=b'buffer')
                print(resp)
                buf = await resp.json()
                pprint(buf)

    async def test_libcortex_httpapi_order(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $obj.methods.head = ${
                $request.replay(200, ({"yup": "it exists"}) )
            }
            $obj.name = 'the hehe/haha handler'
            $obj.desc = 'beep boop zoop robot captain'
            $obj.runas = user
            return ( $obj.iden )
            '''
            iden0 = await core.callStorm(q)

            q = '''
            $obj = $lib.cortex.httpapi.add('hehe')
            $obj.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $obj.authenticated = $lib.false
            return ( $obj.iden )
            '''
            iden1 = await core.callStorm(q)

            q = '''
            $obj = $lib.cortex.httpapi.add('wow')
            $obj.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $obj.authenticated = $lib.false
            return ( $obj.iden )
            '''
            iden2 = await core.callStorm(q)

            msgs = await core.stormlist('httpapi.ext.list')
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            msgs = await core.stormlist('httpapi.ext.stat $iden', opts={'vars': {'iden': iden0}})
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            msgs = await core.stormlist('httpapi.ext.index $iden 1', opts={'vars': {'iden': iden0}})
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            msgs = await core.stormlist('httpapi.ext.list')
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            msgs = await core.stormlist('httpapi.ext.index $iden 100', opts={'vars': {'iden': iden1}})
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            msgs = await core.stormlist('httpapi.ext.list')
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            q = '''$api = $lib.cortex.httpapi.get($iden)

            $api = $lib.cortex.httpapi.get($iden)

            $vars = $api.vars  // _ctor to make a thin object
            $vars.hehe = haha // set and persist hehe=haha

            $lib.print('pre _stor')
            for ($k, $v) in $vars {
                $lib.print(`{$k} -> {$v}`)
            }

            // Use a _stor to smash the data in
            $api.vars = ({"hehe": "i am silly", "why": "why not"})

            $lib.print('post _stor')
            for ($k, $v) in $vars {
                $lib.print(`{$k} -> {$v}`)
            }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'iden': iden0}})
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hehe -> haha', msgs)
            self.stormIsInPrint('hehe -> i am silly', msgs)
            self.stormIsInPrint('why -> why not', msgs)

            msgs = await core.stormlist('httpapi.ext.stat $iden', opts={'vars': {'iden': iden0}})
            for m in msgs:
                if m[0] == 'print':
                    print(m[1].get('mesg'))
                    continue
                print(m)

    async def test_libcortex_httpapi_asbytes(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.methods.get = ${
$data = ({'oh': 'my'})
$body = $lib.json.save($data).encode()
$headers = ({'Secret-Header': 'OhBoy!'})
$headers."Content-Type" = "application/json"
$headers."Content-Length" = $lib.len($body)
$request.reply(200, headers=$headers, body=$body)
            }
            '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha/(.*)/(.*)')
$obj.methods.get = ${
$data = ({'oh': 'we got a wildcard match!'})
$body = $lib.json.save($data).encode()
$headers = ({'Secret-Header': 'ItsWildcarded!'})
$headers."Content-Type" = "application/json"
$headers."Content-Length" = $lib.len($body)
$request.reply(200, headers=$headers, body=$body)
}
            '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha/haha/wow?sup=dude')
                print(resp)
                buf = await resp.read()
                print(buf)

    async def test_libcortex_jsonlines(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''$obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.methods.get = ${
$request.sendcode(201)
$headers = ({"Secret-Header": "OhBoy!", "Content-Type": "application/jsonlines"})
$request.sendheaders($headers)
$request.sendheaders(({"MoreHeader": "SphericalCow"}))
$request.sendheaders(({"Secret-Header": "TheOverwrite"}))
$values = (1, 2, 3)
$newline = "\\n"
$newline = $newline.encode()
for $i in $values {
    $data = ({'oh': $i})
    $body = $lib.json.save($data).encode()
    $request.sendbody($body)
    $request.sendbody($newline)
}
}
            '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha?sup=dude')
                print(resp)
                buf = await resp.read()
                print(buf)

    async def test_libcortex_perms(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $obj.methods.head = ${
                $request.replay(200, ({"yup": "it exists"}) )
            }
            $obj.name = 'the hehe/haha handler'
            $obj.desc = 'beep boop zoop robot captain'
            $obj.runas = user
            $obj.perms = (foocorp.http.user, )
            return ( $obj.iden )
            '''
            iden0 = await core.callStorm(q)

            q = '''$obj = $lib.cortex.httpapi.add('weee')
            $obj.methods.get = ${
            $data = ({'path': $request.path})
            $request.reply(200, body=$data)
            }
            $obj.perms = ( ({'perm': ['foocorp', 'http', 'user']}), ({'perm': ['apiuser'], 'default': $lib.true}) )
            $obj.runas = user
            return ( $obj.iden )
            '''
            iden1 = await core.callStorm(q)

            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                print(resp)
                buf = await resp.read()
                print(buf)

                await core.stormlist('auth.user.addrule lowuser foocorp.http.user')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/weee')
                print(resp)
                buf = await resp.read()
                print(buf)

                await core.stormlist('auth.user.addrule lowuser "!apiuser"')

                resp = await sess.get(f'https://localhost:{hport}/api/ext/weee')
                print(resp)
                buf = await resp.read()
                print(buf)

    async def test_libcortex_view(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            def_view = await core.callStorm('return ( $lib.view.get().iden )')

            q = '$lyr=$lib.layer.add() $view=$lib.view.add(($lyr.iden,), name="iso view") return ( $view.iden )'
            view = await core.callStorm(q)

            q = '''$obj = $lib.cortex.httpapi.add(testpath)
            $obj.methods.get = ${
                $view = $lib.view.get()
                $request.reply(200, body=({'view': $view.iden}) )
            }
            return ( $obj.iden )
            '''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('lowuser', 'secret'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                print(resp)
                data = await resp.json()
                self.eq(data.get('view'), def_view)

                # Change the view the endpoint uses
                q = '$obj=$lib.cortex.httpapi.get($http_iden) $lib.print($obj) $lib.print($lib.vars.type($obj))' \
                    '$view=$lib.view.get($view_iden) $lib.print($view)' \
                    '$obj.view = $view $lib.print($obj) '
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden, 'view_iden': view}})
                for m in msgs:
                    print(m)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath')
                print(resp)
                data = await resp.json()
                self.eq(data.get('view'), view)

                # Our gtor gives a heavy view object
                name = await core.callStorm('$obj=$lib.cortex.httpapi.get($http_iden) return ($obj.view.get(name))',
                                            opts={'vars': {'http_iden': iden}})
                self.eq(name, 'iso view')

    async def test_libcortex_owner(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$obj = $lib.cortex.httpapi.add(testpath)
            $obj.methods.get = ${
                $view = $lib.view.get()
                $request.reply(200, body=({'view': $view.iden}) )
            }
            return ( ($obj.iden, $obj.owner.name) )
            '''
            iden, uname = await core.callStorm(q)
            self.eq(uname, 'root')

            q = '''
            $obj=$lib.cortex.httpapi.get($http_iden)
            $user=$lib.auth.users.byname(lowuser) $obj.owner = $user
            return ($obj.owner.name)'''
            name = await core.callStorm(q, opts={'vars': {'http_iden': iden}})
            self.eq(name, 'lowuser')

    async def test_libcortex_headers_params(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$obj = $lib.cortex.httpapi.add(testpath)
            $obj.methods.get = ${
                $data = ({
                    "Secret-Key": $request.headers."Secret-Key",
                    "secret-key": $request.headers."secret-key",
                    "aaa": $request.headers.AAA,
                    "hehe": $request.params.hehe,
                    "HeHe": $request.params.HeHe,
                })
                $request.reply(200, body=$data )
            }
            return ( ($obj.iden, $obj.owner.name) )
            '''
            iden, uname = await core.callStorm(q)
            self.eq(uname, 'root')

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',
                                      headers=(('secret-KEY', 'myluggagecombination'), ('aaa', 'zzz'), ('aaa', 'wtaf')),
                                      params=(('hehe', 'haha'), ('wow', 'words'), ('hehe', 'badjoke'), ('HeHe', ':)'))
                                      )
                data = await resp.json()

                # Params are flattened and case-sensitive upon access
                self.eq(data.get('hehe'), 'haha')
                self.eq(data.get('HeHe'), ':)')

                # Headers are flattened and NOT case-sensitive upon access
                self.eq(data.get('aaa'), 'zzz')
                self.eq(data.get('Secret-Key'), 'myluggagecombination')
                self.eq(data.get('secret-key'), 'myluggagecombination')

    async def test_libcortex_varz(self):

        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            q = '''$obj = $lib.cortex.httpapi.add(testpath)
            $obj.methods.get =  ${ $data = ({"hehe": $hehe }) $request.reply(200, body=$data) }
            $obj.methods.post = ${ $data = ({"sup": $sup })   $request.reply(200, body=$data) }
            $obj.vars.hehe = haha
            $obj.vars.sup = dawg
            return ( ($obj.iden) )
            '''
            iden = await core.callStorm(q)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',)
                data = await resp.json()
                self.eq(data.get('hehe'), 'haha')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                data = await resp.json()
                self.eq(data.get('sup'), 'dawg')

                q = '''$obj=$lib.cortex.httpapi.get($http_iden)
                $obj.vars = ({ "hehe": "yup", "sup": "word"})
                '''
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden}})
                self.stormHasNoWarnErr(msgs)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/testpath',)
                data = await resp.json()
                self.eq(data.get('hehe'), 'yup')

                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                data = await resp.json()
                self.eq(data.get('sup'), 'word')

                q = '''$obj=$lib.cortex.httpapi.get($http_iden)
                $obj.vars.sup = $lib.undef
                '''
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden}})
                self.stormHasNoWarnErr(msgs)
                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                self.eq(resp.status, 500)
                data = await resp.json()
                # Generic error
                self.eq(data.get('mesg'), 'Handler never set status code.')

                q = '''$obj=$lib.cortex.httpapi.get($http_iden)
                $obj.methods.post = $lib.undef
                '''
                msgs = await core.stormlist(q, opts={'vars': {'http_iden': iden}})
                self.stormHasNoWarnErr(msgs)
                resp = await sess.post(f'https://localhost:{hport}/api/ext/testpath', )
                self.eq(resp.status, 500)
                data = await resp.json()
                self.eq(data.get('mesg'), 'No storm endpoint defined for method post')
