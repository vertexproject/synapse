import json
import base64
import asyncio
import logging

from urllib.parse import urlparse

import tornado.web as t_web
import tornado.websocket as t_websocket

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class Sess(s_base.Base):

    async def __anit__(self, cell, iden, info):

        await s_base.Base.__anit__(self)

        self.user = None
        self.socks = set()

        self.cell = cell

        # for transient session info
        self.locl = {}

        # for persistent session info
        self.iden = iden
        self.info = info

        user = self.info.get('user')
        if user is not None:
            self.user = self.cell.auth.user(user)

    async def set(self, name, valu):
        await self.cell.setHttpSessInfo(self.iden, name, valu)
        self.info[name] = valu

    async def update(self, vals: dict):
        await self.cell.updateHttpSessInfo(self.iden, vals)
        for name, valu in vals.items():
            self.info[name] = valu

    async def login(self, user):
        self.user = user
        await self.set('user', user.iden)
        await self.fire('sess:login')

    async def logout(self):
        self.user = None
        await self.set('user', None)
        await self.fire('sess:logout')

    def addWebSock(self, sock):
        self.socks.add(sock)

    def delWebSock(self, sock):
        self.socks.discard(sock)

class HandlerBase:

    def initialize(self, cell):
        self.cell = cell
        self._web_sess = None
        self._web_user = None  # Deprecated for new handlers
        self.web_useriden = None  # The user iden at the time of authentication.
        self.web_username = None  # The user name at the time of authentication.

        # this can't live in set_default_headers() due to call ordering in tornado
        headers = self.getCustomHeaders()
        if headers is not None:
            for name, valu in headers.items():
                self.add_header(name, valu)

    def getCustomHeaders(self):
        return self.cell.conf.get('https:headers')

    def set_default_headers(self):

        self.clear_header('Server')
        self.add_header('X-Content-Type-Options', 'nosniff')

        origin = self.request.headers.get('origin')
        if origin is not None and self.isOrigHost(origin):
            self.add_header('Access-Control-Allow-Origin', origin)
            self.add_header('Access-Control-Allow-Credentials', 'true')
            self.add_header('Access-Control-Allow-Headers', 'Content-Type')

    def getAuthCell(self):
        '''
        Return a reference to the cell used for auth operations.
        '''
        return self.cell

    def options(self):
        self.set_status(204)
        self.finish()

    def isOrigHost(self, origin):

        host = urlparse(origin).hostname

        hosttag = self.request.headers.get('host')
        if ':' in hosttag:
            hosttag, hostport = hosttag.split(':', 1)

        return host == hosttag

    def check_origin(self, origin):
        return self.isOrigHost(origin)

    def getJsonBody(self, validator=None):
        return self.loadJsonMesg(self.request.body, validator=validator)

    def sendRestErr(self, code, mesg):
        self.set_header('Content-Type', 'application/json')
        return self.write({'status': 'err', 'code': code, 'mesg': mesg})

    def sendRestExc(self, e):
        self.set_header('Content-Type', 'application/json')
        return self.sendRestErr(e.__class__.__name__, str(e))

    def sendRestRetn(self, valu):
        self.set_header('Content-Type', 'application/json')
        return self.write({'status': 'ok', 'result': valu})

    def loadJsonMesg(self, byts, validator=None):
        try:
            item = json.loads(byts)
            if validator is not None:
                validator(item)
            return item

        except s_exc.SchemaViolation as e:
            self.sendRestErr('SchemaViolation', str(e))
            return None

        except Exception:
            self.sendRestErr('SchemaViolation', 'Invalid JSON content.')
            return None

    def logAuthIssue(self, mesg=None, user=None, username=None, level=logging.WARNING):
        '''
        Helper to log issues related to request authentication.

        Args:
            mesg (str): Additional message to log.
            user (str): User iden, if available.
            username (str): Username, if available.
            level (int): Logging level to log the message at. Defaults to logging.WARNING.

        Returns:
            None
        '''
        uri = self.request.uri
        remote_ip = self.request.remote_ip
        enfo = {'uri': uri,
                'remoteip': remote_ip,
                }
        errm = f'Failed to authenticate request to {uri} from {remote_ip} '
        if mesg:
            errm = f'{errm}: {mesg}'
        if user:
            errm = f'{errm}: user={user}'
            enfo['user'] = user
        if username:
            errm = f'{errm} ({username})'
            enfo['username'] = username
        logger.log(level, msg=errm, extra={'synapse': enfo})

    def sendAuthRequired(self):
        self.set_header('WWW-Authenticate', 'Basic realm=synapse')
        self.set_status(401)
        self.sendRestErr('NotAuthenticated', 'The session is not logged in.')

    async def reqAuthUser(self):
        if await self.authenticated():
            return True
        self.sendAuthRequired()
        return False

    async def isUserAdmin(self):
        '''
        Check if the current authenticated user is an admin or not.

        Returns:
            bool: True if the user is an admin, false otherwise.
        '''
        iden = await self.useriden()
        if iden is None:
            return False

        authcell = self.getAuthCell()
        udef = await authcell.getUserDef(iden, packroles=False)
        if not udef.get('admin'):
            return False

        return True

    async def reqAuthAdmin(self):
        '''
        Require the current authenticated user to be an admin.

        Notes:
            If this returns False, an error message has already been sent
            and no additional processing for the request should be done.

        Returns:
            bool: True if the user is an admin, false otherwise.
        '''
        iden = await self.useriden()
        if iden is None:
            self.sendAuthRequired()
            return False

        authcell = self.getAuthCell()
        udef = await authcell.getUserDef(iden, packroles=False)
        if not udef.get('admin'):
            self.sendRestErr('AuthDeny', f'User {self.web_useriden} ({self.web_username}) is not an admin.')
            return False

        return True

    async def sess(self, gen=True):
        '''
        Get the heavy Session object for the request.

        Args:
            gen (bool): If set to True, generate a new session if there is no sess cookie.

        Notes:
            This stores the identifier in the ``sess`` cookie for with a 14 day expiration, stored
            in the Cell.
            Valid requests with that ``sess`` cookie will resolve to the same Session object.

        Returns:
            Sess: A heavy session object. If the sess cookie is invalid or gen is false, this returns None.
        '''

        if self._web_sess is None:

            iden = self.get_secure_cookie('sess', max_age_days=14)

            if iden is None:
                if gen:
                    iden = s_common.guid().encode()
                    opts = {'expires_days': 14, 'secure': True, 'httponly': True}
                    self.set_secure_cookie('sess', iden, **opts)
                else:
                    return None

            self._web_sess = await self.cell.genHttpSess(iden)

        return self._web_sess

    async def useriden(self):
        '''
        Get the user iden of the current session user.

        Note:
            This function will pull the iden from the current session, or
            attempt to resolve the useriden with basic authentication.

        Returns:
            str: The iden of the current session user.
        '''
        if self.web_useriden is not None:
            return self.web_useriden

        sess = await self.sess(gen=False)
        if sess is not None:
            iden = sess.info.get('user')
            name = sess.info.get('username', '<no username>')

            self.web_useriden = iden
            self.web_username = name

            return iden

        # Check for API Keys
        key = self.request.headers.get('X-API-KEY')
        if key is not None:
            return await self.handleApiKeyAuth()

        return await self.handleBasicAuth()

    async def handleBasicAuth(self):
        '''
        Handle basic authentication in the handler.

        Notes:
            Implementors may override this to disable or implement their own basic auth schemes.
            This is expected to set web_useriden and web_username upon successful authentication.

        Returns:
            str: The user iden of the logged in user.
        '''
        authcell = self.getAuthCell()

        auth = self.request.headers.get('Authorization')
        if auth is None:
            return None

        if not auth.startswith('Basic '):
            return None

        _, blob = auth.split(None, 1)

        try:
            text = base64.b64decode(blob).decode('utf8')
            name, passwd = text.split(':', 1)
        except Exception:
            logger.exception('invalid basic auth header')
            return None

        udef = await authcell.getUserDefByName(name)
        if udef is None:
            self.logAuthIssue(mesg='No such user.', username=name)
            return None

        if udef.get('locked'):
            self.logAuthIssue(mesg='User is locked.', user=udef.get('iden'), username=name)
            return None

        if not await authcell.tryUserPasswd(name, passwd):
            self.logAuthIssue(mesg='Incorrect password.', user=udef.get('iden'), username=name)
            return None

        self.web_useriden = udef.get('iden')
        self.web_username = udef.get('name')
        return self.web_useriden

    async def handleApiKeyAuth(self):
        authcell = self.getAuthCell()
        key = self.request.headers.get('X-API-KEY')
        isok, info = await authcell.checkUserApiKey(key)  # errfo or dict with tdef + udef
        if isok is False:
            self.logAuthIssue(mesg=info.get('mesg'), user=info.get('user'), username=info.get('name'))
            return

        udef = info.get('udef')

        self.web_useriden = udef.get('iden')
        self.web_username = udef.get('name')
        return self.web_useriden

    async def allowed(self, perm, default=False, gateiden=None):
        '''
        Check if the authenticated user has the given permission.

        Args:
            perm (tuple): The permission tuple to check.
            default (boolean): The default value for the permission.
            gateiden (str): The gateiden to check the permission against.

        Notes:
            This API sets up HTTP response values if it returns False.

        Returns:
            bool: True if the user has the requested permission.
        '''
        authcell = self.getAuthCell()

        useriden = await self.useriden()
        if useriden is None:
            self.sendAuthRequired()
            return False

        if await authcell.isUserAllowed(useriden, perm, gateiden=gateiden, default=default):
            return True

        self.set_status(403)

        mesg = f'User ({self.web_username}) must have permission {".".join(perm)}'
        if default:
            mesg = f'User ({self.web_username}) is denied the permission {".".join(perm)}'
        if gateiden:
            mesg = f'{mesg} on object {gateiden}'
        self.sendRestErr('AuthDeny', mesg)
        return False

    async def authenticated(self):
        '''
        Check if the request has an authenticated user or not.

        Returns:
            bool: True if the request has an authenticated user, false otherwise.
        '''
        return await self.useriden() is not None

    async def getUseridenBody(self, validator=None):
        '''
        Helper function to confirm that there is an auth user and a valid JSON body in the request.

        Args:
            validator: Validator function run on the deserialized JSON body.

        Returns:
            (str, object): The user definition and body of the request as deserialized JSON,
            or a tuple of s_common.novalu objects if there was no user or json body.
        '''
        if not await self.reqAuthUser():
            return (s_common.novalu, s_common.novalu)

        body = self.getJsonBody(validator=validator)
        if body is None:
            return (s_common.novalu, s_common.novalu)

        useriden = await self.useriden()
        return (useriden, body)

