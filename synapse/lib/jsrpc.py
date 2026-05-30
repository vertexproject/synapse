'''
A reusable JSON-RPC 2.0 server implementation for the Synapse Tornado web server.

This module provides ``JsonRpcHandler``, a Tornado handler which exposes its own
``@s_jsrpc.method`` decorated methods as a JSON-RPC 2.0 endpoint. It is intentionally
generic: it knows nothing about any specific protocol built on top of it (such as MCP).

To use it, extend ``JsonRpcHandler``, implement the decorated methods directly, and mount
it on a Cell using the existing addHttpApi machinery::

    class FooApi(s_jsrpc.JsonRpcHandler):

        @s_jsrpc.method()
        async def echo(self, valu):
            return valu

    cell.addHttpApi('/api/v1/jsonrpc', FooApi, {'cell': cell})

The decorated methods may be plain (sync) functions, coroutine functions, or async
generator functions. Async generator methods may stream their results to the caller as
Server-Sent Events when the request carries an ``Accept: text/event-stream`` header.

The calling user is placed into the task local scope for the duration of dispatch, so a
method may recover it via ``s_scope.get('user')`` (in addition to the handler APIs).
'''
import asyncio
import inspect
import logging
from http import HTTPStatus

import synapse.exc as s_exc

import synapse.lib.json as s_json
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.httpapi as s_httpapi

logger = logging.getLogger(__name__)

# JSON-RPC 2.0 reserved error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Server defined error code (within the reserved -32000 to -32099 range) used to
# indicate that the calling user lacks the permission required by a method.
ACCESS_DENIED = -32000

def method(name=None, desc=None, params=None, returns=None, perm=None):
    '''
    Decorate a method to expose it as a remotely callable JSON-RPC method.

    Args:
        name (str): An optional JSON-RPC method name override. This allows names which are
            not valid python identifiers (e.g. ``tools/list``). Defaults to the function name.
        desc (str): A human readable description of the method.
        params (dict): An optional JSON Schema used to validate the request params.
        returns (dict): An optional JSON Schema describing the result for introspection.
        perm (tuple): An optional Synapse permission tuple the calling user must be allowed.

    Notes:
        Only methods decorated with this decorator are exposed; it is an opt-in allowlist.
    '''
    def wrap(func):
        func._jsrpc_method = {
            'name': name if name is not None else func.__name__,
            'desc': desc,
            'params': params,
            'returns': returns,
            'perm': perm,
            'genr': inspect.isasyncgenfunction(func),
        }
        return func

    return wrap

