import http

import synapse.exc as s_exc
import synapse.lib.cell as s_cell
import synapse.lib.json as s_json
import synapse.lib.mcp as s_mcp
import synapse.lib.jsrpc as s_jsrpc

import synapse.tests.utils as s_tests

class TstMcp(s_mcp.CellMcp):
    '''
    A CellMcp subclass with extra tools to exercise the tool dispatch paths.
    '''
    @s_mcp.tool(name='boom', desc='Raise a non-SynErr.')
    async def boom(self):
        raise ValueError('kaboom')

    @s_mcp.tool(name='synboom', desc='Raise a SynErr.')
    async def synboom(self):
        raise s_exc.BadArg(mesg='bad arg tool')

    @s_mcp.tool(name='gen', desc='Yield a few integers.')
    async def gen(self, n=3):
        for i in range(n):
            yield i

    @s_mcp.tool(name='genboom', desc='Stream then raise.')
    async def genboom(self):
        yield 1
        raise ValueError('streamfail')

    @s_mcp.tool(name='needsperm', perm=('mcp', 'secret'))
    async def needsperm(self):
        return 'ok'

    @s_mcp.tool(name='addone', schema={
        'type': 'object',
        'properties': {'x': {'type': 'integer'}},
        'required': ['x'],
        'additionalProperties': False,
    })
    async def addone(self, x):
        return x + 1

class TstMcpCell(s_cell.Cell):
    _mcp_ctor = TstMcp

