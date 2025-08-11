import time
import shlex
import fnmatch
import imaplib
import contextlib

import regex

from unittest import mock

import synapse.common as s_common

import synapse.lib.link as s_link
import synapse.lib.stormlib.imap as s_imap

import synapse.tests.utils as s_test

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

imap_srv_flags_rgx = regex.compile(
    r'''
    ^
    (?P<op>\+|\-)?
    (?P<name>(FLAGS|FLAGS.SILENT))\s
    \(
      (?P<value>(\\[a-zA-Z]+\s?)+)
    \)
    $
    ''',
    flags=regex.VERBOSE
)

email = '''\
Date: Wed, 17 Jul 1996 02:23:25 -0700 (PDT)\r
From: Terry Gray <gray@cac.washington.edu>\r
Subject: IMAP4rev2 WG mtg summary and minutes\r
To: imap@cac.washington.edu\r
cc: minutes@CNRI.Reston.VA.US, John Klensin <KLENSIN@MIT.EDU>\r
Message-Id: <B27397-0100000@cac.washington.edu>\r
MIME-Version: 1.0\r
Content-Type: TEXT/PLAIN; CHARSET=US-ASCII\r

The meeting minutes are attached.

Thanks,
Terry
'''

class IMAPServer(s_imap.IMAPConnection):
    '''
    This is an extremely naive IMAP server implementation used only for testing.
    '''

    async def postAnit(self):
        self.mail = {
            'user00@vertex.link': {
                'password': 'pass00',
                'mailboxes': {
                    'inbox': {
                        'parent': None,
                        'flags': ['\\HasChildren'],
                    },
                    'drafts': {
                        'parent': None,
                        'flags': ['\\HasNoChildren', '\\Drafts'],
                    },
                    'sent': {
                        'parent': None,
                        'flags': ['\\HasNoChildren', '\\Sent'],
                    },
                    'deleted': {
                        'parent': None,
                        'flags': ['\\HasNoChildren', '\\Trash'],
                    },
                    'retain': {
                        'parent': 'inbox',
                        'flags': ['\\HasNoChildren'],
                    },
                    'status reports': {
                        'parent': 'inbox',
                        'flags': ['\\HasNoChildren'],
                    },
                },
                'messages': {
                    1: {
                        'mailbox': 'inbox',
                        'flags': ['\\Answered', '\\Recent', '\\Seen'],
                        'data': email,
                    },
                    6: {
                        'mailbox': 'inbox',
                        'flags': [],
                        'body': '',
                    },
                    7: {
                        'mailbox': 'inbox',
                        'flags': [],
                        'body': '',
                    },
                    8: {
                        'mailbox': 'inbox',
                        'flags': [],
                        'body': '',
                    },
                    2: {
                        'mailbox': 'drafts',
                        'flags': ['\\Draft'],
                        'body': '',
                    },
                    3: {
                        'mailbox': 'deleted',
                        'flags': ['\\Deleted', '\\Seen'],
                        'body': '',
                    },
                    4: {
                        'mailbox': 'retain',
                        'flags': ['\\Seen'],
                        'body': '',
                    },
                    5: {
                        'mailbox': 'status reports',
                        'flags': [],
                        'body': '',
                    },
                },
            },

            'user01@vertex.link': {
                'password': 'pass01',
                'mailboxes': {
                    'inbox': {
                        'messages': [],
                    },
                    'drafts': {
                        'messages': [],
                    },
                    'sent': {
                        'messages': [],
                    },
                },
                'messages': {
                },
            }
        }

        self.user = None
        self.selected = None
        self.validity = int(time.time())

        self.state = 'NONAUTH'

        self.capabilities = ['IMAP4rev1', 'AUTH=PLAIN']

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
            code = f' [{code}]'

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
        await self.sendMesg(s_imap.UNTAGGED, 'CAPABILITY', ' '.join(self.capabilities))
        await self.sendMesg(tag, 'OK', 'CAPABILITY completed')

    async def login(self, mesg):
        tag = mesg.get('tag')
        try:
            username, passwd = mesg.get('data').decode().split(' ')
        except ValueError:
            return await self.sendMesg(tag, 'BAD', 'Invalid arguments for LOGIN.')

        if (user := self.mail.get(username)) is None or user.get('password') != passwd:
            return await self.sendMesg(tag, 'NO', 'Incorrect username or password.')

        self.state = 'AUTH'
        self.user = username
        await self.sendMesg(tag, 'OK', 'LOGIN completed')

    async def logout(self, mesg):
        tag = mesg.get('tag')
        await self.sendMesg(s_imap.UNTAGGED, 'LOGOUT', f'bye, {self.user}!')
        await self.sendMesg(tag, 'OK', 'LOGOUT completed')
        self.user = None
        await self.fini()

    async def list(self, mesg):
        tag = mesg.get('tag')
        try:
            refname, mboxname = shlex.split(mesg.get('data').decode())
        except ValueError:
            return await self.sendMesg(tag, 'BAD', 'Invalid arguments for LIST.')

        parent = None
        if refname:
            parent = refname

        mailboxes = self.mail.get(self.user).get('mailboxes')

        matches = [k for k in mailboxes.items() if k[1].get('parent') == parent]

        if mboxname:
            matches = [k for k in matches if fnmatch.fnmatch(k[0], mboxname)]

        matches = sorted(matches, key=lambda k: k[0])

        for match in matches:
            name = match[0]
            if parent:
                name = f'{parent}/{name}'

            name = s_imap.quote(name)
            await self.sendMesg(s_imap.UNTAGGED, 'LIST', f'() "/" {name}')

        await self.sendMesg(tag, 'OK', 'LIST completed')

    async def select(self, mesg):
        tag = mesg.get('tag')

        mboxname = mesg.get('data').decode().lower()
        if (mailbox := self.mail[self.user]) is None or mboxname not in mailbox.get('mailboxes'):
            return await self.sendMesg(tag, 'NO', f'No such mailbox: {mailbox}.')

        flags = []
        exists = 0
        recent = 0
        uidnext = 0

        for uid, message in mailbox.get('messages').items():
            exists += 1

            mflags = message.get('flags')
            flags.extend(mflags)

            if '\\Recent' in mflags:
                recent += 1

            uidnext = max(uid, uidnext)

        flags = ' '.join(sorted(set(flags)))

        self.state = 'SELECTED'
        self.selected = mboxname.lower()
        await self.sendMesg(s_imap.UNTAGGED, 'FLAGS', f'({flags})')
        await self.sendMesg(s_imap.UNTAGGED, 'OK', 'Flags permitted.',
                            code='PERMANENTFLAGS (\\Deleted \\Seen \\*)')
        await self.sendMesg(s_imap.UNTAGGED, 'OK', 'UIDs valid.', code=f'UIDVALIDITY {self.validity}')
        await self.sendMesg(s_imap.UNTAGGED, f'{exists} EXISTS', '')
        await self.sendMesg(s_imap.UNTAGGED, f'{recent} RECENT', '')
        await self.sendMesg(s_imap.UNTAGGED, 'OK', 'Predicted next UID.', code=f'UIDNEXT {uidnext + 1}')
        await self.sendMesg(tag, 'OK', 'SELECT completed', code='READ-WRITE')

    async def expunge(self, mesg):
        tag = mesg.get('tag')

        mailbox = self.mail[self.user]

        messages = {
            k: v for k, v in mailbox['messages'].items()
            if v['mailbox'] == self.selected
        }

        uids = []
        for uid, message in messages.items():
            if '\\Deleted' in message.get('flags'):
                uids.append(uid)

        for uid in uids:
            mailbox['messages'].pop(uid)

        await self.sendMesg(tag, 'OK', 'EXPUNGE completed')

    async def uid(self, mesg):
        tag = mesg.get('tag')
        data = mesg.get('data').decode()
        parts = data.split(' ')
        command = parts[0]

        mailbox = self.mail[self.user]
        messages = {
            k: v for k, v in mailbox['messages'].items()
            if v['mailbox'] == self.selected
        }

        if command == 'STORE':
            uidset = parts[1]

            if ':' in uidset:
                start, end = uidset.split(':')

                if end == '*':
                    keys = messages.keys()
                    end = max(keys)

            else:
                start = end = uidset

            match = imap_srv_flags_rgx.match(' '.join(parts[2:]))
            if not match:
                return await self.sendMesg(tag, 'BAD', 'Invalid STORE arguments.')

            flags = match.groupdict()
            values = set(flags.get('value').split(' '))

            for uid in range(int(start), int(end) + 1):
                if uid not in messages:
                    continue

                curv = set(messages[uid]['flags'])
                if flags.get('op') == '+':
                    curv |= values
                elif flags.get('op') == '-':
                    curv ^= values
                else: # op == ''
                    curv = values

                mailbox['messages'][uid]['flags'] = list(curv)

            return await self.sendMesg(tag, 'OK', 'STORE completed')

        elif command == 'SEARCH':
            # We only support a couple of search terms for ease of implementation
            # https://www.rfc-editor.org/rfc/rfc3501#section-6.4.4
            supported = ('Answered', 'Deleted', 'Draft', 'Recent', 'Seen', 'Unanswered', 'Undeleted', 'Unseen')
            if parts[-1].title() not in supported:
                return await self.sendMesg(tag, 'BAD', f'Search term not supported: {parts[-1]}.')

            uids = ' '.join(
                [str(k[0]) for k in messages.items() if f'\\{parts[-1].title()}' in k[1].get('flags')]
            )

            await self.sendMesg(s_imap.UNTAGGED, 'SEARCH', uids)
            return await self.sendMesg(tag, 'OK', 'SEARCH completed')

        elif command == 'FETCH':
            uid = int(parts[1])

            message = messages[uid]['data']

            size = len(message)
            await self.sendMesg(s_imap.UNTAGGED, 'FETCH', f'(UID {uid} RFC822 {{{size}}}', uid=uid)
            await self.send(message.encode())
            await self.send(b')\r\n')

            return await self.sendMesg(tag, 'OK', 'FETCH completed')

        else:
            raise s_imap.ImapError(mesg=f'Unsupported command: {command}')

