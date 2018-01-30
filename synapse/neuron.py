import os
import time
import errno
import socket
import logging
import threading
import collections
import multiprocessing

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.link as s_link
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.net as s_net
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

import synapse.lib.crypto.vault as s_vault
import synapse.lib.crypto.tinfoil as s_tinfoil

logger = logging.getLogger(__file__)

class SessBoss:
    '''
    Mixin base class for sesion managers.
    '''
    def __init__(self, cert, roots):

        self.cert = cert
        self.roots = roots

        self.key = cert.getkey()
        self.certbyts = cert.dump()

    def decrypt(self, byts):
        return self.key.decrypt(byts)

    def valid(self, cert):
        return any([r.signed(cert) for r in self.roots])

class Cell(s_config.Config, s_net.Link, SessBoss):
    '''
    A Cell is a micro-service in a neuron cluster.
    '''
    _def_port = 0

    def __init__(self, dirn, conf=None):

        s_net.Link.__init__(self)
        s_config.Config.__init__(self)

        self.dirn = dirn
        s_common.gendir(dirn)

        # config file in the dir first...
        self.loadConfPath(self.path('config.json'))

        if conf is not None:
            self.setConfOpts(conf)

        self.reqConfOpts()

        self.plex = s_net.Plex()

        self.kvstor = s_kv.KvStor(self.path('cell.lmdb'))

        self.kvinfo = self.kvstor.getKvDict('cell:info')

        # open our vault
        self.vault = s_vault.Vault(self.path('vault.lmdb'))

        self.boot = self._loadBootFile()

        self.root = self.vault.genRootCert()

        # setup our certificate and private key
        user = self.getConfOpt('user')
        cert = self.vault.genUserCert(user)
        roots = self.vault.getRootCerts()

        SessBoss.__init__(self, cert, roots)

        host = self.getConfOpt('host')
        port = self.getConfOpt('port')

        if port == 0:
            port = self.kvinfo.get('port', port)

        def onchan(chan):
            sess = CellSess(chan, self)
            chan.onrx(sess.rx)

        self.sessplex = s_net.ChanPlex(onchan=onchan)

        def onlink(link):
            link.onrx(self.sessplex.rx)

        self._cell_addr = self.plex.listen((host, port), onlink)

        # save the port so it can be semi-stable...
        self.kvinfo.set('port', self._cell_addr[1])

    def handlers(self):
        return {
            'cell:ping': self._onCellPingMesg,
        }

    def genUserAuth(self, name):
        '''
        Generate a user auth blob that is valid for this Cell.
        '''
        return self.vault.genUserAuth(name)

    def getCellPort(self):
        return self.kvinfo.get('port')

    def genRootCert(self):
        return self.root

    def _onCellPingMesg(self, chan, mesg):
        rply = ('retn', {'ok': True, 'data': mesg[1].get('data')})
        chan.txfini(data=rply)

    def _loadBootFile(self):
        '''
        ./node.boot is a msgpack bootstrap dict
        ( it is deleted one loaded the first time )
        '''
        path = self.path('cell.boot')
        if not os.path.isfile(path):
            return None

        with io.open(path, 'rb') as fd:
            byts = fd.read()

        os.unlink(path)

        boot = s_msgpack.un(byts)
        self._initFromBoot(boot)

        return boot

    def _initFromBoot(self, boot):

        # get and trust the root user cert
        root = boot.get('root')
        if root is not None:
            self.vault.addRootCert(root)

        auth = boot.get('auth')
        if auth is not None:
            self.kvinfo('user', auth[0])
            self.vault.addUserAuth(auth, signer=True)

    def path(self, *paths):
        '''
        Join a path relative to the cell persistence directory.
        '''
        return os.path.join(self.dirn, *paths)

    @staticmethod
    @s_config.confdef(name='cell')
    def _getCellConf():
        return (

            ('ctor', {
                'doc': 'The path to the cell constructor'}),

            ('user', {'defval': 'cell@neuron.vertex.link',
                'doc': 'The user this Cell runs as (cert).'}),

            ('root', {
                'doc': 'The SHA256 of our neuron root cert (used for autoconf).'}),

            ('neuron', {
                'doc': 'The host name (and optionally port) of our neuron'}),

            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': 0, 'req': 1,
                'doc': 'The TCP port to bind (defaults to dynamic)'}),
        )

nodeport = 65521

class Neuron(Cell):
    '''
    A neuron node is the "master cell" for a neuron cluster.
    '''
    def __init__(self, dirn, conf=None):
        Cell.__init__(self, dirn, conf=conf)

    @staticmethod
    @s_config.confdef(name='node')
    def _getNodeConf():
        return (
            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': nodeport, 'req': 1,
                'doc': 'The TCP port to bind (defaults to %d)' % nodeport}),
        )

