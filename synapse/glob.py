import os
import pprint
import signal
import asyncio
import logging
import threading
import faulthandler

import synapse.common as s_common
import synapse.lib.time as s_time

logger = logging.getLogger(__name__)

_glob_loop = None
_glob_thrd = None

def _asynciostacks(*args, **kwargs):  # pragma: no cover
    '''
    A signal handler used to print asyncio task stacks and thread stacks.
    '''
    ts = s_time.repr(s_common.now())
    print(80 * '*')
    print(f'Asyncio task stacks @ {ts}:')
    tasks = asyncio.all_tasks(_glob_loop)
    for task in tasks:
        task.print_stack()
        if hasattr(task, '_syn_task'):
            st = task._syn_task
            root = None
            if st.root is not None:
                root = st.root.iden
            print(f'syntask metadata: iden={st.iden} name={st.name} root={root} user={st.user.iden} username={st.user.name}')
            print(pprint.pformat(st.info))
    print(80 * '*')
    print(f'Faulthandler stack frames per thread @ {ts}:')
    faulthandler.dump_traceback()
    print(80 * '*')

def _threadstacks(*args, **kwargs):  # pragma: no cover
    '''
    A signal handler used to print thread stacks.
    '''
    ts = s_time.repr(s_common.now())
    print(80 * '*')
    print(f'Faulthandler stack frames per thread @ {ts}:')
    faulthandler.dump_traceback()
    print(80 * '*')

signal.signal(signal.SIGUSR1, _threadstacks)
signal.signal(signal.SIGUSR2, _asynciostacks)

def initloop():

    global _glob_loop
    global _glob_thrd

    # if there's no global loop....
    if _glob_loop is None:

        # check if it's us....
        try:
            _glob_loop = asyncio.get_running_loop()
            # if we get here, it's us!
            _glob_thrd = threading.current_thread()
            # Enable debug and greedy coro collection
            setGreedCoro(_glob_loop)

        except RuntimeError:
            _glob_loop = asyncio.new_event_loop()
            setGreedCoro(_glob_loop)

            _glob_thrd = threading.Thread(target=_glob_loop.run_forever, name='SynLoop', daemon=True)
            _glob_thrd.start()

    return _glob_loop

def setGreedCoro(loop: asyncio.AbstractEventLoop):
    greedy_threshold = os.environ.get('SYN_GREEDY_CORO')
    if greedy_threshold is not None:  # pragma: no cover
        logger.info(f'Setting ioloop.slow_callback_duration to {greedy_threshold}')
        loop.set_debug(True)
        loop.slow_callback_duration = float(greedy_threshold)

def iAmLoop():
    initloop()
    return threading.current_thread() == _glob_thrd

def _clearGlobals():
    '''
    reset loop / thrd vars. for unit test use.
    '''
    global _glob_loop
    global _glob_thrd
    if _glob_thrd is not None and _glob_thrd.name == 'SynLoop':
        _glob_loop.stop()
        _glob_thrd.join(timeout=30)
    _glob_loop = None
    _glob_thrd = None
