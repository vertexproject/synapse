'''
An RMI framework for synapse.
'''

import os
import ssl
import copy
import time
import yaml
import asyncio
import logging
import contextlib
import collections

import aiohttp

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.queue as s_queue
import synapse.lib.certdir as s_certdir
import synapse.lib.threads as s_threads
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.hashitem as s_hashitem

logger = logging.getLogger(__name__)

televers = (3, 0)

aha_clients = {}

async def addAhaUrl(url):
    '''
    Add (incref) an aha registry URL.

    NOTE: You may also add a list of redundant URLs.
    '''
    hkey = s_hashitem.normitem(url)

    info = aha_clients.get(hkey)
    if info is None:
        info = aha_clients[hkey] = {'refs': 0, 'client': None, 'url': url}

    info['refs'] += 1
    return info

async def delAhaUrl(url):
    '''
    Remove (decref) an aha registry URL.

    NOTE: You may also remove a list of redundant URLs.
    '''
    hkey = s_hashitem.normitem(url)

    info = aha_clients.get(hkey)
    if info is None:
        return 0

    info['refs'] -= 1

    refs = info['refs']

    if refs == 0:
        client = info.get('client')
        if client is not None:
            await client.fini()

        aha_clients.pop(hkey, None)

    return refs

def zipurl(info):
    '''
    Reconstruct a URL string from a parsed telepath info dict.
    '''
    # copy to prevent mutation
    info = dict(info)

    host = info.pop('host', None)
    port = info.pop('port', None)
    path = info.pop('path', None)
    user = info.pop('user', None)
    passwd = info.pop('passwd', None)
    scheme = info.pop('scheme', None)

    url = f'{scheme}://'
    if user:
        url += user
        if passwd:
            url += f':{passwd}'
        url += '@'

    if host:
        url += host
        if port is not None:
            url += f':{port}'

    if path:
        url += f'{path}'

    if info:
        params = '&'.join([f'{k}={v}' for (k, v) in info.items()])
        url += f'?{params}'

    return url

def modurl(url, **info):
    if isinstance(url, str):
        urlinfo = chopurl(url)
        for k, v in info.items():
            urlinfo[k] = v
        return zipurl(urlinfo)
    return [modurl(u, **info) for u in url]

def mergeAhaInfo(info0, info1):

    # info0 - local urlinfo
    # info1 - urlinfo provided by aha

    # copy both to prevent mutation
    info0 = copy.deepcopy(info0)
    info1 = copy.deepcopy(info1)

    # local path wins
    info1.pop('path', None)

    # local user wins if specified
    if info0.get('user') is not None:
        info1.pop('user', None)

    # upstream wins everything else
    info0.update(info1)

    return info0

async def getAhaProxy(urlinfo):
    '''
    Return a telepath proxy by looking up a host from an aha registry.
    '''
    host = urlinfo.get('host')
    if host is None:
        mesg = f'getAhaProxy urlinfo has no host: {urlinfo}'
        raise s_exc.NoSuchName(mesg=mesg)

    if not aha_clients:
        mesg = f'No aha servers registered to lookup {host}'
        raise s_exc.NotReady(mesg=mesg)

    laste = None
    for ahaurl, cnfo in list(aha_clients.items()):
        client = cnfo.get('client')
        if client is None:
            client = await Client.anit(cnfo.get('url'))
            client._fini_atexit = True
            cnfo['client'] = client

        try:
            proxy = await client.proxy(timeout=5)

            cellinfo = await asyncio.wait_for(proxy.getCellInfo(), timeout=5)

            if cellinfo['synapse']['version'] >= (2, 95, 0):
                filters = {
                    'mirror': bool(yaml.safe_load(urlinfo.get('mirror', 'false')))
                }
                ahasvc = await asyncio.wait_for(proxy.getAhaSvc(host, filters=filters), timeout=5)
            else:
                ahasvc = await asyncio.wait_for(proxy.getAhaSvc(host), timeout=5)

            if ahasvc is None:
                continue

            svcinfo = ahasvc.get('svcinfo', {})
            if not svcinfo.get('online'):
                continue

            info = mergeAhaInfo(urlinfo, svcinfo.get('urlinfo', {}))

            return await openinfo(info)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            if isinstance(ahaurl, str):
                surl = s_urlhelp.sanitizeUrl(ahaurl)
            else:
                surl = tuple([s_urlhelp.sanitizeUrl(u) for u in ahaurl])
            logger.exception(f'Unable to get aha client ({surl})')

            laste = e

    if laste is not None:
        raise laste

    mesg = f'aha lookup failed: {host}'
    raise s_exc.NoSuchName(mesg=mesg)