class McpTest(s_tests.SynTest):

    def _initBody(self, _id=1):
        return {'jsonrpc': '2.0', 'id': _id, 'method': 'initialize',
                'params': {'protocolVersion': s_mcp.PROTOCOL_VERSION, 'capabilities': {},
                           'clientInfo': {'name': 'test', 'version': '1'}}}

    async def _initOnly(self, sess, url, headers=None):
        async with sess.post(url, json=self._initBody(), headers=headers) as resp:
            sid = resp.headers.get('Mcp-Session-Id')
            return resp.status, sid, await resp.json()

    async def _handshake(self, sess, url):
        status, sid, data = await self._initOnly(sess, url)
        self.eq(status, http.HTTPStatus.OK)
        self.nn(sid)
        async with sess.post(url, json={'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                             headers={'Mcp-Session-Id': sid}) as resp:
            self.eq(resp.status, http.HTTPStatus.ACCEPTED)
        return sid, data['result']

    async def _rpc(self, sess, url, sid, method, params=None, _id=1, headers=None):
        body = {'jsonrpc': '2.0', 'id': _id, 'method': method}
        if params is not None:
            body['params'] = params
        hdrs = {}
        if sid is not None:
            hdrs['Mcp-Session-Id'] = sid
        if headers:
            hdrs.update(headers)
        async with sess.post(url, json=body, headers=hdrs) as resp:
            return resp.status, await resp.json()

    async def _tool(self, sess, url, sid, name, arguments=None, _id=1):
        params = {'name': name}
        if arguments is not None:
            params['arguments'] = arguments
        return await self._rpc(sess, url, sid, 'tools/call', params=params, _id=_id)

    async def _toolSse(self, sess, url, sid, name, arguments=None):
        params = {'name': name}
        if arguments is not None:
            params['arguments'] = arguments
        body = {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': params}
        hdrs = {'Mcp-Session-Id': sid, 'Accept': 'text/event-stream'}
        async with sess.post(url, json=body, headers=hdrs) as resp:
            self.eq(resp.status, http.HTTPStatus.OK)
            self.isin('text/event-stream', resp.headers.get('Content-Type'))
            text = await resp.text()
        return [s_json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: ')]

    async def test_mcp_lifecycle_and_sessions(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            # unauthenticated requests are rejected before any MCP handling
            async with self.getHttpSess() as anon:
                async with anon.post(url, json=self._initBody()) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                async with anon.delete(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                # initialize returns negotiated version + serverInfo, and a session id
                sid, result = await self._handshake(sess, url)
                self.eq(s_mcp.PROTOCOL_VERSION, result.get('protocolVersion'))
                self.isin('tools', result.get('capabilities'))
                self.true(result.get('serverInfo').get('name').startswith('synapse-'))

                # ping works (before-init guard does not block ping)
                status, data = await self._rpc(sess, url, sid, 'ping')
                self.eq(data.get('result'), {})

                # a notification (no id) to a normal method is accepted with no body
                async with sess.post(url, json={'jsonrpc': '2.0', 'method': 'ping'},
                                     headers={'Mcp-Session-Id': sid}) as resp:
                    self.eq(resp.status, http.HTTPStatus.ACCEPTED)

                # missing session header -> 400
                status, data = await self._rpc(sess, url, None, 'tools/list')
                self.eq(status, http.HTTPStatus.BAD_REQUEST)

                # unknown session id -> 404
                status, data = await self._rpc(sess, url, 'nosuchsession', 'tools/list')
                self.eq(status, http.HTTPStatus.NOT_FOUND)

                # unsupported protocol version header -> 400
                status, data = await self._rpc(sess, url, sid, 'ping',
                                               headers={'MCP-Protocol-Version': '1999-01-01'})
                self.eq(status, http.HTTPStatus.BAD_REQUEST)

                # supplying the negotiated version header is accepted
                status, data = await self._rpc(sess, url, sid, 'ping',
                                               headers={'MCP-Protocol-Version': s_mcp.PROTOCOL_VERSION})
                self.eq(data.get('result'), {})

                # batch (array) bodies are rejected
                async with sess.post(url, json=[self._initBody()]) as resp:
                    item = await resp.json()
                    self.eq(s_jsrpc.INVALID_REQUEST, item.get('error').get('code'))

                # parse error
                async with sess.post(url, data=b'{not json') as resp:
                    item = await resp.json()
                    self.eq(s_jsrpc.PARSE_ERROR, item.get('error').get('code'))

                # GET is not allowed (no server-initiated stream)
                async with sess.get(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.METHOD_NOT_ALLOWED)

                # idle expiry -> 404
                cell._mcp_sessions[sid]['touched'] = 0
                status, data = await self._rpc(sess, url, sid, 'tools/list')
                self.eq(status, http.HTTPStatus.NOT_FOUND)

                # initialize-first enforcement: a fresh (uninitialized) session rejects tools/list
                status, sid2, data = await self._initOnly(sess, url)
                status, data = await self._rpc(sess, url, sid2, 'tools/list')
                self.eq(s_jsrpc.INVALID_REQUEST, data.get('error').get('code'))

                # DELETE ends the session
                sid3, _ = await self._handshake(sess, url)
                async with sess.delete(url, headers={'Mcp-Session-Id': sid3}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                status, data = await self._rpc(sess, url, sid3, 'tools/list')
                self.eq(status, http.HTTPStatus.NOT_FOUND)

            # initialize as a notification (no id) -> 202, no session created
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                async with sess.post(url, json={'jsonrpc': '2.0', 'method': 'initialize',
                                                 'params': {'protocolVersion': s_mcp.PROTOCOL_VERSION}}) as resp:
                    self.eq(resp.status, http.HTTPStatus.ACCEPTED)
                    self.none(resp.headers.get('Mcp-Session-Id'))

                # initialize that errors (too many positional params) -> no session header
                async with sess.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                                                 'params': [1, 2, 3, 4]}) as resp:
                    self.none(resp.headers.get('Mcp-Session-Id'))
                    item = await resp.json()
                    self.eq(s_jsrpc.INVALID_PARAMS, item.get('error').get('code'))

    async def test_mcp_session_user_binding(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            user2 = await cell.auth.addUser('user2')
            await user2.setPasswd('secret2')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as s1:
                sid, _ = await self._handshake(s1, url)

            # a different user may not use root's session
            async with self.getHttpSess(auth=('user2', 'secret2'), port=port) as s2:
                status, data = await self._rpc(s2, url, sid, 'tools/list')
                self.eq(status, http.HTTPStatus.NOT_FOUND)

    async def test_mcp_bearer_auth(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            apikey, kdef = await cell.addUserApiKey(root.iden, 'mcp')

            # no cookie/basic auth - authenticate purely via Authorization: Bearer
            async with self.getHttpSess() as sess:
                status, sid, data = await self._initOnly(sess, url, headers={'Authorization': f'Bearer {apikey}'})
                self.eq(status, http.HTTPStatus.OK)
                self.nn(sid)

                # a bad bearer token is rejected
                async with sess.post(url, json=self._initBody(),
                                     headers={'Authorization': 'Bearer notavalidkey'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

    async def test_mcp_tools(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            lowuser = await cell.auth.addUser('lowuser')
            await lowuser.setPasswd('low')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # tools/list exposes the inherited getCellInfo tool with an inputSchema
                status, data = await self._rpc(sess, url, sid, 'tools/list')
                names = [t['name'] for t in data['result']['tools']]
                self.isin('getCellInfo', names)
                self.isin('addone', names)
                cellinfo = [t for t in data['result']['tools'] if t['name'] == 'getCellInfo'][0]
                self.nn(cellinfo.get('inputSchema'))

                # getCellInfo -> content + structuredContent (a dict)
                status, data = await self._tool(sess, url, sid, 'getCellInfo')
                result = data['result']
                self.false(result.get('isError'))
                self.isin('cell', result.get('structuredContent'))
                self.eq('text', result['content'][0]['type'])

                # non-dict return -> content text, no structuredContent
                status, data = await self._tool(sess, url, sid, 'addone', {'x': 41})
                result = data['result']
                self.eq('42', result['content'][0]['text'])
                self.notin('structuredContent', result)

                # unknown tool
                status, data = await self._tool(sess, url, sid, 'nope')
                self.eq(s_jsrpc.METHOD_NOT_FOUND, data.get('error').get('code'))

                # tools/call params not an object
                status, data = await self._rpc(sess, url, sid, 'tools/call', params=[1, 2])
                self.eq(s_jsrpc.INVALID_PARAMS, data.get('error').get('code'))

                # arguments not an object
                status, data = await self._rpc(sess, url, sid, 'tools/call',
                                               params={'name': 'addone', 'arguments': 5})
                self.eq(s_jsrpc.INVALID_PARAMS, data.get('error').get('code'))

                # bind failure (missing required positional)
                status, data = await self._tool(sess, url, sid, 'addone', {})
                self.eq(s_jsrpc.INVALID_PARAMS, data.get('error').get('code'))

                # schema violation (wrong type)
                status, data = await self._tool(sess, url, sid, 'addone', {'x': 'nope'})
                self.eq(s_jsrpc.INVALID_PARAMS, data.get('error').get('code'))

                # tool execution errors come back as isError results
                status, data = await self._tool(sess, url, sid, 'boom')
                self.true(data['result'].get('isError'))
                self.eq('kaboom', data['result']['content'][0]['text'])

                status, data = await self._tool(sess, url, sid, 'synboom')
                self.true(data['result'].get('isError'))
                self.eq('bad arg tool', data['result']['content'][0]['text'])

                # generator tool, no SSE -> collected into structuredContent items
                status, data = await self._tool(sess, url, sid, 'gen')
                self.eq([0, 1, 2], data['result']['structuredContent']['items'])
                self.false(data['result'].get('isError'))

                # generator tool that raises mid-collect -> isError
                status, data = await self._tool(sess, url, sid, 'genboom')
                self.true(data['result'].get('isError'))
                self.eq('streamfail', data['result']['content'][0]['text'])

                # generator tool with SSE -> notifications + terminal result
                mesgs = await self._toolSse(sess, url, sid, 'gen')
                self.eq([0, 1, 2], [m['params']['data'] for m in mesgs[:3]])
                self.eq('notifications/message', mesgs[0]['method'])
                self.eq([0, 1, 2], mesgs[-1]['result']['structuredContent']['items'])

                # generator tool that raises mid-stream -> terminal isError
                mesgs = await self._toolSse(sess, url, sid, 'genboom')
                self.eq(1, mesgs[0]['params']['data'])
                self.true(mesgs[-1]['result'].get('isError'))

            # permission gated tool is denied for a non-admin without the perm
            async with self.getHttpSess(auth=('lowuser', 'low'), port=port) as sess:
                sid, _ = await self._handshake(sess, url)
                status, data = await self._tool(sess, url, sid, 'needsperm')
                self.eq(s_jsrpc.ACCESS_DENIED, data.get('error').get('code'))
                self.eq(['mcp', 'secret'], data['error']['data']['perm'])

    async def test_mcp_cortex_tools(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            lowuser = await core.auth.addUser('lowuser')
            await lowuser.setPasswd('low')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                status, data = await self._rpc(sess, url, sid, 'tools/list')
                names = [t['name'] for t in data['result']['tools']]
                self.isin('storm', names)
                self.isin('callStorm', names)
                self.isin('getModel', names)

                # callStorm returns a value
                status, data = await self._tool(sess, url, sid, 'callStorm', {'query': 'return((1+2))'})
                self.eq('3', data['result']['content'][0]['text'])

                # getModel returns the model dict
                status, data = await self._tool(sess, url, sid, 'getModel')
                self.isin('types', data['result']['structuredContent'])

                # storm tool, no SSE -> collected messages include a node
                status, data = await self._tool(sess, url, sid, 'storm', {'query': '[ inet:ipv4=1.2.3.4 ]'})
                items = data['result']['structuredContent']['items']
                self.isin('node', [i['type'] for i in items])

                # storm tool with SSE -> streamed messages + terminal result
                mesgs = await self._toolSse(sess, url, sid, 'storm', {'query': '[ inet:ipv4=5.6.7.8 ]'})
                streamed = [m['params']['data']['type'] for m in mesgs if 'params' in m]
                self.isin('node', streamed)
                self.false(mesgs[-1]['result'].get('isError'))

            # a non-admin cannot impersonate another user via opts
            async with self.getHttpSess(auth=('lowuser', 'low'), port=port) as sess:
                sid, _ = await self._handshake(sess, url)
                status, data = await self._tool(sess, url, sid, 'callStorm',
                                                {'query': 'return((1))', 'opts': {'user': root.iden}})
                self.true(data['result'].get('isError'))
                self.isin('impersonate', data['result']['content'][0]['text'])
