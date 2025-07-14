import sys
import asyncio
import argparse

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output

class Parser(argparse.ArgumentParser):
    '''
    argparse.ArgumentParser helper class.

    - exit() is overriden to raise a SynErr ( ParserExit )
    - _print_message prints to an outp object
    - description formatter uses argparse.RawDescriptionHelpFormatter
    '''
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

async def wrapmain(func): # pragma: no cover

    try:
        return await func(sys.argv[1:])

    except s_exc.ParserExit:
        return 1

    except Exception as e:
        print(f'ERROR: {s_exc.reprexc(e)}')
        return 1

    finally:
        await s_coro.await_bg_tasks(timeout=10)

def exitmain(func): # pragma: no cover
    sys.exit(asyncio.run(wrapmain(func)))
