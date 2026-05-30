'''
MCP (Model Context Protocol) server handlers for Synapse cells.

MCP is JSON-RPC 2.0 over a Streamable HTTP transport with a fixed method vocabulary
(``initialize``, ``notifications/initialized``, ``tools/list``, ``tools/call``) where the
actual tools are nested under ``tools/call``. This module builds on the generic
``synapse.lib.jsrpc.JsonRpcHandler``.

``CellMcp`` provides the MCP transport, session lifecycle, and tool dispatch and may be
mounted on any cell. ``CortexMcp`` extends it to plumb Cortex specific tools. A cell opts
in to MCP by setting the ``_mcp_ctor`` class attribute, which the base Cell mounts at
``/api/v1/mcp`` during HTTP API initialization.

Tools are declared with the ``@s_mcp.tool`` decorator and dispatched only via
``tools/call``. Async generator tools stream their results to the caller as Server-Sent
Events when the request carries an ``Accept: text/event-stream`` header.
'''
import asyncio
import inspect
import logging
from http import HTTPStatus

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.jsrpc as s_jsrpc

logger = logging.getLogger(__name__)

# The MCP protocol version this server implements (and the versions it will accept).
PROTOCOL_VERSION = '2025-06-18'
SUPPORTED_VERSIONS = ('2025-06-18', '2025-03-26')

# Idle timeout (in seconds) before an MCP session is considered expired.
SESSION_TIMEOUT = 3600

def tool(name=None, desc=None, schema=None, perm=None):
    '''
    Decorate a method to expose it as an MCP tool (invoked via ``tools/call``).

    Args:
        name (str): An optional tool name override. Defaults to the function name.
        desc (str): A human readable description of the tool.
        schema (dict): An optional JSON Schema for the tool arguments (the MCP inputSchema).
        perm (tuple): An optional Synapse permission tuple the calling user must be allowed.

    Notes:
        Only methods decorated with this decorator are exposed as tools.
    '''
    if schema is None:
        schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}

    def wrap(func):
        func._mcp_tool = {
            'name': name if name is not None else func.__name__,
            'desc': desc,
            'schema': schema,
            'perm': perm,
            'genr': inspect.isasyncgenfunction(func),
        }
        return func

    return wrap