class Sess(s_net.Link):

    def __init__(self, chan, boss, lisn=False):

        s_net.Link.__init__(self, chan)

        self._sess_boss = boss

        self.lisn = lisn    # True if we are the listener.

        self.txkey = s_tinfoil.newkey()
        self.txtinh = s_tinfoil.TinFoilHat(self.txkey)

        self.rxkey = None
        self.rxtinh = None

    def handlers(self):
        return {
            'cert': self._onMesgCert,
            'skey': self._onMesgSkey,
            'xmit': self._onMesgXmit,
        }

    def setRxKey(self, rxkey):
        self.rxkey = rxkey
        self.rxtinh = s_tinfoil.TinFoilHat(rxkey)

    def _tx_real(self, mesg):

        if self.txtinh is None:
            raise s_exc.NotReady()

        data = self.txtinh.enc(s_msgpack.en(mesg))
        self.link.tx(('xmit', {'data': data}))

    def _onMesgXmit(self, link, mesg):

        if self.rxtinh is None:
            logger.warning('xmit message before rxkey')
            raise NotReady()

        data = mesg[1].get('data')
        newm = s_msgpack.un(self.rxtinh.dec(data))

        self.taskplex.rx(self, newm)

    def _onMesgSkey(self, link, mesg):

        data = mesg[1].get('data')

        skey = self._sess_boss.decrypt(data)

        self.setRxKey(skey)

    def sendcert(self):
        #print('%s (%d) sending cert' % (self.__class__.__name__,id(self)))
        self.link.tx(('cert', {'cert': self._sess_boss.certbyts}))

    def _onMesgCert(self, link, mesg):

        if self.lisn:
            self.sendcert()

        cert = s_vault.Cert.load(mesg[1].get('cert'))

        if not self._sess_boss.valid(cert):
            clsn = self.__class__.__name__
            logger.warning('%s got bad cert (%r)' % (clsn, cert.iden(),))
            return

        # send back an skey message with our tx key
        data = cert.public().encrypt(self.txkey)
        self.link.tx(('skey', {'data': data}))

        self.fire('sess:txok')

class UserSess(Sess):
    '''
    The session object for a CellUser.
    '''
    def __init__(self, chan, prox):
        Sess.__init__(self, chan, prox, lisn=False)
        self._sess_prox = prox
        self._txok_evnt = threading.Event()
        self.on('sess:txok', self._setTxOk)

        self.taskplex = s_net.ChanPlex(self)

    def _setTxOk(self, mesg):
        self._txok_evnt.set()

    def waittx(self, timeout=None):
        self._txok_evnt.wait(timeout=timeout)
        return self._txok_evnt.is_set()

    def task(self, mesg, timeout=None):
        '''
        Open a new channel within our session.
        '''
        with s_threads.retnwait() as retn:

            def onchan(chan):
                chan.setq() # make this channel use a Q
                chan.tx(mesg)
                retn.retn(chan)

            self.taskplex.open(self, onchan)

            return retn.wait(timeout=timeout)

class CellSess(Sess):
    '''
    The session object for the Cell.
    '''
    def __init__(self, chan, cell):

        Sess.__init__(self, chan, cell, lisn=True)
        self._sess_cell = cell

        def onchan(chan):
            chan.onrx(self._sess_cell.rx)

        self.taskplex = s_net.ChanPlex(onchan=onchan)

class CellUser(SessBoss):

    def __init__(self, user, path=s_vault.uservault):

        self.user = user
        self.path = path

        self.host = user.split('@', 1)[1]

        with s_vault.shared(path) as vault:

            cert = vault.getUserCert(user)

            if cert is None:
                raise s_exc.NoSuchUser(name=user, mesg='No cert in vault: %s' % (path,))

            roots = vault.getRootCerts()

        SessBoss.__init__(self, cert, roots)

        self.sessplex = s_net.ChanPlex()
        self.taskplex = s_net.ChanPlex()

    def open(self, addr, timeout=None):
        '''
        Open the Cell at the remote addr and return a UserSess Link.

        Args:
            addr ((str,int)): A (host, port) address tuple
            timeout (int/float): Connection timeout in seconds.

        Returns:
            (UserSess): The connected Link (or None).
        '''
        # a *synchronous* open...

        with s_threads.retnwait() as retn:

            def onlink(ok, link):

                if not ok:
                    errs = os.strerror(erno)
                    return retn.errx(OSError(erno, errs))

                link.onrx(self.sessplex.rx)

                def onchan(chan):

                    sess = UserSess(chan, self)

                    chan.onrx(sess.rx)
                    sess.sendcert()

                    retn.retn(sess)

                self.sessplex.open(link, onchan)

            s_glob.plex.connect(addr, onlink)

            sess = retn.wait(timeout=timeout)
            if sess is None:
                return None

            if not sess.waittx(timeout=timeout):
                return None

            return sess

def divide(dirn, conf=None):
    '''
    Create an instance of a Cell in a subprocess.
    '''
    # lets try to find his constructor...
    ctor = None

    if conf is not None:
        ctor = conf.get('ctor')

    path = s_common.genpath(dirn, 'config.json')

    if ctor is None and os.path.isfile(path):
        subconf = s_common.jsload(path)
        ctor = subconf.get('ctor')

    if ctor is None:
        raise ReqConfOpt(name='ctor')

    func = s_dyndeps.getDynLocal(ctor)
    if func is None:
        raise NoSuchCtor(name=ctor)

    proc = multiprocessing.Process(target=_cell_entry, args=(ctor, dirn, conf))
    proc.start()

    return proc

def _cell_entry(ctor, dirn, conf):

    try:

        dirn = s_common.genpath(dirn)
        func = s_dyndeps.getDynLocal(ctor)

        cell = func(dirn, conf)

        logger.info('cell divided: %s (%s)' % (ctor, dirn))

        cell.main()

    except Exception as e:
        logger.exception('_cell_entry: %s (%s)' % (ctor, e))
