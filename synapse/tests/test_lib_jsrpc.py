import http

import synapse.exc as s_exc
import synapse.lib.json as s_json
import synapse.lib.jsrpc as s_jsrpc

import synapse.tests.utils as s_tests

class FakeRpcHandler(s_jsrpc.JsonRpcHandler):
    '''
    A sample handler exercising the various jsrpc method shapes.
    '''
    def _private(self):  # not exposed (no decorator)
        return 'nope'

    def undecorated(self):  # not exposed (no decorator)
        return 'nope'

    @s_jsrpc.method(desc='Echo a value back.')
    async def echo(self, valu):
        return valu

    @s_jsrpc.method(name='add.numbers')
    async def addNumbers(self, a, b):
        return a + b

    @s_jsrpc.method()
    async def whoami(self):
        return self.web_useriden

    @s_jsrpc.method(params={
        'type': 'object',
        'properties': {'name': {'type': 'string'}},
        'required': ['name'],
        'additionalProperties': False,
    }, returns={'type': 'string'})
    async def greet(self, name):
        return f'hello {name}'

    @s_jsrpc.method()
    async def counter(self, n):
        for i in range(n):
            yield i

    @s_jsrpc.method()
    async def boom(self):
        raise s_exc.BadArg(mesg='boom', extra='nope')

    @s_jsrpc.method()
    async def pyboom(self):
        raise ValueError('plain python error')

    @s_jsrpc.method()
    async def failstream(self, n):
        for i in range(n):
            yield i
        raise s_exc.BadArg(mesg='stream broke')

    @s_jsrpc.method()
    async def badinfo(self):
        raise s_exc.BadArg(mesg='badinfo', obj=object())

    @s_jsrpc.method(name='app.error')
    async def apperr(self):
        raise s_exc.JsonRpcError.init(-32050, 'app failure', data={'why': 'because'})