@contextlib.asynccontextmanager
async def withTeleEnv():

    async with loadTeleCell('/vertex/storage'):

        yamlpath = s_common.getSynPath('telepath.yaml')
        telefini = await loadTeleEnv(yamlpath)

        certpath = s_common.getSynPath('certs')
        s_certdir.addCertPath(certpath)

        try:

            yield

        finally:

            s_certdir.delCertPath(certpath)

            if telefini is not None:
                await telefini()

async def loadTeleEnv(path):

    path = s_common.genpath(path)

    if not os.path.isfile(path):
        return

    conf = s_common.yamlload(path)

    vers = conf.get('version')
    if vers != 1:
        logger.warning(f'telepath.yaml unknown version: {vers}')
        return

    ahas = conf.get('aha:servers', ())
    cdirs = conf.get('certdirs', ())

    for a in ahas:
        await addAhaUrl(a)

    for p in cdirs:
        s_certdir.addCertPath(p)

    async def fini():
        for a in ahas:
            await delAhaUrl(a)
        for p in cdirs:
            s_certdir.delCertPath(p)

    return fini

@contextlib.asynccontextmanager
async def loadTeleCell(dirn):

    certpath = s_common.genpath(dirn, 'certs')
    confpath = s_common.genpath(dirn, 'cell.yaml')

    usecerts = os.path.isdir(certpath)

    ahaurl = None
    if os.path.isfile(confpath):
        conf = s_common.yamlload(confpath)
        ahaurl = conf.get('aha:registry')

    if usecerts:
        s_certdir.addCertPath(certpath)

    if ahaurl:
        await addAhaUrl(ahaurl)

    try:

        yield

    finally:

        if usecerts:
            s_certdir.delCertPath(certpath)

        if ahaurl:
            await delAhaUrl(ahaurl)

class Aware:
    '''
    The telepath.Aware mixin allows shared objects to
    handle individual links managed by the Daemon.
    '''
    async def getTeleApi(self, link, mesg, path):
        '''
        Return a shared object for this link.
        Args:
            link (synapse.lib.link.Link): A network link.
            mesg ((str,dict)): The tele:syn handshake message.

        '''
        return self

    def onTeleShare(self, dmon, name):
        pass

class Task:
    '''
    A telepath Task is used to internally track calls/responses.
    '''
    def __init__(self):
        self.retn = None
        self.iden = s_common.guid()
        self.done = asyncio.Event()

    async def result(self):
        await self.done.wait()
        return self.retn

    def reply(self, retn):
        self.retn = retn
        self.done.set()

class Share(s_base.Base):
    '''
    The telepath client side of a dynamically shared object.
    '''
    async def __anit__(self, proxy, iden, sharinfo=None):
        await s_base.Base.__anit__(self)
        self.iden = iden
        self.proxy = proxy

        if sharinfo is None:
            sharinfo = {}
        self.sharinfo = sharinfo
        self.methinfo = sharinfo.get('meths', {})
        self.proxy.shares[iden] = self

        self.txfini = True
        self.onfini(self._txShareFini)

    async def _txShareFini(self):

        self.proxy.shares.pop(self.iden, None)

        if not self.txfini:
            return

        mesg = ('share:fini', {'share': self.iden})
        if not self.proxy.link.isfini:
            await self.proxy.link.tx(mesg)

    def __getattr__(self, name):
        info = self.methinfo.get(name)
        if info is not None and info.get('genr'):
            meth = GenrMethod(self.proxy, name, share=self.iden)
            setattr(self, name, meth)
            return meth

        meth = Method(self.proxy, name, share=self.iden)
        setattr(self, name, meth)
        return meth

    def __enter__(self):
        '''
        Convenience function to enable using Proxy objects as synchronous context managers.

        Note:
            This should never be used by synapse core code.  This is for sync client code convenience only.
        '''
        if s_threads.iden() == self.tid:
            raise s_exc.SynErr('Use of synchronous context manager in async code')

        self._ctxobj = self.schedCoroSafePend(self.__aenter__())
        return self

    def __exit__(self, *args):
        '''
        This should never be used by synapse core code.  This is for sync client code convenience only.
        '''
        return self.schedCoroSafePend(self._ctxobj.__aexit__(*args))