async def imapserv(link):
    await link.greet()

    while not link.isfini:
        mesg = await link.rx()

        # Receive commands from client
        command = mesg.get('command')

        # Check server state
        if link.state not in imaplib.Commands.get(command.upper()):
            mesg = f'{command} not allowed in the {link.state} state.'
            raise s_imap.ImapError(mesg=mesg, state=link.state, command=command)

        # Get command handler
        handler = getattr(link, command.lower(), None)
        if handler is None:
            raise NotImplementedError(f'No handler for command: {command}')

        # Process command
        await handler(mesg)

    await link.waitfini()

class ImapTest(s_test.SynTest):
    async def test_storm_imap(self):

        imaplink = None
        def _imapserv(link):
            nonlocal imaplink
            imaplink = link
            return imapserv(link)

        coro = s_link.listen('127.0.0.1', 0, _imapserv, linkcls=IMAPServer)
        with contextlib.closing(await coro) as server:

            port = server.sockets[0].getsockname()[1]
            user = 'user00@vertex.link'
            opts = {'vars': {'port': port, 'user': user}}

            async with self.getTestCore() as core:

                # list mailboxes
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    return($server.list())
                '''
                retn = await core.callStorm(scmd, opts=opts)
                mailboxes = sorted(
                    [
                        k[0] for k in imaplink.mail[user]['mailboxes'].items()
                        if k[1]['parent'] is None
                    ]
                )
                self.eq((True, mailboxes), retn)

                # search for UIDs
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    $server.select("INBOX")
                    return($server.search("SEEN"))
                '''
                retn = await core.callStorm(scmd, opts=opts)
                seen = sorted(
                    [
                        str(k[0]) for k in imaplink.mail[user]['messages'].items()
                        if k[1]['mailbox'] == 'inbox' and '\\Seen' in k[1]['flags']
                    ]
                )
                self.eq((True, seen), retn)

                # mark seen
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    $server.select("INBOX")
                    return($server.markSeen("1:7"))
                '''
                retn = await core.callStorm(scmd, opts=opts)
                self.eq((True, None), retn)
                self.eq(
                    ['1', '6', '7'],
                    sorted(
                        [
                            str(k[0]) for k in imaplink.mail[user]['messages'].items()
                            if k[1]['mailbox'] == 'inbox' and '\\Seen' in k[1]['flags']
                        ]
                    )
                )

                # delete
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    $server.select("INBOX")
                    return($server.delete("1:7"))
                '''
                retn = await core.callStorm(scmd, opts=opts)
                messages = imaplink.mail[user]['messages']
                self.notin(1, messages)
                self.notin(6, messages)
                self.notin(7, messages)
                self.isin(2, messages)
                self.isin(3, messages)
                self.isin(4, messages)
                self.isin(5, messages)
                self.isin(8, messages)
                self.eq((True, None), retn)

                # fetch and save a message
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    $server.select("INBOX")
                    yield $server.fetch("1")
                '''
                nodes = await core.nodes(scmd, opts=opts)
                self.len(1, nodes)
                self.eq('file:bytes', nodes[0].ndef[0])
                self.true(all(nodes[0].get(p) for p in ('sha512', 'sha256', 'sha1', 'md5', 'size')))
                self.eq('message/rfc822', nodes[0].get('mime'))

                byts = b''.join([byts async for byts in core.axon.get(s_common.uhex(nodes[0].get('sha256')))])
                self.eq(email.encode(), byts)

                # fetch must only be for a single message
                scmd = '''
                    $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                    $server.login($user, "pass00")
                    $server.select("INBOX")
                    $server.fetch("1:*")
                '''
                mesgs = await core.stormlist(scmd, opts=opts)
                self.stormIsInErr('Failed to make an integer', mesgs)

                # sad paths

                # FIXME
                return

                # make sure we can pass around the server object
                scmd = '''
                function foo(s) {
                    return($s.login($user, "pass00"))
                }
                $server = $lib.inet.imap.connect(127.0.0.1, port=$port, ssl=(false))
                $ret00 = $foo($server)
                $ret01 = $server.list()
                return(($ret00, $ret01))
                '''
                retn = await core.callStorm(scmd, opts=opts)
                self.eq(((True, None), (True, ('INBOX',))), retn)

                mesgs = await core.stormlist('$lib.inet.imap.connect(hello.timeout, timeout=(1))')
                self.stormIsInErr('Timed out waiting for IMAP server hello', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.timeout, timeout=(1))
                    $server.login($user, "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('Timed out waiting for IMAP server response', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.bad)
                    $server.login($user, "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('[AUTHENTICATIONFAILED] Invalid credentials (Failure)', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(login.noerr)
                    $server.login($user, "secret")
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('IMAP server returned an error', mesgs)

                scmd = '''
                    $server = $lib.inet.imap.connect(list.bad)
                    $server.login($user, "secret")
                    $server.list()
                '''
                mesgs = await core.stormlist(scmd)
                self.stormIsInErr('Could not parse command', mesgs)

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
