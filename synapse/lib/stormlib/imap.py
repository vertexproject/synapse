import random
import asyncio
import imaplib
import logging

import lark
import regex

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

CRLF = b'\r\n'
CRLFLEN = len(CRLF)
UNTAGGED = '*'

TAGVAL_MIN = 4096
TAGVAL_MAX = 65535

def quote(text, escape=True):
    if text == '""':
        # Don't quote empty string
        return text

    if ' ' not in text and '"' not in text and '\\' not in text:
        return text

    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')

    return f'"{text}"'

_grammar = s_data.getLark('imap')
LarkParser = lark.Lark(_grammar, regex=True, start='input',
                       maybe_placeholders=False, propagate_positions=True, parser='lalr')

class AstConverter(lark.Transformer):
    def quoted(self, args):
        return ''.join(args)

    def unquoted(self, args):
        return ''.join(args)

def qsplit(text):
    '''
    Split on spaces.
    Preserve quoted strings.
    Unescape backslash and double quotes.
    Unquote quoted strings.

    Raise BadDataValu if:
        - quotes are unclosed.
        - quoted strings don't have a space before/after (not including beginning/end of line).
        - double-quotes or backslashes are escaped outside of a quoted string.
    '''
    def on_error(exc):
        # Escaped double-quote or backslash not in quotes
        if exc.token_history and len(exc.token_history) == 1 and (tok := exc.token_history[0]).type == 'UNQUOTED_CHAR' and tok.value == '\\':
            mesg = f'Invalid data: {exc.token.value} cannot be escaped.'
            raise s_exc.BadDataValu(mesg=mesg, data=text) from None

        if exc.token.type == 'UNQUOTED_CHAR' and exc.expected == {'QUOTED_SPECIALS'}:
            mesg = f'Invalid data: {exc.token.value} cannot be escaped.'
            raise s_exc.BadDataValu(mesg=mesg, data=text) from None

        # Double quote (opening a quoted string) at end of line
        if exc.token.type == 'DBLQUOTE' and exc.column == len(text):
            mesg = 'Quoted strings must be preceded and followed by a space.'
            raise s_exc.BadDataValu(mesg=mesg, data=text) from None

        # Unclosed quoted string
        if exc.token.type == '$END' and exc.column == len(text) and exc.expected == {'QUOTED_CHAR', 'DBLQUOTE', 'BACKSLASH'}:
            mesg = 'Unclosed quotes in text.'
            raise s_exc.BadDataValu(mesg=mesg, data=text) from None

        # Catch-all exception
        raise s_exc.BadDataValu(mesg='Unable to parse IMAP response data.', data=text) from None # pragma: no cover

    tree = LarkParser.parse(text, on_error=on_error)
    newtree = AstConverter(text).transform(tree)
    return newtree.children

imap_rgx = regex.compile(
    br'''
    ^
      (?P<tag>\*|\+|[0-9a-zA-Z]+)       # tag is mandatory
      (\s(?P<uid>[0-9]+))?              # uid is optional
      (\s(?P<response>[A-Z]{2,}))       # response is mandatory
      (\s\[(?P<code>.*?)\])?            # code is optional
      (\s(?P<data>.*?(?! {\d+})))?      # data is optional
      (\s({(?P<size>\d+)}))?            # size is optional
    $
    ''',
    flags=regex.VERBOSE
)

imap_rgx_cont = regex.compile(
    br'''
    ^
      ((?P<data>.*?(?! {\d+})))?        # data is optional
      (\s({(?P<size>\d+)}))?            # size is optional
    $
    ''',
    flags=regex.VERBOSE
)

