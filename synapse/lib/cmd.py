import argparse

import synapse.exc as s_exc
import synapse.lib.output as s_output

class Parser(argparse.ArgumentParser):

    def __init__(self, prog=None, outp=s_output.stdout, **kwargs):

        self.outp = outp
        self.exited = False

        argparse.ArgumentParser.__init__(self,
                                         prog=prog,
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         **kwargs)

    def exit(self, status=0, message=None):
        '''
        Argparse expects exit() to be a terminal function and not return.
        As such, this function must raise an exception instead.
        '''
        self.exited = True
        self.status = status

        if message is not None:
            self.outp.printf(message)
        raise s_exc.ParserExit(mesg=message, status=status)

    def _print_message(self, text, fd=None):
        '''
        Note:  this overrides an existing method in ArgumentParser
        '''
        self.outp.printf(text)
