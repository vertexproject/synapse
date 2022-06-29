import asyncio

import aioimaplib

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

async def run_imap_coro(coro):
    '''
    Raises or returns data.
    '''
    try:
        status, data = await coro
    except asyncio.TimeoutError:
        raise s_exc.StormRuntimeError(mesg='Timed out waiting for IMAP server response.') from None

    if status == 'OK':
        return data

    try:
        mesg = data[0].decode()
    except (TypeError, AttributeError, IndexError, UnicodeDecodeError):
        mesg = 'IMAP server returned an error'

    raise s_exc.StormRuntimeError(mesg=mesg, status=status)

@s_stormtypes.registry.registerLib
class ImapLib(s_stormtypes.Lib):
    '''
    A Storm library to connect to an IMAP server.
    '''
    _storm_locals = (
        {
            'name': 'connect',
            'desc': '''
            Open a connection to an IMAP server.

            This method will wait for a "hello" response from the server
            before returning the ``storm:imap:server`` instance.
            ''',
            'type': {
                'type': 'function', '_funcname': 'connect',
                'args': (
                    {'type': 'str', 'name': 'host',
                     'desc': 'The IMAP hostname.'},
                    {'type': 'integer', 'name': 'port', 'default': 993,
                     'desc': 'The IMAP server port.'},
                    {'type': 'int', 'name': 'timeout', 'default': 30,
                     'desc': 'The time to wait for all commands on the server to execute.'},
                    {'type': 'bool', 'name': 'ssl', 'default': True,
                     'desc': 'Use SSL to connect to the IMAP server.'},
                ),
                'returns': {
                    'type': 'storm:imap:server',
                    'desc': 'A new ``storm:imap:server`` instance.'
                },
            },
        },
    )
    _storm_lib_path = ('inet', 'imap', )

    def getObjLocals(self):
        return {
            'connect': self.connect,
        }

    async def connect(self, host, port=993, timeout=30, ssl=True):

        self.runt.confirm(('storm', 'inet', 'imap', 'connect'))

        ssl = await s_stormtypes.tobool(ssl)
        host = await s_stormtypes.tostr(host)
        port = await s_stormtypes.toint(port)
        timeout = await s_stormtypes.toint(timeout, noneok=True)

        if ssl:
            imap_cli = aioimaplib.IMAP4_SSL(host=host, port=port, timeout=timeout)
        else:
            imap_cli = aioimaplib.IMAP4(host=host, port=port, timeout=timeout)

        async def fini():
            # call protocol.logout() so fini() doesn't hang
            await asyncio.wait_for(imap_cli.protocol.logout(), 5)

        self.runt.snap.onfini(fini)

        try:
            await imap_cli.wait_hello_from_server()
        except asyncio.TimeoutError:
            raise s_exc.StormRuntimeError(mesg='Timed out waiting for IMAP server hello.') from None

        return ImapServer(self.runt, imap_cli)

