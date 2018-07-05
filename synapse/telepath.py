'''
An RMI framework for synapse.
'''

import os
import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.urlhelp as s_urlhelp

logger = logging.getLogger(__name__)

televers = (4, 0)

class Aware:
    '''
    The telepath.Aware mixin allows shared objects to
    handle individual links managed by the Daemon.
    '''
    def getTeleApi(self, link, mesg):
        '''
        Return a shared object for this link.
        Args:
            link (synapse.lib.link.Link): A network link.
            mesg ((str,dict)): The tele:syn handshake message.
        '''
        return self

    def onTeleShare(self, dmon, name):
        pass

    def onTeleOpen(self, link, path):
        '''
        Allow a telepath share to create a new sub-share.
        '''
        return None


class Share(s_coro.Fini):
    '''
    The telepath client side of a dynamically shared object.
    '''
    def __init__(self, proxy, iden):
        s_coro.Fini.__init__(self)
        self.iden = iden
        self.proxy = proxy

    def __getattr__(self, name):
        meth = Method(self.proxy, name, share=self.iden)
        setattr(self, name, meth)
        return meth

class Genr:

    def __init__(self, proxy, link):
        self.link = link
        self.proxy = proxy

    async def __aiter__(self):

        try:

            while not self.link.isfini:

                mesg = await self.link.rx()
                if mesg is None:
                    raise s_exc.LinkClosed()

                if mesg[0] == 'genr:data':
                    yield mesg[1]
                    continue

                if mesg[0] == 'genr:fini':
                    # clean exit...
                    await self.proxy._putPoolLink(self.link)
                    self.link = None
                    return

                if mesg[0] == 'genr:errx':
                    # clean exit...
                    await self.proxy._putPoolLink(self.link)
                    # this will raise...
                    s_common.result(mesg[1])

        except Exception as e:
            # this includes GeneratorExit
            await link.fini()
            return

    def __iter__(self):

        # a clone of above with sync() wrappers
        try:

            while not self.link.isfini:

                mesg = s_glob.sync(self.link.rx())
                if mesg is None:
                    raise s_exc.LinkClosed()

                if mesg[0] == 'genr:data':
                    yield mesg[1]
                    continue

                if mesg[0] == 'genr:fini':
                    # clean exit...
                    s_glob.sync(self.proxy._putPoolLink(self.link))
                    self.link = None
                    return

                if mesg[0] == 'genr:errx':
                    # clean exit...
                    s_glob.sync(self.proxy._putPoolLink(self.link))
                    # this will raise...
                    s_common.result(mesg[1])

        except Exception as e:
            # this includes GeneratorExit
            s_glob.sync(link.fini())
            return

class With(Share):

    def __init__(self, proxy, iden):
        Share.__init__(self, proxy, iden)
        # a with is optimized to already be entered.
        # so a fini() with no enter causes exit with error.
        self.entered = True # local to synapse.lib.coro.Fini()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, cls, tb):
        await self.teleexit(exc is not None)

    def __enter__(self):
        return self

    def __exit__(self, exc, cls, tb):
        return s_glob.sync(self.__aexit__(exc, cls, tb))

sharetypes = {
    'share': Share,
    'genr': Genr,
    'with': With,
}

class Method:
    '''
    The telepath Method is used to provide proxy method calls.
    '''
    def __init__(self, proxy, name, share=None):
        self.name = name
        self.share = None
        self.proxy = proxy

        # act as much like a bound method as possible...
        self.__name__ = name
        self.__self__ = proxy

    @s_glob.synchelp
    async def __call__(self, *args, **kwargs):
        todo = (self.name, args, kwargs)
        return await self.proxy.task(todo, name=self.share)

#class PoolLink:

    #def __init__(self, link):
    #async def __aenter__(self):
    #async def __aexit__(self):

