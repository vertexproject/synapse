import threading
import traceback

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.cli as s_cli
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.mixins as s_mixins
import synapse.lib.output as s_output

# Add our commands to the mixins registry
s_mixins.addSynMixin('cmdr', 'synapse.eventbus.EventBus', 'synapse.cmds.common.GuidCmd')
s_mixins.addSynMixin('cmdr', 'synapse.cores.common.Cortex', 'synapse.cmds.cortex.AskCmd')

def openurl(url, **opts):
    '''
    Open a remote CliServer and return a CliProxy class.

    Args:
        url (str): A URL to parse into a link tufo.
        **opts: Additional options which are added to the link tufo.

    Examples:

        Open a connection to a server and drop into an interactive command loop:

            cliprox = openurl('tcp://cliserver.com:8675/mycli')
            cliprox.runCmdLoop()

    Returns:
        CliProxy: A CliProxy object which can be used to interact with a remote object.
    '''
    cliserver = s_telepath.openurl(url, **opts)
    return CliProxy(cliserver)

def getItemCmdr(item, outp=None, **opts):
    '''
    Construct and return a cmdr for the given item.

    Args:
        item (object): Object being commanded
        outp (s_output.Output): An Output object for printing data with.
        **opts: Additional options passed to the Cli.

    Examples:
        Get the CLI for an object and run the command loop:

            cmdr = getItemCmdr(foo)
            cmdr.runCmdLoop()

    Returns:
        s_cli.Cli: A Cli for the object.
    '''
    cmdr = s_cli.Cli(item, outp=outp, **opts)
    cmdr.reflectItem()

    return cmdr

def runItemCmdr(item, outp=None, **opts):
    '''
    Create a cmdr for the given item and run the cmd loop directly.

    Args:
        item (object): Object being commanded
        outp (s_output.Output): An Output object for printing data with.
        **opts: Additional options passed to the Cli.

    Examples:
        Get and run the cmdloop for an object directly:

            runItemCmdr(foo)

    Returns:
        None
    '''
    cmdr = getItemCmdr(item, outp=outp, **opts)
    cmdr.runCmdLoop()

class CliClient(s_cli.Cli):
    '''
    The CliClient is used to implement the server-side Cli object.

    This is created and torn down per user.

    Third party implementations may override this class and provide an updated
    python path to their object as a configable option to the CliServer as
    ``cliserver:clientctor``.
    '''
    def runCmdLoop(self):
        '''
        This is a invalid function to execute on the server side.

        Raises:
            NoSuchImpl: When called.
        '''
        raise s_common.NoSuchImpl(mesg='CliClient cannot run a user cmdloop')

    def runCmdLine(self, line):
        '''
        Run a single command line.

        Args:
            line (str): Line to execute.

        Examples:
            Execute the 'woot' command with the 'help' switch:

                cli.runCmdLine('woot --help')

        Returns:
            object: Arbitrary data from the cmd class.
        '''
        ret = None

        name = line.split(None, 1)[0]

        cmdo = self.getCmdByName(name)
        if cmdo is None:
            self.printf('cmd not found: %s' % (name,))
            return

        self.fire('cli:cmd:run', line=line)

        try:

            ret = cmdo.runCmdLine(line)

        except s_common.CliFini as e:
            raise

        except Exception as e:
            exctxt = traceback.format_exc()
            self.printf(exctxt)
            self.printf('error: %s' % e)

        self.fire('cli:cmd:ret', line=line, ret=ret)

        return ret

    def postClientInit(self):
        '''
        This is executed after the client is initialized by the CliServer.
        Implementors may override this to provide additional server-side
        CLI functionality.

        Notes:
            Several items are placed in the current thread scope when prior to
            this function being executed:

            - sock: Connection socket object.
            - user: User information from the socket connection.
            - server: The CliServer object which owns this Cli object.
            - proxy:iden: The CliProxy iden.

            The Server can be used to send and receive messages from the CliProxy.
            The message "syn:cliserver:init:print:<proxy iden>" can be used to send
            a message directly to the CliProxy to be printed. The message
            "syn:cliserver:init:prompt:<proxy iden>" can be used to send a message
            and a prompt to the CliProxy, which will print and prompt the user for
            input. Responses from the CliProxy are "syn:cliserver:init:response:<proxy iden>"
            messages which can be listened for from the server.
        '''
        pass

