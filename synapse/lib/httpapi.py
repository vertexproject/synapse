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

logger = logging.getLogger(__name__)

class Sess(s_base.Base):

    async def __anit__(self, cell, iden):

        await s_base.Base.__anit__(self)

        self.user = None
        self.socks = set()

        self.cell = cell

        # for transient session info
        self.locl = {}

        # for persistent session info
        self.info = cell._getSessInfo(iden)

        user = self.info.get('user')
        if user is not None:
            self.user = self.cell.auth.user(user)

    async def login(self, user):
        self.user = user
        self.info.set('user', user.iden)
        await self.fire('sess:login')

    async def logout(self):
        self.user = None
        self.info.set('user', None)
        await self.fire('sess:logout')

    def addWebSock(self, sock):
        self.socks.add(sock)

    def delWebSock(self, sock):
        self.socks.discard(sock)

class HandlerBase:

    httpsonly = False

    def initialize(self, cell):
        self.cell = cell
        self._web_sess = None
        self._web_user = None

        if (self.httpsonly or self.cell.httpsonly) and self.request.protocol != 'https':
            self.redirect('https://' + self.request.host, permanent=False)

    def set_default_headers(self):
        origin = self.request.headers.get('origin')
        if origin is not None and self.isOrigHost(origin):
            self.add_header('Access-Control-Allow-Origin', origin)
            self.add_header('Access-Control-Allow-Credentials', 'true')
            self.add_header('Access-Control-Allow-Headers', 'Content-Type')

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

    def getJsonBody(self):
        return self.loadJsonMesg(self.request.body)

    def sendRestErr(self, code, mesg):
        return self.write({'status': 'err', 'code': code, 'mesg': mesg})

    def sendRestExc(self, e):
        return self.sendRestErr(e.__class__.__name__, str(e))

    def sendRestRetn(self, valu):
        return self.write({'status': 'ok', 'result': valu})

    def loadJsonMesg(self, byts):
        try:
            return json.loads(byts)
        except Exception:
            self.sendRestErr('BadJson', 'Invalid JSON content.')
            return None

    def sendAuthReqired(self):
        self.set_header('WWW-Authenticate', 'Basic realm=synapse')
        self.set_status(401)
        self.sendRestErr('NotAuthenticated', 'The session is not logged in.')

    async def reqAuthUser(self):
        if await self.authenticated():
            return True
        self.sendAuthReqired()
        return False

    async def reqAuthAdmin(self):

        if self.cell.insecure:
            return True

        user = await self.user()
        if user is None:
            self.sendAuthReqired()
            return False

        if not user.admin:
            self.sendRestErr('AuthDeny', f'User {user.iden} ({user.name}) is not an admin.')
            return False

        return True

    async def reqAuthAllowed(self, *path):
        '''
        Helper method that subclasses can use for user permission checking.

        Args:
            *path: Permission path components to check.

        Notes:
            This will call reqAuthUser() to ensure that there is a valid user.
            If the cell is insecure, this will return True.  If this returns
            False, the handler should return since the the status code and
            resulting error message will already have been sent.

        Examples:

            Define a handler which checks for ``syn:test`` permission::

                class ReqAuthHandler(s_httpapi.Handler):
                    async def get(self):
                        if not await self.reqAuthAllowed('syn:test'):
                            return
                     return self.sendRestRetn({'data': 'everything is awesome!'})

        Returns:
            bool: True if the user is allowed; False if the user is not allowed.

        Raises:
            s_exc.AuthDeny: If the permission is not allowed.

        '''
        if self.cell.insecure:  # pragma: no cover
            return True

        if not await self.reqAuthUser():
            return False

        user = await self.user()
        if not user.allowed(path):
            mesg = f'User {user.iden} ({user.name}) must have permission {".".join(path)}'
            self.sendRestErr('AuthDeny', mesg)
            return False
        return True

    async def sess(self, gen=True):

        if self._web_sess is None:

            iden = self.get_secure_cookie('sess')

            if iden is None and not gen:
                return None

            if iden is None:
                iden = s_common.guid().encode()
                opts = {'expires_days': 14, 'secure': True, 'httponly': True}
                self.set_secure_cookie('sess', iden, **opts)

            self._web_sess = await self.cell.genHttpSess(iden)

        return self._web_sess

    async def user(self):

        if self._web_user is not None:
            return self._web_user

        sess = await self.sess(gen=False)
        if sess is not None:
            return sess.user

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

        user = self.cell.auth.getUserByName(name)
        if user is None:
            return None

        if user.locked:
            return None

        if not user.tryPasswd(passwd):
            return None

        self._web_user = user
        return user

    async def username(self):
        user = await self.user()
        if user is not None:
            return user.name

    async def authenticated(self):
        if self.cell.insecure:
            return True
        return await self.user() is not None