class JsRpcTest(s_tests.SynTest):

    async def _post(self, sess, url, item=None, data=None, headers=None):
        kwargs = {}
        if item is not None:
            kwargs['json'] = item

        if data is not None:
            kwargs['data'] = data

        if headers is not None:
            kwargs['headers'] = headers

        async with sess.post(url, **kwargs) as resp:
            body = await resp.read()
            return resp.status, body

    async def _call(self, sess, url, item, headers=None):
        status, body = await self._post(sess, url, item=item, headers=headers)
        self.eq(status, http.HTTPStatus.OK)
        return s_json.loads(body)

    async def test_jsrpc_metadata(self):

        info = FakeRpcHandler.echo._jsrpc_method
        self.eq('echo', info.get('name'))
        self.eq('Echo a value back.', info.get('desc'))
        self.false(info.get('genr'))

        self.true(FakeRpcHandler.counter._jsrpc_method.get('genr'))
        self.eq('add.numbers', FakeRpcHandler.addNumbers._jsrpc_method.get('name'))

        # loadMethodDefs only exposes decorated methods and caches on the class
        meths = FakeRpcHandler.loadMethodDefs()
        self.isin('echo', meths)
        self.isin('add.numbers', meths)
        self.notin('undecorated', meths)
        self.notin('_private', meths)
        self.eq('addNumbers', meths.get('add.numbers').get('attr'))
        self.true(FakeRpcHandler.loadMethodDefs() is meths)

        # the method def carries its schemas for higher level introspection
        self.eq('string', meths['greet']['info']['returns']['type'])

        # the registry is JSON compatible; validators and arg signatures are stored separately
        self.nn(s_json.dumps(meths))
        self.nn(FakeRpcHandler._syn_jsrpc_validators.get('greet'))
        self.none(FakeRpcHandler._syn_jsrpc_validators.get('echo'))
        self.nn(FakeRpcHandler._syn_jsrpc_signatures.get('echo'))

        # a non-async method is rejected at registration
        with self.raises(s_exc.BadArg):
            class BadHandler(s_jsrpc.JsonRpcHandler):
                @s_jsrpc.method()
                def notasync(self):
                    return 1

    async def test_jsrpc_calls(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/api/v1/jsrpc', FakeRpcHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/jsrpc'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                # by-position params
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 1, 'method': 'echo', 'params': ['hi']})
                self.eq(retn, {'jsonrpc': '2.0', 'id': 1, 'result': 'hi'})

                # by-name params + async method
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 2, 'method': 'add.numbers',
                                                    'params': {'a': 3, 'b': 4}})
                self.eq(7, retn.get('result'))

                # no params
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 3, 'method': 'whoami'})
                self.eq(root.iden, retn.get('result'))

                # schema validation pass
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 4, 'method': 'greet',
                                                    'params': {'name': 'bob'}})
                self.eq('hello bob', retn.get('result'))

                # explicit null id is a request (not a notification)
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': None, 'method': 'echo', 'params': ['x']})
                self.eq(retn, {'jsonrpc': '2.0', 'id': None, 'result': 'x'})

    async def test_jsrpc_errors(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/api/v1/jsrpc', FakeRpcHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/jsrpc'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            # unauthenticated requests are rejected before dispatch
            async with self.getHttpSess() as anon:
                status, body = await self._post(anon, url, item={'jsonrpc': '2.0', 'id': 1, 'method': 'echo'})
                self.eq(status, http.HTTPStatus.UNAUTHORIZED)

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                # method not found
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 1, 'method': 'nope'})
                self.eq(s_jsrpc.METHOD_NOT_FOUND, retn.get('error').get('code'))

                # invalid request - bad version
                retn = await self._call(sess, url, {'jsonrpc': '1.0', 'id': 2, 'method': 'echo'})
                self.eq(s_jsrpc.INVALID_REQUEST, retn.get('error').get('code'))
                self.none(retn.get('id'))

                # invalid request - method not a string
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 3, 'method': 123})
                self.eq(s_jsrpc.INVALID_REQUEST, retn.get('error').get('code'))

                # invalid request - id is a bool
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': True, 'method': 'echo'})
                self.eq(s_jsrpc.INVALID_REQUEST, retn.get('error').get('code'))

                # invalid request - id is a list
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': [1], 'method': 'echo'})
                self.eq(s_jsrpc.INVALID_REQUEST, retn.get('error').get('code'))

                # invalid params - bind failure (missing required arg)
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 4, 'method': 'greet', 'params': []})
                self.eq(s_jsrpc.INVALID_PARAMS, retn.get('error').get('code'))

                # invalid params - schema violation
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 5, 'method': 'greet',
                                                    'params': {'name': 123}})
                self.eq(s_jsrpc.INVALID_PARAMS, retn.get('error').get('code'))

                # invalid params - params is neither array nor object
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 6, 'method': 'echo', 'params': 'bad'})
                self.eq(s_jsrpc.INVALID_PARAMS, retn.get('error').get('code'))

                # parse error - invalid json body
                status, body = await self._post(sess, url, data=b'{not json')
                self.eq(status, http.HTTPStatus.OK)
                retn = s_json.loads(body)
                self.eq(s_jsrpc.PARSE_ERROR, retn.get('error').get('code'))
                self.none(retn.get('id'))

                # application defined error w/ code + data
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 7, 'method': 'app.error'})
                self.eq(-32050, retn.get('error').get('code'))
                self.eq('app failure', retn.get('error').get('message'))
                self.eq({'why': 'because'}, retn.get('error').get('data'))

                # uncaught SynErr maps to internal error, errinfo attached as data
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 8, 'method': 'boom'})
                self.eq(s_jsrpc.INTERNAL_ERROR, retn.get('error').get('code'))
                self.eq('boom', retn.get('error').get('message'))
                self.eq('nope', retn.get('error').get('data').get('extra'))

                # internal error with non-json-safe errinfo omits the data field
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 9, 'method': 'badinfo'})
                self.eq(s_jsrpc.INTERNAL_ERROR, retn.get('error').get('code'))
                self.none(retn.get('error').get('data'))

                # a non-SynErr exception maps to internal error using its str()
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 10, 'method': 'pyboom'})
                self.eq(s_jsrpc.INTERNAL_ERROR, retn.get('error').get('code'))
                self.eq('plain python error', retn.get('error').get('message'))
                self.none(retn.get('error').get('data'))

    async def test_jsrpc_notifications_and_batch(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/api/v1/jsrpc', FakeRpcHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/jsrpc'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                # a lone notification gets no body and a 204
                status, body = await self._post(sess, url, item={'jsonrpc': '2.0', 'method': 'echo', 'params': ['x']})
                self.eq(status, http.HTTPStatus.NO_CONTENT)
                self.eq(b'', body)

                # a notification to an unknown method still yields no response
                status, body = await self._post(sess, url, item={'jsonrpc': '2.0', 'method': 'nope'})
                self.eq(status, http.HTTPStatus.NO_CONTENT)

                # a notification whose method raises still yields no response
                status, body = await self._post(sess, url, item={'jsonrpc': '2.0', 'method': 'boom'})
                self.eq(status, http.HTTPStatus.NO_CONTENT)

                # batch with mixed requests and a notification (notification omitted)
                batch = [
                    {'jsonrpc': '2.0', 'id': 1, 'method': 'echo', 'params': ['a']},
                    {'jsonrpc': '2.0', 'method': 'echo', 'params': ['ignored']},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'add.numbers', 'params': {'a': 1, 'b': 2}},
                    {'jsonrpc': '2.0', 'id': 3, 'method': 'nope'},
                    'notadict',
                ]
                retn = await self._call(sess, url, batch)
                self.len(4, retn)
                byid = {r.get('id'): r for r in retn}
                self.eq('a', byid.get(1).get('result'))
                self.eq(3, byid.get(2).get('result'))
                self.eq(s_jsrpc.METHOD_NOT_FOUND, byid.get(3).get('error').get('code'))
                self.eq(s_jsrpc.INVALID_REQUEST, byid.get(None).get('error').get('code'))

                # empty batch is a single invalid request error
                retn = await self._call(sess, url, [])
                self.eq(s_jsrpc.INVALID_REQUEST, retn.get('error').get('code'))

                # batch of only notifications yields a 204
                onlynotifs = [
                    {'jsonrpc': '2.0', 'method': 'echo', 'params': ['x']},
                    {'jsonrpc': '2.0', 'method': 'echo', 'params': ['y']},
                ]
                status, body = await self._post(sess, url, item=onlynotifs)
                self.eq(status, http.HTTPStatus.NO_CONTENT)

    async def test_jsrpc_streaming(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/api/v1/jsrpc', FakeRpcHandler, {'cell': core})

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/jsrpc'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                # generator without SSE accept is collected into an array result
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 1, 'method': 'counter', 'params': [3]})
                self.eq([0, 1, 2], retn.get('result'))

                # a non-streaming generator result that exceeds the cap is an error
                toobig = s_jsrpc.MAX_RESULT_ITEMS + 1
                retn = await self._call(sess, url, {'jsonrpc': '2.0', 'id': 9, 'method': 'counter', 'params': [toobig]})
                self.eq(s_jsrpc.RESULT_TOO_LARGE, retn.get('error').get('code'))

                # generator as a notification is drained and produces no response
                status, body = await self._post(sess, url, item={'jsonrpc': '2.0', 'method': 'counter', 'params': [3]})
                self.eq(status, http.HTTPStatus.NO_CONTENT)

                # generator with SSE accept streams events then a terminating response
                headers = {'Accept': 'text/event-stream'}
                async with sess.post(url, json={'jsonrpc': '2.0', 'id': 2, 'method': 'counter', 'params': [3]},
                                     headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    self.isin('text/event-stream', resp.headers.get('Content-Type'))
                    text = await resp.text()

                mesgs = [s_json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: ')]
                self.len(4, mesgs)
                self.eq([0, 1, 2], [m.get('params').get('item') for m in mesgs[:3]])
                self.eq(2, mesgs[-1].get('id'))
                self.none(mesgs[-1].get('result'))

                # a generator that raises mid-stream terminates with an error response
                async with sess.post(url, json={'jsonrpc': '2.0', 'id': 3, 'method': 'failstream', 'params': [2]},
                                     headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    text = await resp.text()

                mesgs = [s_json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: ')]
                self.eq([0, 1], [m.get('params').get('item') for m in mesgs[:2]])
                self.eq(s_jsrpc.INTERNAL_ERROR, mesgs[-1].get('error').get('code'))
                self.eq('stream broke', mesgs[-1].get('error').get('message'))
