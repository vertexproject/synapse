import os
import ssl
import asyncio
import logging
import threading

import tornado.web as t_web
import tornado.netutil as t_netutil
import tornado.httpserver as t_http

import synapse.exc as s_exc

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

'''
Base classes for the synapse "cell" microservice architecture.
'''
def adminapi(f):

    def func(*args, **kwargs):

        if args[0].user is None:
            raise s_exc.AuthDeny(mesg='Auth not enabled.')

        if not args[0].user.admin:
            raise s_exc.AuthDeny(mesg='User is not an admin.',
                                 user=args[0].user.name)

        logger.info('Executing [%s] as [%s] with args [%s][%s]',
                    f.__qualname__, args[0].user, args[1:], kwargs)

        return f(*args, **kwargs)

    return func

#class HttpEndp:

class HttpEndp:

    def initialize(self, cell):

        self.cell = cell
        #self.sess = None

        #iden = self.get_secure_cookie('sess')

        #if iden is not None:
            #iden = iden.decode('utf8')
            #self.sess = self.cell.sessions.gen(iden)

    async def sendJsonMesg(self, item):
        self.set_header('content-type', 'application/json')
        return await self.write(json.dumps(item))

    def loadJsonMesg(self, byts):
        try:
            return json.loads(byts)
        except Exception as e:
            logger.exception('invalid json message: %r' % (byts,))
            return None

#class Handler(Base, t_web.RequestHandler):

    #def options(self):
        #self.set_headers()
        #self.set_status(204)
        #self.finish()

    #def set_headers(self):

        #if self.cell.conf.get('devmode'):

            #origin = self.request.headers.get('origin')

            #if origin is not None:
                #self.add_header('Access-Control-Allow-Origin', origin)
                #self.add_header('Access-Control-Allow-Credentials', 'true')
                #self.add_header('Access-Control-Allow-Headers', 'Content-Type')


class HttpApi:
    '''
    The cell.yaml can configure this object via:

    httpapi:

        # the port to bind
        port: 8080

        # the IPv4/IPv6 to bind
        bind: 0.0.0.0

        # and optionally...
        #sslkey: /path/to/ssl/key.pem
        #sslcert: /path/to/ssl/cert.pem

    '''

    def __init__(self, cell):

        self.cell = cell

        conf = cell.conf.get('httpapi')
        if conf is None:
            conf = {}

        port = conf.get('port', 8080)
        bind = conf.get('bind', '0.0.0.0')

        sslkey = conf.get('sslkey')
        sslcert = conf.get('sslcert')

        #wwwroot = self.conf.get('wwwroot')
        #if not os.path.isdir(wwwroot):
            #raise Exception('Bad Web Root: %r' % (wwwroot,))

        # Set up SSL Context
        if sslkey is not None and sslcert is not None:
            sctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            sctx.load_cert_chain(sslcert, sslkey)

        #asyncio.set_event_loop(s_glob.plex.loop)

        #self.sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        #self.sslctx.load_cert_chain(certpath, keypath)

        #keypath = self.conf.get('sslkey')
        #if keypath is None:
            #keypath = s_common.reqpath(self.dirn, 'sslkey.pem')

        #certpath = self.conf.get('sslcert')
        #if certpath is None:
            #certpath = s_common.reqpath(self.dirn, 'sslcert.pem')

        #self.sslctx.load_cert_chain(certpath, keypath)

        # Generate/Load a Cookie Secret
        #secpath = os.path.join(self.dirn, 'httpapi', 'cookie.secret')
        #if not os.path.isfile(secpath):
            #with s_common.genfile(secpath) as fd:
                #fd.write(s_common.guid().encode('utf8'))

        opts = {
            'cookie_secret': self._getCookieSecret(),
            'websocket_ping_interval': 10
        }

        self.webapp = t_web.Application(**opts)

        opts = {'ssl_options': self.sslctx}
        self.httpserver = t_httpserver.HTTPServer(self.wapp, **opts)

        #port = self.conf.get('port')

        socks = t_netutil.bind_sockets(port, '0.0.0.0')
        self.webaddr = socks[0].getsockname()

        self.httpserver.add_sockets(socks)

        #self.webapp.add_handlers('.*', (
            #(r'/', r_handlers.IndexHandler, {'cell': self}),
            #(r'/auth/magic', r_handlers.MagicAuthHandler, {'cell': self}),
            #(r'/auth/logout', r_handlers.LogoutHandler, {'cell': self}),
            #(r'/ws', r_handlers.WebSocketHandler, {'cell': self}),
            #(r'/api/v1/eval', r_handlers.EvalV1Handler, {'cell': self}),
            #(r'/(.*)', t_web.StaticFileHandler, {'path': wwwroot}),

        #))

        #self.thr = s_common.firethread(self.loop.start())

    #def addHttpEndp(self, path, ctor):

    def _getCookieSecret(self):

        # Generate/Load a Cookie Secret
        secpath = os.path.join(self.cell.dirn, 'httpapi', 'cookie.secret')
        if not os.path.isfile(secpath):
            with s_common.genfile(secpath) as fd:
                fd.write(s_common.guid().encode('utf8'))

        return s_common.getfile(secpath).read().decode('utf8')