class IMAPBase(s_link.Link):
    '''
    Base class for IMAPClient and IMAPServer (in test_lib_stormlib_imap.py).
    '''
    async def __anit__(self, reader, writer, info=None, forceclose=False):
        await s_link.Link.__anit__(self, reader, writer, info=info, forceclose=forceclose)

        self._rxbuf = b''
        self.state = 'LOGOUT'

    def _parseLine(self, line): # pragma: no cover
        raise NotImplementedError('Not implemented')

    def pack(self, mesg): # pragma: no cover
        raise NotImplementedError('Not implemented')

    def feed(self, byts):
        ret = []

        # Append new bytes to existing bytes
        self._rxbuf += byts

        # Iterate through buffer and parse out (up to 32) complete messages.
        # NB: The 32 message maximum is an arbitrary number to keep this loop
        # from running forever with an endless number of messages from the
        # server.
        while (offs := self._rxbuf.find(CRLF)) != -1 and len(ret) < 32:

            # Get the line out of the buffer
            line = self._rxbuf[:offs]

            # Parse line
            mesg = self._parseLine(line)

            end = offs + CRLFLEN

            # Handle continuations
            while (size := mesg.get('size')) is not None:
                start = end
                end = start + size

                # Check for complete data
                if len(self._rxbuf) < start + end - start: # pragma: no cover
                    return ret

                # Check for end of message
                if (offs := self._rxbuf[end:].find(CRLF)) == -1: # pragma: no cover
                    return ret

                # Extract the attachment and add it to the message
                attachment = self._rxbuf[start:end]
                mesg['attachments'].append(attachment)

                msgdata = self._rxbuf[end:end + offs]

                # Get the data and/or size from the trailing message data
                cont = imap_rgx_cont.match(msgdata).groupdict()
                if (size := cont.get('size')) is not None:
                    size = int(size)

                mesg['size'] = size

                contdata = cont.get('data', b'')
                mesg['data'] += contdata

                end = end + offs + CRLFLEN

            # Increment buffer
            self._rxbuf = self._rxbuf[end:]

            # Log only under __debug__ because there might be sensitive info like passwords
            if __debug__:
                logger.debug('%s RECV: %s', self.__class__.__name__, mesg)

            ret.append((None, mesg))

        return ret

class IMAPClient(IMAPBase):
    async def postAnit(self):
        self._tagval = random.randint(TAGVAL_MIN, TAGVAL_MAX)
        self.readonly = False
        self.capabilities = []

        # Get and handle the server greeting
        response = await self.getResponse()
        greeting = response.get(UNTAGGED)[0]

        if greeting.get('response') == 'PREAUTH':
            self.state = 'AUTH'
        elif greeting.get('response') == 'OK':
            self.state = 'NONAUTH'
        else:
            # Includes greeting.get('response') == 'BYE'
            raise s_exc.ImapError(mesg=greeting.get('data').decode(), response=response)

        # Some servers will list capabilities in the greeting
        if (code := greeting.get('code')) is not None and code.startswith('CAPABILITY'):
            self.capabilities = qsplit(code)[1:]

        if not self.capabilities:
            (ok, data) = await self.capability()
            if not ok:
                mesg = data[0].decode()
                raise s_exc.ImapError(mesg=mesg)

        return self

    def _parseLine(self, line):
        match = imap_rgx.match(line)
        if match is None:
            mesg = 'Unable to parse response from server.'
            raise s_exc.ImapError(mesg=mesg, data=line)

        mesg = match.groupdict()

        for key, valu in mesg.items():
            if key == 'data' or valu is None:
                continue

            mesg[key] = valu.decode()

        if mesg.get('data') is None:
            mesg['data'] = b''

        if (uid := mesg.get('uid')) is not None:
            mesg['uid'] = int(uid)

        if (size := mesg.get('size')) is not None:
            mesg['size'] = int(size)

        # For attaching continuation data
        mesg['attachments'] = []

        return mesg

    async def pack(self, mesg):
        (tag, command, args) = mesg

        cmdargs = ''
        if args:
            cmdargs = ' ' + ' '.join(args)

        mesg = f'{tag} {command}{cmdargs}\r\n'

        # Log only under __debug__ because there might be sensitive info like passwords
        if __debug__:
            logger.debug('%s SEND: %s', self.__class__.__name__, mesg)

        return mesg.encode()

    async def getResponse(self, tag=None):
        resp = {}

        while True:
            msg = await self.rx()

            mtag = msg.get('tag')
            resp.setdefault(mtag, []).append(msg)

            if tag is None or mtag == tag:
                break

        return resp

    def _genTag(self):
        self._tagval = (self._tagval + 1) % TAGVAL_MAX
        if self._tagval == 0:
            self._tagval = TAGVAL_MIN

        return imaplib.Int2AP(self._tagval).decode()

    async def _command(self, tag, command, *args):
        if command.upper() not in imaplib.Commands:
            mesg = f'Unsupported command: {command}.'
            raise s_exc.ImapError(mesg=mesg, command=command)

        if self.state not in imaplib.Commands.get(command.upper()):
            mesg = f'{command} not allowed in the {self.state} state.'
            raise s_exc.ImapError(mesg=mesg, state=self.state, command=command)

        await self.tx((tag, command, args))
        return await self.getResponse(tag)

    def okSetState(self, response, state):
        if response.get('response') == 'OK':
            self.state = state

    async def capability(self):
        tag = self._genTag()
        resp = await self._command(tag, 'CAPABILITY')

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        if len(untagged := resp.get(UNTAGGED, [])) != 1:
            return False, [b'Invalid server response.']

        capabilities = untagged[0].get('data').decode()
        self.capabilities = qsplit(capabilities)

        return True, [capabilities]

    async def login(self, user, passwd):
        if 'AUTH=PLAIN' not in self.capabilities:
            return False, [b'Plain authentication not available on server.']

        if 'LOGINDISABLED' in self.capabilities:
            return False, [b'Login disabled on server.']

        tag = self._genTag()
        resp = await self._command(tag, 'LOGIN', quote(user), quote(passwd))

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        # Some servers will update capabilities with the login response
        if (code := response.get('code')) is not None and code.startswith('CAPABILITY'):
            self.capabilities = qsplit(code)[1:]

        self.okSetState(response, 'AUTH')

        return True, [response.get('data')]

    async def select(self, mailbox='INBOX'):
        tag = self._genTag()
        resp = await self._command(tag, 'SELECT', quote(mailbox))

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        if (code := response.get('code')) is not None:
            if 'READ-ONLY' in code:
                self.readonly = True

            if 'READ-WRITE' in code:
                self.readonly = False

        self.okSetState(response, 'SELECTED')
        return True, [response.get('data')]

    async def list(self, refname, pattern):
        tag = self._genTag()
        resp = await self._command(tag, 'LIST', quote(refname), quote(pattern))

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        data = []
        for mesg in resp.get(UNTAGGED, []):
            data.append(mesg.get('data'))

        return True, data

    async def uid_store(self, uidset, dataname, datavalu):
        if self.readonly:
            return False, [b'Selected mailbox is read-only.']

        args = f'{uidset} {dataname} {datavalu}'
        return await self.uid('STORE', args)

    async def uid_search(self, *criteria, charset='UTF-8'):
        args = ''
        if charset is not None:
            args += f'CHARSET {charset} '
        args += ' '.join(quote(c) for c in criteria)
        return await self.uid('SEARCH', args)

    async def uid_fetch(self, uidset, datanames):
        args = f'{uidset} {datanames}'
        return await self.uid('FETCH', args)

    async def uid(self, cmdname, cmdargs):
        tag = self._genTag()

        resp = await self._command(tag, 'UID', cmdname, cmdargs)

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        untagged = resp.get(UNTAGGED, [])

        if cmdname == 'FETCH':
            # FETCH returns a list of attachments from each message followed by
            # the message data. For example, a FETCH 4 (RFC822 BODY[HEADER])
            # would return:
            # [ <RFC822 message>, <BODY[HEADER] message>, '(UID 4 RFC822 BODY[HEADER])' ]
            #
            # This allows the consumer to get each of the requested data
            # messages and then parse the message data to figure out which
            # attachment is which.

            ret = []
            for u in untagged:
                ret.extend(u.get('attachments'))
                ret.append(u.get('data'))
            return True, ret

        return True, [u.get('data') for u in untagged]

    async def expunge(self):
        if self.readonly:
            return False, [b'Selected mailbox is read-only.']

        tag = self._genTag()
        resp = await self._command(tag, 'EXPUNGE')

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        return True, [response.get('data')]

    async def logout(self):
        tag = self._genTag()
        resp = await self._command(tag, 'LOGOUT')

        response = resp.get(tag)[0]
        if response.get('response') != 'OK':
            return False, [response.get('data')]

        untagged = resp.get(UNTAGGED, [])
        if len(untagged) != 1 or untagged[0].get('response') != 'BYE':
            return False, [b'Server failed to send expected BYE response.']

        self.okSetState(response, 'LOGOUT')
        return True, [response.get('data')]