class WebSocket(HandlerBase, t_websocket.WebSocketHandler):

    async def xmit(self, name, **info):
        await self.write_message(json.dumps({'type': name, 'data': info}))

    async def _reqUserAllow(self, perm):

        iden = await self.useriden()
        if iden is None:
            mesg = 'Session is not authenticated.'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm)

        authcell = self.getAuthCell()
        if not await authcell.isUserAllowed(iden, perm):
            ptxt = '.'.join(perm)
            mesg = f'Permission denied: {ptxt}.'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm)

class Handler(HandlerBase, t_web.RequestHandler):

    def prepare(self):
        self.task = asyncio.current_task()

    def on_connection_close(self):
        if hasattr(self, 'task'):
            self.task.cancel()

    async def _reqValidOpts(self, opts):

        if opts is None:
            opts = {}

        useriden = await self.useriden()

        opts.setdefault('user', useriden)
        if opts.get('user') != useriden:
            if not await self.allowed(('impersonate',)):
                return None

        return opts

class RobotHandler(HandlerBase, t_web.RequestHandler):
    async def get(self):
        self.write('User-agent: *\n')
        self.write('Disallow: /\n')

@t_web.stream_request_body
class StreamHandler(Handler):
    '''
    Subclass for Tornado streaming uploads.

    Notes:
        - Async method prepare() is called after headers are read but before body processing.
        - Sync method on_finish() can be used to cleanup after a request.
        - Sync method on_connection_close() can be used to cleanup after a client disconnect.
        - Async methods post(), put(), etc are called after the streaming has completed.
    '''

    async def data_received(self, chunk):
        raise s_exc.NoSuchImpl(mesg='data_received must be implemented by subclasses.',
                               name='data_received')

