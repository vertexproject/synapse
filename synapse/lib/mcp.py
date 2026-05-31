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

In addition to tools, handlers may expose **resources** (``@s_mcp.resource``, readable
URI-addressed content), **prompts** (``@s_mcp.prompt``, user-selectable templates), and
argument **completions** (``@s_mcp.completer``). Server **logging** is supported via
``logging/setLevel`` and ``notifications/message`` emitted on the SSE stream.
'''
import base64
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

# RFC 5424 syslog severities, in ascending order, used by MCP logging.
LOG_LEVELS = ('debug', 'info', 'notice', 'warning', 'error', 'critical', 'alert', 'emergency')

# JSON-RPC error code MCP uses for a resource which does not exist.
RESOURCE_NOT_FOUND = -32002

def _logEnabled(minlevel, level):
    return LOG_LEVELS.index(level) >= LOG_LEVELS.index(minlevel)

def tool(name=None, desc=None, schema=None):
    '''
    Decorate a method to expose it as an MCP tool (invoked via ``tools/call``).

    Args:
        name (str): An optional tool name override. Defaults to the function name.
        desc (str): A human readable description of the tool.
        schema (dict): An optional JSON Schema for the tool arguments (the MCP inputSchema).

    Notes:
        Only methods decorated with this decorator are exposed as tools. A tool that
        requires permissions enforces them itself within its method body.
    '''
    if schema is None:
        schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}

    def wrap(func):
        if not (inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)):
            raise s_exc.BadArg(mesg=f'mcp tool must be async: {func.__qualname__}')

        func._mcp_tool = {
            'name': name if name is not None else func.__name__,
            'desc': desc,
            'schema': schema,
            'genr': inspect.isasyncgenfunction(func),
        }
        return func

    return wrap

def resource(uri, name=None, desc=None, mimeType='application/json', completers=None):
    '''
    Decorate a method to expose it as an MCP resource (read via ``resources/read``).

    Args:
        uri (str): The resource URI. A URI containing ``{var}`` segments is a template
            (listed via ``resources/templates/list``); the method receives the captured
            segments as keyword arguments.
        name (str): An optional resource name. Defaults to the function name.
        desc (str): A human readable description of the resource.
        mimeType (str): The MIME type of the resource contents.
        completers (dict): For templates, maps a template variable name to a completer name.

    Notes:
        A resource that requires permissions enforces them itself within its method body.
        The decorated method must be a coroutine function.
    '''
    def wrap(func):
        if not inspect.iscoroutinefunction(func):
            raise s_exc.BadArg(mesg=f'mcp resource must be async: {func.__qualname__}')

        func._mcp_resource = {
            'uri': uri,
            'name': name if name is not None else func.__name__,
            'desc': desc,
            'mimeType': mimeType,
            'completers': completers if completers is not None else {},
            'template': '{' in uri,
        }
        return func

    return wrap

def prompt(name=None, desc=None, arguments=()):
    '''
    Decorate a method to expose it as an MCP prompt (rendered via ``prompts/get``).

    Args:
        name (str): An optional prompt name. Defaults to the function name.
        desc (str): A human readable description of the prompt.
        arguments (list): A list of argument descriptors, each a dict with ``name`` and
            optional ``description``, ``required``, and ``complete`` (a completer name).

    Notes:
        The method receives the prompt arguments as keyword arguments and returns either a
        string (a single user text message) or a list of MCP prompt messages. A prompt that
        requires permissions enforces them itself within its method body. The decorated
        method must be a coroutine function.
    '''
    def wrap(func):
        if not inspect.iscoroutinefunction(func):
            raise s_exc.BadArg(mesg=f'mcp prompt must be async: {func.__qualname__}')

        func._mcp_prompt = {
            'name': name if name is not None else func.__name__,
            'desc': desc,
            'arguments': arguments,
        }
        return func

    return wrap

def completer(name=None):
    '''
    Decorate a method as a named argument completer.

    The method has the signature ``async def(self, value, context) -> list[str]`` where
    ``value`` is the partial value being completed and ``context`` is a dict of already
    resolved argument values. It is referenced by name from prompt arguments
    (``complete``) and resource template variables (``completers``).
    '''
    def wrap(func):
        if not inspect.iscoroutinefunction(func):
            raise s_exc.BadArg(mesg=f'mcp completer must be async: {func.__qualname__}')

        func._mcp_completer = {'name': name if name is not None else func.__name__}
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
    def getMcpTools(cls):
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
        for attrname, info in cls._getMarkedMethods('_mcp_tool'):

            validator = None
            if info.get('schema') is not None:
                validator = s_config.getJsValidator(info.get('schema'))

            tools[info.get('name')] = {'attr': attrname, 'info': info, 'validator': validator}

        cls._mcp_tools = tools
        return tools

    @classmethod
    def getMcpResources(cls):
        '''Return the MCP resource registry, keyed by URI.'''
        resources = cls.__dict__.get('_mcp_resources')
        if resources is None:
            resources = {info.get('uri'): {'attr': attrname, 'info': info}
                         for attrname, info in cls._getMarkedMethods('_mcp_resource')}
            cls._mcp_resources = resources

        return resources

    @classmethod
    def getMcpPrompts(cls):
        '''Return the MCP prompt registry, keyed by name.'''
        prompts = cls.__dict__.get('_mcp_prompts')
        if prompts is None:
            prompts = {info.get('name'): {'attr': attrname, 'info': info}
                       for attrname, info in cls._getMarkedMethods('_mcp_prompt')}
            cls._mcp_prompts = prompts

        return prompts

    @classmethod
    def getMcpCompleters(cls):
        '''Return the argument completer registry, keyed by name.'''
        completers = cls.__dict__.get('_mcp_completers')
        if completers is None:
            completers = {info.get('name'): {'attr': attrname, 'info': info}
                          for attrname, info in cls._getMarkedMethods('_mcp_completer')}
            cls._mcp_completers = completers

        return completers

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

            self.mcpsess = session

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
                'loglevel': 'info',
                'touched': s_common.now(),
            }
            self.set_header('Mcp-Session-Id', sid)

        self._sendResp(resp)

    # --- MCP JSON-RPC methods ---

    @s_jsrpc.method(name='initialize')
    async def _initialize(self, protocolVersion=None, capabilities=None, clientInfo=None, **info):
        vers = protocolVersion if protocolVersion in self.SUPPORTED_VERSIONS else self.PROTOCOL_VERSION

        # Advertise only the capabilities this handler class actually provides.
        caps = {'tools': {'listChanged': False}, 'logging': {}}
        if self.getMcpResources():
            caps['resources'] = {}
        if self.getMcpPrompts():
            caps['prompts'] = {'listChanged': False}
        if self.getMcpCompleters():
            caps['completions'] = {}

        return {
            'protocolVersion': vers,
            'capabilities': caps,
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
        cls = type(self)
        result = cls.__dict__.get('_mcp_tools_list')
        if result is None:
            tools = []
            for name, entry in sorted(self.getMcpTools().items()):
                info = entry.get('info')
                tools.append({
                    'name': name,
                    'description': info.get('desc'),
                    'inputSchema': info.get('schema'),
                })
            result = {'tools': tools}
            cls._mcp_tools_list = result

        return result

    # --- resources ---

    @s_jsrpc.method(name='resources/list')
    async def _resourcesList(self, cursor=None):
        cls = type(self)
        result = cls.__dict__.get('_mcp_resources_list')
        if result is None:
            resources = []
            for uri, entry in sorted(self.getMcpResources().items()):
                info = entry.get('info')
                if info.get('template'):
                    continue
                resources.append({
                    'uri': uri,
                    'name': info.get('name'),
                    'description': info.get('desc'),
                    'mimeType': info.get('mimeType'),
                })
            result = {'resources': resources}
            cls._mcp_resources_list = result

        return result

    @s_jsrpc.method(name='resources/templates/list')
    async def _resourcesTemplatesList(self, cursor=None):
        cls = type(self)
        result = cls.__dict__.get('_mcp_resource_templates_list')
        if result is None:
            templates = []
            for uri, entry in sorted(self.getMcpResources().items()):
                info = entry.get('info')
                if not info.get('template'):
                    continue
                templates.append({
                    'uriTemplate': uri,
                    'name': info.get('name'),
                    'description': info.get('desc'),
                    'mimeType': info.get('mimeType'),
                })
            result = {'resourceTemplates': templates}
            cls._mcp_resource_templates_list = result

        return result

    @s_jsrpc.method(name='resources/read')
    async def _resourcesRead(self, uri=None):
        resolved = self._resolveResource(uri)
        if resolved is None:
            raise s_exc.JsonRpcError.init(RESOURCE_NOT_FOUND, f'Resource not found: {uri}', data={'uri': uri})

        entry, kwargs = resolved
        info = entry.get('info')

        meth = getattr(self, entry.get('attr'))
        valu = await meth(**kwargs)

        return {'contents': [self._resourceContent(uri, info.get('mimeType'), valu)]}

    def _resolveResource(self, uri):
        if uri is None:
            return None

        resources = self.getMcpResources()

        entry = resources.get(uri)
        if entry is not None and not entry.get('info').get('template'):
            return (entry, {})

        for tmpl, entry in resources.items():
            if not entry.get('info').get('template'):
                continue
            kwargs = self._matchTemplate(tmpl, uri)
            if kwargs is not None:
                return (entry, kwargs)

        return None

    def _matchTemplate(self, tmpl, uri):
        tparts = tmpl.split('/')
        uparts = uri.split('/')
        if len(tparts) != len(uparts):
            return None

        kwargs = {}
        for tpart, upart in zip(tparts, uparts):
            if tpart.startswith('{') and tpart.endswith('}'):
                kwargs[tpart[1:-1]] = upart
            elif tpart != upart:
                return None

        return kwargs

    def _resourceContent(self, uri, mimeType, valu):
        if isinstance(valu, bytes):
            return {'uri': uri, 'mimeType': mimeType, 'blob': base64.b64encode(valu).decode()}

        if isinstance(valu, str):
            return {'uri': uri, 'mimeType': mimeType, 'text': valu}

        return {'uri': uri, 'mimeType': mimeType, 'text': s_json.dumps(valu).decode()}

    # --- prompts ---

    @s_jsrpc.method(name='prompts/list')
    async def _promptsList(self, cursor=None):
        cls = type(self)
        result = cls.__dict__.get('_mcp_prompts_list')
        if result is None:
            prompts = []
            for name, entry in sorted(self.getMcpPrompts().items()):
                info = entry.get('info')
                arguments = [{'name': a.get('name'), 'description': a.get('description'),
                              'required': a.get('required', False)} for a in info.get('arguments')]
                prompts.append({'name': name, 'description': info.get('desc'), 'arguments': arguments})
            result = {'prompts': prompts}
            cls._mcp_prompts_list = result

        return result

    @s_jsrpc.method(name='prompts/get')
    async def _promptsGet(self, name=None, arguments=None):
        entry = self.getMcpPrompts().get(name)
        if entry is None:
            raise s_exc.JsonRpcError.init(s_jsrpc.INVALID_PARAMS, f'Unknown prompt: {name}')

        if arguments is None:
            arguments = {}

        info = entry.get('info')
        for arg in info.get('arguments'):
            if arg.get('required') and arg.get('name') not in arguments:
                raise s_exc.JsonRpcError.init(s_jsrpc.INVALID_PARAMS, f'Missing required argument: {arg.get("name")}')

        meth = getattr(self, entry.get('attr'))
        try:
            inspect.signature(meth).bind(**arguments)
        except TypeError as e:
            raise s_exc.JsonRpcError.init(s_jsrpc.INVALID_PARAMS, f'Invalid arguments: {e}')

        valu = await meth(**arguments)

        if isinstance(valu, str):
            valu = [{'role': 'user', 'content': {'type': 'text', 'text': valu}}]

        return {'description': info.get('desc'), 'messages': valu}

    # --- completions ---

    @s_jsrpc.method(name='completion/complete')
    async def _completionComplete(self, ref=None, argument=None, context=None):
        values = await self._resolveCompletion(ref, argument, context)
        total = len(values)
        values = values[:100]
        return {'completion': {'values': values, 'total': total, 'hasMore': total > len(values)}}

    async def _resolveCompletion(self, ref, argument, context):
        if not isinstance(ref, dict) or not isinstance(argument, dict):
            return []

        cname = self._completerName(ref, argument.get('name'))
        if cname is None:
            return []

        entry = self.getMcpCompleters().get(cname)
        if entry is None:
            return []

        ctxargs = context.get('arguments') if isinstance(context, dict) else None
        meth = getattr(self, entry.get('attr'))
        return await meth(argument.get('value') or '', ctxargs if ctxargs is not None else {})

    def _completerName(self, ref, argname):
        rtype = ref.get('type')

        if rtype == 'ref/prompt':
            entry = self.getMcpPrompts().get(ref.get('name'))
            if entry is None:
                return None
            for arg in entry.get('info').get('arguments'):
                if arg.get('name') == argname:
                    return arg.get('complete')
            return None

        if rtype == 'ref/resource':
            entry = self.getMcpResources().get(ref.get('uri'))
            if entry is None:
                return None
            return entry.get('info').get('completers').get(argname)

        return None

    # --- logging ---

    @s_jsrpc.method(name='logging/setLevel')
    async def _loggingSetLevel(self, level=None):
        if level not in LOG_LEVELS:
            raise s_exc.JsonRpcError.init(s_jsrpc.INVALID_PARAMS, f'Invalid log level: {level}')

        self.mcpsess['loglevel'] = level
        return {}

    def _streamItemLevel(self, item):
        # Overridable: the log level at which a streamed tool item is emitted.
        return 'info'

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

        entry = self.getMcpTools().get(name)
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
            valu = await meth(**arguments)
        except Exception as e:
            self._sendResp(self._toolErrResp(reqid, e))
            return

        self._sendResp({'jsonrpc': '2.0', 'id': reqid, 'result': self._toolResult(valu, stream=False)})

    async def _streamToolCall(self, reqid, meth, arguments):

        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')

        minlevel = self.mcpsess.get('loglevel', 'info')

        items = []
        try:
            async for item in meth(**arguments):
                items.append(item)
                level = self._streamItemLevel(item)
                if _logEnabled(minlevel, level):
                    await self._sendSse({'jsonrpc': '2.0', 'method': 'notifications/message',
                                         'params': {'level': level, 'data': item}})

            result = self._toolResult(items, stream=True)

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

    # --- tools and resources ---

    @tool(name='getCellInfo', desc='Return metadata about the cell.')
    async def getCellInfo(self):
        return await self.cell.getCellInfo()

    @resource(uri='syn://cellinfo', name='cellinfo', desc='Metadata about the cell.')
    async def _resCellInfo(self):
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

    @tool(name='getModel', desc='Return the Synapse data model definition.')
    async def getModel(self):
        return await self.cell.getModelDict()

    def _streamItemLevel(self, item):
        # Map Storm message types to MCP log levels for streamed storm() output.
        if isinstance(item, dict):
            mtype = item.get('type')
            if mtype == 'warn':
                return 'warning'
            if mtype == 'err':
                return 'error'

        return 'info'

    # --- resources ---

    @resource(uri='syn://model', name='datamodel', desc='The Synapse data model definition.')
    async def _resModel(self):
        return await self.cell.getModelDict()

    @resource(uri='syn://stormdocs', name='stormdocs', desc='Storm library, type, and command documentation.')
    async def _resStormDocs(self):
        return await self.cell.getStormDocs()

    @resource(uri='syn://model/form/{name}', name='form', desc='A single data model form definition.',
              completers={'name': 'model:forms'})
    async def _resForm(self, name):
        mdef = await self.cell.getModelDict()
        form = mdef['forms'].get(name)
        if form is None:
            raise s_exc.JsonRpcError.init(RESOURCE_NOT_FOUND, f'No such form: {name}',
                                          data={'uri': f'syn://model/form/{name}'})
        return form

    # --- prompts ---

    @prompt(name='storm-query', desc='Draft a Storm query.',
            arguments=[{'name': 'form', 'description': 'A form to focus the query on.',
                        'required': False, 'complete': 'model:forms'},
                       {'name': 'typename', 'description': 'A model type to reference.',
                        'required': False, 'complete': 'model:types'}])
    async def _promptStormQuery(self, form=None, typename=None):
        text = 'Write a Storm query'
        if form:
            text += f' that lifts and operates on {form} nodes'
        if typename:
            text += f' involving the {typename} type'
        text += '. Consult the syn://model resource for the available data model.'
        return text

    # --- completers ---

    @completer(name='model:forms')
    async def _completeForms(self, value, context):
        return self.cell.model.getFormsByPrefix(value)

    @completer(name='model:types')
    async def _completeTypes(self, value, context):
        return sorted(name for name in self.cell.model.types if name.startswith(value))
