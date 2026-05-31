import http
import base64

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
    _mcp_instructions = 'Test MCP instructions.'

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

    @s_mcp.tool(name='addone', schema={
        'type': 'object',
        'properties': {'x': {'type': 'integer'}},
        'required': ['x'],
        'additionalProperties': False,
    })
    async def addone(self, x):
        return x + 1

    @s_mcp.resource(uri='syn://text', name='text', desc='A text resource.', mimeType='text/plain')
    async def _resText(self):
        return 'hello text'

    @s_mcp.resource(uri='syn://bytes', name='bytes', mimeType='application/octet-stream')
    async def _resBytes(self):
        return b'\x00\x01\x02'

    @s_mcp.resource(uri='syn://thing/{tid}', name='thing', completers={'tid': 'things'})
    async def _resThing(self, tid):
        return {'tid': tid}

    @s_mcp.prompt(name='greet', desc='Greet someone.',
                  arguments=[{'name': 'who', 'description': 'who to greet', 'required': True, 'complete': 'names'}])
    async def _promptGreet(self, who):
        return f'Say hello to {who}'

    @s_mcp.prompt(name='convo', desc='A two message prompt.')
    async def _promptConvo(self):
        return [{'role': 'user', 'content': {'type': 'text', 'text': 'hi'}},
                {'role': 'assistant', 'content': {'type': 'text', 'text': 'hello'}}]

    @s_mcp.prompt(name='ghost', arguments=[{'name': 'g', 'complete': 'nosuchcompleter'}])
    async def _promptGhost(self, g=None):
        return 'boo'

    @s_mcp.completer(name='names')
    async def _completeNames(self, value, context):
        return [n for n in ('alice', 'bob', 'carol') if n.startswith(value)]

    @s_mcp.completer(name='things')
    async def _completeThings(self, value, context):
        return [f'thing{i}' for i in range(150) if f'thing{i}'.startswith(value)]

class TstMcpCell(s_cell.Cell):
    _mcp_ctor = TstMcp

