import os
import sys
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

import synapse.lib.coro as s_coro
import synapse.lib.urlhelp as s_urlhelp

class Share(s_coro.Fini):
    '''
    Class to wrap a dynamically shared object.
    '''
    def __init__(self, link, item):
        s_coro.Fini.__init__(self)

        self.link = link

        self.orig = item    # for context management
        self.item = item

        self.iden = s_common.guid()

        self.exited = False
        self.entered = False

        items = link.get('dmon:items')
        async def fini():
            items.pop(self.iden, None)
            self.item

        self.onfini(fini)
        items[self.iden] = self

    async def _runShareLoop(self):
        return

class With(Share):
    '''
    Server side context for a telepath With() proxy.
    '''
    typename = 'with'

    def __init__(self, link, item):
        Share.__init__(self, link, item)

        self.exitok = None  # None/False == error
        self.onfini(self._onWithFini)

    async def _onWithFini(self):

        if self.exitok:
            return await self._runExitFunc((None, None, None))

        try:
            raise s_exc.SynErr()
        except Exception as e:
            args = sys.exc_info()
            return await self._runExitFunc(args)

    async def _runExitFunc(self, args):

        exit = getattr(self.orig, '__aexit__', None)
        if exit:
            await exit(*args)
            return

        exit = getattr(self.orig, '__exit__', None)
        if exit:
            await s_glob.executor(exit, *args)
            return

    async def _runShareLoop(self):

        self.orig = self.item

        enter = getattr(self.orig, '__aenter__', None)
        if enter:
            self.item = await enter()
            return

        enter = getattr(self.orig, '__enter__', None)
        if enter:
            self.item = await s_glob.executor(enter)
            return

    async def teleexit(self, isexc):
        self.exitok = isexc
        await self.fini()

class Genr(Share):

    typename = 'genr'

    async def _runShareLoop(self):

        # automatically begin yielding

        def syncloop():

            try:

                for item in self.item:

                    if self.isfini:
                        self.item.close()
                        break

                    retn = (True, item)
                    mesg = ('share:data', {'share': self.iden, 'data': retn})
                    s_glob.sync(self.link.tx(mesg))

            except Exception as e:

                retn = s_common.retnexc(e)
                mesg = ('share:data', {'share': self.iden, 'data': retn})
                s_glob.sync(self.link.tx(mesg))

            finally:

                mesg = ('share:data', {'share': self.iden, 'data': None})
                s_glob.sync(self.link.tx(mesg))
                s_glob.sync(self.fini())

        await s_glob.executor(syncloop)

class AsyncGenr(Share):

    typename = 'genr'

    async def _runShareLoop(self):

        try:

            async for item in self.item:

                if self.isfini:
                    break

                retn = (True, item)
                mesg = ('share:data', {'share': self.iden, 'data': retn})
                await self.link.tx(mesg)

        except Exception as e:

            retn = s_common.retnexc(e)
            mesg = ('share:data', {'share': self.iden, 'data': retn})
            await self.link.tx(mesg)

        finally:

            mesg = ('share:data', {'share': self.iden, 'data': None})
            await self.link.tx(mesg)
            await self.fini()

dmonwrap = (
    (types.AsyncGeneratorType, AsyncGenr),
    (types.GeneratorType, Genr),
)

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
            'share:fini': self._onShareFini,
        }

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

            await func(link, mesg)

        except Exception as e:
            logger.exception('Dmon.onLinkMesg Handler: %r' % (mesg,))

    async def _onShareFini(self, link, mesg):

        iden = mesg[1].get('share')
        share = link.get('dmon:items').get(iden)
        if share is None:
            return

        await share.fini()

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

            items = {None: item}
            link.set('dmon:items', items)

            @s_glob.synchelp
            async def fini():

                items = list(link.get('dmon:items').values())

                for item in items:
                    try:
                        await item.fini()
                    except Exception as e:
                        logger.exception(f'item fini error: {e}')

            link.onfini(fini)

        except Exception as e:
            logger.exception('tele:syn error')
            reply[1]['retn'] = s_common.retnexc(e)

        await link.tx(reply)

    async def _runTodoMeth(self, link, meth, args, kwargs):

        # do we get to dispatch it ourselves?
        if asyncio.iscoroutinefunction(meth):
            return await meth(*args, **kwargs)
        else:
            # the method isn't async :(
            return await s_glob.executor(meth, *args, **kwargs)

    async def _tryWrapValu(self, link, valu):

        for wraptype, wrapctor in dmonwrap:
            if isinstance(valu, wraptype):
                return wrapctor(link, valu)

        # turtles all the way down...
        if asyncio.iscoroutine(valu):
            valu = await valu
            return await self._tryWrapValu(link, valu)

        return valu

    def _getTaskFiniMesg(self, task, valu):

        if not isinstance(valu, Share):
            retn = (True, valu)
            return ('task:fini', {'task': task, 'retn': retn})

        retn = (True, valu.iden)
        typename = valu.typename
        return ('task:fini', {'task': task, 'retn': retn, 'type': typename})

    async def _onTaskInit(self, link, mesg):

        task = mesg[1].get('task')
        name = mesg[1].get('name')

        item = link.get('dmon:items').get(name)

        #import synapse.lib.scope as s_scope
        #with s_scope.enter({'syn:user': user}):

        try:

            name, args, kwargs = mesg[1].get('todo')

            if name[0] == '_':
                raise s_exc.NoSuchMeth(name=name)

            meth = getattr(item, name, None)
            if meth is None:
                logger.warning(f'{item!r} has no method: {name}')
                raise s_exc.NoSuchMeth(name=name)

            valu = await self._runTodoMeth(link, meth, args, kwargs)
            valu = await self._tryWrapValu(link, valu)

            mesg = self._getTaskFiniMesg(task, valu)
            await link.tx(mesg)

            # if it's a Share() give it a shot to run..
            if isinstance(valu, Share):
                await valu._runShareLoop()

        except Exception as e:

            logger.exception('on task:init: %r' % (mesg,))

            retn = s_common.retnexc(e)

            await link.tx(
                ('task:fini', {'task': task, 'retn': retn})
            )

    def _getTestProxy(self, name):
        host, port = self.addr
        return s_telepath.openurl(f'tcp:///{name}', host=host, port=port)