class CellHandler(t_web.RequestHandler):

    def initialize(self, cell):
        self.cell = cell

    async def sendRestReply(self, item):
        mesg = {'status': 'ok', 'result': item}
        await self.sendJsonReply(mesg)

    async def sendJsonReply(self, item):
        self.set_header('content-type', 'application/json')
        byts = json.dumps(item)
        self.write(byts)

class HttpCellStatus(CellHandler):

    async def get(self):
        status = await self.cell.getCellStatus()
        await self.sendJsonReply(status)

#class HttpModelApiV1(t_web.RequestHandler):

    #async def get(self):
        #self.set_header('content-type', 'application/json')
        #modl = self.core.model.getModelDict()
        #byts = json.dumps({'status': 'ok', 'result': modl})
        #self.write(byts)

class CellApi(s_base.Base):

    def __init__(self, cell, link):
        s_base.Base.__init__(self)
        self.cell = cell
        self.link = link
        self.user = link.get('cell:user')

    def getCellType(self):
        return self.cell.getCellType()

    def getCellIden(self):
        return self.cell.getCellIden()

    @adminapi
    def addAuthUser(self, name):
        self.cell.auth.addUser(name)

    @adminapi
    def addAuthRole(self, name):
        self.cell.auth.addRole(name)

    @adminapi
    def getAuthUsers(self):
        return self.cell.auth.getUsers()

    @adminapi
    def getAuthRoles(self):
        return self.cell.auth.getRoles()

    @adminapi
    def addAuthRule(self, name, rule, indx=None):
        item = self._getAuthItem(name)
        return item.addRule(rule, indx=indx)

    @adminapi
    def delAuthRule(self, name, indx):
        item = self._getAuthItem(name)
        return item.delRule(indx)

    @adminapi
    def setAuthAdmin(self, name, admin):
        '''
        Set the admin status of the given user/role.
        '''
        item = self._getAuthItem(name)
        item.setAdmin(admin)

    @adminapi
    def setUserPasswd(self, name, passwd):
        user = self.cell.auth.users.get(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        user.setPasswd(passwd)

    @adminapi
    def setUserLocked(self, name, locked):
        user = self.cell.auth.users.get(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        user.setLocked(locked)

    @adminapi
    def addUserRole(self, username, rolename):
        user = self.cell.auth.users.get(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        role = self.cell.auth.roles.get(rolename)
        if role is None:
            raise s_exc.NoSuchRole(role=rolename)

        user.addRole(rolename)

    @adminapi
    def delUserRole(self, username, rolename):

        user = self.cell.auth.users.get(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        role = self.cell.auth.roles.get(rolename)
        if role is None:
            raise s_exc.NoSuchRole(role=rolename)

        user.delRole(rolename)

    @adminapi
    def getAuthInfo(self, name):
        '''
        An admin only API endpoint for getting user info.
        '''
        item = self._getAuthItem(name)
        if item is None:
            return None

        return self._getAuthInfo(item)

    def _getAuthItem(self, name):
        # return user or role by name.
        user = self.cell.auth.users.get(name)
        if user is not None:
            return user

        role = self.cell.auth.roles.get(name)
        if role is not None:
            return role

        raise s_exc.NoSuchName(name=name)

    def _getAuthInfo(self, role):

        authtype = role.info.get('type')
        info = {
            'type': authtype,
            'admin': role.admin,
            'rules': role.info.get('rules', ()),
        }

        if authtype == 'user':
            info['locked'] = role.locked

            roles = []
            info['roles'] = roles

            for userrole in role.roles.values():
                roles.append(self._getAuthInfo(userrole))

        return (role.name, info)

bootdefs = (

    #('cell:name', {
        #'doc': 'Set the log/display name for this cell.'}),

    ('auth:en', {'defval': False,
        'doc': 'Set to True to enable auth for this cortex.'}),

    #('auth:required', {'defval': True,
        #'doc': 'If auth is enabled, allow non-auth connections.  Cell must manage perms.'})

    ('auth:admin', {'defval': None,
        'doc': 'Set to <user>:<passwd> (local only) to bootstrap an admin.'}),
)

class Cell(s_base.Base, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.
    '''
    cellapi = CellApi
    httpapi = HttpApi

    # config options that are in all cells...
    confbase = (
        ('http:en', {'defval': True,
            'doc': 'Enable the HTTP API for this cell.'}),

        ('http:port', {'defval': 0,
            'doc': 'The port for the HTTP API listener.'}),
    )

    confdefs = ()

    def __init__(self, dirn):

        s_base.Base.__init__(self)
        s_telepath.Aware.__init__(self)

        self.dirn = s_common.gendir(dirn)

        # used by the HTTP API subsystem
        self.webapp = None
        self.webaddr = None
        self.webserver = None

        self.cellfini = threading.Event()
        self.onfini(self.cellfini.set)

        self.auth = None

        # each cell has a guid
        path = s_common.genpath(dirn, 'cell.guid')

        # generate a guid file if needed
        if not os.path.isfile(path):
            with open(path, 'w') as fd:
                fd.write(s_common.guid())

        # read our guid file
        with open(path, 'r') as fd:
            self.iden = fd.read().strip()

        boot = self._loadCellYaml('boot.yaml')
        self.boot = s_common.config(boot, bootdefs)

        conf = self._loadCellYaml('cell.yaml')
        self.conf = s_common.config(conf, self.confdefs + self.confbase)

        self.cmds = {}

        self.cellname = self.boot.get('cell:name')
        if self.cellname is None:
            self.cellname = self.__class__.__name__

    async def __anit__(self):
        await self._initCellAuth()
        await self._initCellSlab()
        await self._initHttpApi()
        self.onfini(self._finiCellAsync)

    async def _initHttpApi(self):

        conf = self.conf.get('httpapi')
        if conf is None:
            return

        handlers = [
            ('/cell/status', HttpCellStatus, {'cell': self}),
        ]

        handlers.extend(self.getHttpHandlers())

        self.webapp = t_web.Application(handlers)

        port = conf.get('port', 8888)
        host = conf.get('host', 'localhost')

        socks = t_netutil.bind_sockets(port, host)

        self.webaddr = socks[0].getsockname()

        logger.debug('Starting webserver at [%r]', self.webaddr)

        self.webserver = t_http.HTTPServer(self.webapp)
        self.webserver.add_sockets(socks)

    def _getTestHttpUrl(self, *path):
        base = '/'.join(path)
        host, port = self.webaddr
        return f'http://{host}:{port}/' + base

    async def _finiCellAsync(self):

        if self.webserver is not None:
            self.webserver.stop()

    def getHttpHandlers(self):
        return ()

    def addHttpApi(self, path, ctor):
        self.webapp.add_handlers('.*', [
            (path, ctor),
        ])

    async def _initCellSlab(self):

        s_common.gendir(self.dirn, 'slabs')
        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        self.slab = await s_lmdb.Slab.anit(path, map_size=s_const.gibibyte)
        self.onfini(self.slab.fini)

    async def _initCellAuth(self):

        if not self.boot.get('auth:en'):
            return

        # runtime import.  dep loop.
        import synapse.cells as s_cells

        authdir = s_common.gendir(self.dirn, 'auth')
        self.auth = await s_cells.init('auth', authdir)

        admin = self.boot.get('auth:admin')
        if admin is not None:

            name, passwd = admin.split(':')

            user = self.auth.users.get(name)
            if user is None:
                user = self.auth.addUser(name)
                logger.warning(f'adding admin user: {name} to {self.cellname}')

            user.setAdmin(True)
            user.setPasswd(passwd)

        self.onfini(self.auth.fini)

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    @classmethod
    def deploy(cls, dirn):
        # sub-classes may over-ride to do deploy initialization
        pass

    def getHttpApi(self):
        '''
        Returns an HttpApi instance for the cell or None.
        '''
        http = None

        #if self.conf.get('http')

        hapi = self.httpapi()

    def getTeleApi(self, link, mesg):

        if self.auth is None:
            return self.cellapi(self, link)

        user = self._getCellUser(link, mesg)
        if user is None:
            _auth = mesg[1].get('auth')
            user = _auth[0] if _auth else None
            raise s_exc.AuthDeny(mesg='Unable to find cell user.',
                                 user=user)

        link.set('cell:user', user)
        return self.cellapi(self, link)

    def getCellType(self):
        return self.__class__.__name__.lower()

    def getCellIden(self):
        return self.iden

    def _getCellUser(self, link, mesg):

        # with SSL a valid client cert sets ssl:user
        name = link.get('ssl:user')
        if name is not None:
            return self.auth.users.get(name)

        # fall back on user/passwd
        auth = mesg[1].get('auth')
        if auth is None:
            return None

        name, info = auth

        user = self.auth.users.get(name)
        if user is None:
            return None

        # passwd None always fails...
        passwd = info.get('passwd')
        if not user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password',
                                 user=user.name)

        return user

    def initCellAuth(self):

        # To avoid import cycle
        import synapse.lib.auth as s_auth

        valu = self.boot.get('auth:en')
        if not valu:
            return

        url = self.boot.get('auth:url')
        if url is not None:
            self.auth = s_telepath.openurl(url)
            return

        # setup local auth

        dirn = s_common.gendir(self.dirn, 'auth')

        self.auth = s_auth.Auth(dirn)  # FIXME this is not imported, but would cause circular import

        # let them hard code an initial admin user:passwd
        admin = self.boot.get('auth:admin')
        if admin is not None:
            name, passwd = admin.split(':', 1)

            user = self.auth.getUser(name)
            if user is None:
                user = self.auth.addUser(name)

            user.setAdmin(True)
            user.setPasswd(passwd)

    def addCellCmd(self, name, func):
        '''
        Add a Cmdr() command to the cell.
        '''
        self.cmds[name] = func
