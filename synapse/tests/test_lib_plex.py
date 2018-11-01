import os
import logging
import functools
import threading

import synapse.glob as s_glob
import synapse.lib.plex as s_plex
import synapse.lib.certdir as s_certdir

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class PlexTest(s_t_utils.SynTest):

    def test_plex_callLater(self):
        evt = threading.Event()
        data = {}

        def func(*args, **kwargs):
            evt.set()
            data['args'] = args
            data['kwargs'] = kwargs

        partial = functools.partial(func, 1, 2, key='valu')

        t0 = s_glob.plex.time()
        delay = 0.1
        s_glob.plex.callLater(delay, partial)
        self.true(evt.wait(2))
        t1 = s_glob.plex.time()
        self.ge(t1 - t0, delay)
        self.isin('args', data)
        self.isin('kwargs', data)

    def test_plex_callAt(self):
        evt = threading.Event()
        data = {}

        @s_glob.inpool
        def func(*args, **kwargs):
            evt.set()
            data['args'] = args
            data['kwargs'] = kwargs

        partial = functools.partial(func, 1, 2, key='valu')

        t0 = s_glob.plex.time()
        delay = 0.2
        s_glob.plex.callAt(t0 + delay, partial)
        self.true(evt.wait(3))
        t1 = s_glob.plex.time()
        self.ge(t1 - t0, delay)
        self.isin('args', data)
        self.isin('kwargs', data)