async def run_imap_coro(coro, timeout):
    '''
    Raises or returns data.
    '''
    try:
        status, data = await s_common.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        raise s_exc.TimeOut(mesg='Timed out waiting for IMAP server response.') from None

    if status:
        return data

    try:
        mesg = data[0].decode()
    except (TypeError, AttributeError, IndexError, UnicodeDecodeError):
        mesg = 'IMAP server returned an error'

    raise s_exc.ImapError(mesg=mesg, status=status)

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
            before returning the ``inet:imap:server`` instance.
            ''',
            'type': {
                'type': 'function', '_funcname': 'connect',
                'args': (
                    {'type': 'str', 'name': 'host',
                     'desc': 'The IMAP hostname.'},
                    {'type': 'int', 'name': 'port', 'default': 993,
                     'desc': 'The IMAP server port.'},
                    {'type': 'int', 'name': 'timeout', 'default': 30,
                     'desc': 'The time to wait for all commands on the server to execute.'},
                    {'type': 'bool', 'name': 'ssl', 'default': True,
                     'desc': 'Use SSL to connect to the IMAP server.'},
                    {'type': 'bool', 'name': 'ssl_verify', 'default': True,
                     'desc': 'Perform SSL/TLS verification.'},
                ),
                'returns': {
                    'type': 'inet:imap:server',
                    'desc': 'A new ``inet:imap:server`` instance.'
                },
            },
        },
    )
    _storm_lib_path = ('inet', 'imap', )
    _storm_lib_perms = (
        {'perm': ('storm', 'inet', 'imap', 'connect'), 'gate': 'cortex',
         'desc': 'Controls connecting to external servers via imap.'},
    )

    def getObjLocals(self):
        return {
            'connect': self.connect,
        }

    async def connect(self, host, port=imaplib.IMAP4_SSL_PORT, timeout=30, ssl=True, ssl_verify=True):

        self.runt.confirm(('storm', 'inet', 'imap', 'connect'))

        ssl = await s_stormtypes.tobool(ssl)
        host = await s_stormtypes.tostr(host)
        port = await s_stormtypes.toint(port)
        ssl_verify = await s_stormtypes.tobool(ssl_verify)
        timeout = await s_stormtypes.toint(timeout, noneok=True)

        ctx = None
        if ssl:
            ctx = self.runt.snap.core.getCachedSslCtx(opts=None, verify=ssl_verify)

        coro = s_link.connect(host=host, port=port, ssl=ctx, linkcls=IMAPClient)

        try:
            imap = await s_common.wait_for(coro, timeout)
        except asyncio.TimeoutError:
            raise s_exc.TimeOut(mesg='Timed out waiting for IMAP server hello.') from None

        async def fini():
            async def _logout():
                await s_common.wait_for(imap.logout(), 5)
                await imap.fini()
            s_coro.create_task(_logout())

        self.runt.snap.onfini(fini)

        return ImapServer(self.runt, imap, timeout)

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
                    'type': 'node',
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
                    {'type': ['str', 'null'], 'name': 'charset', 'default': 'utf-8',
                     'desc': 'The CHARSET used for the search. May be set to ``(null)`` to disable CHARSET.'},
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
    _storm_typename = 'inet:imap:server'

    def __init__(self, runt, imap_cli, timeout, path=None):
        s_stormtypes.StormType.__init__(self, path=path)
        self.runt = runt
        self.imap_cli = imap_cli
        self.timeout = timeout
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
        await run_imap_coro(coro, self.timeout)

        return True, None

    async def list(self, reference_name='""', pattern='*'):
        pattern = await s_stormtypes.tostr(pattern)
        reference_name = await s_stormtypes.tostr(reference_name)

        coro = self.imap_cli.list(reference_name, pattern)
        data = await run_imap_coro(coro, self.timeout)

        names = []
        for item in data:
            names.append(qsplit(item.decode())[-1])

        return True, names

    async def select(self, mailbox='INBOX'):
        mailbox = await s_stormtypes.tostr(mailbox)

        coro = self.imap_cli.select(mailbox=mailbox)
        await run_imap_coro(coro, self.timeout)

        return True, None

    async def search(self, *args, charset='utf-8'):
        args = [await s_stormtypes.tostr(arg) for arg in args]
        charset = await s_stormtypes.tostr(charset, noneok=True)

        coro = self.imap_cli.uid_search(*args, charset=charset)
        data = await run_imap_coro(coro, self.timeout)

        uids = qsplit(data[0].decode()) if data[0] else []
        return True, uids

    async def fetch(self, uid):
        # IMAP fetch accepts a message set (e.g. "1", "1:*", "1,2,3"),
        # however this method forces fetching a single uid
        # to prevent retrieving a very large blob of data.
        uid = await s_stormtypes.toint(uid)

        await self.runt.snap.core.getAxon()
        axon = self.runt.snap.core.axon

        coro = self.imap_cli.uid_fetch(str(uid), '(RFC822)')
        data = await run_imap_coro(coro, self.timeout)

        if not data:
            return False, f'No data received from fetch request for uid {uid}.'

        size, sha256b = await axon.put(data[0])

        props = await axon.hashset(sha256b)
        props['size'] = size
        props['mime'] = 'message/rfc822'

        filenode = await self.runt.snap.addNode('file:bytes', props['sha256'], props=props)
        return filenode

    async def delete(self, uid_set):
        uid_set = await s_stormtypes.tostr(uid_set)

        coro = self.imap_cli.uid_store(uid_set, '+FLAGS.SILENT', '(\\Deleted)')
        await run_imap_coro(coro, self.timeout)

        coro = self.imap_cli.expunge()
        await run_imap_coro(coro, self.timeout)

        return True, None

    async def markSeen(self, uid_set):
        uid_set = await s_stormtypes.tostr(uid_set)

        coro = self.imap_cli.uid_store(uid_set, '+FLAGS.SILENT', '(\\Seen)')
        await run_imap_coro(coro, self.timeout)

        return True, None