class CliProxy(s_eventbus.EventBus):
    '''
    A client-side helper for connecting to a CLI server.

    This acts as the client side pump for sending commands to a CLI server
    and printing events from the CliServer. These events names are dynamically
    generated, as sessions are created with the CliServer and as commands are
    individually executed.

    When the proxy is being initialized to a CliServer, it generates its own
    proxy iden. This is used to set ``syn:cliserver:init:print:<iden>`` and
    ``syn:cliserver:init:prompt:<iden>`` events, which the CLI server may use to
    both send messages to the CliProxy for display to the user, and prompt
    the CliProxy for additional input which is obtained through self.get_input().
    This process is also used when addressing reconnect events.

    After the session has been established with the CliServer, a session specific
    iden is then used to monitor for syn:cliserver:<session_iden> events.  These
    may be sent by the CliServer in order to send an arbitrary message to the
    CliProxy to be displayed to the user.

    When the user requests a specific command to be executed, a per-command iden
    is generated, and the event syn:cliserver:outp:<cmdiden> is used to listen
    for messages from the CliServer in response to the requested command. This
    allows for a user to use ctrl+c to exit out of a potentially long running
    command and no longer receive any messages for that commands execution.
    '''
    def __init__(self, prox, outp=None, timeout=None):
        s_eventbus.EventBus.__init__(self)
        self.disconnect_evt = threading.Event()

        if outp is None:
            outp = s_output.OutPut()
        self.outp = outp

        self.iden = s_common.guid()  # per-instance guid
        self.cmdprompt = ''
        self._quit_cmd = 'quit'  # Add set/get api?
        self.prox = prox  # type: s_telepath.Proxy

        self._connectToServer()

        def _setDisconnectEvt(mesg):
            already_set = self.disconnect_evt.is_set()
            self.disconnect_evt.set()
            # Only print this message and fire this once
            if not already_set:
                self.printf('Server disconnect detected.')
                self.fire('syn:cliproxy:disconnect')

        # Allow for per-cli messages to be sent to the CliProxy
        self.prox.on('syn:cliserver:outp:%s' % self.session_iden, self._onPrintf)

        # setup disconnect / reconnect handlers
        self.prox.on('tele:sock:runsockfini', _setDisconnectEvt)
        self.prox.on('tele:sock:init', self._onTeleSockInit)

        self.cmdprompt = self.prox.getCmdPrompt()

        self.onfini(self._cliProxFini)

    def _onTeleSockInit(self, mesg):
        '''
        When the proxy object reconnects, attempt a reconnect to the CLI server.
        '''
        self._reconnect()
        self.disconnect_evt.clear()

    def _reconnect(self):
        '''
        Perform a reconnect operation - disable old event handlers, connect and readd event handlers.
        '''
        self.prox.off('syn:cliserver:outp:%s' % self.session_iden, self._onPrintf)
        self._connectToServer()
        self.prox.on('syn:cliserver:outp:%s' % self.session_iden, self._onPrintf)
        self.printf('Reconnected to server.')
        self.fire('syn:cliproxy:reconnect', session_iden=self.session_iden)

    def _connectToServer(self):
        '''
        Perform the connection, setting the syn:cliserver:init:print:<iden> and
        syn:cliserver:init:prompt:<iden> event handlers for the duration of the
        client startup.
        '''
        # The CliServer may print events to us during session connection
        # that we want to print to users.
        with self.prox.onWith('syn:cliserver:init:print:%s' % self.iden, self._onPrintf):
            # The syn:cliserver:init:prompt:<iden> events may cause a call/response
            # cycle with the CliProxy
            with self.prox.onWith('syn:cliserver:init:prompt:%s' % self.iden,
                                 self._onInitPrompt):
                # Do our sessions setup on the server
                self.session_iden = self.prox.getCmdrSession(self.iden)

    def _cliProxFini(self):
        self.prox.fini()

    def _onPrintf(self, mesg):
        msg = mesg[1].get('mesg')
        self.printf(msg, False)

    def printf(self, mesg, addnl=True):
        self.outp.printf(mesg, addnl=addnl)

    def _onInitPrompt(self, mesg):
        '''
        Print a message and get a user response
        '''
        prompt = mesg[1].get('prompt', self.cmdprompt)
        pmesg = mesg[1].get('mesg')
        self.printf(pmesg)
        line = self.get_input(prompt)
        self.prox.fire('syn:cliserver:init:response:%s' % self.iden, line=line)

    def get_input(self, prompt=None):
        '''
        Get the input string to parse.

        Args:
            prompt (str): Optional string to use as the prompt. Otherwise self.cmdprompt is used.

        Notes:
            This fires a 'cli:getinput' event prior to getting the
            input string from the user.

        Returns:
            str: A string to process.
        '''
        return s_cli.Cli.get_input(self, prompt)

    def runCmdLine(self, line):
        '''
        Run a single command line on the remote CLI.

        Args:
            line (str): Line to execute.

        Examples:
            Execute the 'woot' command with the 'help' switch:

                cli.runCmdLine('woot --help')

        Notes:
            This generates a random guid and sets the proxy event
            'syn:cliserver:outp:<guid>' to call self._onPrintf() in order
            to capture the output sent from the remote server.

        Returns:
            object: Arbitrary data from the cmd class.
        '''

        self.fire('cli:cmd:run', line=line)

        iden = s_common.guid()
        evtname = 'syn:cliserver:outp:%s' % iden

        with self.prox.onWith(evtname, self._onPrintf):
            ret = self.prox.runCmdLine(iden, line)

        self.fire('cli:cmd:ret', line=line, ret=ret)

        return ret

    def runCmdLoop(self):
        '''
        Run commands from a user in an interactive fashion until fini() or EOFError is raised.

        Notes:

            In the event that a disconnect is detected with the Proxy, this
            will prompt the user that a disconnect has occured and subsequent
            command execution will attempt a reconnect.
        '''
        import readline
        readline.read_init_file()

        while not self.isfini:

            # FIXME history / completion

            try:

                line = self.get_input()
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                if self.disconnect_evt.is_set():
                    if line.lower() == self._quit_cmd:
                        s_cli.CmdQuit.runCmdOpts(self, None)

                    mesg = 'Disconnected - enter "%s" to exit your session or wait for a reconnect to occur.' % \
                           self._quit_cmd
                    self.printf(mesg)
                    continue

                self.runCmdLine(line)

            except KeyboardInterrupt as e:
                self.printf('<ctrl-c>')

            except s_common.NoCurrSess as e:
                self.printf('Current session has expired on the server.')
                self._reconnect()

            except (s_common.CliFini, EOFError) as e:
                self.fini()

            except Exception as e:
                s = traceback.format_exc()
                self.printf(s)

