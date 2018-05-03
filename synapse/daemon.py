import os
import json
import yaml
import types
import asyncio
import inspect
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath

from synapse.eventbus import EventBus

import synapse.lib.urlhelp as s_urlhelp

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

        self.mesgfuncs = {
            'tele:syn': self._onTeleSyn,
            'task:init': self._onTaskInit,
            #'chan:data': self._onChanData,
            'chan:fini': self._onChanFini,
        }

        self._loadDmonConf()
        self._loadDmonCells()

        self.onfini(self._onDmonFini)

        #self._loadDmonYaml()
        #self._loadSvcDir()

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
        self.shared[name] = item

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
            with open(path, 'rb') as fd:
                text = fd.read().decode('utf8')
                return yaml.load(text)

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

        path = os.path.join(dirn, 'cell.yaml')

        if not os.path.exists(path):
            raise s_exc.NoSuchFile(name=path)

        conf = self._loadYamlPath(path)

        kind = conf.get('type')

        #ctor = s_registry.getService(kind)
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

        async def onrx(mesg):
            await self._onLinkMesg(link, mesg)

        link.onrx(onrx)

    async def _onLinkMesg(self, link, mesg):

        try:

            func = self.mesgfuncs.get(mesg[0])
            if func is None:
                logger.exception('Dmon.onLinkMesg Invalid: %r' % (mesg,))
                return

            coro = func(link, mesg)
            if asyncio.iscoroutine(coro):
                await coro

        except Exception as e:
            logger.exception('Dmon.onLinkMesg Handler: %r' % (mesg,))

    async def _onChanFini(self, link, mesg):

        iden = mesg[1].get('chan')

        chan = link.chans.get(iden)
        if chan is None:
            return

        chan.fini()

    async def _onTeleSyn(self, link, mesg):

        reply = ('tele:syn', {
            'vers': self.televers,
            'retn': (True, None),
        })

        try:

            vers = mesg[1].get('vers')

            if vers[0] != s_telepath.televers[0]:
                raise s_exc.BadMesgVers(vers=vers, myvers=s_telepath.televers)

            name = mesg[1].get('name')

            item = self.shared.get(name)
            if item is None:
                raise s_exc.NoSuchName(name=name)

            if isinstance(item, s_telepath.Aware):
                item = item.getTeleApi(link, mesg)

            link.set('dmon:item', item)

        except Exception as e:
            logger.exception('tele:syn error')
            reply[1]['retn'] = s_common.retnexc(e)

        await link.tx(reply)

    async def _feedAsyncGenrChan(self, link, iden, genr):

        chan = link.chan()
        try:

            if not await chan.init(iden):
                return

            async for item in genr:
                if not await chan.tx(item):
                    return

        except Exception as e:
            logger.exception()
            await chan.txexc(e)

        finally:
            await chan.txfini()
            chan.fini()

    @s_glob.inpool
    def _feedGenrChan(self, link, iden, genr):

        chan = link.chan()
        try:

            if not s_glob.sync(chan.init(iden)):
                return

            for item in genr:

                if not s_glob.sync(chan.tx(item)):
                    break

        except Exception as e:
            logger.exception()
            s_glob.sync(chan.txexc(e))

        finally:
            s_glob.sync(chan.txfini())

    #await s_glob.exector(self.runGenrChan, task, todo)

    def _runGenrChan(self, chan, genr):
        for item in genr:
            s_glob.sync(chan.tx(item))

    async def _onTaskInit(self, link, mesg):

        task = mesg[1].get('task')

        user = link.get('syn:user')
        item = link.get('dmon:item')

        import synapse.lib.scope as s_scope

        ##with s_scope.enter({'dmon': self, 'sock': sock, 'syn:user': user, 'syn:auth': self.auth}):

        with s_scope.enter({'syn:user': user}):

            try:

                name, args, kwargs = mesg[1].get('todo')

                if name[0] == '_':
                    raise s_exc.NoSuchMeth(name=name)

                meth = getattr(item, name, None)
                if meth is None:
                    print('NO SUCH METH: %s on %r' % (name, item))
                    raise s_exc.NoSuchMeth(name=name)

                # do we get to dispatch it ourselves?
                if asyncio.iscoroutinefunction(meth):

                    valu = await meth(*args, **kwargs)

                    await link.tx(
                        ('task:fini', {'task': task, 'retn': (True, valu)})
                    )

                    return

                if inspect.isasyncgenfunction(meth):

                    chan = link.chan()
                    try:
                        await chan.init(task)

                        async for item in meth(*args, **kwargs):
                            await chan.tx(item)

                        await chan.txfini()

                    except Exception as e:

                        await chan.txexc(e)

                    finally:
                        chan.fini()

                    return

                # the method isn't async :(
                valu = await s_glob.executor(meth, *args, **kwargs)

                if isinstance(valu, types.GeneratorType):

                    chan = link.chan()
                    try:

                        await chan.init(task)

                        await s_glob.executor(self._runGenrChan, chan, valu)

                        await chan.txfini()

                    except Exception as e:
                        await chan.txexc(e)
                        await chan.txfini()

                    finally:
                        chan.fini()

                    return

                await link.tx(
                    ('task:fini', {'task': task, 'retn': (True, valu)})
                )

                return

            except Exception as e:

                logger.exception('on task:init: %r' % (mesg,))

                retn = s_common.retnexc(e)

                await link.tx(
                    ('task:fini', {'task': task, 'retn': retn})
                )

    def _getTestProxy(self, name):
        host, port = self.addr
        return s_telepath.openurl(f'tcp:///{name}', host=host, port=port)