class Proxy(s_coro.Fini):
    '''
    A telepath Proxy is used to call remote APIs on a shared object.

    Example:

        import synpase.telepath as s_telepath

        # open the "foo" object shared in a dmon on localhost:3344

        async def doFooThing():

            proxy = await s_telepath.openurl('tcp://127.0.0.1:3344/foo')

            valu = await proxy.getFooValu(x, y)

    The proxy ( and openurl function ) may also be used from sync code:

        proxy = s_telepath.openurl('tcp://127.0.0.1:3344/foo')

        valu = proxy.getFooValu(x, y)

    '''
    def __init__(self, url, opts=None):

        s_coro.Fini.__init__(self)

        info = s_urlhelp.chopurl(url)
        if opts is not None:
            info.update(opts)

        self.sess = s_common.guid()

        self.host = info.get('host')
        self.port = info.get('port')

        self.name = info.get('path')[1:]

        self.auth = None
        self.user = info.get('user')
        self.passwd = info.get('passwd')

        if self.user is not None:
            self.auth = (self.user, {'passwd': self.passwd})

        self.tasks = {}
        self.shares = {}

        self.pool = collections.deque()
        self.links = {}

        self.synack = None
        self.syndone = asyncio.Event()

        self.timeout = None     # API call timeout default

        self.handlers = {
            'tele:syn': self._onTeleSyn,
            'task:fini': self._onTaskFini,
            'share:data': self._onShareData,
            'share:fini': self._onShareFini,
        }

        async def fini():
            # fini all the links
            links = list(self.links.values())
            for link in links:
                await link.fini()

        self.onfini(fini)

    async def handshake(self):
        # force one connection with auth/handshake
        link = await self._getPoolLink()
        await self._putPoolLink(link)

    async def call(self, name, *args, **kwargs):
        '''
        Call a remote method by name.

        Args:
            name (str): The name of the remote method.
            *args: Arguments to the method call.
            **kwargs: Keyword arguments to the method call.

        Most use cases will likely use the proxy methods directly:

        The following two are effectively the same:

            valu = proxy.getFooBar(x, y)
            valu = proxy.call('getFooBar', x, y)
        '''
        todo = (name, args, kwargs)
        return await self.task(todo)

    async def task(self, todo, name=None):

        link = await self._getPoolLink()

        await link.tx(('task:init', {
                    #'task': task.iden,
                    'todo': todo,
                    'name': name,
        }))

        mesg = await link.rx()
        if mesg is None:
            # link is already fini()
            raise s_exc.LinkClosed()

        if mesg[0] != 'task:fini':
            await link.fini()
            raise s_exc.BadMesgType()

        retn = mesg[1].get('retn')

        retntype = mesg[1].get('type')
        if retntype is not None:

            if retntype == 'genr':
                # Genr() owns the link
                return Genr(self, link)

            if retntype == 'share':
                await self._putPoolLink(link)
                return Share(self, retn[1])

            # since we dont know the remaining proto
            # we must abort and close the link
            await link.fini()
            raise s_exc.NoSuchCtor(name=retntype)

        # we sent a simple request, and got a reply. pool the link.
        await self._putPoolLink(link)
        return s_common.result(retn)

    async def _putPoolLink(self, link):

        if len(self.pool) > 10: # TODO config...
            await link.fini()
            return

        self.pool.append(link)

    async def _getPoolLink(self):

        try:
            return self.pool.popleft()
        except IndexError as e:
            pass

        link = await s_glob.plex.link(self.host, self.port)
        self.links[link.iden] = link

        async def fini():
            self.links.pop(link.iden, None)

        link.onfini(fini)

        # do our auth/handlshake...
        await link.tx(('tele:syn', {
            'auth': self.auth,
            'vers': televers,
            'name': self.name,
            'sess': self.sess,
        }))

        mesg = await link.rx()
        vers = mesg[1].get('vers')

        if vers[0] != televers[0]:
            raise s_exc.BadMesgVers(myver=televers, hisver=vers)

        # this will raise if there was an error
        retn = mesg[1].get('retn')
        s_common.result(retn)

        return link

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self, name, meth)
        return meth

def alias(name):
    '''
    Resolve a telpath alias via ~/.syn/aliases.yaml
    '''
    path = s_common.getSynPath('aliases.yaml')
    if not os.path.isfile(path):
        return None

    conf = s_common.yamlload(path)
    return conf.get(name)

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

    '''
    if url.find('://') == -1:
        newurl = alias(url)
        if newurl is None:
            raise s_exc.BadUrl(f':// not found in [{url}] and no alias found!')
        url = newurl

    prox = Proxy(url, opts=opts)
    await prox.handshake()

    return prox