class Genr(Share):

    async def __anit__(self, proxy, iden):
        await Share.__anit__(self, proxy, iden, sharinfo={})
        self.queue = await s_queue.AQueue.anit()
        self.onfini(self.queue.fini)

    async def _onShareData(self, data):
        self.queue.put(data)

    async def __aiter__(self):

        try:
            while not self.isfini:

                for retn in await self.queue.slice():
                    if retn is None:
                        return

                    yield s_common.result(retn)

            raise s_exc.LinkShutDown(mesg='Remote peer disconnected')

        finally:
            await self.fini()

    def __iter__(self):

        try:
            while not self.isfini:

                for retn in s_glob.sync(self.queue.slice()):

                    if retn is None:
                        return

                    yield s_common.result(retn)

        finally:
            s_glob.sync(self.fini())

sharetypes = {
    'share': Share,
    'genr': Genr,
}

class Method:
    '''
    The telepath Method is used to provide proxy method calls.
    '''
    def __init__(self, proxy, name, share=None):
        self.name = name
        self.share = share
        self.proxy = proxy

        # act as much like a bound method as possible...
        self.__name__ = name
        self.__self__ = proxy

    @s_glob.synchelp
    async def __call__(self, *args, **kwargs):
        todo = (self.name, args, kwargs)
        return await self.proxy.task(todo, name=self.share)

class GenrIter:
    '''
    An object to help delay a telepath call until iteration.
    '''
    def __init__(self, proxy, todo, share):
        self.todo = todo
        self.proxy = proxy
        self.share = share

    async def list(self):
        return [x async for x in self]

    async def __aiter__(self):

        genr = await self.proxy.task(self.todo, name=self.share)
        if genr is None:
            return

        async for item in genr:
            yield item
            await asyncio.sleep(0)

    def __iter__(self):
        genr = s_glob.sync(self.proxy.task(self.todo, name=self.share))
        for item in genr:
            yield item

class GenrMethod(Method):

    def __call__(self, *args, **kwargs):
        todo = (self.name, args, kwargs)
        return GenrIter(self.proxy, todo, self.share)

class Pipeline(s_base.Base):

    async def __anit__(self, proxy, genr, name=None):

        await s_base.Base.__anit__(self)

        self.genr = genr
        self.name = name
        self.proxy = proxy

        self.count = 0

        self.link = await proxy.getPoolLink()
        self.task = self.schedCoro(self._runGenrLoop())
        self.taskexc = None

    async def _runGenrLoop(self):

        try:
            async for todo in self.genr:

                mesg = ('t2:init', {
                        'todo': todo,
                        'name': self.name,
                        'sess': self.proxy.sess})

                await self.link.tx(mesg)
                self.count += 1

        except asyncio.CancelledError:
            raise

        except Exception as e:
            self.taskexc = e
            await self.link.fini()
            raise

    async def __aiter__(self):

        taskdone = False
        while not self.isfini:

            if not taskdone and self.task.done():
                taskdone = True
                self.task.result()

            if taskdone and self.count == 0:
                if not self.link.isfini:
                    await self.proxy._putPoolLink(self.link)
                await self.fini()
                return

            mesg = await self.link.rx()
            if self.taskexc:
                raise self.taskexc

            if mesg is None:
                raise s_exc.LinkShutDown(mesg='Remote peer disconnected')

            if mesg[0] == 't2:fini':
                self.count -= 1
                yield mesg[1].get('retn')
                continue

            logger.warning(f'Pipeline got unhandled message: {mesg!r}.')  # pragma: no cover