class CellMcp(s_jsrpc.JsonRpcHandler):
    '''
    An MCP server handler which exposes a cell's ``@s_mcp.tool`` methods over MCP.
    '''
    PROTOCOL_VERSION = PROTOCOL_VERSION
    SUPPORTED_VERSIONS = SUPPORTED_VERSIONS
    SESSION_TIMEOUT = SESSION_TIMEOUT

    @classmethod
    def getToolInfo(cls):
        '''
        Introspect the handler class and return its MCP tool registry.

        Returns:
            dict: A mapping of tool name to ``{'attr': attrname, 'info': info,
            'validator': validator}`` where validator is a compiled args validator or None.
        '''
        tools = cls.__dict__.get('_mcp_tools')
        if tools is not None:
            return tools

        tools = {}
        for attrname in dir(cls):

            attr = getattr(cls, attrname, None)
            if not callable(attr):
                continue

            info = getattr(attr, '_mcp_tool', None)
            if info is None:
                continue

            validator = None
            if info.get('schema') is not None:
                validator = s_config.getJsValidator(info.get('schema'))

            tools[info.get('name')] = {'attr': attrname, 'info': info, 'validator': validator}

        cls._mcp_tools = tools
        return tools

    async def handleBasicAuth(self):
        # In addition to the inherited Basic auth, accept an Authorization: Bearer <token>
        # header by treating the token as a Synapse user API key (MCP client convention).
        auth = self.request.headers.get('Authorization')
        if auth is not None and auth.startswith('Bearer '):

            _, key = auth.split(None, 1)

            authcell = self.getAuthCell()
            isok, info = await authcell.checkUserApiKey(key)
            if not isok:
                self.logAuthIssue(mesg=info.get('mesg'))
                return None

            udef = info.get('udef')
            self.web_useriden = udef.get('iden')
            self.web_username = udef.get('name')
            return self.web_useriden

        return await s_jsrpc.JsonRpcHandler.handleBasicAuth(self)

    # --- transport ---

    async def post(self):

        if not await self.reqAuthUser():
            return

        useriden = await self.useriden()
        user = self.getAuthCell().auth.user(useriden)

        vers = self.request.headers.get('MCP-Protocol-Version')
        if vers is not None and vers not in self.SUPPORTED_VERSIONS:
            self.set_status(HTTPStatus.BAD_REQUEST)
            self._sendResp(self._errResp(None, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, f'Unsupported MCP-Protocol-Version: {vers}')))
            return

        try:
            mesg = s_json.loads(self.request.body)
        except Exception:
            self._sendResp(self._errResp(None, s_exc.JsonRpcError.init(s_jsrpc.PARSE_ERROR, 'Parse error')))
            return

        if isinstance(mesg, list):
            self._sendResp(self._errResp(None, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, 'Batch requests are not supported by MCP.')))
            return

        method = mesg.get('method') if isinstance(mesg, dict) else None

        with s_scope.enter({'user': user}):

            if method == 'initialize':
                await self._handleInitialize(mesg, user)
                return

            session = self._reqSession(user)
            if session is None:
                return

            if method == 'notifications/initialized':
                session['initialized'] = True
                self.set_status(HTTPStatus.ACCEPTED)
                return

            if not session.get('initialized') and method != 'ping':
                self._sendResp(self._errResp(mesg.get('id'), s_exc.JsonRpcError.init(
                    s_jsrpc.INVALID_REQUEST, 'Session is not initialized.')))
                return

            if method == 'tools/call':
                await self._handleToolsCall(mesg)
                return

            _, resp = await self._dispatch(mesg, allow_stream=False)
            if resp is None:
                self.set_status(HTTPStatus.ACCEPTED)
                return

            self._sendResp(resp)

    async def get(self):
        # We do not offer a server-initiated SSE stream.
        self.set_status(HTTPStatus.METHOD_NOT_ALLOWED)

    async def delete(self):
        if not await self.reqAuthUser():
            return

        sid = self.request.headers.get('Mcp-Session-Id')
        if sid is not None:
            self._sessions().pop(sid, None)

        self.set_status(HTTPStatus.OK)

    # --- session management ---

    def _sessions(self):
        # The session store is created by Cell._initCellHttpApis when the MCP endpoint
        # is mounted (whenever _mcp_ctor is set).
        return self.cell._mcp_sessions

    def _getSession(self, sid):
        sessions = self._sessions()
        session = sessions.get(sid)
        if session is None:
            return None

        if s_common.now() - session.get('touched') > self.SESSION_TIMEOUT * 1000:
            sessions.pop(sid, None)
            return None

        return session

    def _reqSession(self, user):
        sid = self.request.headers.get('Mcp-Session-Id')
        if sid is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            self._sendResp(self._errResp(None, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, 'Missing Mcp-Session-Id header.')))
            return None

        session = self._getSession(sid)
        if session is None or session.get('user') != user.iden:
            self.set_status(HTTPStatus.NOT_FOUND)
            self._sendResp(self._errResp(None, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, 'Unknown or expired MCP session.')))
            return None

        session['touched'] = s_common.now()
        return session

    async def _handleInitialize(self, mesg, user):

        _, resp = await self._dispatch(mesg, allow_stream=False)
        if resp is None:
            self.set_status(HTTPStatus.ACCEPTED)
            return

        if resp.get('result') is not None:
            sid = s_common.guid()
            self._sessions()[sid] = {
                'iden': sid,
                'user': user.iden,
                'version': resp['result'].get('protocolVersion'),
                'initialized': False,
                'touched': s_common.now(),
            }
            self.set_header('Mcp-Session-Id', sid)

        self._sendResp(resp)

    # --- MCP JSON-RPC methods ---

    @s_jsrpc.method(name='initialize')
    async def _initialize(self, protocolVersion=None, capabilities=None, clientInfo=None, **info):
        vers = protocolVersion if protocolVersion in self.SUPPORTED_VERSIONS else self.PROTOCOL_VERSION
        return {
            'protocolVersion': vers,
            'capabilities': {'tools': {'listChanged': False}},
            'serverInfo': {
                'name': f'synapse-{self.cell.getCellType()}',
                'version': self.cell.VERSTRING,
            },
        }

    @s_jsrpc.method(name='ping')
    async def _ping(self):
        return {}

    @s_jsrpc.method(name='tools/list')
    async def _toolsList(self, cursor=None):
        tools = []
        for name, entry in sorted(self.getToolInfo().items()):
            info = entry.get('info')
            tools.append({
                'name': name,
                'description': info.get('desc'),
                'inputSchema': info.get('schema'),
            })

        return {'tools': tools}

    # --- tool dispatch ---

    async def _handleToolsCall(self, mesg):

        reqid = mesg.get('id')
        params = mesg.get('params')

        if not isinstance(params, dict):
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_PARAMS, 'tools/call params must be an object.')))
            return

        name = params.get('name')
        arguments = params.get('arguments')
        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_PARAMS, 'tools/call arguments must be an object.')))
            return

        entry = self.getToolInfo().get(name)
        if entry is None:
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.METHOD_NOT_FOUND, f'Unknown tool: {name}')))
            return

        info = entry.get('info')
        meth = getattr(self, entry.get('attr'))

        try:
            inspect.signature(meth).bind(**arguments)
        except TypeError as e:
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_PARAMS, f'Invalid arguments: {e}')))
            return

        validator = entry.get('validator')
        if validator is not None:
            try:
                validator(arguments)
            except s_exc.SchemaViolation as e:
                self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                    s_jsrpc.INVALID_PARAMS, e.get('mesg', str(e)))))
                return

        perm = info.get('perm')
        if perm is not None:
            user = s_scope.get('user')
            if user is None or not user.allowed(tuple(perm)):
                self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                    s_jsrpc.ACCESS_DENIED, f'Permission denied: {".".join(perm)}', data={'perm': list(perm)})))
                return

        if info.get('genr'):

            if self._wantsStream():
                await self._streamToolCall(reqid, meth, arguments)
                return

            try:
                items = [item async for item in meth(**arguments)]
            except Exception as e:
                self._sendResp(self._toolErrResp(reqid, e))
                return

            self._sendResp({'jsonrpc': '2.0', 'id': reqid, 'result': self._toolResult(items, stream=True)})
            return

        try:
            valu = meth(**arguments)
            if inspect.isawaitable(valu):
                valu = await valu
        except Exception as e:
            self._sendResp(self._toolErrResp(reqid, e))
            return

        self._sendResp({'jsonrpc': '2.0', 'id': reqid, 'result': self._toolResult(valu, stream=False)})

    async def _streamToolCall(self, reqid, meth, arguments):

        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')

        items = []
        try:
            async for item in meth(**arguments):
                items.append(item)
                await self._sendSse({'jsonrpc': '2.0', 'method': 'notifications/message',
                                     'params': {'level': 'info', 'data': item}})

            result = self._toolResult(items, stream=True)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            result = self._toolError(e)

        await self._sendSse({'jsonrpc': '2.0', 'id': reqid, 'result': result})

    def _toolResult(self, valu, stream=False):
        if stream:
            text = s_json.dumps(valu).decode()
            return {'content': [{'type': 'text', 'text': text}], 'structuredContent': {'items': valu}, 'isError': False}

        result = {'content': [{'type': 'text', 'text': s_json.dumps(valu).decode()}], 'isError': False}
        if isinstance(valu, dict):
            result['structuredContent'] = valu

        return result

    def _toolError(self, exc):
        mesg = exc.get('mesg', str(exc)) if isinstance(exc, s_exc.SynErr) else str(exc)
        return {'content': [{'type': 'text', 'text': mesg}], 'isError': True}

    def _toolErrResp(self, reqid, exc):
        return {'jsonrpc': '2.0', 'id': reqid, 'result': self._toolError(exc)}

    # --- tools ---

    @tool(name='getCellInfo', desc='Return metadata about the cell.')
    async def getCellInfo(self):
        return await self.cell.getCellInfo()

