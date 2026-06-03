import http
import base64
import asyncio
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.lib.base as s_base
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

                # unknown session id -> 404, and the error echoes the request id
                status, data = await self._rpc(sess, url, 'nosuchsession', 'tools/list', _id=42)
                self.eq(status, http.HTTPStatus.NOT_FOUND)
                self.eq(42, data['id'])
                self.eq(s_jsrpc.INVALID_REQUEST, data['error']['code'])

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

                # ...nor may they DELETE (terminate) root's session
                async with s2.delete(url, headers={'Mcp-Session-Id': sid}) as resp:
                    self.eq(resp.status, http.HTTPStatus.NOT_FOUND)

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as s1:

                # root's session survived the foreign DELETE attempt
                status, data = await self._rpc(s1, url, sid, 'tools/list')
                self.eq(status, http.HTTPStatus.OK)

                # the owner may DELETE their own session
                async with s1.delete(url, headers={'Mcp-Session-Id': sid}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)

                status, data = await self._rpc(s1, url, sid, 'tools/list')
                self.eq(status, http.HTTPStatus.NOT_FOUND)

    async def test_mcp_apikey_auth(self):

        async with self.getTestCell(TstMcpCell) as cell:

            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await cell.auth.getUserByName('root')
            apikey, kdef = await cell.addUserApiKey(root.iden, 'mcp')

            # no cookie/basic auth - authenticate purely via the X-API-KEY header
            async with self.getHttpSess() as sess:
                status, sid, data = await self._initOnly(sess, url, headers={'X-API-KEY': apikey})
                self.eq(status, http.HTTPStatus.OK)
                self.nn(sid)

                # a bad api key is rejected
                async with sess.post(url, json=self._initBody(),
                                     headers={'X-API-KEY': 'notavalidkey'}) as resp:
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

                # view_get returns the user's default view
                status, data = await self._tool(sess, url, sid, 'view_get')
                self.eq(mainiden, data['result']['structuredContent']['view'])

                # view_get honors the user's cortex:view profile default when set
                await root.setProfileValu('cortex:view', forkiden)
                status, data = await self._tool(sess, url, sid, 'view_get')
                self.eq(forkiden, data['result']['structuredContent']['view'])
                await root.popProfileValu('cortex:view')

                # view_list (admin sees all views, including the fork)
                status, data = await self._tool(sess, url, sid, 'view_list')
                idens = [v['iden'] for v in data['result']['structuredContent']['views']]
                self.isin(mainiden, idens)
                self.isin(forkiden, idens)

                # view_fork with no view defaults to the user's default view
                status, data = await self._tool(sess, url, sid, 'view_fork')
                defres = data['result']['structuredContent']
                self.eq(mainiden, defres['parent'])
                self.notin('session_view', defres)
                await self._tool(sess, url, sid, 'view_del', {'view': defres['view']})

                # storm runs in the view named by opts; without it, the user's default view
                status, data = await self._tool(sess, url, sid, 'call_storm',
                                                {'query': 'return($lib.view.get().iden)', 'opts': {'view': forkiden}})
                self.eq(forkiden, s_json.loads(data['result']['content'][0]['text']))

                # view_fork with no view forks the user's default view; result has no session_view
                status, data = await self._tool(sess, url, sid, 'view_fork', {'view': forkiden, 'name': 'ingest test'})
                forkres = data['result']['structuredContent']
                ingestiden = forkres['view']
                self.eq(forkiden, forkres['parent'])
                self.notin('session_view', forkres)

                # ingest edits made in the fork (via the view opt) stay isolated from the parent
                await self._tool(sess, url, sid, 'call_storm',
                                 {'query': '[ inet:fqdn=ingest.test ]', 'opts': {'view': ingestiden}})
                cq = 'inet:fqdn=ingest.test return($node.repr())'
                status, data = await self._tool(sess, url, sid, 'call_storm', {'query': cq, 'opts': {'view': forkiden}})
                self.none(s_json.loads(data['result']['content'][0]['text']))

                # view_del removes the fork (and its isolated edits)
                status, data = await self._tool(sess, url, sid, 'view_del', {'view': ingestiden})
                delres = data['result']['structuredContent']
                self.eq(ingestiden, delres['deleted'])
                self.eq(forkiden, delres['parent'])
                self.none(core.getView(ingestiden))

                # view_merge applies a fork's edits to its parent
                status, data = await self._tool(sess, url, sid, 'view_fork', {'view': forkiden})
                mergeiden = data['result']['structuredContent']['view']
                await self._tool(sess, url, sid, 'call_storm',
                                 {'query': '[ inet:fqdn=merge.test ]', 'opts': {'view': mergeiden}})

                status, data = await self._tool(sess, url, sid, 'view_merge', {'view': mergeiden})
                mres = data['result']['structuredContent']
                self.eq(mergeiden, mres['merged'])
                self.eq(forkiden, mres['parent'])

                # the merged node is now present in the parent view
                cq = 'inet:fqdn=merge.test return($node.repr())'
                status, data = await self._tool(sess, url, sid, 'call_storm', {'query': cq, 'opts': {'view': forkiden}})
                self.eq('merge.test', s_json.loads(data['result']['content'][0]['text']))

                # view_merge does not delete the fork; remove it explicitly
                status, data = await self._tool(sess, url, sid, 'view_del', {'view': mergeiden})
                self.eq(mergeiden, data['result']['structuredContent']['deleted'])
                self.none(core.getView(mergeiden))

                # a non-fork view cannot be merged
                status, data = await self._tool(sess, url, sid, 'view_merge', {'view': mainiden})
                self.true(data['result']['isError'])

            async with self.getHttpSess(auth=('lowuser', 'low'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                # view_list filters out views the user cannot read
                status, data = await self._tool(sess, url, sid, 'view_list')
                idens = [v['iden'] for v in data['result']['structuredContent']['views']]
                self.isin(mainiden, idens)
                self.notin(forkiden, idens)

                # forking requires the view.add permission
                status, data = await self._tool(sess, url, sid, 'view_fork', {'view': mainiden})
                self.true(data['result']['isError'])

                await lowuser.addRule((True, ('view', 'add')))

                # lowuser cannot read the fork in order to fork it
                status, data = await self._tool(sess, url, sid, 'view_fork', {'view': forkiden})
                self.true(data['result']['isError'])

                # deleting requires the view.del permission
                status, data = await self._tool(sess, url, sid, 'view_del', {'view': mainiden})
                self.true(data['result']['isError'])

    async def test_mcp_cortex_remote(self):
        # Exercise the getCore() seam against the cortex over a telepath proxy -- the path
        # Optic uses. getCore()/getAuthCell() return a proxy, so every cortex operation the
        # handler performs must be telepath-safe.
        async with self.getTestCore() as core:

            async with core.getLocalProxy() as prox:

                class RemoteCortexMcp(s_mcp.CortexMcp):
                    def getCore(self):
                        return prox

                    def getAuthCell(self):
                        return prox

                core.addHttpApi('/api/v1/mcpremote', RemoteCortexMcp, {'cell': core})

                host, port = await core.addHttpsPort(0, host='127.0.0.1')
                url = f'https://localhost:{port}/api/v1/mcpremote'

                root = await core.auth.getUserByName('root')
                await root.setPasswd('secret')

                async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                    sid, _ = await self._handshake(sess, url)

                    # model_find proxies via getCore().getModelDict()
                    status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': 'inet:ipv4'})
                    self.isin('inet:ipv4', data['result']['structuredContent']['forms'])

                    # the stormdocs resource proxies via getCore().getCoreInfoV2()
                    status, data = await self._rpc(sess, url, sid, 'resources/read',
                                                   params={'uri': 'syn://stormdocs'})
                    self.isin('libraries', s_json.loads(data['result']['contents'][0]['text']))

                    # the storm tool creates a node on the backend cortex (as the auth'd user)
                    await self._tool(sess, url, sid, 'storm', {'query': '[ inet:ipv4=1.2.3.4 ]'})
                    self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

                    # completion -> model:forms completer -> CoreApi.getFormsByPrefix over telepath
                    status, data = await self._rpc(sess, url, sid, 'completion/complete',
                                                   params={'ref': {'type': 'ref/resource',
                                                                   'uri': 'syn://model/form/{name}'},
                                                           'argument': {'name': 'name', 'value': 'inet:ip'}})
                    self.isin('inet:ipv4', data['result']['completion']['values'])

                    # view fork/del round-trips through $lib.view via the proxy
                    status, data = await self._tool(sess, url, sid, 'view_fork')
                    forkiden = data['result']['structuredContent']['view']
                    self.nn(core.getView(forkiden))

                    status, data = await self._tool(sess, url, sid, 'view_del', {'view': forkiden})
                    self.eq(forkiden, data['result']['structuredContent']['deleted'])
                    self.none(core.getView(forkiden))

                    # get_service_info proxies via getCore().getCellInfo()
                    status, data = await self._tool(sess, url, sid, 'get_service_info')
                    self.isin('cell', data['result']['structuredContent'])

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
                self.isin('model_find', names)
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

                # model_find returns the matching subset of the model (types/forms/interfaces)
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': 'inet:ipv4'})
                res = data['result']['structuredContent']
                self.isin('inet:ipv4', res['types'])
                self.isin('inet:ipv4', res['forms'])

                # a doc-only match (no name contains "address") still finds inet:ipv4 by its doc
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': '(?i)IPv4 address'})
                self.isin('inet:ipv4', data['result']['structuredContent']['types'])

                # a property-only match returns the entire form definition
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': 'dns:a:fqdn'})
                res = data['result']['structuredContent']
                self.isin('inet:dns:a', res['forms'])
                self.isin('fqdn', res['forms']['inet:dns:a']['props'])
                self.isin('ipv4', res['forms']['inet:dns:a']['props'])

                # an interface match
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': 'doc:document'})
                self.isin('doc:document', data['result']['structuredContent']['interfaces'])

                # no matches -> empty subsets
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': 'zzznosuchthingzzz'})
                res = data['result']['structuredContent']
                self.eq({}, res['types'])
                self.eq({}, res['forms'])

                # an invalid regex is a tool error
                status, data = await self._tool(sess, url, sid, 'model_find', {'pattern': '('})
                self.true(data['result']['isError'])

                # storm tool returns a page of (type, info) messages; small query is fully
                # drained in one page (cursor is null)
                status, data = await self._tool(sess, url, sid, 'storm', {'query': '[ inet:ipv4=1.2.3.4 ]'})
                res = data['result']['structuredContent']
                self.none(res['cursor'])
                self.isin('node', [m[0] for m in res['messages']])

                # Cortex resources
                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://model'})
                self.isin('types', s_json.loads(data['result']['contents'][0]['text']))

                status, data = await self._rpc(sess, url, sid, 'resources/read', params={'uri': 'syn://stormdocs'})
                self.isin('libraries', s_json.loads(data['result']['contents'][0]['text']))

                # the raw Storm Lark grammar is served as a text resource
                status, data = await self._rpc(sess, url, sid, 'resources/list')
                self.isin('syn://storm/grammar', [r['uri'] for r in data['result']['resources']])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'syn://storm/grammar'})
                content = data['result']['contents'][0]
                self.eq('text/x-lark', content['mimeType'])
                self.isin('Grammar for the Storm Query Language', content['text'])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'syn://model/form/inet:ipv4'})
                self.eq('inet:ipv4', s_json.loads(data['result']['contents'][0]['text'])['name'])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'syn://model/form/nosuchform'})
                self.eq(s_mcp.RESOURCE_NOT_FOUND, data['error']['code'])

                # the storm skill is served from disk as a markdown resource
                status, data = await self._rpc(sess, url, sid, 'resources/list')
                self.isin('skill://storm/SKILL.md', [r['uri'] for r in data['result']['resources']])

                status, data = await self._rpc(sess, url, sid, 'resources/read',
                                               params={'uri': 'skill://storm/SKILL.md'})
                content = data['result']['contents'][0]
                self.eq('text/markdown', content['mimeType'])
                self.isin('# Storm Query Language Skill', content['text'])

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

    async def test_mcp_storm_pagination(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            # a query producing 14 messages (init + 12 print + fini)
            query = 'for $i in $lib.range(12) { $lib.print(`m{$i}`) }'

            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                sid, _ = await self._handshake(sess, url)

                with mock.patch.object(s_mcp, 'STORM_PAGE_SIZE', 5):

                    # the first page returns STORM_PAGE_SIZE messages and a cursor
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    res = data['result']['structuredContent']
                    self.len(5, res['messages'])
                    self.nn(res['cursor'])

                    # drain the rest via storm_continue until the cursor is null
                    cursor = res['cursor']
                    msgs = list(res['messages'])
                    while cursor is not None:
                        _, data = await self._tool(sess, url, sid, 'storm_continue', {'cursor': cursor})
                        res = data['result']['structuredContent']
                        msgs.extend(res['messages'])
                        cursor = res['cursor']

                    self.len(12, [m for m in msgs if m[0] == 'print'])

                    # an unknown/drained cursor is a tool error
                    _, data = await self._tool(sess, url, sid, 'storm_continue', {'cursor': 'nope'})
                    self.true(data['result']['isError'])

                    # storm_cancel releases a running query
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    cursor = data['result']['structuredContent']['cursor']
                    self.nn(cursor)
                    _, data = await self._tool(sess, url, sid, 'storm_cancel', {'cursor': cursor})
                    self.eq(cursor, data['result']['structuredContent']['cancelled'])

                    # cancelling it again is an error
                    _, data = await self._tool(sess, url, sid, 'storm_cancel', {'cursor': cursor})
                    self.true(data['result']['isError'])

                    # an idle cursor expires and is reported as such
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    cursor = data['result']['structuredContent']['cursor']
                    core._mcp_sessions[sid]['cursors'][cursor]['touched'] = 0
                    _, data = await self._tool(sess, url, sid, 'storm_continue', {'cursor': cursor})
                    self.true(data['result']['isError'])

                    # an idle cursor is also swept when a new query starts
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    stale = data['result']['structuredContent']['cursor']
                    core._mcp_sessions[sid]['cursors'][stale]['touched'] = 0
                    await self._tool(sess, url, sid, 'storm', {'query': query})
                    self.notin(stale, core._mcp_sessions[sid]['cursors'])

                    # opening more than STORM_MAX_CURSORS evicts the oldest
                    with mock.patch.object(s_mcp, 'STORM_MAX_CURSORS', 2):
                        _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                        c1 = data['result']['structuredContent']['cursor']
                        await self._tool(sess, url, sid, 'storm', {'query': query})
                        await self._tool(sess, url, sid, 'storm', {'query': query})
                        cursors = core._mcp_sessions[sid]['cursors']
                        self.len(2, cursors)
                        self.notin(c1, cursors)

                    # a failure in the storm producer surfaces as a tool error and releases
                    # the cursor
                    async def boomstorm(query, opts=None):
                        yield ('init', {})
                        raise s_exc.BadArg(mesg='boomstorm')

                    with mock.patch.object(core, 'storm', boomstorm):
                        _, data = await self._tool(sess, url, sid, 'storm', {'query': 'x'})
                        self.true(data['result']['isError'])
                        self.isin('boomstorm', data['result']['content'][0]['text'])

                    # ending the session releases any still-open cursors
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    self.nn(data['result']['structuredContent']['cursor'])
                    async with sess.delete(url, headers={'Mcp-Session-Id': sid}) as resp:
                        self.eq(resp.status, http.HTTPStatus.OK)

    async def test_mcp_storm_reaper(self):

        async with self.getTestCore() as core:

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            query = 'for $i in $lib.range(12) { $lib.print(`m{$i}`) }'

            # the reaper task is started lazily on the first MCP session
            self.none(core._mcp_sess_reaper)

            with mock.patch.object(s_mcp, 'STORM_PAGE_SIZE', 5):

                async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:

                    sid, _ = await self._handshake(sess, url)
                    reaper = core._mcp_sess_reaper
                    self.nn(reaper)

                    # a second session does not start a second reaper
                    sid2, _ = await self._handshake(sess, url)
                    self.eq(reaper, core._mcp_sess_reaper)

                    # a single reaper pass evicts an idle cursor and shuts down its producer
                    # task (and therefore its storm generator)
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    cursor = data['result']['structuredContent']['cursor']
                    task = core._mcp_sessions[sid]['cursors'][cursor]['task']
                    core._mcp_sessions[sid]['cursors'][cursor]['touched'] = 0
                    await s_mcp._reapMcpSessionsOnce(core)
                    self.notin(cursor, core._mcp_sessions[sid]['cursors'])
                    self.true(task.done())

                    # an idle session is dropped along with all of its cursors
                    _, data = await self._tool(sess, url, sid, 'storm', {'query': query})
                    ctask = core._mcp_sessions[sid]['cursors'][data['result']['structuredContent']['cursor']]['task']
                    core._mcp_sessions[sid]['touched'] = 0
                    await s_mcp._reapMcpSessionsOnce(core)
                    self.notin(sid, core._mcp_sessions)
                    self.true(ctask.done())

                    # _getSession drops an idle session on access and cleans up its cursors
                    _, data = await self._tool(sess, url, sid2, 'storm', {'query': query})
                    gtask = core._mcp_sessions[sid2]['cursors'][data['result']['structuredContent']['cursor']]['task']
                    core._mcp_sessions[sid2]['touched'] = 0
                    status, _ = await self._rpc(sess, url, sid2, 'tools/list')
                    self.eq(status, http.HTTPStatus.NOT_FOUND)
                    self.notin(sid2, core._mcp_sessions)
                    for _ in range(100):
                        if gtask.done():
                            break
                        await asyncio.sleep(0.01)
                    self.true(gtask.done())

                    # the running reaper loop evicts an idle cursor on its own schedule
                    sid3, _ = await self._handshake(sess, url)
                    _, data = await self._tool(sess, url, sid3, 'storm', {'query': query})
                    rcursor = data['result']['structuredContent']['cursor']
                    core._mcp_sessions[sid3]['cursors'][rcursor]['touched'] = 0

                    with mock.patch.object(s_mcp, 'STORM_CURSOR_TIMEOUT', 0.1):
                        loop_task = asyncio.get_running_loop().create_task(s_mcp._reapMcpSessions(core))
                        try:
                            for _ in range(200):
                                if rcursor not in core._mcp_sessions[sid3]['cursors']:
                                    break
                                await asyncio.sleep(0.02)
                            self.notin(rcursor, core._mcp_sessions[sid3]['cursors'])
                        finally:
                            loop_task.cancel()
                            await asyncio.gather(loop_task, return_exceptions=True)

        # the reaper loop exits cleanly when its cell finis (in addition to the automatic
        # cancel+await that cell.schedCoro() provides for the live reaper)
        base = await s_base.Base.anit()
        base._mcp_sessions = {}
        loop_task = asyncio.get_running_loop().create_task(s_mcp._reapMcpSessions(base))
        await asyncio.sleep(0)
        await base.fini()
        await asyncio.wait_for(loop_task, timeout=5)
        self.true(loop_task.done())

    async def test_mcp_async_required(self):

        with self.raises(s_exc.BadArg):
            @s_mcp.tool(name='x')
            def synctool(self):
                return 1

        # tools must be coroutine functions, not async generators
        with self.raises(s_exc.BadArg):
            @s_mcp.tool(name='genr')
            async def genrtool(self):
                yield 1

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

        # Cortex advertises tools/resources/completions (no prompts)
        async with self.getTestCore() as core:
            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            url = f'https://localhost:{port}/api/v1/mcp'
            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                _, result = await self._handshake(sess, url)
                caps = result['capabilities']
                for name in ('tools', 'resources', 'completions'):
                    self.isin(name, caps)
                # CortexMcp exposes no prompts (and no logging capability)
                self.notin('prompts', caps)
                self.notin('logging', caps)
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