class Proxy(s_base.Base):
    '''
    A telepath Proxy is used to call remote APIs on a shared object.

    Example:

        import synapse.telepath as s_telepath

        # open the "foo" object shared in a dmon on localhost:3344

        async def doFooThing():

            proxy = await s_telepath.openurl('tcp://127.0.0.1:3344/foo')

            valu = await proxy.getFooValu(x, y)

    The proxy (and openurl function) may also be used from sync code:

        proxy = s_telepath.openurl('tcp://127.0.0.1:3344/foo')

        valu = proxy.getFooValu(x, y)

    '''
    async def __anit__(self, link, name):

        await s_base.Base.__anit__(self)
        self.tid = s_threads.iden()

        self.link = link
        self.name = name

        self.tasks = {}
        self.shares = {}

        self.sharinfo = {}
        self.methinfo = {}

        self.sess = None
        self.links = collections.deque()
        self._link_poolsize = 4

        self.synack = None
        self.syndone = asyncio.Event()

        self.handlers = {
            'task:fini': self._onTaskFini,
            'share:data': self._onShareData,
            'share:fini': self._onShareFini,
        }

        async def fini():

            for item in list(self.shares.values()):
                await item.fini()

            mesg = ('task:fini', {'retn': (False, ('IsFini', {}))})
            for name, task in list(self.tasks.items()):
                task.reply(mesg)
                del self.tasks[name]

            for link in self.links:
                await link.fini()

            del self.syndone
            await self.link.fini()

        self.onfini(fini)
        self.link.onfini(self.fini)

    def _getSynVers(self):
        '''
        Helper method to retrieve the remote Synapse version from Proxy.

        Notes:
            This will return None if the synapse version was not supplied
            during the Telepath handshake.

        Returns:
            tuple: A tuple of major, minor, patch information as integers.
        '''
        version = self.sharinfo.get('syn:version')
        return version

    def _getSynCommit(self):
        '''
        Helper method to retrieve the remote Synapse commit hash from Proxy.

        Notes:
            This will return None if the synapse commit hash was not supplied
            during the Telepath handshake.

        Returns:
            str: A string containing the commit hash. This may be a empty string.
        '''
        return self.sharinfo.get('syn:commit')

    def _getClasses(self):
        '''
        Helper method to retrieve the classes that comprise the remote object.

        Notes:
            This will return None if the class version was not supplied
            during the Telepath handshake.

        Returns:
            tuple: A tuple of strings containing the class paths for the remote object.
        '''
        classes = self.sharinfo.get('classes')
        return classes

    async def getPoolLink(self):

        while self.links and not self.isfini:

            link = self.links.popleft()

            if link.isfini:
                continue

            return link

        # we need a new one...
        return await self._initPoolLink()

    async def getPipeline(self, genr, name=None):
        '''
        Construct a proxy API call pipeline in order to make
        multiple telepath API calls while minimizing round trips.

        Args:
            genr (async generator): An async generator that yields todo tuples.
            name (str): The name of the shared object on the daemon.

        Example:

            def genr():
                yield s_common.todo('getFooByBar', 10)
                yield s_common.todo('getFooByBar', 20)

            for retn in proxy.getPipeline(genr()):
                valu = s_common.result(retn)
        '''
        async with await Pipeline.anit(self, genr, name=name) as pipe:
            async for retn in pipe:
                yield retn

    async def _initPoolLink(self):

        # TODO loop / backoff

        if self.link.get('unix'):

            path = self.link.get('path')
            link = await s_link.unixconnect(path)

        else:

            ssl = self.link.get('ssl')
            host = self.link.get('host')
            port = self.link.get('port')

            link = await s_link.connect(host, port, ssl=ssl)

        self.onfini(link)

        return link

    async def _putPoolLink(self, link):

        if link.isfini:
            return

        # If we've exceeded our poolsize, discard the current link.
        if len(self.links) >= self._link_poolsize:
            return await link.fini()

        self.links.append(link)

    def __enter__(self):
        '''
        Convenience function to enable using Proxy objects as synchronous context managers.

        Note:
            This must not be used from async code, and it should never be used in core synapse code.
        '''
        if s_threads.iden() == self.tid:
            raise s_exc.SynErr('Use of synchronous context manager in async code')
        self._ctxobj = self.schedCoroSafePend(self.__aenter__())
        return self

    def __exit__(self, *args):
        '''
        Note:
            This should never be used by core synapse code.
        '''
        return self.schedCoroSafePend(self._ctxobj.__aexit__(*args))

    async def _onShareFini(self, mesg):

        iden = mesg[1].get('share')
        share = self.shares.get(iden)
        if share is None:
            return

        share.txfini = False
        await share.fini()

    async def _onShareData(self, mesg):

        data = mesg[1].get('data')
        iden = mesg[1].get('share')

        share = self.shares.get(iden)
        if share is None:
            return

        await share._onShareData(data)

    async def call(self, methname, *args, **kwargs):
        '''
        Call a remote method by name.

        Args:
            methname (str): The name of the remote method.
            *args: Arguments to the method call.
            **kwargs: Keyword arguments to the method call.

        Most use cases will likely use the proxy methods directly:

        The following two are effectively the same:

            valu = proxy.getFooBar(x, y)
            valu = proxy.call('getFooBar', x, y)
        '''
        todo = (methname, args, kwargs)
        return await self.task(todo)

    async def taskv2(self, todo, name=None):

        mesg = ('t2:init', {
                'todo': todo,
                'name': name,
                'sess': self.sess})

        link = await self.getPoolLink()

        await link.tx(mesg)

        mesg = await link.rx()
        if mesg is None:
            raise s_exc.LinkShutDown(mesg='Remote peer disconnected')

        if mesg[0] == 't2:fini':
            await self._putPoolLink(link)
            retn = mesg[1].get('retn')
            return s_common.result(retn)

        if mesg[0] == 't2:genr':

            async def genrloop():

                try:

                    while True:

                        mesg = await link.rx()
                        if mesg is None:
                            raise s_exc.LinkShutDown(mesg=mesg)

                        if mesg[0] != 't2:yield':  # pragma: no cover
                            info = 'Telepath protocol violation:  unexpected message received'
                            raise s_exc.BadMesgFormat(mesg=info)

                        retn = mesg[1].get('retn')
                        if retn is None:
                            await self._putPoolLink(link)
                            return

                        # if this is an exception, it's the end...
                        if not retn[0]:
                            await self._putPoolLink(link)

                        yield s_common.result(retn)

                except GeneratorExit:
                    # if they bail early on the genr, fini the link
                    await link.fini()

            return s_coro.GenrHelp(genrloop())

        if mesg[0] == 't2:share':
            iden = mesg[1].get('iden')
            sharinfo = mesg[1].get('sharinfo')
            await self._putPoolLink(link)
            return await Share.anit(self, iden, sharinfo)

    async def task(self, todo, name=None):

        if self.isfini:
            raise s_exc.IsFini(mesg='Telepath Proxy isfini')

        if self.sess is not None:
            return await self.taskv2(todo, name=name)

        task = Task()

        mesg = ('task:init', {
                'task': task.iden,
                'todo': todo,
                'name': name, })

        self.tasks[task.iden] = task

        try:

            await self.link.tx(mesg)
            retn = await task.result()
            return s_common.result(retn)

        finally:
            self.tasks.pop(task.iden, None)

    async def handshake(self, auth=None):

        mesg = ('tele:syn', {
            'auth': auth,
            'vers': televers,
            'name': self.name,
        })

        await self.link.tx(mesg)

        self.synack = await self.link.rx()
        if self.synack is None:
            mesg = 'socket closed by server before handshake'
            raise s_exc.LinkShutDown(mesg=mesg)

        self.sess = self.synack[1].get('sess')
        self.sharinfo = self.synack[1].get('sharinfo', {})
        self.methinfo = self.sharinfo.get('meths', {})

        vers = self.synack[1].get('vers')
        if vers[0] != televers[0]:
            raise s_exc.BadMesgVers(myver=televers, hisver=vers)

        async def rxloop():

            while not self.link.isfini:

                mesg = await self.link.rx()
                if mesg is None:
                    return

                try:

                    func = self.handlers.get(mesg[0])
                    if func is None:
                        logger.warning('Proxy.rxloop: Invalid Message: %r' % (mesg,))
                        return

                    await func(mesg)

                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                    raise

                except Exception:
                    logger.exception('Proxy.rxloop for %r' % (mesg,))

        retn = self.synack[1].get('retn')
        valu = s_common.result(retn)

        self.schedCoro(rxloop())

        return valu

    async def _txShareExc(self, iden):
        # send a share:fini for an unhandled share.
        await self.link.tx(
            ('share:fini', {'share': iden, 'isexc': True})
        )

    async def _onTaskFini(self, mesg):

        # handle task:fini message
        iden = mesg[1].get('task')

        task = self.tasks.pop(iden, None)
        if task is None:
            logger.warning('task:fini for invalid task: %r' % (iden,))
            return

        retn = mesg[1].get('retn')
        type = mesg[1].get('type')

        if type is None:
            return task.reply(retn)

        ctor = sharetypes.get(type, Share)
        item = await ctor.anit(self, retn[1])

        return task.reply((True, item))

    def __getattr__(self, name):

        info = self.methinfo.get(name)
        if info is not None and info.get('genr'):
            meth = GenrMethod(self, name)
            setattr(self, name, meth)
            return meth

        meth = Method(self, name)
        setattr(self, name, meth)
        return meth