class StormHandler(Handler):

    def getCore(self):
        # add an abstraction to allow subclasses to dictate how
        # a reference to the cortex is returned from the handler.
        return self.cell

class StormNodesV1(StormHandler):

    async def post(self):
        return await self.get()

    async def get(self):

        user, body = await self.getUseridenBody()
        if body is s_common.novalu:
            return

        s_common.deprecated('HTTP API /api/v1/storm/nodes', curv='2.110.0')

        # dont allow a user to be specified
        opts = body.get('opts')
        query = body.get('query')
        stream = body.get('stream')
        jsonlines = stream == 'jsonlines'

        opts = await self._reqValidOpts(opts)
        if opts is None:
            return

        view = self.cell._viewFromOpts(opts)

        taskinfo = {'query': query, 'view': view.iden}
        await self.cell.boss.promote('storm', user=user, info=taskinfo)

        async for pode in view.iterStormPodes(query, opts=opts):
            self.write(json.dumps(pode))
            if jsonlines:
                self.write("\n")
            await self.flush()

class StormV1(StormHandler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        body = self.getJsonBody()
        if body is None:
            return

        opts = body.get('opts')
        query = body.get('query')
        stream = body.get('stream')
        jsonlines = stream == 'jsonlines'

        # Maintain backwards compatibility with 0.1.x output
        opts = await self._reqValidOpts(opts)
        if opts is None:
            return

        opts.setdefault('editformat', 'nodeedits')

        async for mesg in self.getCore().storm(query, opts=opts):
            self.write(json.dumps(mesg))
            if jsonlines:
                self.write("\n")
            await self.flush()

class StormCallV1(StormHandler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        body = self.getJsonBody()
        if body is None:
            return

        opts = body.get('opts')
        query = body.get('query')

        opts = await self._reqValidOpts(opts)
        if opts is None:
            return

        try:
            ret = await self.getCore().callStorm(query, opts=opts)
        except s_exc.SynErr as e:
            mesg = e.get('mesg', str(e))
            return self.sendRestErr(e.__class__.__name__, mesg)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            mesg = str(e)
            return self.sendRestErr(e.__class__.__name__, mesg)
        else:
            return self.sendRestRetn(ret)

class StormExportV1(StormHandler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        body = self.getJsonBody()
        if body is None:
            return

        opts = body.get('opts')
        query = body.get('query')

        opts = await self._reqValidOpts(opts)
        if opts is None:
            return

        try:
            self.set_header('Content-Type', 'application/x-synapse-nodes')
            async for pode in self.getCore().exportStorm(query, opts=opts):
                self.write(s_msgpack.en(pode))
                await self.flush()

        except Exception as e:
            return self.sendRestExc(e)

class ReqValidStormV1(StormHandler):

    async def post(self):
        return await self.get()

    async def get(self):

        _, body = await self.getUseridenBody()
        if body is s_common.novalu:
            return

        opts = body.get('opts', {})
        query = body.get('query')

        try:
            valid = await self.cell.reqValidStorm(query, opts)
        except s_exc.SynErr as e:
            mesg = e.get('mesg', str(e))
            return self.sendRestErr(e.__class__.__name__, mesg)
        else:
            return self.sendRestRetn(valid)

class BeholdSockV1(WebSocket):

    async def onInitMessage(self, byts):
        try:
            mesg = json.loads(byts)
            if mesg.get('type') != 'call:init':
                raise s_exc.BadMesgFormat('Invalid initial message')

            admin = await self.isUserAdmin()
            if not admin:
                await self.xmit('errx', code='AuthDeny', mesg='Beholder API requires admin privs')
                return

            async with self.cell.beholder() as beholder:

                await self.xmit('init')

                async for mesg in beholder:
                    await self.xmit('iter', **mesg)

                await self.xmit('fini')

        except s_exc.SynErr as e:
            text = e.get('mesg', str(e))
            await self.xmit('errx', code=e.__class__.__name__, mesg=text)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception as e:
            await self.xmit('errx', code=e.__class__.__name__, mesg=str(e))

    async def on_message(self, byts):
        self.cell.schedCoro(self.onInitMessage(byts))

class LoginV1(Handler):

    async def post(self):

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('user')
        passwd = body.get('passwd')

        authcell = self.getAuthCell()
        udef = await authcell.getUserDefByName(name)
        if udef is None:
            self.logAuthIssue(mesg='No such user.', username=name)
            return self.sendRestErr('AuthDeny', 'No such user.')

        if udef.get('locked'):
            self.logAuthIssue(mesg='User is locked.', user=udef.get('iden'), username=name)
            return self.sendRestErr('AuthDeny', 'User is locked.')

        if not await authcell.tryUserPasswd(name, passwd):
            self.logAuthIssue(mesg='Incorrect password.', user=udef.get('iden'), username=name)
            return self.sendRestErr('AuthDeny', 'Incorrect password.')

        iden = udef.get('iden')
        sess = await self.sess()
        await sess.set('user', iden)
        await sess.set('username', name)
        await sess.fire('sess:login')
        self.web_useriden = iden
        self.web_username = name

        return self.sendRestRetn(await authcell.getUserDef(iden))

class LogoutV1(Handler):

    async def get(self):
        sess = await self.sess(gen=False)
        if sess is not None:
            self.web_useriden = sess.info.get('user')
            self.web_username = sess.info.get('username', '<no username>')
            await self.getAuthCell().delHttpSess(sess.iden)

        self.clear_cookie('sess')

        self.sendRestRetn(True)

class AuthUsersV1(Handler):

    async def get(self):

        if not await self.reqAuthUser():
            return

        try:

            archived = int(self.get_argument('archived', default='0'))
            if archived not in (0, 1):
                return self.sendRestErr('BadHttpParam', 'The parameter "archived" must be 0 or 1 if specified.')

        except Exception:
            return self.sendRestErr('BadHttpParam', 'The parameter "archived" must be 0 or 1 if specified.')

        users = await self.getAuthCell().getUserDefs()

        if not archived:
            users = [udef for udef in users if not udef.get('archived')]

        self.sendRestRetn(users)

        return

class AuthRolesV1(Handler):

    async def get(self):

        if not await self.reqAuthUser():
            return

        self.sendRestRetn(await self.getAuthCell().getRoleDefs())

class AuthUserV1(Handler):

    async def get(self, iden):

        if not await self.reqAuthUser():
            return

        udef = await self.getAuthCell().getUserDef(iden, packroles=False)
        if udef is None:
            self.sendRestErr('NoSuchUser', f'User {iden} does not exist.')
            return

        self.sendRestRetn(udef)

    async def post(self, iden):

        # TODO allow user to change their own name / email via this API
        if not await self.reqAuthAdmin():
            return

        authcell = self.getAuthCell()

        udef = await authcell.getUserDef(iden)
        if udef is None:
            self.sendRestErr('NoSuchUser', f'User {iden} does not exist.')
            return

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('name')
        if name is not None:
            await authcell.setUserName(iden, name=name)

        email = body.get('email')
        if email is not None:
            await authcell.setUserEmail(iden, email)

        locked = body.get('locked')
        if locked is not None:
            await authcell.setUserLocked(iden, bool(locked))

        rules = body.get('rules')
        if rules is not None:
            await authcell.setUserRules(iden, rules, gateiden=None)

        admin = body.get('admin')
        if admin is not None:
            await authcell.setUserAdmin(iden, bool(admin), gateiden=None)

        archived = body.get('archived')
        if archived is not None:
            await authcell.setUserArchived(iden, bool(archived))

        self.sendRestRetn(await authcell.getUserDef(iden, packroles=False))

class AuthUserPasswdV1(Handler):

    async def post(self, iden):

        current_user, body = await self.getUseridenBody()
        if body is s_common.novalu:
            return

        authcell = self.getAuthCell()
        udef = await authcell.getUserDef(iden)
        if udef is None:
            self.sendRestErr('NoSuchUser', f'User does not exist: {iden}')
            return

        password = body.get('passwd')

        cdef = await authcell.getUserDef(current_user)
        if cdef.get('admin') or cdef.get('iden') == udef.get('iden'):
            try:
                await authcell.setUserPasswd(iden, password)
            except s_exc.BadArg as e:
                self.sendRestErr('BadArg', e.get('mesg'))
                return
        self.sendRestRetn(await authcell.getUserDef(iden, packroles=False))

class AuthRoleV1(Handler):

    async def get(self, iden):

        if not await self.reqAuthUser():
            return

        rdef = await self.getAuthCell().getRoleDef(iden)
        if rdef is None:
            self.sendRestErr('NoSuchRole', f'Role {iden} does not exist.')
            return

        self.sendRestRetn(rdef)

    async def post(self, iden):

        if not await self.reqAuthAdmin():
            return

        authcell = self.getAuthCell()
        rdef = await authcell.getRoleDef(iden)
        if rdef is None:
            self.sendRestErr('NoSuchRole', f'Role {iden} does not exist.')
            return

        body = self.getJsonBody()
        if body is None:
            return

        rules = body.get('rules')
        if rules is not None:
            await authcell.setRoleRules(iden, rules, gateiden=None)

        self.sendRestRetn(await authcell.getRoleDef(iden))

class AuthGrantV1(Handler):
    '''
    /api/v1/auth/grant?user=iden&role=iden
    '''
    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        useriden = body.get('user')
        authcell = self.getAuthCell()
        udef = await authcell.getUserDef(useriden)
        if udef is None:
            self.sendRestErr('NoSuchUser', f'User iden {useriden} not found.')
            return

        roleiden = body.get('role')
        rdef = await authcell.getRoleDef(roleiden)
        if rdef is None:
            self.sendRestErr('NoSuchRole', f'Role iden {roleiden} not found.')
            return

        await authcell.addUserRole(useriden, roleiden)
        self.sendRestRetn(await authcell.getUserDef(useriden, packroles=False))

        return

class AuthRevokeV1(Handler):
    '''
    /api/v1/auth/grant?user=iden&role=iden
    '''
    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        useriden = body.get('user')
        authcell = self.getAuthCell()
        udef = await authcell.getUserDef(useriden)
        if udef is None:
            self.sendRestErr('NoSuchUser', f'User iden {useriden} not found.')
            return

        roleiden = body.get('role')
        rdef = await authcell.getRoleDef(roleiden)
        if rdef is None:
            self.sendRestErr('NoSuchRole', f'Role iden {roleiden} not found.')
            return

        await authcell.delUserRole(useriden, roleiden)
        self.sendRestRetn(await authcell.getUserDef(useriden, packroles=False))

        return

class AuthAddUserV1(Handler):

    async def post(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('name')
        if name is None:
            self.sendRestErr('MissingField', 'The adduser API requires a "name" argument.')
            return

        authcell = self.getAuthCell()
        if await authcell.getUserDefByName(name) is not None:
            self.sendRestErr('DupUser', f'A user named {name} already exists.')
            return

        udef = await authcell.addUser(name=name)
        iden = udef.get('iden')

        passwd = body.get('passwd', None)
        if passwd is not None:
            await authcell.setUserPasswd(iden, passwd)

        admin = body.get('admin', None)
        if admin is not None:
            await authcell.setUserAdmin(iden, bool(admin))

        email = body.get('email', None)
        if email is not None:
            await authcell.setUserEmail(iden, email)

        rules = body.get('rules')
        if rules is not None:
            await authcell.setUserRules(iden, rules, gateiden=None)

        udef = await authcell.getUserDef(iden, packroles=False)

        self.sendRestRetn(udef)
        return

class AuthAddRoleV1(Handler):

    async def post(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('name')
        if name is None:
            self.sendRestErr('MissingField', 'The addrole API requires a "name" argument.')
            return

        authcell = self.getAuthCell()
        if await authcell.getRoleDefByName(name) is not None:
            self.sendRestErr('DupRole', f'A role named {name} already exists.')
            return

        rdef = await authcell.addRole(name)
        iden = rdef.get('iden')

        rules = body.get('rules', None)
        if rules is not None:
            await authcell.setRoleRules(iden, rules, gateiden=None)

        self.sendRestRetn(await authcell.getRoleDef(iden))
        return

class AuthDelRoleV1(Handler):

    async def post(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('name')
        if name is None:
            self.sendRestErr('MissingField', 'The delrole API requires a "name" argument.')
            return

        authcell = self.getAuthCell()
        rdef = await authcell.getRoleDefByName(name)
        if rdef is None:
            return self.sendRestErr('NoSuchRole', f'The role {name} does not exist!')

        await authcell.delRole(rdef.get('iden'))

        self.sendRestRetn(None)
        return

class ModelNormV1(Handler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        body = self.getJsonBody()
        if body is None:
            return

        propname = body.get('prop')
        propvalu = body.get('value')

        if propname is None:
            self.sendRestErr('MissingField', 'The property normalization API requires a prop name.')
            return

        try:
            valu, info = await self.cell.getPropNorm(propname, propvalu)
        except s_exc.NoSuchProp:
            return self.sendRestErr('NoSuchProp', 'The property {propname} does not exist.')
        except Exception as e:
            return self.sendRestExc(e)
        else:
            self.sendRestRetn({'norm': valu, 'info': info})

class ModelV1(Handler):

    async def get(self):

        if not await self.reqAuthUser():
            return

        resp = await self.cell.getModelDict()
        return self.sendRestRetn(resp)

class HealthCheckV1(Handler):

    async def get(self):
        if not await self.allowed(('health', )):
            return
        resp = await self.cell.getHealthCheck()
        return self.sendRestRetn(resp)

class ActiveV1(Handler):

    async def get(self):
        resp = {'active': self.cell.isactive}
        return self.sendRestRetn(resp)

class StormVarsGetV1(Handler):

    async def get(self):

        body = self.getJsonBody()
        if body is None:
            return

        varname = str(body.get('name'))
        defvalu = body.get('default')

        if not await self.allowed(('globals', 'get', varname)):
            return

        valu = await self.cell.getStormVar(varname, default=defvalu)
        return self.sendRestRetn(valu)

class StormVarsPopV1(Handler):

    async def post(self):

        body = self.getJsonBody()
        if body is None:
            return

        varname = str(body.get('name'))
        defvalu = body.get('default')

        if not await self.allowed(('globals', 'pop', varname)):
            return

        valu = await self.cell.popStormVar(varname, default=defvalu)
        return self.sendRestRetn(valu)

class StormVarsSetV1(Handler):

    async def post(self):

        body = self.getJsonBody()
        if body is None:
            return

        varname = str(body.get('name'))
        varvalu = body.get('value', s_common.novalu)
        if varvalu is s_common.novalu:
            return self.sendRestErr('BadArg', 'The "value" field is required.')

        if not await self.allowed(('globals', 'set', varname)):
            return

        await self.cell.setStormVar(varname, varvalu)
        return self.sendRestRetn(True)

class OnePassIssueV1(Handler):
    '''
    /api/v1/auth/onepass/issue
    '''
    async def post(self):

        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody()
        if body is None:
            return

        iden = body.get('user')
        duration = body.get('duration', 600000)
        authcell = self.getAuthCell()
        try:
            passwd = await authcell.genUserOnepass(iden, duration)
        except s_exc.NoSuchUser:
            return self.sendRestErr('NoSuchUser', 'The user iden does not exist.')

        return self.sendRestRetn(passwd)

class FeedV1(Handler):
    '''
    /api/v1/feed

    Examples:

        Example data::

            {
                'name': 'syn.nodes',
                'view': null,
                'items': [...],
            }
    '''
    async def post(self):
        # Note: This API handler is intended to be used on a heavy Cortex object.

        if not await self.reqAuthUser():
            return

        body = self.getJsonBody()
        if body is None:
            return

        items = body.get('items')
        name = body.get('name', 'syn.nodes')

        func = self.cell.getFeedFunc(name)
        if func is None:
            return self.sendRestErr('NoSuchFunc', f'The feed type {name} does not exist.')

        user = self.cell.auth.user(self.web_useriden)

        view = self.cell.getView(body.get('view'), user)
        if view is None:
            return self.sendRestErr('NoSuchView', 'The specified view does not exist.')

        wlyr = view.layers[0]
        perm = ('feed:data', *name.split('.'))

        if not user.allowed(perm, gateiden=wlyr.iden):
            permtext = '.'.join(perm)
            mesg = f'User does not have {permtext} permission on gate: {wlyr.iden}.'
            return self.sendRestErr('AuthDeny', mesg)

        try:

            info = {'name': name, 'view': view.iden, 'nitems': len(items)}
            await self.cell.boss.promote('feeddata', user=user, info=info)

            async with await self.cell.snap(user=user, view=view) as snap:
                snap.strict = False
                await snap.addFeedData(name, items)

            return self.sendRestRetn(None)

        except Exception as e:  # pragma: no cover
            return self.sendRestExc(e)

class CoreInfoV1(Handler):
    '''
    /api/v1/core/info
    '''

    async def get(self):

        if not await self.reqAuthUser():
            return

        resp = await self.cell.getCoreInfoV2()
        return self.sendRestRetn(resp)

class ExtApiHandler(StormHandler):
    '''
    /api/ext/.*
    '''

    storm_prefix = 'init { $request = $lib.cortex.httpapi.response($_http_request_info) }'

    # Disables the etag header from being computed and set. It is too much magic for
    # a user defined API to utilize.
    def compute_etag(self):
        return None

    def set_default_headers(self):
        self.clear_header('Server')

    async def get(self, path):
        return await self._runHttpExt('get', path)

    async def head(self, path):
        return await self._runHttpExt('head', path)

    async def post(self, path):
        return await self._runHttpExt('post', path)

    async def put(self, path):
        return await self._runHttpExt('put', path)

    async def delete(self, path):
        return await self._runHttpExt('delete', path)

    async def patch(self, path):
        return await self._runHttpExt('patch', path)

    async def options(self, path):
        return await self._runHttpExt('options', path)

    async def _runHttpExt(self, meth, path):
        core = self.getCore()
        adef, args = await core.getHttpExtApiByPath(path)
        if adef is None:
            self.set_status(404)
            self.sendRestErr('NoSuchPath', f'No Extended HTTP API endpoint matches {path}')
            return await self.finish()

        requester = ''
        iden = adef.get("iden")
        useriden = adef.get('owner')

        if adef.get('authenticated'):

            requester = await self.useriden()

            if requester is None:
                await self.reqAuthUser()
                return

            for pdef in adef.get('perms'):
                if not await self.allowed(pdef.get('perm'), default=pdef.get('default')):
                    return

            if adef.get('runas') == 'user':
                useriden = requester

        storm = adef['methods'].get(meth)
        if storm is None:
            self.set_status(405)
            meths = [meth.upper() for meth in adef.get('methods')]
            self.set_header('Allowed', ', '.join(meths))
            mesg = f'Extended HTTP API {iden} has no method for {meth.upper()}.'
            if meths:
                mesg = f'{mesg} Supports {", ".join(meths)}.'
            self.sendRestErr('NeedConfValu', mesg)
            return await self.finish()

        # We flatten the request headers and parameters into a flat key/valu map.
        # The first instance of a given key wins.
        request_headers = {}
        for key, valu in self.request.headers.get_all():
            request_headers.setdefault(key.lower(), valu)

        params = {}
        for key, valus in self.request.query_arguments.items():
            for valu in valus:
                params.setdefault(key, valu.decode())

        info = {
            'uri': self.request.uri,
            'body': self.request.body,
            'iden': iden,
            'path': path,
            'user': requester,
            'method': self.request.method,
            'params': params,
            'headers': request_headers,
            'args': args,
            'client': self.request.remote_ip,
        }

        varz = adef.get('vars')
        varz['_http_request_info'] = info

        opts = {
            'readonly': adef.get('readonly'),
            'show': (
                'http:resp:body',
                'http:resp:code',
                'http:resp:headers',
            ),
            'user': useriden,
            'vars': varz,
            'view': adef.get('view'),
        }

        query = '\n'.join((self.storm_prefix, storm))

        rcode = False
        rbody = False

        try:
            async for mtyp, info in core.storm(query, opts=opts):
                if mtyp == 'http:resp:code':
                    if rbody:
                        # We've already flushed() the stream at this point, so we cannot
                        # change the status code or the response headers. We just have to
                        # log the error and move along.
                        mesg = f'Extended HTTP API {iden} tried to set code after sending body.'
                        logger.error(mesg)
                        continue

                    rcode = True
                    self.set_status(info['code'])

                elif mtyp == 'http:resp:headers':
                    if rbody:
                        # We've already flushed() the stream at this point, so we cannot
                        # change the status code or the response headers. We just have to
                        # log the error and move along.
                        mesg = f'Extended HTTP API {iden} tried to set headers after sending body.'
                        logger.error(mesg)
                        continue
                    for hkey, hval in info['headers'].items():
                        self.set_header(hkey, hval)

                elif mtyp == 'http:resp:body':
                    if not rcode:
                        self.clear()
                        self.set_status(500)
                        self.sendRestErr('StormRuntimeError',
                                         f'Extended HTTP API {iden} must set status code before sending body.')
                        return await self.finish()
                    rbody = True
                    body = info['body']
                    self.write(body)
                    await self.flush()

                elif mtyp == 'err':
                    errname, erfo = info
                    mesg = f'Error executing Extended HTTP API {iden}: {errname} {erfo.get("mesg")}'
                    logger.error(mesg)
                    if rbody:
                        # We've already flushed() the stream at this point, so we cannot
                        # change the status code or the response headers. We just have to
                        # log the error and move along.
                        continue

                    # Since we haven't flushed the body yet, we can clear the handler
                    # and send the error the user.
                    self.clear()
                    self.set_status(500)
                    self.sendRestErr(errname, erfo.get('mesg'))
                    rcode = True
                    rbody = True

        except Exception as e:
            rcode = True
            enfo = s_common.err(e)
            logger.exception(f'Extended HTTP API {iden} encountered fatal error: {enfo[1].get("mesg")}')
            if rbody is False:
                self.clear()
                self.set_status(500)
                self.sendRestErr(enfo[0],
                                 f'Extended HTTP API {iden} encountered fatal error: {enfo[1].get("mesg")}')

        if rcode is False:
            self.clear()
            self.set_status(500)
            self.sendRestErr('StormRuntimeError', f'Extended HTTP API {iden} never set status code.')

        await self.finish()