class CortexMcp(CellMcp):
    '''
    An MCP server handler which plumbs Cortex specific tools.
    '''
    _storm_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'The Storm query to execute.'},
            'opts': {'type': 'object', 'description': 'Optional Storm query opts.'},
        },
        'required': ['query'],
        'additionalProperties': False,
    }

    def _stormOpts(self, opts):
        user = s_scope.get('user')

        if opts is None:
            opts = {}

        opts.setdefault('user', user.iden)
        if opts.get('user') != user.iden:
            if not user.allowed(('impersonate',)):
                raise s_exc.AuthDeny(mesg='Impersonation requires the impersonate permission.',
                                     user=user.iden, username=user.name, perm='impersonate')

        return opts

    @tool(name='storm', desc='Run a Storm query and stream the result messages.', schema=_storm_schema)
    async def storm(self, query, opts=None):
        opts = self._stormOpts(opts)
        async for mesg in self.cell.storm(query, opts=opts):
            yield {'type': mesg[0], 'data': mesg[1]}

    @tool(name='callStorm', desc='Run a Storm query and return the value from its return() statement.',
          schema=_storm_schema)
    async def callStorm(self, query, opts=None):
        opts = self._stormOpts(opts)
        return await self.cell.callStorm(query, opts=opts)

    @tool(name='getModel', desc='Return the Cortex data model definition.')
    async def getModel(self):
        return await self.cell.getModelDict()