class Client(s_base.Base):
    '''
    A Telepath client object which reconnects and allows waiting for link up.

    Notes:

        The conf data allows changing parameters such as timeouts, retry period, and link pool size. The default
        conf data can be seen below::

            conf = {
                'timeout': 10,
                'retrysleep': 0.2,
                'link_poolsize': 4,
            }

    '''
    async def __anit__(self, url, opts=None, conf=None, onlink=None):

        await s_base.Base.__anit__(self)

        if conf is None:
            conf = {}

        if opts is None:
            opts = {}

        self._t_url = url
        self._t_urls = collections.deque()

        self._t_opts = opts
        self._t_conf = conf

        self._t_proxy = None
        self._t_ready = asyncio.Event()
        self._t_onlinks = []
        self._t_methinfo = None
        self._t_named_meths = set()

        if onlink is not None:
            self._t_onlinks.append(onlink)

        async def fini():
            if self._t_proxy is not None:
                await self._t_proxy.fini()
            # Wake any waiters which may be waiting on waitready() calls so those
            # without timeouts specified are not waiting forever.
            self._t_ready.set()

        self.onfini(fini)

        await self._fireLinkLoop()

    def _initUrlDeque(self):
        self._t_urls.clear()
        if isinstance(self._t_url, str):
            self._t_urls.append(self._t_url)
            return
        self._t_urls.extend(self._t_url)

    def _getNextUrl(self):
        # TODO url list in deque
        if not self._t_urls:
            self._initUrlDeque()
        return self._t_urls.popleft()

    def _setNextUrl(self, url):
        self._t_urls.appendleft(url)

    async def onlink(self, func):
        self._t_onlinks.append(func)
        if self._t_proxy:
            await func(self._t_proxy)

    async def offlink(self, func):
        self._t_onlinks.remove(func)

    async def _fireLinkLoop(self):
        self._t_proxy = None
        self._t_ready.clear()
        self.schedCoro(self._teleLinkLoop())

    async def _teleLinkLoop(self):
        lastlog = 0.0

        while not self.isfini:

            url = self._getNextUrl()

            try:
                await self._initTeleLink(url)
                self._t_ready.set()
                return

            except s_exc.TeleRedir as e:
                self._setNextUrl(e.errinfo.get('url'))
                continue

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception as e:
                now = time.monotonic()
                if now > lastlog + 60.0:  # don't logspam the disconnect message more than 1/min
                    logger.exception(f'telepath client ({s_urlhelp.sanitizeUrl(url)}) encountered an error: {e}')
                    lastlog = now
                await self.waitfini(timeout=self._t_conf.get('retrysleep', 0.2))

    async def proxy(self, timeout=10):
        await self.waitready(timeout=timeout)
        ret = self._t_proxy
        if ret is None or ret.isfini is True:
            raise s_exc.IsFini(mesg='Telepath Client Proxy is not available.')
        return ret

    async def _initTeleLink(self, url):
        self._t_proxy = await openurl(url, **self._t_opts)
        self._t_methinfo = self._t_proxy.methinfo
        self._t_proxy._link_poolsize = self._t_conf.get('link_poolsize', 4)

        async def fini():
            if self._t_named_meths:
                for name in self._t_named_meths:
                    delattr(self, name)
                self._t_named_meths.clear()
            if not self.isfini:
                await self._fireLinkLoop()

        self._t_proxy.onfini(fini)

        for onlink in self._t_onlinks:
            try:
                await onlink(self._t_proxy)
                # in case the callback fini()s the proxy
                if self._t_proxy is None:
                    break
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.exception(f'onlink: {onlink}')

    async def task(self, todo, name=None):
        # implement the main workhorse method for a proxy to allow Method
        # objects to use us as the proxy.
        while not self.isfini:
            try:
                await self.waitready()

                # there is a small race where the daemon may fini the proxy
                # account for that here...
                if self._t_proxy is None or self._t_proxy.isfini:
                    self._t_ready.clear()
                    continue

                return await self._t_proxy.task(todo, name=name)

            except s_exc.TeleRedir as e:
                url = e.errinfo.get('url')
                self._setNextUrl(url)
                logger.warning(f'telepath task redirected: ({s_urlhelp.sanitizeUrl(url)})')
                await self._t_proxy.fini()

        raise s_exc.IsFini(mesg='Telepath Client isfini')

    async def waitready(self, timeout=10):
        await asyncio.wait_for(self._t_ready.wait(), self._t_conf.get('timeout', timeout))

    def __getattr__(self, name):
        if self._t_methinfo is None:
            raise s_exc.NotReady(mesg='Must call waitready() on Client before first method call')

        info = self._t_methinfo.get(name)
        if info is not None and info.get('genr'):
            meth = GenrMethod(self, name)
            setattr(self, name, meth)
            self._t_named_meths.add(name)
            return meth

        meth = Method(self, name)
        self._t_named_meths.add(name)
        setattr(self, name, meth)
        return meth

    def _getSynVers(self):
        '''
        Helper method to retrieve the remote Synapse version from Client
        for the currently connected Proxy.

        Notes:
            This will return None if the synapse version was not supplied
            during the Telepath handshake.

        Returns:
            tuple: A tuple of major, minor, patch information as integers.
        '''
        return self._t_proxy._getSynVers()

    def _getSynCommit(self):
        '''
        Helper method to retrieve the remote Synapse commit hash from Proxy.

        Notes:
            This will return None if the synapse commit hash was not supplied
            during the Telepath handshake.

        Returns:
            str: A string containing the commit hash. This may be a empty string.
        '''
        return self._t_proxy._getSynCommit()

    def _getClasses(self):
        '''
        Helper method to retrieve the classes that comprise the remote object
        for the currently connected Proxy.

        Notes:
            This will return None if the class version was not supplied
            during the Telepath handshake.

        Returns:
            tuple: A tuple of strings containing the class paths for the remote object.
        '''
        return self._t_proxy._getClasses()

