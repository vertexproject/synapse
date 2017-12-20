import synapse.lib.cli as s_cli
import synapse.lib.cmdr as s_cmdr
import synapse.lib.mixins as s_mixins

from synapse.tests.common import *

class TstCliClient(s_cmdr.CliClient):
    '''
    Example client which implements a basic interactive username/password auth
    '''
    authtimeout = 6

    def postClientInit(self):
        # Simple username/password combination example
        server = s_scope.get('server')
        proxyiden = self.get('proxy:iden')

        resps = []

        def getResponse(mesg):
            line = mesg[1].get('line')
            resps.append(line)

        evnt = 'syn:cliserver:init:response:%s' % proxyiden
        promptevt = 'syn:cliserver:init:prompt:%s' % proxyiden
        printevt = 'syn:cliserver:init:print:%s' % proxyiden
        server.fire(printevt, mesg='You will need to identify yourself to proceed.')
        with server.onWith(evnt, getResponse):
            w = server.waiter(1, evnt)
            server.fire(promptevt, mesg='Login required', prompt='login> ')

            r = w.wait(self.authtimeout)
            if not r:
                raise NoSuchUser(mesg='User required within timeout!')

            username = resps[0].strip()

            w = server.waiter(1, evnt)
            server.fire(promptevt, mesg='Password required', prompt='password> ')

            r = w.wait(self.authtimeout)
            if not r:
                raise NoSuchUser(mesg='Password required within timeout!')
            password = resps[1].strip()

        r = self.item.checkAuth(username, password)
        if not r:
            raise NoAuthUser(mesg='Invalid userauth provided.')

        self.set('auth:user', username)
        # Could do custom mixins per user, etc.

class TstAuthyDude(s_eventbus.EventBus):
    def __init__(self):
        s_eventbus.EventBus.__init__(self)

        self.users = {
            'pennywise': 'hunter2',
            'visi': '12345'
        }

    def checkAuth(self, username, password):
        if self.users.get(username) == password:
            return True
        return False

    def listUsers(self):
        return list(self.users)

class TstUsersCmd(s_cli.Cmd):
    '''
    List the users on the AuthyDude
    '''
    _cmd_name = 'users'

    def runCmdOpts(self, opts):
        ret = self._cmd_cli.item.listUsers()
        mesg = json.dumps(ret, indent=2, sort_keys=True)
        self.printf(mesg)

class TstThrowCmd(s_cli.Cmd):
    '''
    Throw an exception.
    '''
    _cmd_name = 'throwzero'

    def runCmdOpts(self, opts):
        ret = 1 / 0

s_mixins.addSynMixin('cmdr', 'synapse.tests.test_lib_cmdr.TstAuthyDude', 'synapse.tests.test_lib_cmdr.TstUsersCmd')

