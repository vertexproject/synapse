import asyncio

from unittest import mock

import aioimaplib

import synapse.common as s_common

import synapse.tests.utils as s_test

resp = aioimaplib.Response

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

class ImapTest(s_test.SynTest):

    async def test_storm_imap(self):

        with mock.patch('aioimaplib.IMAP4.create_client', mock_create_client), \
            mock.patch('aioimaplib.IMAP4_SSL.create_client', mock_create_client):

            async with self.getTestCore() as core:

                # list mailboxes
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    return($server.list())
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('INBOX',)), retn)

                # search for UIDs
                scmd = '''
                    $server = $lib.inet.imap.connect(hello)
                    $server.login("vtx@email.com", "secret")
                    $server.select("INBOX")
                    return($server.search("FROM", "foo@mail.com"))
                '''
                retn = await core.callStorm(scmd)
                self.eq((True, ('8181', '8192', '8194')), retn)

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