async def disc_consul(info):
    '''
    Support for updating a URL info dictionary which came from a protocol+consul:// URL.

    Notes:
        This updates the info-dictionary in place, placing the ``host`` value into
        an ``original_host`` key, and updating ``host`` and ``port``.

        By default we pull the ``host`` value from the catalog ``Address`` value,
        and the ``port`` from the ``ServicePort`` value.

        The following HTTP parameters are supported:

        - consul: This is the consul host (schema, fqdn and port) to connect to.
        - consul_tag: If set, iterate through the catalog results until a result
          is found which matches the tag value. This is a case sensitive match.
        - consul_tag_address: If set, prefer the ``TaggedAddresses`` from the catalog.
        - consul_service_tag_address: If set, prefer the associated value from the
          ``ServiceTaggedAddresses`` field.
        - consul_nosslverify: If set, disables SSL verification.

    '''
    info.setdefault('original_host', info.get('host'))
    service = info.get('original_host')
    host = info.get('consul')
    tag = info.get('consul_tag')  # iterate through entries until a match for tag is present.
    ctag_addr = info.get('consul_tag_address')  # Prefer a taggedAddress if set
    csvc_tag_addr = info.get('consul_service_tag_address')  # Prefer a serviceTaggedAddress if set
    gkwargs = {'raise_for_status': True}
    if info.get('consul_nosslverify'):
        gkwargs['ssl'] = False

    if ctag_addr and csvc_tag_addr:
        mesg = 'Cannot resolve consul values with both consul_tag_address and consul_service_tag_address'
        raise s_exc.BadUrl(mesg=mesg, consul_tag_address=ctag_addr,
                           consul_service_tag_address=csvc_tag_addr)

    url = f'{host}/v1/catalog/service/{service}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **gkwargs) as resp:
                if resp.status == 200:
                    found = await resp.json()
                    for entry in found:

                        # If the consul_tag parameter is passed, we will iterate over
                        # the Consul results until we find the service which matches
                        # our requested tag. Otherwise, we will grab data from the
                        # first record from the service catalog.
                        if tag and tag not in entry.get('ServiceTags'):
                            continue

                        if csvc_tag_addr:
                            # Use the ServiceTaggedAddresses
                            info['host'] = entry['ServiceTaggedAddresses'][csvc_tag_addr]['address']
                            info['port'] = entry['ServiceTaggedAddresses'][csvc_tag_addr]['port']
                        elif ctag_addr:
                            # Use the TaggedAddresses values.
                            info['host'] = entry['TaggedAddresses'][ctag_addr]
                            info['port'] = entry['ServicePort']
                        else:
                            # Use the generic service address/port
                            info['host'] = entry['Address']
                            info['port'] = entry['ServicePort']
                        return

    except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
        raise
    except Exception as e:
        raise s_exc.BadUrl(mesg=f'Unknown error while resolving service name [{service}] via consul [{str(e)}].',
                           name=service, consul=host) from e
    raise s_exc.BadUrl(mesg=f'Unable to resolve service information from consul for [{service}].',
                       name=service, consul=host, tag=tag)