class BareMcpCell(s_cell.Cell):
    # Mounts the base CellMcp (which has a tool + a resource, but no prompts/completers).
    _mcp_ctor = s_mcp.CellMcp

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
                self.eq('Test MCP instructions.', result.get('instructions'))

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

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # tools/list exposes the inherited get_service_info tool with an inputSchema
                status, data = await self._rpc(sess, url, sid, 'tools/list')
                names = [t['name'] for t in data['result']['tools']]
                self.isin('get_service_info', names)
                self.isin('addone', names)
                cellinfo = [t for t in data['result']['tools'] if t['name'] == 'get_service_info'][0]
                self.nn(cellinfo.get('inputSchema'))

                # get_service_info -> content + structuredContent (a dict)
                status, data = await self._tool(sess, url, sid, 'get_service_info')
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

    async def test_mcp_example_completer(self):

        # model:types is registered as an example completer (not yet wired to a ref)
        self.isin('model:types', s_mcp.CortexMcp.getMcpCompleters())

        async with self.getTestCore() as core:

            class _stub:
                cell = core

            vals = await s_mcp.CortexMcp._completeTypes(_stub(), 'inet:ipv', {})
            self.isin('inet:ipv4', vals)

    async def test_mcp_cortex_views(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            mainiden = core.view.iden
            forkview = await core.view.fork()
            forkiden = forkview.get('iden')

            lowuser = await core.auth.addUser('lowuser')
            await lowuser.setPasswd('low')
            # lowuser may read the main view but not the fork
            await lowuser.addRule((True, ('view', 'read')), gateiden=mainiden)

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # view_get is null before any view_set
                status, data = await self._tool(sess, url, sid, 'view_get')
                self.none(data['result']['structuredContent']['view'])

                # view_list (admin sees all views, including the fork)
                status, data = await self._tool(sess, url, sid, 'view_list')
                idens = [v['iden'] for v in data['result']['structuredContent']['views']]
                self.isin(mainiden, idens)
                self.isin(forkiden, idens)

                # view_set returns both content and structuredContent; view_get round-trips it
                status, data = await self._tool(sess, url, sid, 'view_set', {'view': forkiden})
                self.eq(forkiden, data['result']['structuredContent']['view'])
                self.nn(data['result']['content'][0]['text'])

                status, data = await self._tool(sess, url, sid, 'view_get')
                self.eq(forkiden, data['result']['structuredContent']['view'])

                # the session view flows into subsequent storm tool calls
                status, data = await self._tool(sess, url, sid, 'call_storm',
                                                {'query': 'return($lib.view.get().iden)'})
                self.eq(forkiden, s_json.loads(data['result']['content'][0]['text']))

                # an unknown view is an error
                status, data = await self._tool(sess, url, sid, 'view_set', {'view': 'nope'})
                self.true(data['result']['isError'])

            async with self.getHttpSess(auth=('lowuser', 'low'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # view_list filters out views the user cannot read
                status, data = await self._tool(sess, url, sid, 'view_list')
                idens = [v['iden'] for v in data['result']['structuredContent']['views']]
                self.isin(mainiden, idens)
                self.notin(forkiden, idens)

                # view_set on an unreadable view is denied (returned as an error result)
                status, data = await self._tool(sess, url, sid, 'view_set', {'view': forkiden})
                self.true(data['result']['isError'])

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
                self.isin('call_storm', names)
                self.isin('get_model', names)
                self.isin('storm_validate', names)

                # call_storm returns a value
                status, data = await self._tool(sess, url, sid, 'call_storm', {'query': 'return((1+2))'})
                self.eq('3', data['result']['content'][0]['text'])

                # storm_validate parses without executing
                status, data = await self._tool(sess, url, sid, 'storm_validate', {'query': 'inet:ipv4=1.2.3.4'})
                self.true(data['result']['structuredContent']['valid'])

                status, data = await self._tool(sess, url, sid, 'storm_validate', {'query': '[ inet:ipv4=1.2.3.4'})
                self.false(data['result']['structuredContent']['valid'])
                self.nn(data['result']['structuredContent'].get('mesg'))

                # get_model returns the model dict
                status, data = await self._tool(sess, url, sid, 'get_model')
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

                # Cortex resources
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://model'})
                self.isin('types', s_json.loads(data['result']['contents'][0]['text']))

                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://stormdocs'})
                self.isin('libraries', s_json.loads(data['result']['contents'][0]['text']))

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'syn://model/form/inet:ipv4'})
                self.eq('inet:ipv4', s_json.loads(data['result']['contents'][0]['text'])['name'])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'syn://model/form/nosuchform'})
                self.eq(s_mcp.RESOURCE_NOT_FOUND, data['error']['code'])

                # the storm-syntax skill is served from disk as a markdown resource
                status, data = await self._rpc(sess, url, sid, 'resources/list')
                self.isin('skill://storm-syntax/SKILL.md', [r['uri'] for r in data['result']['resources']])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'skill://storm-syntax/SKILL.md'})
                content = data['result']['contents'][0]
                self.eq('text/markdown', content['mimeType'])
                self.isin('# Storm Syntax', content['text'])

                # Cortex completer (model:forms via the form resource template)
                status, data = await self._rpc(sess, url, sid, 'completion/complete',
                                               params={'ref': {'type': 'ref/resource', 'uri': 'syn://model/form/{name}'},
                                                       'argument': {'name': 'name', 'value': 'inet:ipv'}})
                self.isin('inet:ipv4', data['result']['completion']['values'])

            # a non-admin cannot impersonate another user via opts
            async with self.getHttpSess(auth=('lowuser', 'low'), port=port) as sess:
                sid, _ = await self._handshake(sess, url)
                status, data = await self._tool(sess, url, sid, 'call_storm',
                                                {'query': 'return((1))', 'opts': {'user': root.iden}})
                self.true(data['result'].get('isError'))
                self.isin('impersonate', data['result']['content'][0]['text'])

    async def test_mcp_async_required(self):

        with self.raises(s_exc.BadArg):
            @s_mcp.tool(name='x')
            def synctool(self):
                return 1

        with self.raises(s_exc.BadArg):
            @s_mcp.resource(uri='syn://x')
            def syncres(self):
                return 1

        with self.raises(s_exc.BadArg):
            @s_mcp.prompt(name='x')
            def syncprompt(self):
                return 'x'

        with self.raises(s_exc.BadArg):
            @s_mcp.completer(name='x')
            def synccompleter(self, value, context):
                return []

    async def test_mcp_name_validation(self):
        # tool and prompt names must match the strict, broadly-compatible pattern
        for badname in ('bad-name', 'bad.name', 'tools/call', '1leading', 'has space'):

            with self.raises(s_exc.BadArg):
                @s_mcp.tool(name=badname)
                async def badtool(self):
                    return None

            with self.raises(s_exc.BadArg):
                @s_mcp.prompt(name=badname)
                async def badprompt(self):
                    return 'x'

        # a valid snake_case name is accepted
        @s_mcp.tool(name='ok_name')
        async def oktool(self):
            return None

        self.eq('ok_name', oktool._mcp_tool['name'])

    async def test_mcp_registry_caching(self):
        # the get*Info registries are built once and cached on the class
        self.true(TstMcp.getMcpTools() is TstMcp.getMcpTools())
        self.true(TstMcp.getMcpResources() is TstMcp.getMcpResources())
        self.true(TstMcp.getMcpPrompts() is TstMcp.getMcpPrompts())
        self.true(TstMcp.getMcpCompleters() is TstMcp.getMcpCompleters())

    async def test_mcp_list_caching(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # each list result is built once and cached on the class
                for method, cacheattr in (('tools/list', '_mcp_tools_list'),
                                          ('resources/list', '_mcp_resources_list'),
                                          ('resources/templates/list', '_mcp_resource_templates_list'),
                                          ('prompts/list', '_mcp_prompts_list')):
                    _, first = await self._rpc(sess, url, sid, method)
                    self.nn(s_mcp.CortexMcp.__dict__.get(cacheattr))
                    _, second = await self._rpc(sess, url, sid, method)
                    self.eq(first['result'], second['result'])

    async def test_mcp_capabilities(self):

        # Cortex advertises tools/logging/resources/completions (no prompts)
        async with self.getTestCore() as core:
            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'
            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                _, result = await self._handshake(sess, url)
                caps = result['capabilities']
                for name in ('tools', 'logging', 'resources', 'completions'):
                    self.isin(name, caps)
                # CortexMcp exposes no prompts
                self.notin('prompts', caps)
                self.isin('Storm', result.get('instructions'))

        # A bare CellMcp has a tool + a resource, but no prompts/completers
        async with self.getTestCell(BareMcpCell) as cell:
            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'
            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                _, result = await self._handshake(sess, url)
                caps = result['capabilities']
                self.isin('resources', caps)
                self.isin('logging', caps)
                self.notin('prompts', caps)
                self.notin('completions', caps)
                # no instructions are declared on the base CellMcp
                self.notin('instructions', result)

    async def test_mcp_resources(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # resources/list contains static resources but not templates
                status, data = await self._rpc(sess, url, sid, 'resources/list')
                uris = [r['uri'] for r in data['result']['resources']]
                self.isin('syn://cellinfo', uris)
                self.isin('syn://text', uris)
                self.isin('syn://bytes', uris)
                self.notin('syn://thing/{tid}', uris)

                # resources/templates/list contains only templates
                status, data = await self._rpc(sess, url, sid, 'resources/templates/list')
                self.eq(['syn://thing/{tid}'], [r['uriTemplate'] for r in data['result']['resourceTemplates']])

                # text content
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://text'})
                content = data['result']['contents'][0]
                self.eq('hello text', content['text'])
                self.eq('text/plain', content['mimeType'])

                # bytes content -> base64 blob
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://bytes'})
                self.eq(base64.b64encode(b'\x00\x01\x02').decode(), data['result']['contents'][0]['blob'])

                # dict content -> json text
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://cellinfo'})
                self.isin('cell', s_json.loads(data['result']['contents'][0]['text']))

                # template content read
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://thing/abc'})
                content = data['result']['contents'][0]
                self.eq('syn://thing/abc', content['uri'])
                self.eq('abc', s_json.loads(content['text'])['tid'])

                # unknown resource -> -32002
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://nope'})
                self.eq(s_mcp.RESOURCE_NOT_FOUND, data['error']['code'])

                # a uri that is the right shape but does not match the template literal -> -32002
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://other/x'})
                self.eq(s_mcp.RESOURCE_NOT_FOUND, data['error']['code'])

                # missing uri -> -32002
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={})
                self.eq(s_mcp.RESOURCE_NOT_FOUND, data['error']['code'])

    async def test_mcp_prompts(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                status, data = await self._rpc(sess, url, sid, 'prompts/list')
                prompts = {p['name']: p for p in data['result']['prompts']}
                self.isin('greet', prompts)
                self.isin('convo', prompts)
                self.eq('who', prompts['greet']['arguments'][0]['name'])
                self.true(prompts['greet']['arguments'][0]['required'])

                # str return -> a single user message
                status, data = await self._rpc(sess, url, sid, 'prompts/get',
                                               params={'name': 'greet', 'arguments': {'who': 'sam'}})
                msgs = data['result']['messages']
                self.len(1, msgs)
                self.isin('sam', msgs[0]['content']['text'])

                # list return -> messages used directly
                status, data = await self._rpc(sess, url, sid, 'prompts/get', params={'name': 'convo'})
                self.len(2, data['result']['messages'])

                # missing required argument
                status, data = await self._rpc(sess, url, sid, 'prompts/get',
                                               params={'name': 'greet', 'arguments': {}})
                self.eq(s_jsrpc.INVALID_PARAMS, data['error']['code'])

                # unknown prompt
                status, data = await self._rpc(sess, url, sid, 'prompts/get', params={'name': 'nope'})
                self.eq(s_jsrpc.INVALID_PARAMS, data['error']['code'])

                # unexpected argument -> bind error
                status, data = await self._rpc(sess, url, sid, 'prompts/get',
                                               params={'name': 'greet', 'arguments': {'who': 'x', 'extra': 1}})
                self.eq(s_jsrpc.INVALID_PARAMS, data['error']['code'])

    async def test_mcp_completions(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                async def complete(ref, argument, context=None):
                    params = {'ref': ref, 'argument': argument}
                    if context is not None:
                        params['context'] = context
                    _, data = await self._rpc(sess, url, sid, 'completion/complete', params=params)
                    return data['result']['completion']

                # prompt argument completion
                comp = await complete({'type': 'ref/prompt', 'name': 'greet'}, {'name': 'who', 'value': 'a'})
                self.eq(['alice'], comp['values'])

                # resource template variable completion, with context, capped at 100
                comp = await complete({'type': 'ref/resource', 'uri': 'syn://thing/{tid}'},
                                      {'name': 'tid', 'value': 'thing'}, context={'arguments': {}})
                self.len(100, comp['values'])
                self.eq(150, comp['total'])
                self.true(comp['hasMore'])

                # lenient empties: unknown prompt, unknown resource, unknown arg, unknown ref type,
                # malformed ref, and a referenced-but-unregistered completer
                self.eq([], (await complete({'type': 'ref/prompt', 'name': 'nope'}, {'name': 'who', 'value': 'a'}))['values'])
                self.eq([], (await complete({'type': 'ref/resource', 'uri': 'syn://nope'}, {'name': 'x', 'value': ''}))['values'])
                self.eq([], (await complete({'type': 'ref/prompt', 'name': 'greet'}, {'name': 'nope', 'value': ''}))['values'])
                self.eq([], (await complete({'type': 'ref/bogus'}, {'name': 'x', 'value': ''}))['values'])
                self.eq([], (await complete('notadict', {'name': 'x', 'value': ''}))['values'])
                self.eq([], (await complete({'type': 'ref/prompt', 'name': 'ghost'}, {'name': 'g', 'value': ''}))['values'])

    async def test_mcp_logging(self):

        # unit coverage of the storm message -> log level mapping
        self.eq('warning', s_mcp.CortexMcp._streamItemLevel(None, {'type': 'warn'}))
        self.eq('error', s_mcp.CortexMcp._streamItemLevel(None, {'type': 'err'}))
        self.eq('info', s_mcp.CortexMcp._streamItemLevel(None, {'type': 'node'}))
        self.eq('info', s_mcp.CortexMcp._streamItemLevel(None, 'notadict'))
        self.eq('info', s_mcp.CellMcp._streamItemLevel(None, {'type': 'warn'}))

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # invalid level
                status, data = await self._rpc(sess, url, sid, 'logging/setLevel', params={'level': 'bogus'})
                self.eq(s_jsrpc.INVALID_PARAMS, data['error']['code'])

                # raise the minimum level to warning
                status, data = await self._rpc(sess, url, sid, 'logging/setLevel', params={'level': 'warning'})
                self.eq({}, data['result'])

                # streamed info-level messages are suppressed, warn is delivered
                mesgs = await self._toolSse(sess, url, sid, 'storm',
                                            {'query': '$lib.warn("omg") [ inet:ipv4=1.2.3.4 ]'})
                notifs = [m for m in mesgs if m.get('method') == 'notifications/message']
                levels = {m['params']['level'] for m in notifs}
                self.notin('info', levels)
                self.isin('warning', levels)
                self.true(any(m['params']['data'].get('type') == 'warn' for m in notifs))
                self.false(mesgs[-1]['result'].get('isError'))