class CliServerTest(SynTest):
    def test_cmdr_runitemcmdr(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator(['help',
                             'quit'])
        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            s_cmdr.runItemCmdr(None, outp)
        self.true(outp.expect('quit'))
        self.true(outp.expect('o/'))

    def test_cli_server_basic(self):
        outp = self.getTestOutp()
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            w = server.waiter(1, 'syn:cliserver:sockfini')
            with s_telepath.openurl(url) as prox:
                with s_cmdr.CliProxy(prox, outp) as cli:
                    cli.runCmdLine('help')
                    self.true(outp.expect('quit'))

                    cli.runCmdLine('ask [inet:ipv4=1.2.3.4]')
                    self.true(outp.expect('1.2.3.4'))
                    self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))

                    cli.runCmdLine('float down here')
                    self.true(outp.expect('cmd not found: float'))

                    # We have one sesssion on the server
                    self.len(1, server.sessions)

                    # Attempting to re-establish a session with the current proxy socket fails
                    self.raises(SessAlreadyExists, prox.getCmdrSession, 'hehe')

                    # server side CLI session cannot run a cmdloop
                    servercli = server.sessions[list(server.sessions.keys())[0]]
                    self.raises(NoSuchImpl, servercli.runCmdLoop)

                    # Insert a bad command which will cause an exception
                    servercli.addCmdClass(TstThrowCmd)
                    cli.runCmdLine('throwzero')
                    self.true(outp.expect('ZeroDivisionError'))

                    # the runCmdLine executed by the proxy must havee a valid iden
                    self.raises(BadTypeValu, prox.runCmdLine, 'hehe', 'help')

            w.wait(1)
            # We have zero sessions since the disconnect of the client
            # triggers a removal of the sesssion.
            self.len(0, server.sessions)

            # The openurl helper works
            cli = s_cmdr.openurl(url)
            self.isinstance(cli, s_cmdr.CliProxy)
            self.len(1, server.sessions)
            cli.fini()

            with s_telepath.openurl(url) as prox:
                # A session must be established prior to executing commands.
                self.raises(NoCurrSess, prox.runCmdLine, guid(), 'help')

                # A proxyiden must have a valid guid to be make a session
                self.raises(BadTypeValu, prox.getCmdrSession, 'lolnope')

            dmon.fini()

    def test_cli_server_reconnect(self):
        outp = self.getTestOutp()
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            prox = s_telepath.openurl(url)
            cli = s_cmdr.CliProxy(prox, outp)

            cli.runCmdLine('help')
            self.true(outp.expect('quit'))

            w = cli.waiter(1, 'syn:cliproxy:disconnect')
            dmon.fini()  # tear down the servers
            w.wait(2)

            self.true(outp.expect('Server disconnect detected.'))

            # Now bring the server back up and we should reconnect
            w = cli.waiter(1, 'syn:cliproxy:reconnect')
            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)
            dmon.share('server', server, fini=True)
            w.wait(3)

            self.true(outp.expect('Reconnected to server.'))

            cli.runCmdLine('locs')
            self.true(outp.expect(cli.iden))

            cli.fini()

    def test_cli_server_multiple_clis(self):
        outp0 = self.getTestOutp()
        outp1 = self.getTestOutp()

        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            prox0 = s_telepath.openurl(url)
            cli0 = s_cmdr.CliProxy(prox0, outp0)

            w = server.waiter(1, 'syn:cliserver:sockfini')

            with s_telepath.openurl(url) as prox1:
                with s_cmdr.CliProxy(prox1, outp1) as cli1:
                    # We have two session on the server
                    self.len(2, server.sessions)

                    server._broadcastMesg('We all float down here')
                    time.sleep(0.1)
                    self.true(outp0.expect('We all float down here'))
                    self.true(outp1.expect('We all float down here'))

                    # Ensure messages are not sent between objects
                    cli1.runCmdLine('help')
                    time.sleep(0.1)
                    self.true(outp1.expect('quit'))
                    self.false(outp0.expect('quit', throw=False))

                    cli0.runCmdLine('ask [inet:ipv4=1.2.3.4]')
                    time.sleep(0.1)
                    self.true(outp0.expect('1.2.3.4'))
                    self.false(outp1.expect('1.2.3.4', throw=False))

            # Our context manager controlled cli is gone
            w.wait(1)
            self.len(1, server.sessions)

            w = server.waiter(1, 'syn:cliserver:sockfini')
            cli0.fini()
            w.wait(1)

            self.len(0, server.sessions)
            dmon.fini()

    def test_cli_server_runcmdloop(self):
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            cmdg = CmdGenerator(['ask [inet:ipv4=1.2.3.4]',
                                 'locs',
                                 '',
                                 '    ',
                                 'quit',
                                 ])
            outp = self.getTestOutp()
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                with s_telepath.openurl(url) as prox:
                    with s_cmdr.CliProxy(prox, outp) as cli:
                        cli.runCmdLoop()
                    self.true(outp.expect('o/'))
                    self.true(outp.expect('1.2.3.4'))
                    self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
                    self.true(cli.isfini)

            # Exercise some exception handlers
            cmdg = CmdGenerator(['help',
                                 ],
                                KeyboardInterrupt)
            outp = self.getTestOutp()

            data = {'count': 0}
            def _onGetInput(mesg):
                data['count'] = data['count'] + 1
                if data['count'] > 2:
                    cmdg.addCmd('quit')

            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                with s_telepath.openurl(url) as prox:
                    with s_cmdr.CliProxy(prox, outp) as cli:
                        cli.on('cli:getinput', _onGetInput)
                        cli.runCmdLoop()
                    self.true(outp.expect('<ctrl-c>'))
                    self.true(outp.expect('o/'))
                    self.true(cli.isfini)

    def test_cli_server_runcmdloop_disconnect(self):
        outp = self.getTestOutp()
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            cmdg = CmdGenerator(['help',
                                 ],
                                on_end='help')
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                with s_telepath.openurl(url) as prox:
                    with s_cmdr.CliProxy(prox, outp) as cli:

                        w = cli.waiter(1, 'syn:cliproxy:disconnect')

                        def kill_dmon(mesg):
                            if not dmon.isfini:
                                dmon.fini()
                                w.wait(2)

                        def onCliProxDisconnect(mesg):
                            cmdg.addCmd('hehehe')
                            cmdg.addCmd('quit')

                        cli.on('syn:cliproxy:disconnect', onCliProxDisconnect)
                        cli.on('cli:cmd:ret', kill_dmon)
                        cli.runCmdLoop()
                        self.true(cli.isfini)
                        self.true(outp.expect('Disconnected - enter'))
                        self.true(outp.expect('to exit your session or wait for a reconnect to occur.'))
                        self.true(outp.expect('o/'))

    def test_cli_server_banner(self):
        outp0 = self.getTestOutp()
        outp1 = self.getTestOutp()
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            prox0 = s_telepath.openurl(url)
            cli0 = s_cmdr.CliProxy(prox0, outp0)

            server.setConfOpt('cliserver:banner', 'Welcome to Derry!\n')

            with s_telepath.openurl(url) as prox1:
                with s_cmdr.CliProxy(prox1, outp1) as cli1:
                    self.true(outp1.expect('Welcome to Derry!\n'))

            self.false(outp0.expect('Welcome to Derry!', throw=False))

            dmon.fini()

    def test_cli_server_dmonconf(self):
        conf = {
            'ctors': [
                [
                    'core',
                    'syn:cortex',
                    {
                        'url': 'ram://'
                    }
                ],
                [
                    'cliserver',
                    'ctor://synapse.lib.cmdr.CliServer(core)',
                    {}
                ]
            ],
            'share': [
                [
                    'cliserver',
                    {}
                ]
            ]
        }

        outp = self.getTestOutp()

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)

            link = dmon.listen('tcp://127.0.0.1:0/')
            port = link[1].get('port')

            prox = s_telepath.openurl('tcp://127.0.0.1/cliserver', port=port)
            cli = s_cmdr.CliProxy(prox, outp)
            self.len(1, dmon.locs.get('cliserver').sessions)

        # The dmon tore down the CliServer object for us automatically
        # tearing down open sessions
        self.len(0, dmon.locs.get('cliserver').sessions)

        # Ok now the dmon has fini'd our cli should have gotten a disconnect
        # event set based on the prox being disconnected
        self.true(cli.disconnect_evt.wait(1))

        # Avoid leaking proxy objects
        cli.fini()

    def test_cli_server_custom_impl(self):
        conf = {
            'ctors': [
                [
                    'authy',
                    'ctor://synapse.tests.test_lib_cmdr.TstAuthyDude()',
                    {}
                ],
                [
                    'cliserver',
                    'ctor://synapse.lib.cmdr.CliServer(authy)',
                    {
                        'config': 'cliserver'
                    }
                ]
            ],
            'configs': {
                'cliserver': {
                    'cliserver:banner': 'Welcome to the revolution!\n',
                    'cliserver:cmdprompt': 'hehe> ',
                    'cliserver:clientctor': 'synapse.tests.test_lib_cmdr.TstCliClient',
                }
            },
            'share': [
                [
                    'cliserver',
                    {}
                ]
            ]
        }

        outp = self.getTestOutp()

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)

            link = dmon.listen('tcp://127.0.0.1:0/')
            port = link[1].get('port')

            # The first two lines get consumed by the initialization call/response hooks.
            cmdg = CmdGenerator(['pennywise',
                                 'hunter2',
                                 'help',
                                 'users',
                                 'quit',
                                 ])
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                with s_telepath.openurl('tcp://127.0.0.1/cliserver', port=port) as prox:
                    with s_cmdr.CliProxy(prox, outp) as cli:
                        cli.runCmdLoop()
                        self.true(cli.isfini)
                        self.true(outp.expect('Welcome to the revolution!'))
                        self.true(outp.expect('You will need to identify yourself to proceed.'))
                        self.true(outp.expect('Login required'))
                        self.true(outp.expect('Password required'))
                        self.true(outp.expect('List the users'))
                        self.true(outp.expect('"visi"'))
                        self.true(outp.expect('o/'))
