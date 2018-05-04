import synapse.eventbus as s_eventbus

import synapse.lib.output as s_output

class Quit(Exception): pass

class Cmdr(s_eventbus.EventBus):
    '''
    A cmdline interface to a telepath Service.
    '''
    def __init__(self, prox, outp=s_output.stdout):

        s_eventbus.EventBus.__init__(self)

        self.prox = prox
        self.outp = outp

        self.localcmds = {
            'quit': self._runCmdQuit,
        }

        name = prox.getSvcType()
        self.prompt = '%s> ' % name

    def _runCmdQuit(self, line):
        self.printf('signing off...')
        raise Quit()

    def getCmdInput(self):
        '''
        Get the input string to parse.

        Returns:
            (str): A command line string to process.
        '''
        return input(self.prompt).strip()

    def printf(self, mesg, addnl=True):
        return self.outp.printf(mesg, addnl=addnl)

    def runCmdLoop(self):
        '''
        Run a command loop from stdin.
        '''
        import readline
        readline.read_init_file()

        while not self.isfini:

            # FIXME history / completion

            try:

                line = self.getCmdInput()
                if not line:
                    continue

                self.runCmdLine(line)

            except KeyboardInterrupt as e:
                self.printf('<ctrl-c>')

            except (Quit, EOFError) as e:
                self.fini()

            except Exception as e:
                s = traceback.format_exc()
                self.printf(s)

    def runCmdLine(self, line):
        '''
        Run a single command line.

        Args:
            line (str): Line to execute.
        '''
        name = line.split(None, 1)[0]

        func = self.localcmds.get(name)
        if func is not None:
            return func(line)

        # optimal generator syntax for a proxy call...
        for text in self.prox.runSvcCmd(line):
        #with self.prox.runSvcCmd(line) as outp:
            #for text in outp:
            print('TEXT: %r' % (text,))
            self.printf(text)