class CliServer(s_config.Config):
    '''
    Server for managing server-side CliClients.

    Args:
        item (object): Item being commanded by the CliServer.

    Notes:
        All events fired by the CliServer are dynamically generated and it is
        expected that client side users will listen for those events as they
        trigger the server side actions to occur; or they subscribe to events
        which are specific for their CLI sessions.
    '''
    def __init__(self, item):
        s_config.Config.__init__(self)

        self.item = item
        self.outp = s_output.OutPutBus()
        # Track user sessions by socket iden to Cli object
        self.sessions = {}
        self.onfini(self._finiServer)
        self.postServerInit()

    @staticmethod
    @s_config.confdef(name='cliserver')
    def _clis_confdefs():
        confdefs = (
            ('cliserver:cmdprompt', {'type': 'str', 'defval': 'cli> ',
                                     'doc': 'Default cmdprompt',
                                     }),
            ('cliserver:clientctor', {'type': 'str', 'defval': 'synapse.lib.cmdr.CliClient',
                                      'doc': 'python path to the CliClient implementation'}),
            ('cliserver:banner', {'type': 'str', 'defval': '',
                                  'doc': 'Banner displayed to user upon on connection. It is sent prior to '
                                         'postClientInit being called.'})
        )
        return confdefs

    def _finiServer(self):
        # Tear down our CLI objects via their .sock objects so they are
        # properly cleaned up and we only have to care about defining fini
        # routines in a single place
        clis = list(self.sessions.items())
        for iden, cli in clis:
            cli.sock.fini()

    def _broadcastMesg(self, mesg, addnl=True):
        '''
        Broadcast a message to all connected CLI clients.

        Args:
            mesg (str): Message to send.
            addnl (bool): Add a newline to the message.

        Notes:
            This method is private so that it may not be exposed to remote
            users via Telepath. CliServer implementors may choose to use it
            in their implementations.

        Returns:
            None
        '''
        self.outp.printf(mesg, addnl=addnl)

    def postServerInit(self):
        '''
        This is executed at the end of the CliServer __init__ method.

        Implementors may override this to provide additional functionality..
        '''
        pass

    def getCmdrSession(self, proxyiden):
        '''
        Establissh a remote CLI session with the current socket connection.

        Args:
            proxyiden (str): An iden for the proxy.

        Examples:
            Connect to the CliServer and get a new session, then listen for print events specific for the session:

                prox = s_telepath.openurl('tcp://cliserver.com:8675/mycli')
                session_iden = prox.getCmdrSession(guid())
                prox.on('syn:cliserver:outp:%s' % session_iden, some_print_func)

        Notes:
            This method is typically called by the CliProxy classs directly
            and most users do not need to ever call this manually.

        Returns:
            str: A session iden.

        Raises:
            SessAlreadyExists: If the current connection already has an existing CLI session.
            BadTypeValu: If the proxyiden is not a guid.
        '''

        sock = s_scope.get('sock')
        user = s_scope.get('user')

        cliden = sock.get('cli:iden')
        if cliden is not None:
            raise s_common.SessAlreadyExists(mesg='sock already has a cli iden')
        if not s_common.isguid(proxyiden):
            raise s_common.BadTypeValu(valu=proxyiden,
                                       mesg='proxyiden must be a guid')

        # Make the proxy iden locally available
        s_scope.set('proxy:iden', proxyiden)
        s_scope.set('server', self)

        # Make the per-session iden / outp
        iden = s_common.guid()
        outp = s_output.OutPutBus()

        ctor = self.getConfOpt('cliserver:clientctor')
        opts = {'sock:iden': sock.iden,
                'sock:user': user,
                'sess:iden': iden,
                'proxy:iden': proxyiden}
        cli = s_dyndeps.tryDynFunc(ctor, self.item, outp, **opts)  # type: CliClient
        cli.reflectItem()

        # Strap in a server-side handler to allow for per-cli messages to be sent
        # to the remote. This handler cannot be used until this function has returned
        # and the CliProxy has a chance to register the handler for itself.
        evtname = 'syn:cliserver:outp:%s' % iden

        def _onPrint(mesg):
            self.fire(evtname, **mesg[1])

        self.outp.on('syn:output:print', _onPrint)

        # Stamp the sock onto the cli so we can refer to it later
        sock.set('cli:iden', iden)
        cli.sock = sock

        # Stamp the command prompt in
        cli.cmdprompt = self.getConfOpt('cliserver:cmdprompt')
        self.sessions[iden] = cli

        def onSockFini():
            # Multiplexor - DO NOT BLOCK
            def _onSockFini():
                self.sessions.pop(iden, None)
                self.outp.off(evtname, _onPrint)
                cli.sock = None
                cli.fini()
            s_glob.pool.call(_onSockFini)

        sock.onfini(onSockFini)

        banner = self.getConfOpt('cliserver:banner')
        if banner:
            # Shovel the banner to the client via socket.
            sock.tx(('syn:cliserver:init:print:%s' % proxyiden, {'mesg': banner}))

        # Allow implementors a change to hook the server-side CLI startup.
        cli.postClientInit()

        return iden

    def _getCliObj(self):
        '''
        Get the CLI object for the current socket.

        Returns:
            CliClient: A CliClient implementation.

        Raises:
            NoCurrSess: If there is no current session associated with the Socket.
        '''

        sock = s_scope.get('sock')
        iden = sock.get('cli:iden')

        cli = self.sessions.get(iden)
        if cli is None:
            raise s_common.NoCurrSess(mesg='No session established. Call getCmdrSesssion first.')

        return cli

    def runCmdLine(self, reqiden, line):
        '''
        Run a single command line for the current sessions CLI.

        Args:
            reqiden (str): GUID used for firing print messages for the CliProxy to pickup.
            line (str): Line to execute.

        Examples:
            Execute the 'woot' command with the 'help' switch:

                iden = guid()
                with cli.onWith('syn:cliserver:outp:%s'% iden, some_print_func):
                    cli.runCmdLine(iden, 'woot --help')

        Notes:
            This method is typically called by the CliProxy classs directly
            and most users do not need to ever call this manually.

        Returns:
            object: Arbitrary data from the cmd class.
        '''
        cli = self._getCliObj()
        if not s_common.isguid(reqiden):
            raise s_common.BadTypeValu(valu=reqiden,
                                       mesg='reqiden must be a guid')

        evtname = 'syn:cliserver:outp:%s' % reqiden

        def _onPrint(mesg):
            self.fire(evtname, **mesg[1])

        with cli.outp.onWith('syn:output:print', _onPrint):
            cli.runCmdLine(line)

    def getCmdPrompt(self):
        '''
        Get the command prompt for the current sessions CLI.

        Returns:
            str: A prompt string.
        '''
        cli = self._getCliObj()
        return cli.getCmdPrompt()