class JsonRpcHandler(s_httpapi.Handler):
    '''
    A Tornado handler which exposes its own decorated methods as a JSON-RPC 2.0 endpoint.

    Subclass this and implement methods decorated with ``@s_jsrpc.method``.
    '''
    @classmethod
    def getMethInfo(cls):
        '''
        Introspect the handler class and return its JSON-RPC method registry.

        Returns:
            dict: A mapping of JSON-RPC method name to ``{'attr': attrname, 'info': info,
            'validator': validator}`` where validator is a compiled params validator or None.
        '''
        meths = cls.__dict__.get('_syn_jsrpc_meths')
        if meths is not None:
            return meths

        meths = {}
        for attrname in dir(cls):

            attr = getattr(cls, attrname, None)
            if not callable(attr):
                continue

            info = getattr(attr, '_jsrpc_method', None)
            if info is None:
                continue

            validator = None
            if info.get('params') is not None:
                validator = s_config.getJsValidator(info.get('params'))

            meths[info.get('name')] = {'attr': attrname, 'info': info, 'validator': validator}

        cls._syn_jsrpc_meths = meths
        return meths

    @classmethod
    def descrMethods(cls):
        '''
        Return a JSON safe listing of the methods exposed by the handler class.

        This is intended for building higher level introspection or discovery APIs without
        coupling this module to any particular protocol.
        '''
        meths = cls.getMethInfo()

        retn = []
        for name in sorted(meths):
            info = meths.get(name).get('info')
            retn.append({
                'name': name,
                'desc': info.get('desc'),
                'params': info.get('params'),
                'returns': info.get('returns'),
            })

        return retn

    async def post(self):

        if not await self.reqAuthUser():
            return

        useriden = await self.useriden()
        user = self.getAuthCell().auth.user(useriden)

        try:
            mesg = s_json.loads(self.request.body)
        except Exception:
            exc = s_exc.JsonRpcError.init(PARSE_ERROR, 'Parse error')
            self._sendResp(self._errResp(None, exc))
            return

        with s_scope.enter({'user': user}):

            if isinstance(mesg, list):
                await self._handleBatch(mesg)
            else:
                await self._handleSingle(mesg)

    async def _handleSingle(self, req):

        kind, *rest = await self._dispatch(req, allow_stream=True)

        if kind == 'stream':
            reqid, agen = rest
            await self._streamSse(reqid, agen)
            return

        resp = rest[0]
        if resp is None:
            self.set_status(HTTPStatus.NO_CONTENT)
            return

        self._sendResp(resp)

    async def _handleBatch(self, batch):

        if len(batch) == 0:
            exc = s_exc.JsonRpcError.init(INVALID_REQUEST, 'Invalid Request')
            self._sendResp(self._errResp(None, exc))
            return

        resps = []
        for req in batch:
            kind, resp = await self._dispatch(req, allow_stream=False)
            if resp is not None:
                resps.append(resp)

        if not resps:
            self.set_status(HTTPStatus.NO_CONTENT)
            return

        self._sendResp(resps)

    async def _dispatch(self, req, allow_stream):
        '''
        Dispatch a single parsed JSON-RPC request object.

        Returns:
            tuple: Either ``('resp', obj_or_None)`` where obj is a JSON-RPC response
            object (or None to suppress a notification response), or
            ``('stream', reqid, agen)`` to stream an async generator to the caller.
        '''
        if not self._isValidReq(req):
            # The validity of the request is in question, so the id cannot be trusted and
            # the JSON-RPC spec requires the response id to be null.
            exc = s_exc.JsonRpcError.init(INVALID_REQUEST, 'Invalid Request')
            return ('resp', self._errResp(None, exc))

        hasid = 'id' in req
        reqid = req.get('id')
        name = req.get('method')
        params = req.get('params')

        try:
            entry = self.getMethInfo().get(name)
            if entry is None:
                raise s_exc.JsonRpcError.init(METHOD_NOT_FOUND, f'Method not found: {name}')

            args, kwargs = self._bindParams(params)

            meth = getattr(self, entry.get('attr'))
            try:
                inspect.signature(meth).bind(*args, **kwargs)
            except TypeError as e:
                raise s_exc.JsonRpcError.init(INVALID_PARAMS, f'Invalid params: {e}')

            validator = entry.get('validator')
            if validator is not None:
                try:
                    validator(params)
                except s_exc.SchemaViolation as e:
                    raise s_exc.JsonRpcError.init(INVALID_PARAMS, e.get('mesg', str(e)))

            perm = entry.get('info').get('perm')
            if perm is not None:
                user = s_scope.get('user')
                if user is None or not user.allowed(tuple(perm)):
                    mesg = f'Permission denied: {".".join(perm)}'
                    raise s_exc.JsonRpcError.init(ACCESS_DENIED, mesg, data={'perm': list(perm)})

            if entry.get('info').get('genr'):

                agen = meth(*args, **kwargs)

                if hasid and allow_stream and self._wantsStream():
                    return ('stream', reqid, agen)

                result = [item async for item in agen]

            else:
                result = meth(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result

        except s_exc.JsonRpcError as e:
            if not hasid:
                return ('resp', None)
            return ('resp', self._errResp(reqid, e))

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            logger.exception(f'jsonrpc method error: {name}')
            if not hasid:
                return ('resp', None)
            return ('resp', self._internalErrResp(reqid, e))

        if not hasid:
            return ('resp', None)

        return ('resp', {'jsonrpc': '2.0', 'id': reqid, 'result': result})

    def _isValidReq(self, req):

        if not isinstance(req, dict):
            return False

        if req.get('jsonrpc') != '2.0':
            return False

        if not isinstance(req.get('method'), str):
            return False

        if 'id' in req:
            reqid = req.get('id')
            if isinstance(reqid, bool) or not isinstance(reqid, (str, int, float, type(None))):
                return False

        return True

    def _bindParams(self, params):

        if params is None:
            return (), {}

        if isinstance(params, (list, tuple)):
            return tuple(params), {}

        if isinstance(params, dict):
            return (), dict(params)

        raise s_exc.JsonRpcError.init(INVALID_PARAMS, 'Params must be an array or object.')

    def _errResp(self, reqid, exc):

        err = {'code': exc.get('code'), 'message': exc.get('mesg')}

        data = exc.get('data')
        if data is not None:
            err['data'] = data

        return {'jsonrpc': '2.0', 'id': reqid, 'error': err}

    def _internalErrResp(self, reqid, exc):

        err = {'code': INTERNAL_ERROR, 'message': 'Internal error'}

        if isinstance(exc, s_exc.SynErr):
            err['message'] = exc.get('mesg', str(exc))
            data = self._safeData(exc.items())
            if data:
                err['data'] = data
        else:
            err['message'] = str(exc)

        return {'jsonrpc': '2.0', 'id': reqid, 'error': err}

    def _safeData(self, info):
        try:
            s_json.dumps(info)
            return info
        except Exception:
            return None

    def _wantsStream(self):
        return 'text/event-stream' in self.request.headers.get('Accept', '')

    def _sendResp(self, obj):
        self.set_header('Content-Type', 'application/json')
        self.write(s_json.dumps(obj))

    async def _streamSse(self, reqid, agen):

        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')

        try:
            async for item in agen:
                mesg = {'jsonrpc': '2.0', 'method': 'data', 'params': {'id': reqid, 'item': item}}
                await self._sendSse(mesg)

            resp = {'jsonrpc': '2.0', 'id': reqid, 'result': None}

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            logger.exception('jsonrpc stream error')
            resp = self._internalErrResp(reqid, e)

        await self._sendSse(resp)

    async def _sendSse(self, mesg):
        self.write(b'data: ')
        self.write(s_json.dumps(mesg))
        self.write(b'\n\n')
        await self.flush()
