import ssl
import asyncio
import contextlib
import collections

import regex

from unittest import mock

import synapse.common as s_common

import synapse.lib.link as s_link
import synapse.lib.stormlib.imap as s_imap

import synapse.tests.utils as s_test

resp = collections.namedtuple('Response', ('status', 'data'))

mesgb = bytearray(b'From: Foo <foo@mail.com>\nTo: Bar <bar@mail.com>\nSubject: Test\n\nThe body\n')

class MockIMAPProtocol:
    # NOTE: Unused lines are not necessarily IMAP compliant

    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def wait(self, *args, **kwargs) -> None:
        # only used for wait_hello_from_server
        if self.host == 'hello.timeout':
            await asyncio.sleep(5)

    async def login(self, user, passwd) -> resp:
        if self.host == 'login.timeout':
            await asyncio.sleep(5)

        if self.host == 'login.bad':
            return resp('NO', [b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'])

        if self.host == 'login.noerr':
            return resp('NO', [])

        lines = [
            b'CAPABILITY IMAP4rev1',
            f'{user} authenticated (Success)'.encode(),
        ]
        return resp('OK', lines)

    async def logout(self) -> resp:
        lines = [
            b'BYE LOGOUT Requested',
            b'73 good day (Success)',
        ]
        return resp('OK', lines)

    async def simple_command(self, name, *args) -> resp:
        # only used for list
        if self.host == 'list.bad':
            return resp('BAD', [b'Could not parse command'])

        lines = [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'Success',
        ]
        return resp('OK', lines)

    async def select(self, mailbox) -> resp:
        lines = [
            b'FLAGS (\\Answered \\Flagged \\Draft \\Deleted \\Seen $NotPhishing $Phishing)',
            b'OK [PERMANENTFLAGS (\\Answered \\Flagged \\Draft \\Deleted \\Seen $NotPhishing $Phishing \\*)] Flags permitted.',
            b'OK [UIDVALIDITY 1] UIDs valid.',
            b'8253 EXISTS',
            b'0 RECENT',
            b'OK [UIDNEXT 8294] Predicted next UID.',
            b'OK [HIGHESTMODSEQ 1030674]',
            b'[READ-WRITE] INBOX selected. (Success)',
        ]
        return resp('OK', lines)

    async def search(self, *args, **kwargs) -> resp:
        if self.host == 'search.empty':
            lines = [
                b'',
                b'SEARCH completed (Success)',
            ]
            return resp('OK', lines)

        if kwargs.get('charset') is None:
            lines = [
                b'2001 2010 2061 3001',
                b'SEARCH completed (Success)',
            ]
            return resp('OK', lines)

        if kwargs.get('charset') == 'us-ascii':
            lines = [
                b'1138 4443 8443',
                b'SEARCH completed (Success)',
            ]
            return resp('OK', lines)

        lines = [
            b'8181 8192 8194',
            b'SEARCH completed (Success)',
        ]
        return resp('OK', lines)

    async def uid(self, name, *args, **kwargs) -> resp:
        # only used for store and fetch

        if name == 'STORE':
            return resp('OK', [b'STORE completed (Success)'])

        lines = [
            b'8181 FETCH (RFC822 {44714}',
            mesgb,
            b')',
            b'Success',
        ]
        return resp('OK', lines)

    async def expunge(self) -> resp:
        return resp('OK', [b'EXPUNGE completed (Success)'])

def mock_create_client(self, host, port, *args, **kwargs):
    self.protocol = MockIMAPProtocol(host, port)
    return

imap_srv_rgx = regex.compile(
    br'''
    ^
      (?P<tag>\*|\+|[0-9a-pA-P]+)\s?
      (?P<command>[A-Z]{2,})\s?
      (?P<data>.*?)?
    $
    ''',
    flags=regex.VERBOSE
)

class IMAPServer(s_imap.IMAPConnection):

    def _parseLine(self, line):
        match = imap_srv_rgx.match(line)
        if match is None:
            mesg = 'Unable to parse response from client.'
            raise s_imap.ImapError(mesg=mesg, data=line)

        mesg = match.groupdict()

        tag = mesg.get('tag').decode()
        mesg['tag'] = tag
        mesg['command'] = mesg.get('command').decode()
        mesg['raw'] = line[len(tag) + 1:]

        return mesg

    async def pack(self, mesg):
        (tag, response, data, uid, code, size) = mesg

        if uid is None:
            uid = ''
        else:
            uid = f' {uid}'

        if code is None:
            code = ''
        else:
            code = f' {code}'

        if size is None:
            size = ''
        else:
            size = f' {size}'

        return f'{tag}{uid} {response}{code} {data}{size}\r\n'.encode()

    async def sendMesg(self, tag, response, data, uid=None, code=None, size=None):
        await self.tx((tag, response, data, uid, code, size))

    async def greet(self):
        await self.sendMesg(s_imap.UNTAGGED, 'OK', 'SynImap ready.')

    async def capability(self, mesg):
        tag = mesg.get('tag')
        await self.sendMesg(s_imap.UNTAGGED, 'CAPABILITY', 'IMAP4rev1 AUTH=PLAIN')
        await self.sendMesg(tag, 'OK', 'CAPABILITY completed')

    async def login(self, mesg):
        tag = mesg.get('tag')
        await self.sendMesg(tag, 'OK', 'LOGIN completed')

    async def logout(self, mesg):
        tag = mesg.get('tag')
        await self.sendMesg(s_imap.UNTAGGED, 'LOGOUT', 'bye, felicia')
        await self.sendMesg(tag, 'OK', 'LOGOUT completed')
        await self.fini()

async def imapserv(link):
    await link.greet()

    while not link.isfini:
        mesg = await link.rx()

        # Receive commands from client
        command = mesg.get('command')

        # Get command handler
        handler = getattr(link, command.lower(), None)
        if handler is None:
            raise NotImplementedError(f'No handler for command: {command}')

        # Process command
        await handler(mesg)

    await link.waitfini()

class ImapTest(s_test.SynTest):
    async def test_storm_imap_basic(self):

        serv = s_link.listen('127.0.0.1', 0, imapserv, linkcls=IMAPServer)
        with contextlib.closing(await serv) as server:

            async with self.getTestCore() as core:

                q = '''
                $imap = $lib.inet.imap.connect("127.0.0.1", port=$port, ssl=(false)) $imap.login(blackout, pass)
                '''

                port = server.sockets[0].getsockname()[1]
                opts = {'vars': {'port': port}}
                msgs = await core.stormlist(q, opts=opts)
                self.stormHasNoWarnErr(msgs)

    async def test_storm_imap_parseLine(self):

        def parseLine(line):
            return s_imap.IMAPClient._parseLine(None, line)

        with self.raises(s_imap.ImapError) as exc:
            # q is not a valid tag character
            line = b'abcq OK CAPABILITY completed'
            parseLine(line)
        self.eq(exc.exception.get('mesg'), 'Unable to parse response from server.')

        # NB: Most of the examples in this test are taken from RFC9051

        # Server greetings
        line = b'* OK IMAP4rev2 server ready'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'OK',
            'data': b'IMAP4rev2 server ready',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'* OK [CAPABILITY IMAP4rev1 LITERAL+ SASL-IR LOGIN-REFERRALS ID ENABLE IDLE AUTH=PLAIN AUTH=LOGIN] Dovecot ready.'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'OK',
            'data': b'Dovecot ready.',
            'raw': line[2:],
            'code': 'CAPABILITY IMAP4rev1 LITERAL+ SASL-IR LOGIN-REFERRALS ID ENABLE IDLE AUTH=PLAIN AUTH=LOGIN',
            'uid': None, 'size': None,
        })

        line = b'* PREAUTH IMAP4rev2 server logged in as Smith'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'PREAUTH',
            'data': b'IMAP4rev2 server logged in as Smith',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'* BYE Autologout; idle for too long'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'BYE',
            'data': b'Autologout; idle for too long',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        # Capability response
        line = b'* CAPABILITY IMAP4rev2 STARTTLS AUTH=GSSAPI LOGINDISABLED'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'CAPABILITY',
            'data': b'IMAP4rev2 STARTTLS AUTH=GSSAPI LOGINDISABLED',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'abcd OK CAPABILITY completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'abcd',
            'response': 'OK',
            'data': b'CAPABILITY completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        # Login responses
        line = b'a001 OK LOGIN completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'a001',
            'response': 'OK',
            'data': b'LOGIN completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        # Select responses
        line = b'* 172 EXISTS'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'EXISTS',
            'data': b'',
            'raw': line[2:],
            'code': None,
            'uid': 172,
            'size': None,
        })

        line = b'* OK [UIDVALIDITY 3857529045] UIDs valid'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'OK',
            'data': b'UIDs valid',
            'raw': line[2:],
            'code': 'UIDVALIDITY 3857529045',
            'uid': None, 'size': None,
        })

        line = b'* OK [UIDNEXT 4392] Predicted next UID'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'OK',
            'data': b'Predicted next UID',
            'raw': line[2:],
            'code': 'UIDNEXT 4392',
            'uid': None, 'size': None,
        })

        line = br'* FLAGS (\Answered \Flagged \Deleted \Seen \Draft)'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'FLAGS',
            'data': br'(\Answered \Flagged \Deleted \Seen \Draft)',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* OK [PERMANENTFLAGS (\Deleted \Seen \*)] Limited'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'OK',
            'data': br'Limited',
            'raw': line[2:],
            'code': r'PERMANENTFLAGS (\Deleted \Seen \*)',
            'uid': None, 'size': None,
        })

        line = b'* LIST () "/" INBOX'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': b'() "/" INBOX',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'A142 OK [READ-WRITE] SELECT completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A142',
            'response': 'OK',
            'data': b'SELECT completed',
            'raw': line[5:],
            'code': 'READ-WRITE',
            'uid': None, 'size': None,
        })

        # List responses
        line = br'* LIST (\Noselect) "/" ""'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'(\Noselect) "/" ""',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* LIST (\Noselect) "." #news.'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'(\Noselect) "." #news.',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* LIST (\Noselect) "/" /'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'(\Noselect) "/" /',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* LIST (\Noselect) "/" ~/Mail/foo'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'(\Noselect) "/" ~/Mail/foo',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'* LIST () "/" ~/Mail/meetings'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'() "/" ~/Mail/meetings',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* LIST (\Marked \NoInferiors) "/" "inbox"'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'(\Marked \NoInferiors) "/" "inbox"',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'* LIST () "/" "Fruit"'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': b'() "/" "Fruit"',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'* LIST () "/" "Fruit/Apple"'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'LIST',
            'data': br'() "/" "Fruit/Apple"',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'A101 OK LIST Completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A101',
            'response': 'OK',
            'data': b'LIST Completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        # UID responses
        line = b'* 3 EXPUNGE'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'EXPUNGE',
            'data': b'',
            'raw': line[2:],
            'code': None,
            'uid': 3,
            'size': None,
        })

        line = b'A003 OK UID EXPUNGE completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A003',
            'response': 'OK',
            'data': b'UID EXPUNGE completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        line = br'* 25 FETCH (FLAGS (\Seen) UID 4828442)'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'FETCH',
            'data': br'(FLAGS (\Seen) UID 4828442)',
            'raw': line[2:],
            'code': None,
            'uid': 25,
            'size': None,
        })

        line = b'* 12 FETCH (BODY[HEADER] {342}'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'FETCH',
            'data': b'(BODY[HEADER]',
            'raw': line[2:],
            'code': None,
            'uid': 12,
            'size': 342,
        })

        line = b'A999 OK UID FETCH completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A999',
            'response': 'OK',
            'data': b'UID FETCH completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        # Expunge responses
        line = b'* 8 EXPUNGE'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'EXPUNGE',
            'data': b'',
            'raw': line[2:],
            'code': None,
            'uid': 8,
            'size': None,
        })

        line = b'A202 OK EXPUNGE completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A202',
            'response': 'OK',
            'data': b'EXPUNGE completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

        # Logout responses
        line = b'* BYE IMAP4rev2 Server logging out'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': '*',
            'response': 'BYE',
            'data': b'IMAP4rev2 Server logging out',
            'raw': line[2:],
            'code': None, 'uid': None, 'size': None,
        })

        line = b'A023 OK LOGOUT completed'
        mesg = parseLine(line)
        self.eq(mesg, {
            'tag': 'A023',
            'response': 'OK',
            'data': b'LOGOUT completed',
            'raw': line[5:],
            'code': None, 'uid': None, 'size': None,
        })

    async def __test_storm_imap(self):

        client_args = []
        def client_mock(*args, **kwargs):
            client_args.append((args, kwargs))
            return mock_create_client(*args, **kwargs)

        with mock.patch('aioimaplib.IMAP4.create_client', client_mock), \
            mock.patch('aioimaplib.IMAP4_SSL.create_client', client_mock):

            async with self.getTestCore() as core:

                # list mailboxes
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    return($server.list())
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('INBOX',)), retn)
                ctx = self.nn(client_args[-1][0][5])  # type: ssl.SSLContext
                self.eq(ctx.verify_mode, ssl.CERT_REQUIRED)

                # search for UIDs
                scmd = '''
                    $server = $lib.inet.imap.connect(hello, ssl_verify=(false))
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    return($server.search("FROM", "foo@mail.com"))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('8181', '8192', '8194')), retn)
                ctx = self.nn(client_args[-1][0][5])  # type: ssl.SSLContext
                self.eq(ctx.verify_mode, ssl.CERT_NONE)

                # search for UIDs with specific charset
                scmd = '''
                $server = $lib.inet.imap.connect(hello)
                $server.login("vtx@email.com", "secret")
                $server.select("INBOX")
                return($server.search("FROM", "foo@mail.com", charset=us-ascii))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('1138', '4443', '8443')), retn)

                # search for UIDs with no charset
                scmd = '''
                $server = $lib.inet.imap.connect(hello)
                $server.login("vtx@email.com", "secret")
                $server.select("INBOX")
                return($server.search("FROM", "foo@mail.com", charset=$lib.null))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('2001', '2010', '2061', '3001')), retn)

                scmd = '''
                    $server = $lib.inet.imap.connect(search.empty)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    return($server.search("FROM", "newp@mail.com"))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ()), retn)

                # mark seen
                scmd = '''
                    $server = $lib.inet.imap.connect(hello, ssl=$lib.false)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    return($server.markSeen("1:4"))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, None), retn)
                self.none(client_args[-1][0][5])

                # delete
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    return($server.delete("1:4"))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, None), retn)

                # fetch and save a message
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    yield $server.fetch("1")
                '''
                nodes = await core.nodes(scmd)
                self.len(1, nodes)
                self.eq('file:bytes', nodes[0].ndef[0])
                self.true(all(nodes[0].get(p) for p in ('sha512', 'sha256', 'sha1', 'md5', 'size')))
                self.eq('message/rfc822', nodes[0].get('mime'))

                byts = b''.join([byts async for byts in core.axon.get(s_common.uhex(nodes[0].get('sha256')))])
                self.eq(mesgb, byts)

                # fetch must only be for a single message
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    $server.fetch("1:*")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('Failed to make an integer', mesgs)

                # make sure we can pass around the server object
                scmd = '''
                function foo(s) {
                    return($s.login("vtx@email.com", "secret"))
                }
                $server = $lib.inet.imap.connect(hello)
                $ret00 = $foo($server)
                $ret01 = $server.list()
                return(($ret00, $ret01))
                '''
                retn = await core.callStorm(scmd)
                self.eq(((True, None), (True, ('INBOX',))), retn)

                # sad paths

                mesgs = await core.stormlist('$lib.inet.imap.connect(hello.timeout, timeout=(1))')
                self.stormIsInErr('Timed out waiting for IMAP server hello', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.timeout, timeout=(1))
                    $server.login("vtx@email.com", "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('Timed out waiting for IMAP server response', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.bad)
                    $server.login("vtx@email.com", "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('[AUTHENTICATIONFAILED] Invalid credentials (Failure)', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.noerr)
                    $server.login("vtx@email.com", "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('IMAP server returned an error', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(list.bad)
                    $server.login("vtx@email.com", "secret")
                    $server.list()
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('Could not parse command', mesgs)
