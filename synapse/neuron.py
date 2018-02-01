import os
import sys
import time
import errno
import fcntl
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

import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.vault as s_vault
import synapse.lib.crypto.tinfoil as s_tinfoil

logger = logging.getLogger(__file__)

class SessBoss:
    '''
    Mixin base class for sesion managers.
    '''
    def __init__(self, auth, roots=()):

        self._boss_auth = auth

        self.roots = list(roots)

        root = s_vault.Cert.load(auth[1].get('root'))
        self.roots.append(root)

        self.rkey = s_rsa.PriKey.load(auth[1].get('rsa:key'))

        self.cert = s_vault.Cert.load(auth[1].get('cert'))
        self.certbyts = self.cert.dump()

    def decrypt(self, byts):
        return self.rkey.decrypt(byts)

    def valid(self, cert):
        return any([r.signed(cert) for r in self.roots])

class Cell(s_config.Config, s_net.Link, SessBoss):
    '''
    A Cell is a micro-service in a neuron cluster.

    Args:
        dirn (str): Path to the directory backing the Cell.
        conf (dict): Configuration data.
    '''
    _def_port = 0

    def __init__(self, dirn, conf=None):

        s_net.Link.__init__(self)
        s_config.Config.__init__(self)

        self.dirn = dirn
        s_common.gendir(dirn)

        # config file in the dir first...
        self.loadConfPath(self._path('config.json'))
        if conf is not None:
            self.setConfOpts(conf)
        self.reqConfOpts()

        self.plex = s_net.Plex()
        self.kvstor = s_kv.KvStor(self._path('cell.lmdb'))
        self.kvinfo = self.kvstor.getKvDict('cell:info')

        # open our vault
        self.vault = s_vault.Vault(self._path('vault.lmdb'))
        self.root = self.vault.genRootCert()

        # setup our certificate and private key
        auth = None

        path = self._path('cell.auth')
        if os.path.isfile(path):
            with open(path, 'rb') as fd:
                auth = s_msgpack.un(fd.read())

        # if we dont have provided auth, assume we stand alone
        if auth is None:

            auth = self.vault.genUserAuth('root')
            with open(path, 'wb') as fd:
                fd.write(s_msgpack.en(auth))

            path = self._path('user.auth')
            auth = self.vault.genUserAuth('user')

            with open(path, 'wb') as fd:
                fd.write(s_msgpack.en(auth))

        roots = self.vault.getRootCerts()
        SessBoss.__init__(self, auth, roots)

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

        # Give implementers the chance to hook into the cell
        self.postCell()

        # lock cell.lock
        self.lockfd = s_common.genfile(self._path('cell.lock'))
        try:
            fcntl.lockf(self.lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            logger.exception('Failed to obtain lock for [%s]', self.lockfd.name)
            raise
        self.onfini(self._onCellFini)
        self.onfini(self.finiCell)
        logger.debug('Cell is done initializing')

    def _onCellFini(self):
        self.plex.fini()
        self.sessplex.fini()
        self.kvstor.fini()
        self.vault.fini()
        self.lockfd.close()

    def postCell(self):
        '''
        Module implementers may over-ride this method to initialize the cell
        *after* the configuration data has been loaded.

        Returns:
            None
        '''
        pass

    def finiCell(self):
        '''
        Module implementors may over-ride this method to automatically tear down
        resources created during postCell().
        '''
        pass

    def handlers(self):
        '''
        Module implementors may over-ride this method to provide the
        ``<mesg>:<func>`` mapping required for the Cell link layer.

        Returns:
            dict: Dictionary mapping endpoints to functions.
        '''
        return {
            'cell:ping': self._onCellPing,
        }

    def genUserAuth(self, name):
        '''
        Generate a user auth blob that is valid for this Cell.

        Args:
            name (str): Name of the user to generate the auth blob for.

        Returns:
            ((str, dict)): A user auth tufo.
        '''
        return self.vault.genUserAuth(name)

    def getCellPort(self):
        '''
        Get the port the Cell is listening on.

        Returns:
            int: Port the cell is running on.
        '''
        return self.kvinfo.get('port')

    def getRootCert(self):
        '''
        Get the root certificate for the cell.

        Returns:
            s_vault.Cert: The root Cert object for the cell.
        '''
        return self.root

    def getCellDict(self, name):
        '''
        Get a KvDict with a given name.

        Args:
            name (str): Name of the KvDict.

        Notes:
            Module implementers may use the ``getCellDict()`` API to get
            a KvDict object which acts like a Python dictionary, but will
            persist data across process startup/shutdown.  The keys and
            values are msgpack encoded prior to storing them, allowing the
            persistence of complex data structures.

        Returns:
            s_kv.KvDict: A persistent KvDict.
        '''
        return self.kvstor.getKvDict('cell:data:' + name)

    def _onCellPing(self, chan, mesg):
        data = mesg[1].get('data')
        chan.txfini(data=data)

    def _path(self, *paths):
        '''
        Join a path relative to the cell persistence directory.
        '''
        return os.path.join(self.dirn, *paths)

    def getCellPath(self, *paths):
        '''
        Get a file path underneath the underlying Cell path.

        Args:
            *paths: Paths to join together.

        Notes:
            Does not protect against path traversal.

        Returns:
            str: P
        '''
        return os.path.join(self.dirn, 'cell', *paths)

    @staticmethod
    @s_config.confdef(name='cell')
    def _getCellConf():
        return (

            ('ctor', {
                'doc': 'The path to the cell constructor'}),

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
            raise s_common.NotReady()

        data = mesg[1].get('data')
        newm = s_msgpack.un(self.rxtinh.dec(data))

        self.taskplex.rx(self, newm)

    def _onMesgSkey(self, link, mesg):

        data = mesg[1].get('data')

        skey = self._sess_boss.decrypt(data)

        self.setRxKey(skey)

    def sendcert(self):
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

    def call(self, mesg, timeout=None):
        '''
        Call a Cell endpoint which returns a single value.
        '''
        with self.task(mesg, timeout=timeout) as chan:
            return chan.next(timeout=timeout)

    def iter(self, mesg, timeout=None):
        '''
        Access a Cell endpoint that uses the iter convention.
        '''
        with self.task(mesg, timeout=timeout) as chan:
            for item in chan.iter():
                chan.tx(True)
                yield item

    def task(self, mesg=None, timeout=None):
        '''
        Open a new channel within our session.
        '''
        with s_threads.retnwait() as retn:

            def onchan(chan):

                chan.setq() # make this channel use a Q

                if mesg is not None:
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

    def __init__(self, auth, roots=()):

        SessBoss.__init__(self, auth, roots=roots)

        self.sessplex = s_net.ChanPlex()
        self.taskplex = s_net.ChanPlex()

    def open(self, addr, timeout=None):
        '''
        Open the Cell at the remote addr and return a UserSess Link.

        Args:
            addr ((str,int)): A (host, port) address tuple
            timeout (int/float): Connection timeout in seconds.

        Returns:
            UserSess: The connected Link (or None).
        '''
        # a *synchronous* open...

        with s_threads.retnwait() as retn:

            def onlink(ok, link):

                if not ok:
                    # XXX untested!
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

def getCellCtor(dirn, conf=None):
    '''
    Find the ctor option for a cell and resolve the function.
    '''
    ctor = None

    if conf is not None:
        ctor = conf.get('ctor')

    path = s_common.genpath(dirn, 'config.json')

    if ctor is None and os.path.isfile(path):
        subconf = s_common.jsload(path)
        ctor = subconf.get('ctor')

    if ctor is None:
        raise s_common.ReqConfOpt(mesg='Missing ctor, cannot divide',
                                  name='ctor')

    func = s_dyndeps.getDynLocal(ctor)
    if func is None:
        raise s_common.NoSuchCtor(mesg='Cannot resolve ctor',
                                  name=ctor)

    return ctor, func

def divide(dirn, conf=None):
    '''
    Create an instance of a Cell in a subprocess.

    Args:
        dirn (str):
        conf (dict):

    Returns:
        multiprocessing.Process: The Process object which was created to run the Cell
    '''
    proc = multiprocessing.Process(target=main, args=(dirn, conf))
    proc.start()

    return proc

def main(dirn, conf=None):
    '''
    Initialize and execute the main loop for a Cell.

    Args:
        dirn (str): Directory backing the Cell data.
        conf (dict): Configuration dictionary.

    Notes:
        This ends up calling ``main()`` on the Cell, and does not return
         anything. It cals sys.exit() at the end of its processing.
    '''
    try:

        dirn = s_common.genpath(dirn)
        ctor, func = getCellCtor(dirn, conf=conf)

        cell = func(dirn, conf)

        port = cell.getCellPort()
        logger.warning('cell divided: %s (%s) port: %d' % (ctor, dirn, port))

        cell.main()
        sys.exit(0)
    except Exception as e:
        logger.exception('main: %s (%s)' % (dirn, e))
        sys.exit(1)

if __name__ == '__main__':
    import sys
    main(sys.argv[1])
