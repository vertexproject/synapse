'''
An RMI framework for synapse.
'''

import os
import asyncio
import logging
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

logger = logging.getLogger(__name__)

televers = (3, 0)

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
                            return

                        assert mesg[0] == 't2:yield'

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
            raise s_exc.IsFini()

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
        self._t_onlink = onlink
        self._t_methinfo = None
        self._t_named_meths = set()

        async def fini():
            if self._t_proxy is not None:
                await self._t_proxy.fini()
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

    async def _fireLinkLoop(self):
        self._t_proxy = None
        self._t_ready.clear()
        self.schedCoro(self._teleLinkLoop())

    async def _teleLinkLoop(self):

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
                logger.warning(f'telepath client ({s_urlhelp.sanitizeUrl(url)}): {e}')
                await self.waitfini(timeout=self._t_conf.get('retrysleep', 0.2))

    async def proxy(self, timeout=10):
        await self.waitready(timeout=timeout)
        return self._t_proxy

    async def _initTeleLink(self, url):
        if self._t_proxy is not None:
            await self._t_proxy.fini()

        self._t_proxy = await openurl(url, **self._t_opts)
        self._t_methinfo = self._t_proxy.methinfo
        self._t_proxy._link_poolsize = self._t_conf.get('link_poolsize', 4)

        if self._t_onlink is not None:
            await self._t_onlink(self._t_proxy)

        async def fini():
            if self._t_named_meths:
                for name in self._t_named_meths:
                    delattr(self, name)
                self._t_named_meths.clear()
            await self._fireLinkLoop()

        self._t_proxy.onfini(fini)

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
    query = info.get('query')
    host = query.get('consul')
    tag = query.get('consul_tag')  # iterate through entries until a match for tag is present.
    ctag_addr = query.get('consul_tag_address')  # Prefer a taggedAddress if set
    csvc_tag_addr = query.get('consul_service_tag_address')  # Prefer a serviceTaggedAddress if set
    gkwargs = {'raise_for_status': True}
    if query.get('consul_nosslverify'):
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
    if url.find('://') == -1:
        newurl = alias(url)
        if newurl is None:
            raise s_exc.BadUrl(mesg=f':// not found in [{url}] and no alias found!',
                               url=url)
        url = newurl

    info = s_urlhelp.chopurl(url)
    info.update(opts)

    scheme = info.get('scheme')

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

        sslctx = None
        if scheme == 'ssl':

            certname = None
            certpath = None

            certdir = opts.get('certdir')

            query = info.get('query')
            if query is not None:
                certpath = query.get('certdir')
                certname = query.get('certname')

            if certdir is None:
                certdir = s_certdir.CertDir(certpath)

            sslctx = certdir.getClientSSLContext(certname=certname)

        link = await s_link.connect(host, port, ssl=sslctx)

    prox = await Proxy.anit(link, name)
    prox.onfini(link)

    try:
        await prox.handshake(auth=auth)

    except (asyncio.CancelledError, Exception):
        await prox.fini()
        raise

    return prox