def alias(name):
    '''
    Resolve a telepath alias via ~/.syn/aliases.yaml

    Args:
        name (str): Name of the alias to resolve.

    Notes:
        An exact match against the aliases will always be returned first.
        If no exact match is found and the name contains a '/' in it, the
        value before the slash is looked up and the remainder of the path
        is joined to any result. This is done to support dynamic Telepath
        share names.

    Returns:
        str: The url string, if present in the alias.  None will be returned
        if there are no matches.
    '''
    path = s_common.getSynPath('aliases.yaml')
    if not os.path.isfile(path):
        return None

    conf = s_common.yamlload(path)

    # Is there an exact match - if so, return it.
    url = conf.get(name)
    if url:
        return url

    # Since telepath supports dynamic shared object access,
    # slice a name at the first '/', look up using that value
    # and then append the second value to it.
    dynname = None
    if '/' in name:
        name, dynname = name.split('/', 1)
    url = conf.get(name)
    if url and dynname:
        url = '/'.join([url, dynname])

    return url

@s_glob.synchelp
async def openurl(url, **opts):
    '''
    Open a URL to a remote telepath object.

    Args:
        url (str): A telepath URL.
        **opts (dict): Telepath connect options.

    Returns:
        (synapse.telepath.Proxy): A telepath proxy object.

    The telepath proxy may then be used for sync or async calls:

        proxy = openurl(url)
        value = proxy.getFooThing()

    ... or ...

        proxy = await openurl(url)
        valu = await proxy.getFooThing()

    ... or ...

        async with await openurl(url) as proxy:
            valu = await proxy.getFooThing()
    '''
    info = chopurl(url, **opts)
    return await openinfo(info)