@s_stormtypes.registry.registerType
class ImapServer(s_stormtypes.StormType):
    '''
    An IMAP server for retrieving email messages.
    '''
    _storm_locals = (
        {
            'name': 'list',
            'desc': '''
            List mailbox names.

            By default this method uses a reference_name and pattern to return
            all mailboxes from the root.
            ''',
            'type': {
                'type': 'function', '_funcname': 'list',
                'args': (
                    {'type': 'str', 'name': 'reference_name', 'default': '""',
                     'desc': 'The mailbox reference name.'},
                    {'type': 'str', 'name': 'pattern', 'default': '*',
                     'desc': 'The pattern to filter by.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple where $valu is a list of names if $ok=True.'
                },
            },
        },
        {
            'name': 'fetch',
            'desc': '''
            Fetch a message by UID in RFC822 format.

            The message is saved to the Axon, and a ``file:bytes`` node is returned.

            Examples:
                Fetch a message, save to the Axon, and yield ``file:bytes`` node::

                    yield $server.fetch("8182")
            ''',
            'type': {
                'type': 'function', '_funcname': 'fetch',
                'args': (
                    {'type': 'str', 'name': 'uid',
                     'desc': 'The single message UID.'},
                ),
                'returns': {
                    'type': 'storm:node',
                    'desc': 'The file:bytes node representing the message.'
                },
            },
        },
        {
            'name': 'login',
            'desc': 'Login to the IMAP server.',
            'type': {
                'type': 'function', '_funcname': 'login',
                'args': (
                    {'type': 'str', 'name': 'user',
                     'desc': 'The username to login with.'},
                    {'type': 'str', 'name': 'passwd',
                     'desc': 'The password to login with.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple.'
                },
            },
        },
        {
            'name': 'search',
            'desc': '''
            Search for messages using RFC2060 syntax.

            Examples:
                Retrieve all messages::

                    ($ok, $uids) = $server.search("ALL")

                Search by FROM and SINCE::

                    ($ok, $uids) = $server.search("FROM", "visi@vertex.link", "SINCE", "01-Oct-2021")

                Search by a subject substring::

                    ($ok, $uids) = $search.search("HEADER", "Subject", "An email subject")
            ''',
            'type': {
                'type': 'function', '_funcname': 'search',
                'args': (
                    {'type': 'str', 'name': '*args',
                     'desc': 'A set of search criteria to use.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple, where $valu is a list of UIDs if $ok=True.'
                },
            },
        },
        {
            'name': 'select',
            'desc': 'Select a mailbox to use in subsequent commands.',
            'type': {
                'type': 'function', '_funcname': 'select',
                'args': (
                    {'type': 'str', 'name': 'mailbox', 'default': 'INBOX',
                     'desc': 'The mailbox name to select.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple.'
                },
            },
        },
        {
            'name': 'markSeen',
            'desc': '''
            Mark messages as seen by an RFC2060 UID message set.

            The command uses the +FLAGS.SILENT command and applies the \\Seen flag.

            Examples:
                Mark a single messsage as seen::

                    ($ok, $valu) = $server.markSeen("8182")

                Mark ranges of messages as seen::

                    ($ok, $valu) = $server.markSeen("1:3,6:9")
            ''',
            'type': {
                'type': 'function', '_funcname': 'markSeen',
                'args': (
                    {'type': 'str', 'name': 'uid_set',
                     'desc': 'The UID message set to apply the flag to.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple.'
                },
            },
        },
        {
            'name': 'delete',
            'desc': '''
            Mark an RFC2060 UID message as deleted and expunge the mailbox.

            The command uses the +FLAGS.SILENT command and applies the \\Deleted flag.
            The actual behavior of these commands are mailbox configuration dependent.

            Examples:
                Mark a single message as deleted and expunge::

                    ($ok, $valu) = $server.delete("8182")

                Mark ranges of messages as deleted and expunge::

                    ($ok, $valu) = $server.delete("1:3,6:9")
            ''',
            'type': {
                'type': 'function', '_funcname': 'delete',
                'args': (
                    {'type': 'str', 'name': 'uid_set',
                     'desc': 'The UID message set to apply the flag to.'},
                ),
                'returns': {
                    'type': 'list',
                    'desc': 'An ($ok, $valu) tuple.'
                },
            },
        },
    )
    _storm_typename = 'storm:imap:server'

    def __init__(self, runt, imap_cli, path=None):
        s_stormtypes.StormType.__init__(self, path=path)
        self.runt = runt
        self.imap_cli = imap_cli
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'list': self.list,
            'fetch': self.fetch,
            'login': self.login,
            'delete': self.delete,
            'search': self.search,
            'select': self.select,
            'markSeen': self.markSeen,
        }

    async def login(self, user, passwd):
        user = await s_stormtypes.tostr(user)
        passwd = await s_stormtypes.tostr(passwd)

        coro = self.imap_cli.login(user, passwd)
        await run_imap_coro(coro)

        return True, None

    async def list(self, reference_name='""', pattern='*'):
        pattern = await s_stormtypes.tostr(pattern)
        reference_name = await s_stormtypes.tostr(reference_name)

        coro = self.imap_cli.list(reference_name, pattern)
        data = await run_imap_coro(coro)

        names = []
        for item in data:
            if item == b'Success':
                break
            names.append(item.split(b' ')[-1].decode().strip('"'))

        return True, names

    async def select(self, mailbox='INBOX'):
        mailbox = await s_stormtypes.tostr(mailbox)

        coro = self.imap_cli.select(mailbox=mailbox)
        await run_imap_coro(coro)

        return True, None

    async def search(self, *args):
        args = [await s_stormtypes.tostr(arg) for arg in args]

        coro = self.imap_cli.uid_search(*args)
        data = await run_imap_coro(coro)

        uids = data[0].decode().split(' ') if data[0] else []
        return True, uids

    async def fetch(self, uid):
        # IMAP fetch accepts a message set (e.g. "1", "1:*", "1,2,3"),
        # however this method forces fetching a single uid
        # to prevent retrieving a very large blob of data.
        uid = await s_stormtypes.toint(uid)

        await self.runt.snap.core.getAxon()
        axon = self.runt.snap.core.axon

        coro = self.imap_cli.uid('FETCH', str(uid), '(RFC822)')
        data = await run_imap_coro(coro)

        size, sha256b = await axon.put(data[1])

        props = await axon.hashset(sha256b)
        props['size'] = size
        props['mime'] = 'message/rfc822'

        filenode = await self.runt.snap.addNode('file:bytes', props['sha256'], props=props)
        return filenode

    async def delete(self, uid_set):
        uid_set = await s_stormtypes.tostr(uid_set)

        coro = self.imap_cli.uid('STORE', uid_set, '+FLAGS.SILENT (\\Deleted)')
        await run_imap_coro(coro)

        coro = self.imap_cli.expunge()
        await run_imap_coro(coro)

        return True, None

    async def markSeen(self, uid_set):
        uid_set = await s_stormtypes.tostr(uid_set)

        coro = self.imap_cli.uid('STORE', uid_set, '+FLAGS.SILENT (\\Seen)')
        await run_imap_coro(coro)

        return True, None
