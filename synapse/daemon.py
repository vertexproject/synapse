import os
import sys
import time
import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath

from synapse.eventbus import EventBus

import synapse.lib.coro as s_coro
import synapse.lib.urlhelp as s_urlhelp

class Share(s_coro.Fini):
    '''
    Class to wrap a dynamically shared object.
    '''
    def __init__(self):
        s_coro.Fini.__init__(self)

class Sess(s_coro.Fini):

    def __init__(self):
        s_coro.Fini.__init__(self)

        self.tick = s_common.now()
        self.count = 1

        self.shared = {}
        self.onfini(self._onSessFini)

    async def _onSessFini(self):

        # pop the main object...
        self.shared.pop(None, None)

        for name, item in self.shared.items():
            try:
                await item.fini()
            except Exception as e:
                logger.exception(f'coro fini() error for {item.__class__.__name__}')

    def incref(self):
        self.count += 1

    def decref(self):
        self.tick = time.time()
        self.count -= 1

sesstick = 60
sesslife = 120  # session lifespan with 0 active links

class Daemon(EventBus):

    confdefs = (

        ('listen', {'defval': 'tcp://127.0.0.1:27492',
            'doc': 'The default listen host/port'}),

        ('modules', {'defval': (),
            'doc': 'A list of python modules to import before Cell construction.'}),

        #('hostname', {'defval':
        #('ssl': {'defval': None,
            #'doc': 'An SSL config dict with certfile/keyfile optional cacert.'}),
    )

    def __init__(self, dirn):

        EventBus.__init__(self)

        self.dirn = s_common.gendir(dirn)

        conf = self._loadDmonYaml()
        self.conf = s_common.config(conf, self.confdefs)

        self.mods = {}      # keep refs to mods we load ( mostly for testing )
        self.televers = s_telepath.televers

        self.addr = None    # our main listen address
        self.cells = {}     # all cells are shared.  not all shared are cells.
        self.shared = {}    # objects provided by daemon

        self.sessions = {}

        self.mesgfuncs = {
            'tele:syn': self._onTeleSyn,
            'task:init': self._onTaskInit,
        }

        s_glob.plex.coroLoopTask(self._cullDeadSess())

        self._loadDmonConf()
        self._loadDmonCells()

        self.onfini(self._onDmonFini)

    def listen(self, url, **opts):
        '''
        Bind and listen on the given host/port with possible SSL.

        Args:
            host (str): A hostname or IP address.
            port (int): The TCP port to bind.
            ssl (ssl.SSLContext): An SSL context or None...
        '''
        info = s_urlhelp.chopurl(url, **opts)

        host = info.get('host')
        port = info.get('port')

        # TODO: SSL
        ssl = None

        return s_glob.plex.listen(host, port, self._onLinkInit, ssl=ssl)

    def share(self, name, item):
        '''
        Share an object via the telepath protocol.

        Args:
            name (str): Name of the shared object
            item (object): The object to share over telepath.
        '''

        try:

            if isinstance(item, s_telepath.Aware):
                item.onTeleShare(self, name)

            self.shared[name] = item

        except Exception as e:
            logger.exception(f'onTeleShare() error for: {name}')

    async def _cullDeadSess(self):

        while not self.isfini:

            mintime = time.time() - sesslife

            items = list(self.sessions.items())

            for iden, sess in items:

                if sess.count > 0:
                    continue

                if sess.tick > mintime:
                    continue

                self.sessions.pop(iden, None)
                await sess.fini()

            await asyncio.sleep(sesstick)

    def _onDmonFini(self):
        for name, cell in self.cells.items():
            cell.fini()

    def _getSslCtx(self):
        return None
        #info = self.conf.get('ssl')
        ##if info is None:
            #return None

        #capath = s_common.genpath(self.dirn, 'ca.crt')
        ##keypath = s_common.genpath(self.dirn, 'server.key')
        #certpath = s_common.genpath(self.dirn, 'server.crt')

        # TODO: build an ssl.SSLContext()

    def _loadDmonYaml(self):
        path = s_common.genpath(self.dirn, 'dmon.yaml')
        return self._loadYamlPath(path)

    def _loadYamlPath(self, path):
        if os.path.isfile(path):
            return s_common.yamlload(path)

        logger.warning('config not found: %r' % (path,))
        return {}

    def _loadDmonCells(self):

        # load our services from a directory

        path = s_common.gendir(self.dirn, 'cells')

        for name in os.listdir(path):

            if name.startswith('.'):
                continue

            self.loadDmonCell(name)

    def loadDmonCell(self, name):

        dirn = s_common.gendir(self.dirn, 'cells', name)
        logger.warning(f'loading cell from: {dirn}')

        path = os.path.join(dirn, 'boot.yaml')

        if not os.path.exists(path):
            raise s_exc.NoSuchFile(name=path)

        conf = self._loadYamlPath(path)

        kind = conf.get('type')

        cell = s_cells.init(kind, dirn)

        self.share(name, cell)
        self.cells[name] = cell

    def _loadDmonConf(self):

        # process per-conf elements...
        for name in self.conf.get('modules', ()):
            try:
                self.mods[name] = s_dyndeps.getDynMod(name)
            except Exception as e:
                logger.exception('dmon module error')

        lisn = self.conf.get('listen')
        if lisn is not None:
            self.addr = self.listen(lisn)

    async def _onLinkInit(self, link):

        while not link.isfini:

            mesg = await link.rx()
            if mesg is None:
                return

            await self._onLinkMesg(link, mesg)

    async def _onLinkMesg(self, link, mesg):

        try:

            func = self.mesgfuncs.get(mesg[0])
            if func is None:
                logger.exception('Dmon.onLinkMesg Invalid: %.80r' % (mesg,))
                return

            await func(link, mesg)

        except Exception as e:
            await link.fini()
            logger.exception('Dmon.onLinkMesg Handler: %.80r' % (mesg,))

    async def _getDmonSess(self, iden):

        sess = self.sessions.get(iden)
        if sess is not None:
            sess.incref()
            return sess

        sess = Sess()
        self.sessions[iden] = sess
        return sess

    async def _onTeleSyn(self, link, mesg):

        reply = ('tele:syn', {
            'vers': self.televers,
            'retn': (True, None),
        })

        try:

            iden = mesg[1].get('sess')
            sess = await self._getDmonSess(iden)

            # decrement the sess.count on link fini
            link.onfini(sess.decref)
            link.set('sess', sess)

            vers = mesg[1].get('vers')

            if vers[0] != s_telepath.televers[0]:
                raise s_exc.BadMesgVers(vers=vers, myvers=s_telepath.televers)

            name = mesg[1].get('name')

            item = self.shared.get(name)

            # allow a telepath aware object a shot at dynamic share names
            if item is None and name.find('/') != -1:

                path = name.split('/')

                base = self.shared.get(path[0])
                if base is not None and isinstance(base, s_telepath.Aware):
                    item = base.onTeleOpen(link, path)

            if item is None:
                raise s_exc.NoSuchName(name=name)

            if isinstance(item, s_telepath.Aware):
                item = item.getTeleApi(link, mesg)

            sess.shared[None] = item

        except Exception as e:
            logger.exception('tele:syn error')
            reply[1]['retn'] = s_common.retnexc(e)

        await link.tx(reply)

    async def _runTodoMeth(self, meth, args, kwargs):

        # do we get to dispatch it ourselves?
        if asyncio.iscoroutinefunction(meth):
            return await meth(*args, **kwargs)
        else:
            # the method isn't async :(
            return await s_glob.executor(meth, *args, **kwargs)

    async def _runGenrLoop(self, link, genr):

        def loop():
            try:

                for item in genr:
                    mesg = ('genr:data', item)
                    if not s_glob.sync(link.tx(mesg)):
                        return False

                mesg = ('genr:fini', None)
                s_glob.sync(link.tx(mesg))
                return True

            except Exception as e:
                mesg = ('genr:errx', s_common.retnexc(e))
                s_glob.sync(link.tx(mesg))
                return False

        if not await s_glob.executor(loop):
            print('BORK')
            await link.fini()

    async def _onTaskInit(self, link, mesg):

        name = mesg[1].get('name')

        sess = link.get('sess')
        if sess is None:
            await link.fini()
            return

        item = sess.shared.get(name)

        try:

            name, args, kwargs = mesg[1].get('todo')

            if name[0] == '_':
                raise s_exc.NoSuchMeth(name=name)

            meth = getattr(item, name, None)
            if meth is None:
                logger.warning(f'{item!r} has no method: {name}')
                raise s_exc.NoSuchMeth(name=name)

            valu = await self._runTodoMeth(meth, args, kwargs)

            # if it's a generator, fire a thread to run it...
            if isinstance(valu, types.GeneratorType):

                mesg = ('task:fini', {'type': 'genr', 'retn': (True, None)})
                if not await link.tx(mesg):
                    return

                await self._runGenrLoop(link, valu)
                return

            # handle a returned async generator in-line
            if isinstance(valu, types.AsyncGeneratorType):

                mesg = ('task:fini', {'type': 'genr', 'retn': (True, None)})
                if not await link.tx(mesg):
                    return

                try:

                    async for item in valu:

                        if not await link.tx(('genr:data', item)):
                            return

                    if not await link.tx(('genr:fini', None)):
                        return

                except Exception as e:
                    mesg = ('genr:errx', s_common.retnexc(e))
                    await link.tx(mesg)

                return

            # otherwise, it may be a new Share()
            if isinstance(valu, Share):
                # a new dynamic share
                iden = s_common.guid()
                sess.shared[iden] = valu
                await link.tx(('task:fini', {'type': 'share', 'retn': (True, iden)}))
                return

            await link.tx(('task:fini', {'retn': (True, valu)}))

        except Exception as e:

            logger.exception('on task:init: %r' % (mesg,))

            retn = s_common.retnexc(e)

            await link.tx(
                ('task:fini', {'retn': retn})
            )

    def _getTestProxy(self, name, **kwargs):
        host, port = self.addr
        kwargs.update({'host': host, 'port': port})
        return s_telepath.openurl(f'tcp:///{name}', **kwargs)