def chopurl(url, **opts):

    if isinstance(url, str):
        if url.find('://') == -1:
            newurl = alias(url)
            if newurl is None:
                raise s_exc.BadUrl(mesg=f':// not found in [{url}] and no alias found!',
                                   url=url)
            url = newurl

        info = s_urlhelp.chopurl(url)

        # flatten query params into info
        query = info.pop('query', None)
        if query is not None:
            info.update(query)

    elif isinstance(url, dict):
        info = dict(url)

    else:
        mesg = 'telepath.chopurl() requires a str or dict.'
        raise s_exc.BadArg(mesg)

    info.update(opts)

    return info

class TeleSSLObject(ssl.SSLObject):

    def do_handshake(self):
        # steal a reference for later so we can get the cert
        self.context.telessl = self
        return ssl.SSLObject.do_handshake(self)

async def openinfo(info):

    scheme = info.get('scheme')

    if scheme == 'aha':
        return await getAhaProxy(info)

    if '+' in scheme:
        scheme, disc = scheme.split('+', 1)
        # Discovery protocols modify info dict inband?
        if disc == 'consul':
            await disc_consul(info)

        else:
            raise s_exc.BadUrl(mesg=f'Unknown discovery protocol [{disc}].',
                               disc=disc)

    host = info.get('host')
    port = info.get('port')

    auth = None

    user = info.get('user')
    if user is not None:
        passwd = info.get('passwd')
        auth = (user, {'passwd': passwd})

    if scheme == 'cell':
        # cell:///path/to/celldir:share
        # cell://rel/path/to/celldir:share
        path = info.get('path')

        name = info.get('name', '*')

        # support cell://<relpath>/<to>/<cell>
        # by detecting host...
        host = info.get('host')
        if host:
            path = path.strip('/')
            path = os.path.join(host, path)

        if ':' in path:
            path, name = path.split(':')

        full = os.path.join(path, 'sock')
        link = await s_link.unixconnect(full)

    elif scheme == 'unix':
        # unix:///path/to/sock:share
        name = '*'
        path = info.get('path')
        if ':' in path:
            path, name = path.split(':')
        link = await s_link.unixconnect(path)

    else:

        path = info.get('path')
        name = info.get('name', path[1:])

        if port is None:
            port = 27492

        hostname = None

        sslctx = None

        linkinfo = {}

        if scheme == 'ssl':

            certdir = info.get('certdir')
            certhash = info.get('certhash')
            certname = info.get('certname')
            hostname = info.get('hostname', host)

            linkinfo['certhash'] = certhash
            linkinfo['hostname'] = hostname

            if certdir is None:
                certdir = s_certdir.getCertDir()

            # if a TLS connection specifies a user with no password
            # attempt to auto-resolve a user certificate for the given
            # host/network.
            if certname is None and user is not None and passwd is None:
                certname = f'{user}@{hostname}'

            if certhash is None:
                sslctx = certdir.getClientSSLContext(certname=certname)
            else:
                sslctx = ssl.create_default_context()
                sslctx.check_hostname = False
                sslctx.verify_mode = ssl.CERT_NONE
                sslctx.sslobject_class = TeleSSLObject

            # do hostname checking manually to avoid DNS lookups
            # ( to support dynamic IP addresses on services )
            sslctx.check_hostname = False

            linkinfo['ssl'] = sslctx

        link = await s_link.connect(host, port, linkinfo=linkinfo)

    prox = await Proxy.anit(link, name)
    prox.onfini(link)

    try:
        await prox.handshake(auth=auth)

    except (asyncio.CancelledError, Exception):
        await prox.fini()
        raise

    return prox