class WebSocket(HandlerBase, t_websocket.WebSocketHandler):

    async def xmit(self, name, **info):
        await self.write_message(json.dumps({'type': name, 'data': info}))

    async def _reqUserAllow(self, perm):

        user = await self.user()
        if user is None:
            mesg = 'Session is not authenticated.'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm)

        if not user.allowed(perm):
            ptxt = '.'.join(perm)
            mesg = f'Permission denied: {ptxt}.'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm)

class Handler(HandlerBase, t_web.RequestHandler):
    pass

class StormNodesV1(Handler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        user = await self.user()

        body = self.getJsonBody()
        if body is None:
            return

        # dont allow a user to be specified
        opts = body.get('opts')
        query = body.get('query')

        await self.cell.boss.promote('storm', user=user, info={'query': query})

        async for pode in self.cell.iterStormPodes(query, opts=opts, user=user):
            self.write(json.dumps(pode))
            await self.flush()

class StormV1(Handler):

    async def post(self):
        return await self.get()

    async def get(self):

        if not await self.reqAuthUser():
            return

        user = await self.user()
        body = self.getJsonBody()
        if body is None:
            return

        # dont allow a user to be specified
        opts = body.get('opts')
        query = body.get('query')

        await self.cell.boss.promote('storm', user=user, info={'query': query})

        async for mesg in self.cell.streamstorm(query, opts=opts, user=user):
            self.write(json.dumps(mesg))
            await self.flush()

class WatchSockV1(WebSocket):
    '''
    A web-socket based API endpoint for distributing cortex events.
    '''
    async def onWatchMesg(self, byts):

        try:

            wdef = json.loads(byts)
            iden = wdef.get('view', self.cell.view.iden)

            perm = ('watch', 'view', iden)
            await self._reqUserAllow(perm)

            async with self.cell.watcher(wdef) as watcher:

                await self.xmit('init')

                async for mesg in watcher:
                    await self.xmit(mesg[0], **mesg[1])

                # pragma: no cover
                # (this would only happen on slow-consumer)
                await self.xmit('fini')

        except s_exc.SynErr as e:

            text = e.get('mesg', str(e))
            await self.xmit('errx', code=e.__class__.__name__, mesg=text)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            await self.xmit('errx', code=e.__class__.__name__, mesg=str(e))

    async def on_message(self, byts):
        self.cell.schedCoro(self.onWatchMesg(byts))

class LoginV1(Handler):

    async def post(self):

        sess = await self.sess()

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('user')
        passwd = body.get('passwd')

        user = self.cell.auth.getUserByName(name)
        if user is None:
            return self.sendRestErr('AuthDeny', 'No such user.')

        if not user.tryPasswd(passwd):
            return self.sendRestErr('AuthDeny', 'Incorrect password.')

        await sess.login(user)

        return self.sendRestRetn(user.pack())

class AuthUsersV1(Handler):

    async def get(self):

        if not await self.reqAuthUser():
            return

        try:

            archived = int(self.get_argument('archived', default='0'))
            if archived not in (0, 1):
                return self.sendRestErr('BadHttpParam', 'The parameter "archived" must be 0 or 1 if specified.')

        except Exception as e:
            return self.sendRestErr('BadHttpParam', 'The parameter "archived" must be 0 or 1 if specified.')

        if archived:
            self.sendRestRetn([u.pack() for u in self.cell.auth.users()])
            return

        self.sendRestRetn([u.pack() for u in self.cell.auth.users() if not u.info.get('archived')])
        return

class AuthRolesV1(Handler):

    async def get(self):

        if not await self.reqAuthUser():
            return

        self.sendRestRetn([r.pack() for r in self.cell.auth.roles()])

class AuthUserV1(Handler):

    async def get(self, iden):

        if not await self.reqAuthUser():
            return

        user = self.cell.auth.user(iden)
        if user is None:
            self.sendRestErr('NoSuchUser', f'User {iden} does not exist.')
            return

        self.sendRestRetn(user.pack())

    async def post(self, iden):

        # TODO allow user to change their own name / email via this API
        if not await self.reqAuthAdmin():
            return

        user = self.cell.auth.user(iden)
        if user is None:
            self.sendRestErr('NoSuchUser', f'User {iden} does not exist.')
            return

        body = self.getJsonBody()
        if body is None:
            return

        name = body.get('name')
        if name is not None:
            await user.setName(str(name))

        email = body.get('email')
        if email is not None:
            await user.info.set('email', email)

        locked = body.get('locked')
        if locked is not None:
            await user.setLocked(bool(locked))

        rules = body.get('rules')
        if rules is not None:
            await user.setRules(rules)

        admin = body.get('admin')
        if admin is not None:
            await user.setAdmin(bool(admin))

        archived = body.get('archived')
        if archived is not None:
            await user.setArchived(bool(archived))

        self.sendRestRetn(user.pack())

class AuthUserPasswdV1(Handler):

    async def post(self, iden):

        if not await self.reqAuthUser():
            return
        current_user = await self.user()

        body = self.getJsonBody()
        if body is None:
            return

        user = self.cell.auth.user(iden)
        if user is None:
            self.sendRestErr('NoSuchUser', f'User does not exist: {iden}')
            return

        password = body.get('passwd')

        if current_user.admin or current_user.iden == user.iden:
            try:
                await user.setPasswd(password)
            except s_exc.BadArg as e:
                self.sendRestErr('BadArg', e.get('mesg'))
                return
        self.sendRestRetn(user.pack())

class AuthRoleV1(Handler):

    async def get(self, iden):

        if not await self.reqAuthUser():
            return

        role = self.cell.auth.role(iden)
        if role is None:
            self.sendRestErr('NoSuchRole', f'Role {iden} does not exist.')
            return

        self.sendRestRetn(role.pack())

    async def post(self, iden):

        if not await self.reqAuthAdmin():
            return

        role = self.cell.auth.role(iden)
        if role is None:
            self.sendRestErr('NoSuchRole', f'Role {iden} does not exist.')
            return

        body = self.getJsonBody()
        if body is None:
            return

        rules = body.get('rules')
        if rules is not None:
            await role.setRules(rules)

        self.sendRestRetn(role.pack())

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

        iden = body.get('user')
        user = self.cell.auth.user(iden)
        if user is None:
            self.sendRestErr('NoSuchUser', f'User iden {iden} not found.')
            return

        iden = body.get('role')
        role = self.cell.auth.role(iden)
        if role is None:
            self.sendRestErr('NoSuchRole', f'Role iden {iden} not found.')
            return

        await user.grantRole(role)

        self.sendRestRetn(user.pack())

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

        iden = body.get('user')
        user = self.cell.auth.user(iden)
        if user is None:
            self.sendRestErr('NoSuchUser', f'User iden {iden} not found.')
            return

        iden = body.get('role')
        role = self.cell.auth.role(iden)
        if role is None:
            self.sendRestErr('NoSuchRole', f'Role iden {iden} not found.')
            return

        await user.revokeRole(role)
        self.sendRestRetn(user.pack())

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

        if self.cell.auth.getUserByName(name) is not None:
            self.sendRestErr('DupUser', f'A user named {name} already exists.')
            return

        user = await self.cell.auth.addUser(name)

        passwd = body.get('passwd', None)
        if passwd is not None:
            await user.setPasswd(passwd)

        admin = body.get('admin', None)
        if admin is not None:
            await user.setAdmin(bool(admin))

        email = body.get('email', None)
        if email is not None:
            await user.info.set('email', email)

        rules = body.get('rules')
        if rules is not None:
            await user.setRules(rules)

        self.sendRestRetn(user.pack())
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

        if self.cell.auth.getRoleByName(name) is not None:
            self.sendRestErr('DupRole', f'A role named {name} already exists.')
            return

        role = await self.cell.auth.addRole(name)

        rules = body.get('rules', None)
        if rules is not None:
            await role.setRules(rules)

        self.sendRestRetn(role.pack())
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

        role = self.cell.auth.getRoleByName(name)
        if role is None:
            return self.sendRestErr('NoSuchRole', f'The role {name} does not exist!')

        await self.cell.auth.delRole(name)

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
        if not await self.reqAuthAllowed('health'):
            return
        resp = await self.cell.getHealthCheck()
        return self.sendRestRetn(resp)
