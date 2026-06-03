'''
MCP (Model Context Protocol) server handlers for Synapse cells.

MCP is JSON-RPC 2.0 over a Streamable HTTP transport. This module builds on the generic
``synapse.lib.jsrpc.JsonRpcHandler`` to implement the MCP server methods: the lifecycle
(``initialize``, ``notifications/initialized``, ``ping``), ``tools/list`` and
``tools/call``, ``resources/list`` / ``resources/templates/list`` / ``resources/read``,
``prompts/list`` / ``prompts/get``, ``completion/complete``, and ``logging/setLevel``.

``CellMcp`` provides the MCP transport (POST for messages, GET returns 405, DELETE ends a
session), the session lifecycle, and dispatch, and may be mounted on any cell. ``CortexMcp``
extends it to plumb Cortex specific tools, resources, prompts, and completers. A cell opts
in to MCP by setting the ``_mcp_ctor`` class attribute, which the base Cell mounts at
``/api/v1/mcp`` during HTTP API initialization.

Sessions are stateful and bound to the authenticating user: ``initialize`` issues an
``Mcp-Session-Id`` (returned as a response header and required on subsequent requests),
held in memory with an idle timeout. Every request is authenticated via the inherited
handler auth (session cookie, HTTP Basic, or an ``X-API-KEY`` header).

Server features are exposed via opt-in decorators, each requiring an async method:

* ``@s_mcp.tool`` - a callable tool. Async generator tools stream their results as
  Server-Sent Events when the request carries an ``Accept: text/event-stream`` header.
* ``@s_mcp.resource`` - readable URI-addressed content; a URI with ``{var}`` segments is a
  template whose captured segments are passed to the method as keyword arguments.
* ``@s_mcp.prompt`` - a user-selectable prompt template.
* ``@s_mcp.completer`` - a named argument completer for prompt arguments and resource
  template variables.

Capabilities are advertised dynamically based on which registries a handler class actually
provides. A method that requires permissions enforces them itself within its body. Server
``logging`` notifications (``notifications/message``) are emitted on the SSE stream and
filtered by the per-session level set via ``logging/setLevel``.
'''
import re
import base64
import asyncio
import inspect
import logging
from http import HTTPStatus

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.config as s_config
import synapse.lib.jsrpc as s_jsrpc

logger = logging.getLogger(__name__)

# The MCP protocol version this server implements (and the versions it will accept).
PROTOCOL_VERSION = '2025-06-18'
SUPPORTED_VERSIONS = ('2025-06-18', '2025-03-26')

# Idle timeout (in seconds) before an MCP session is considered expired.
SESSION_TIMEOUT = 3600

# Storm tool pagination: the maximum number of messages returned per page, the idle timeout
# (in seconds) before an open storm cursor is reclaimed, and the maximum number of open storm
# cursors retained per session (the oldest is evicted past this).
STORM_PAGE_SIZE = 100
STORM_CURSOR_TIMEOUT = 300
STORM_MAX_CURSORS = 8

# RFC 5424 syslog severities, in ascending order, used by MCP logging.
LOG_LEVELS = ('debug', 'info', 'notice', 'warning', 'error', 'critical', 'alert', 'emergency')

# JSON-RPC error code MCP uses for a resource which does not exist.
RESOURCE_NOT_FOUND = -32002

# The strictest tool/prompt name pattern currently known to be compatible everywhere: it
# must start with an ASCII letter or underscore (Gemini/Vertex reject other leading chars)
# and otherwise contain only ASCII letters, digits, and underscores (avoiding the dash, dot,
# and slash that various clients and function-calling backends reject), max length 64.
_NAME_REGEX = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')

def _reqValidName(name):
    if _NAME_REGEX.match(name) is None:
        raise s_exc.BadArg(mesg=f'MCP name must match {_NAME_REGEX.pattern}: {name}')

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

        toolname = name if name is not None else func.__name__
        _reqValidName(toolname)

        func._mcp_tool = {
            'name': toolname,
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

        promptname = name if name is not None else func.__name__
        _reqValidName(promptname)

        func._mcp_prompt = {
            'name': promptname,
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

    # Subclasses may set this to a server-wide instructions string returned in the MCP
    # initialize response. If None, no instructions field is included.
    _mcp_instructions = None

    def getCore(self):
        # Abstraction (mirrors s_httpapi.StormHandler.getCore) which allows subclasses to
        # dictate how a reference to the cortex is returned from the handler. Defaults to the
        # cell the handler is mounted on; a subclass (e.g. mounted on Optic) may override this
        # to return a telepath proxy to a remote cortex.
        return self.cell

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

    # --- transport ---

    async def post(self):

        if not await self.reqAuthUser():
            return

        # Authentication may be delegated to a remote cell via getAuthCell() (a telepath
        # proxy), so we carry the authenticated user iden and run permission checks through
        # getAuthCell()'s telepath-safe APIs rather than resolving a local user object.
        useriden = await self.useriden()

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
        reqid = mesg.get('id') if isinstance(mesg, dict) else None

        if method == 'initialize':
            await self._handleInitialize(mesg, useriden)
            return

        session = self._reqSession(useriden, reqid)
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

        useriden = await self.useriden()

        sid = self.request.headers.get('Mcp-Session-Id')
        session = self._getSession(sid) if sid is not None else None
        if session is None or session.get('user') != useriden:
            self.set_status(HTTPStatus.NOT_FOUND)
            return

        self.cell._mcp_sessions.pop(sid, None)
        await self._closeSessionResources(session)
        self.set_status(HTTPStatus.OK)

    async def _closeSessionResources(self, session):
        # Release any long-lived async resources a session is holding (e.g. open storm
        # pagination cursor producer tasks) when the session ends.
        for info in session.pop('cursors', {}).values():
            info['task'].cancel()
            try:
                await info['task']
            except asyncio.CancelledError:
                pass
            except Exception:  # pragma: no cover
                logger.exception('error closing mcp session cursor')

    # --- session management ---
    # The session store (self.cell._mcp_sessions) is created by Cell._initCellHttpApis
    # when the MCP endpoint is mounted (whenever _mcp_ctor is set).

    def _getSession(self, sid):
        sessions = self.cell._mcp_sessions
        session = sessions.get(sid)
        if session is None:
            return None

        if s_common.now() - session.get('touched') > self.SESSION_TIMEOUT * 1000:
            sessions.pop(sid, None)
            return None

        return session

    def _reqSession(self, useriden, reqid=None):
        sid = self.request.headers.get('Mcp-Session-Id')
        if sid is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, 'Missing Mcp-Session-Id header.')))
            return None

        session = self._getSession(sid)
        if session is None or session.get('user') != useriden:
            self.set_status(HTTPStatus.NOT_FOUND)
            self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                s_jsrpc.INVALID_REQUEST, 'Unknown or expired MCP session.')))
            return None

        session['touched'] = s_common.now()
        return session

    async def _handleInitialize(self, mesg, useriden):

        _, resp = await self._dispatch(mesg, allow_stream=False)
        if resp is None:
            self.set_status(HTTPStatus.ACCEPTED)
            return

        if resp.get('result') is not None:
            sid = s_common.guid()
            self.cell._mcp_sessions[sid] = {
                'iden': sid,
                'user': useriden,
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

        result = {
            'protocolVersion': vers,
            'capabilities': caps,
            'serverInfo': {
                'name': f'synapse-{self.cell.getCellType()}',
                'version': self.cell.VERSTRING,
            },
        }

        if self._mcp_instructions is not None:
            result['instructions'] = self._mcp_instructions

        return result

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

            agen = meth(**arguments)
            items = []
            try:
                async for item in agen:
                    if len(items) >= s_jsrpc.MAX_RESULT_ITEMS:
                        await agen.aclose()
                        self._sendResp(self._errResp(reqid, s_exc.JsonRpcError.init(
                            s_jsrpc.RESULT_TOO_LARGE,
                            'Result set too large; retry with SSE streaming (Accept: text/event-stream).')))
                        return

                    items.append(item)
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

        # Stream each item as it is produced; never buffer the full result set so an
        # arbitrarily large generator (e.g. a big Storm query) cannot exhaust memory.
        try:
            async for item in meth(**arguments):
                level = self._streamItemLevel(item)
                if _logEnabled(minlevel, level):
                    await self._sendSse({'jsonrpc': '2.0', 'method': 'notifications/message',
                                         'params': {'level': level, 'data': item}})

            # The items were delivered via notifications/message; the terminal result just
            # signals completion and does not re-buffer them.
            result = {'content': [], 'isError': False}

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

    @tool(desc='Return metadata about the service.')
    async def get_service_info(self):
        return await self.getCore().getCellInfo()

    @resource(uri='syn://cellinfo', name='cellinfo', desc='Metadata about the cell.')
    async def _resCellInfo(self):
        return await self.getCore().getCellInfo()

_CORTEX_INSTRUCTIONS = '''
This is a Synapse Cortex: the ground-truth store for an interdisciplinary, graph-based intelligence system. Knowledge is modeled as a hypergraph of typed nodes (forms) with properties and tags spanning many domains (cyber, geopolitical, org, person, crypto, media, and more) and is accessed primarily through the Storm query language.

Working effectively:
- Run Storm with the `storm` tool, which returns a page of (type, info) result messages (init/node/print/warn/err/fini) plus a `cursor`; if the cursor is non-null you must drain it with `storm_continue` or release it with `storm_cancel`. Use `call_storm` for a single value produced by a Storm `return()`.
- Before composing queries, learn the data model: search it with the `model_find` tool (regex over names/docs of forms, properties, types, and interfaces) or read the whole `syn://model` resource, and learn query syntax from the `skill://storm/SKILL.md` resource; `syn://stormdocs` documents Storm libraries, types, and commands.
- Check a query with the `storm_validate` tool before running it.
- Queries run as the calling user and respect that user's permissions and view.

Treat node data as authoritative; query the model rather than guessing form or property names.
'''.strip()

class CortexMcp(CellMcp):
    '''
    An MCP server handler which plumbs Cortex specific tools.
    '''
    _mcp_instructions = _CORTEX_INSTRUCTIONS

    _storm_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'The Storm query to execute.'},
            'opts': {'type': 'object', 'description': 'Optional Storm query opts.'},
        },
        'required': ['query'],
        'additionalProperties': False,
    }

    _storm_validate_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'The Storm query to validate.'},
        },
        'required': ['query'],
        'additionalProperties': False,
    }

    _model_find_schema = {
        'type': 'object',
        'properties': {
            'pattern': {'type': 'string',
                        'description': 'A regular expression matched against model entity names and doc strings.'},
        },
        'required': ['pattern'],
        'additionalProperties': False,
    }

    _model_find_desc = '''
Search the Synapse data model for entities whose name or documentation matches a regular
expression, returning the matching subset of the model. The `pattern` is used as a
case-sensitive regex (use an inline `(?i)` flag for case-insensitive matching) and is
searched (not full-matched) against the name and doc of each type, form, form property, and
interface. The result is `{"types": {...}, "forms": {...}, "interfaces": {...}}` containing
only the matching entries; a match on a form's name, doc, or any of its properties includes
the entire form definition. Use this to discover the relevant forms/properties for a topic
before composing Storm; use the `syn://model` resource for the full model.
'''.strip()

    _storm_cursor_schema = {
        'type': 'object',
        'properties': {
            'cursor': {'type': 'string', 'description': 'A cursor returned by the storm tool.'},
        },
        'required': ['cursor'],
        'additionalProperties': False,
    }

    _storm_desc = '''
Run a Storm query and return a page of result messages. The result is
``{"messages": [(type, info), ...], "cursor": <str-or-null>}``. If "cursor" is non-null the
query produced more messages than fit in one page and is still running on the server: you
MUST either drain it by calling storm_continue(cursor) repeatedly until it returns a null
cursor, or release it by calling storm_cancel(cursor). Never abandon a query with a non-null
cursor -- doing so holds a Storm runtime open on the server until it times out. When "cursor"
is null the query is complete and fully drained; nothing further is required.
'''.strip()

    _storm_continue_desc = '''
Fetch the next page of messages from a running Storm query started by the storm tool. Takes
the "cursor" from the previous storm or storm_continue result and returns the same
``{"messages": [...], "cursor": <str-or-null>}`` shape. Keep calling storm_continue until the
returned cursor is null, which means the query is complete and the cursor has been released.
'''.strip()

    _storm_cancel_desc = '''
Release a running Storm query without draining the rest of its results, given the "cursor"
from a storm or storm_continue result. Use this to abandon a query you do not intend to fully
read so its server-side Storm runtime is torn down immediately rather than waiting to time
out.
'''.strip()

    _view_set_schema = {
        'type': 'object',
        'properties': {
            'view': {'type': 'string', 'description': 'The iden of the view to set as active.'},
        },
        'required': ['view'],
        'additionalProperties': False,
    }

    _view_fork_schema = {
        'type': 'object',
        'properties': {
            'view': {'type': 'string',
                     'description': 'The iden of the view to fork. Defaults to the active session view.'},
            'name': {'type': 'string', 'description': 'An optional name for the new fork view.'},
        },
        'additionalProperties': False,
    }

    _view_del_schema = {
        'type': 'object',
        'properties': {
            'view': {'type': 'string',
                     'description': 'The iden of the view to delete. Defaults to the active session view.'},
        },
        'additionalProperties': False,
    }

    _view_merge_schema = {
        'type': 'object',
        'properties': {
            'view': {'type': 'string',
                     'description': 'The iden of the forked view to merge. Defaults to the active session view.'},
            'force': {'type': 'boolean', 'description': 'Force the merge past optional merge checks.'},
        },
        'additionalProperties': False,
    }

    _view_get_desc = '''
Get the view active for this session. If no view has been set for the session with view_set, this returns the calling user's default view.
'''.strip()

    _view_fork_desc = '''
Fork a view, creating a new child view with its own writable top layer; defaults to the active session view. If the forked view is the active session view, the session view is automatically switched to the new fork so subsequent storm tools run inside it. A view_fork followed (after testing) by a view_del is the safe way to develop ingest logic that edits nodes: fork the view, run the ingest in the fork, inspect the results, then view_del the fork to discard every change. ALWAYS develop and test node-editing or ingest logic this way so it never touches the underlying data.
'''.strip()

    _view_del_desc = '''
Delete a view (its layers are not deleted); defaults to the active session view. If the deleted view is the active session view, the session view is changed to the deleted view's parent once the deletion completes. Combined with view_fork this is the safe way to develop ingest logic that edits nodes: view_fork your view, run the ingest in the fork, then view_del the fork to discard every change.
'''.strip()

    _view_merge_desc = '''
Merge a forked view's changes down into its parent view (the fork itself is not deleted); defaults to the active session view. The view must be a fork whose parent does not require quorum voting. If the merged view is the active session view, the session view is changed to the parent once the merge completes.
'''.strip()

    async def _stormOpts(self, opts):
        useriden = self.web_useriden

        if opts is None:
            opts = {}

        opts.setdefault('user', useriden)

        view = self.mcpsess.get('view')
        if view is not None:
            opts.setdefault('view', view)

        if opts.get('user') != useriden:
            if not await self.getAuthCell().isUserAllowed(useriden, ('impersonate',)):
                raise s_exc.AuthDeny(mesg='Impersonation requires the impersonate permission.',
                                     user=useriden, perm='impersonate')

        return opts

    def _coreOpts(self, **varz):
        # Storm opts used to run view operations on getCore() as the calling user. Running
        # them via $lib.view (rather than live View objects) keeps them telepath-safe and
        # lets Storm enforce the view permissions uniformly, whether getCore() is the local
        # cortex or a remote telepath proxy.
        opts = {'user': self.web_useriden}
        if varz:
            opts['vars'] = varz

        return opts

    async def _userViewIden(self):
        # The calling user's effective default view, honoring their cortex:view profile.
        # Resolved on the cortex via getCore() so it works for a local or remote cortex.
        return await self.getCore().callStorm('return($lib.view.get().iden)', opts=self._coreOpts())

    async def _sessionViewIden(self):
        # The view subsequent storm tools run in: the session view if one has been set with
        # view_set, otherwise the calling user's default view.
        viewiden = self.mcpsess.get('view')
        if viewiden is not None:
            return viewiden

        return await self._userViewIden()

    async def _viewTarget(self, view):
        # Resolve the target view for a view_* operation, defaulting to the session view.
        if view is not None:
            return view

        return await self._sessionViewIden()

    # --- storm pagination cursors (session-scoped, idle-evicted) ---
    #
    # A storm query is driven by a background task (owned by the cell, not the request) which
    # feeds a bounded queue; the cursor reads pages from that queue. This decouples the query
    # from the request that started it -- the storm generator is bound to its producing task,
    # so it cannot be suspended in one request and resumed in another. The bounded queue also
    # provides backpressure so a slow client cannot make the producer buffer the whole result.

    async def _finiStormCursor(self, info):
        info['task'].cancel()
        try:
            await info['task']
        except asyncio.CancelledError:
            pass
        except Exception:  # pragma: no cover
            logger.exception('error closing storm cursor task')

    async def _closeStormCursor(self, cursors, iden):
        info = cursors.pop(iden, None)
        if info is not None:
            await self._finiStormCursor(info)

    async def _sweepStormCursors(self, cursors):
        now = s_common.now()
        for iden in list(cursors):
            if now - cursors[iden]['touched'] > STORM_CURSOR_TIMEOUT * 1000:
                await self._closeStormCursor(cursors, iden)

    async def _startStormCursor(self, query, opts):
        cursors = self.mcpsess.setdefault('cursors', {})

        await self._sweepStormCursors(cursors)

        if len(cursors) >= STORM_MAX_CURSORS:
            oldest = min(cursors, key=lambda i: cursors[i]['touched'])
            await self._closeStormCursor(cursors, oldest)

        core = self.getCore()
        queue = asyncio.Queue(maxsize=STORM_PAGE_SIZE * 2)

        async def produce():
            try:
                async for mesg in core.storm(query, opts=opts):
                    await queue.put(('mesg', mesg))

                await queue.put(('done', None))

            except asyncio.CancelledError:
                raise

            except Exception as e:
                await queue.put(('err', e))

        iden = s_common.guid()
        cursors[iden] = {'queue': queue, 'task': self.cell.schedCoro(produce()), 'touched': s_common.now()}
        return iden

    async def _reqStormCursor(self, cursor):
        cursors = self.mcpsess.get('cursors', {})

        info = cursors.get(cursor)
        if info is None:
            raise s_exc.BadArg(mesg=f'Unknown or expired storm cursor: {cursor}')

        if s_common.now() - info['touched'] > STORM_CURSOR_TIMEOUT * 1000:
            await self._closeStormCursor(cursors, cursor)
            raise s_exc.BadArg(mesg=f'Storm cursor expired: {cursor}')

        return info

    async def _stormCursorPage(self, cursor):
        cursors = self.mcpsess.get('cursors', {})
        info = cursors[cursor]
        queue = info['queue']

        msgs = []
        done = False
        try:
            while len(msgs) < STORM_PAGE_SIZE:
                kind, item = await queue.get()
                if kind == 'mesg':
                    msgs.append(item)
                    continue

                if kind == 'err':
                    raise item

                done = True
                break
        except Exception:
            await self._closeStormCursor(cursors, cursor)
            raise

        if done:
            await self._closeStormCursor(cursors, cursor)
            return {'messages': msgs, 'cursor': None}

        info['touched'] = s_common.now()
        return {'messages': msgs, 'cursor': cursor}

    @tool(desc=_storm_desc, schema=_storm_schema)
    async def storm(self, query, opts=None):
        opts = await self._stormOpts(opts)
        cursor = await self._startStormCursor(query, opts)
        return await self._stormCursorPage(cursor)

    @tool(desc=_storm_continue_desc, schema=_storm_cursor_schema)
    async def storm_continue(self, cursor):
        await self._reqStormCursor(cursor)
        return await self._stormCursorPage(cursor)

    @tool(desc=_storm_cancel_desc, schema=_storm_cursor_schema)
    async def storm_cancel(self, cursor):
        cursors = self.mcpsess.get('cursors', {})
        if cursor not in cursors:
            raise s_exc.BadArg(mesg=f'Unknown or expired storm cursor: {cursor}')

        await self._closeStormCursor(cursors, cursor)
        return {'cancelled': cursor}

    @tool(desc='Run a Storm query and return the value from its return() statement.', schema=_storm_schema)
    async def call_storm(self, query, opts=None):
        opts = await self._stormOpts(opts)
        return await self.getCore().callStorm(query, opts=opts)

    @tool(desc='Validate the syntax of a Storm query without executing it.', schema=_storm_validate_schema)
    async def storm_validate(self, query):
        valid, info = await self.getCore().isValidStorm(query)
        if valid:
            return {'valid': True}

        errname, errinfo = info
        return {'valid': False, 'err': errname, 'mesg': errinfo.get('mesg')}

    @tool(desc=_model_find_desc, schema=_model_find_schema)
    async def model_find(self, pattern):
        try:
            regx = re.compile(pattern)
        except re.error as e:
            raise s_exc.BadArg(mesg=f'Invalid model_find pattern: {e}') from None

        mdef = await self.getCore().getModelDict()

        types = {}
        for name, tdef in mdef['types'].items():
            await asyncio.sleep(0)
            if regx.search(name) or regx.search(tdef['info'].get('doc', '')):
                types[name] = tdef

        ifaces = {}
        for name, idef in mdef['interfaces'].items():
            await asyncio.sleep(0)
            if regx.search(name) or regx.search(idef.get('doc', '')):
                ifaces[name] = idef

        forms = {}
        for name, fdef in mdef['forms'].items():
            await asyncio.sleep(0)

            # forms carry their doc on the same-named type
            formdoc = mdef['types'][name]['info'].get('doc', '')
            matched = regx.search(name) is not None or regx.search(formdoc) is not None

            # a match on any property includes the entire form definition
            if not matched:
                for pdef in fdef['props'].values():
                    await asyncio.sleep(0)
                    if regx.search(pdef['full']) or regx.search(pdef.get('doc', '')):
                        matched = True
                        break

            if matched:
                forms[name] = fdef

        return {'types': types, 'forms': forms, 'interfaces': ifaces}

    @tool(desc='List the views this user can read.')
    async def view_list(self):
        query = '''
        $views = ([])
        for $view in $lib.view.list() {
            if $lib.user.allowed("view.read", gateiden=$view.iden) {
                $views.append(({"iden": $view.iden, "name": $view.get(name), "parent": $view.parent}))
            }
        }
        return($views)
        '''
        return {'views': await self.getCore().callStorm(query, opts=self._coreOpts())}

    @tool(desc='Set the active view for this session, used by subsequent storm tools.',
          schema=_view_set_schema)
    async def view_set(self, view):
        # Confirm the view exists (NoSuchView if not) and that the user can read it.
        query = '''
        $iden = $lib.view.get($iden).iden
        if (not $lib.user.allowed("view.read", gateiden=$iden)) {
            $lib.raise(AuthDeny, `User may not read view {$iden}.`)
        }
        return($iden)
        '''
        await self.getCore().callStorm(query, opts=self._coreOpts(iden=view))

        self.mcpsess['view'] = view
        return {'view': view}

    @tool(desc=_view_get_desc)
    async def view_get(self):
        return {'view': await self._sessionViewIden()}

    @tool(desc=_view_fork_desc, schema=_view_fork_schema)
    async def view_fork(self, view=None, name=None):
        iden = await self._viewTarget(view)

        # $lib.view fork enforces view.add / view.read / view.fork as the calling user.
        query = 'return($lib.view.get($iden).fork(name=$name).iden)'
        forkiden = await self.getCore().callStorm(query, opts=self._coreOpts(iden=iden, name=name))

        # If we forked the active session view, switch the session to the new fork.
        if iden == await self._sessionViewIden():
            self.mcpsess['view'] = forkiden

        return {'view': forkiden, 'parent': iden, 'session_view': await self._sessionViewIden()}

    @tool(desc=_view_del_desc, schema=_view_del_schema)
    async def view_del(self, view=None):
        iden = await self._viewTarget(view)

        # $lib.view.get() raises NoSuchView if missing and enforces read perm; we need the
        # parent iden for the session fallback before deleting.
        parent = await self.getCore().callStorm('return($lib.view.get($iden).parent)',
                                                opts=self._coreOpts(iden=iden))

        wascur = iden == await self._sessionViewIden()

        # $lib.view.del enforces the caller's view.del permission.
        await self.getCore().callStorm('$lib.view.del($iden)', opts=self._coreOpts(iden=iden))

        # If we deleted the active session view, fall back to its parent view.
        if wascur:
            if parent is not None:
                self.mcpsess['view'] = parent
            else:
                self.mcpsess.pop('view', None)

        return {'deleted': iden, 'parent': parent, 'session_view': await self._sessionViewIden()}

    @tool(desc=_view_merge_desc, schema=_view_merge_schema)
    async def view_merge(self, view=None, force=False):
        iden = await self._viewTarget(view)

        parent = await self.getCore().callStorm('return($lib.view.get($iden).parent)',
                                                opts=self._coreOpts(iden=iden))
        if parent is None:
            raise s_exc.BadArg(mesg=f'View {iden} is not a fork and cannot be merged.')

        wascur = iden == await self._sessionViewIden()

        # $lib.view merge enforces the caller's merge permissions and quorum rules.
        await self.getCore().callStorm('$lib.view.get($iden).merge(force=$force)',
                                       opts=self._coreOpts(iden=iden, force=force))

        # If we merged the active session view, switch the session to its parent.
        if wascur:
            self.mcpsess['view'] = parent

        return {'merged': iden, 'parent': parent, 'session_view': await self._sessionViewIden()}

    # --- resources ---

    @resource(uri='syn://model', name='datamodel', desc='The Synapse data model definition.')
    async def _resModel(self):
        return await self.getCore().getModelDict()

    @resource(uri='syn://stormdocs', name='stormdocs', desc='Storm library, type, and command documentation.')
    async def _resStormDocs(self):
        return (await self.getCore().getCoreInfoV2()).get('stormdocs')

    @resource(uri='skill://storm/SKILL.md', name='storm',
              desc='A skill describing the Storm query language syntax.', mimeType='text/markdown')
    async def _resStormSyntaxSkill(self):
        with open(s_data.path('skills', 'storm', 'SKILL.md')) as fd:
            return fd.read()

    @resource(uri='syn://storm/grammar', name='storm:grammar',
              desc='The raw Lark grammar defining the Storm query language syntax.', mimeType='text/x-lark')
    async def _resStormGrammar(self):
        return s_data.getLark('storm')

    @resource(uri='syn://model/form/{name}', name='form', desc='A single data model form definition.',
              completers={'name': 'model:forms'})
    async def _resForm(self, name):
        mdef = await self.getCore().getModelDict()
        form = mdef['forms'].get(name)
        if form is None:
            raise s_exc.JsonRpcError.init(RESOURCE_NOT_FOUND, f'No such form: {name}',
                                          data={'uri': f'syn://model/form/{name}'})

        return form

    # --- completers ---

    @completer(name='model:forms')
    async def _completeForms(self, value, context):
        return await self.getCore().getFormsByPrefix(value)
