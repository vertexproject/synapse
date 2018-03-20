from synapse.tests.common import *

import synapse.lib.fifo as s_fifo

class FifoTest(SynTest):

    def test_fifo_nack_past(self):
        with self.getTestDir() as dirn:

            conf = {
                'dir': dirn,
                'file:maxsize': 1024,
                'window:max': 4,
                'window:min': 2,
                'window:fill': 1,
            }

            sent = []

            with s_fifo.Fifo(conf) as fifo:

                self.eq(fifo.wind.nack, 0)

                while fifo.atom.size != 0:
                    fifo.put('whee')

                nseq = fifo.nseq
                path = fifo._getSeqPath(0)

            os.unlink(path)

            with s_fifo.Fifo(conf) as fifo:
                self.eq(fifo.wind.nack, nseq)

    def test_fifo_flush(self):

        with self.getTestDir() as dirn:

            conf = {'dir': dirn}

            sent = []
            with s_fifo.Fifo(conf) as fifo:

                fifo.put('whee')
                fifo.put('whee')

                fifo.resync(xmit=sent.append)

                fifo.ack(sent[0][1])

                # dirty
                fifo.flush()

                # not dirty
                fifo.flush()

    def test_fifo_ack_neg1(self):

        with self.getTestDir() as dirn:

            conf = {'dir': dirn}

            sent = []
            with s_fifo.Fifo(conf, xmit=sent.append) as fifo:

                fifo.put('foo')
                fifo.put('bar')

                slen = len(sent)
                fifo.ack(-1)

                self.eq(len(sent), slen * 2)
                self.eq(sent[:slen], sent[slen:])

                # also test ack of lower than nack
                self.true(fifo.ack(sent[0][1]))
                self.false(fifo.ack(sent[0][1]))

    def test_fifo_fifo(self):

        with self.getTestDir() as dirn:

            # some very small settings so we trigger
            # more of the cleanup / culling code...
            conf = {
                'dir': dirn,
                'file:maxsize': 1024,
                'window:max': 4,
                'window:min': 2,
                'window:fill': 1,
            }

            sent = []

            with s_fifo.Fifo(conf) as fifo:

                fifo.put('foo')

                fifo.resync(xmit=sent.append)

                self.eq(sent[0][2], 'foo')
                self.len(1, fifo.wind.dequ)

                # these should all end up in the window
                fifo.put('bar')
                fifo.put('baz')
                fifo.put('faz')

                self.eq(sent[1][2], 'bar')
                self.eq(sent[2][2], 'baz')
                self.eq(sent[3][2], 'faz')

                self.len(4, fifo.wind.dequ)
                self.true(fifo.wind.caught)

                # the next should *not* make it in the window
                fifo.put('hehe')
                fifo.put('haha')
                fifo.put('hoho')

                self.len(4, fifo.wind.dequ)
                self.false(fifo.wind.caught)

                # ack 0 should shrink the window, but not fill()
                self.true(fifo.ack(sent[0][0]))
                self.len(3, fifo.wind.dequ)

                # ack next should trigger fill and load hehe/haha
                # but still not catch us up...
                self.true(fifo.ack(sent[1][0]))

                self.len(6, sent)
                self.len(4, fifo.wind.dequ)
                self.false(fifo.wind.caught)

                # ack skip to the window end (which should also set caught)
                self.true(fifo.ack(sent[-1][0]))

                self.len(7, sent)
                self.true(fifo.wind.caught)

                # now that we are caught up again, a put should xmit
                fifo.put('visi')
                self.eq(sent[-1][2], 'visi')

            # now lets check starting with an existing one...
            with s_fifo.Fifo(conf) as fifo:

                sent = []
                fifo.resync(xmit=sent.append)

                self.eq(sent[0][2], 'hoho')
                self.eq(sent[1][2], 'visi')

                self.true(fifo.wind.caught)

                # send a skip ack
                fifo.ack(sent[1][0])

                # put in enough messages to cause file next
                while fifo.atom.size != 0:
                    fifo.put('whee')

                self.len(2, fifo.seqs)
                self.false(fifo.wind.caught)

                # put in enough that when we jump over to
                # reading this file, we will not be caught up
                fifo.put('foo1')
                fifo.put('bar1')
                fifo.put('baz1')
                fifo.put('faz1')
                fifo.put('zip1')

                self.true(os.path.isfile(fifo._getSeqPath(0)))

                while sent[-1][2] == 'whee':
                    fifo.ack(sent[-1][0])

                self.len(1, fifo.seqs)
                self.none(fifo.atoms.get(0))
                self.false(os.path.isfile(fifo._getSeqPath(0)))

                # the last message should be one of the following
                # ( we may not know exactly which due to whee mod math )
                self.true(sent[-1][2] in ('foo1', 'bar1', 'baz1', 'faz1'))
                self.false(fifo.wind.caught)

                # by acking until faz1 we will fill zip1 into the window
                # and cause ourselves to be caught up again...
                # faz1 should be lifted into the window
                while sent[-1][2] != 'zip1':
                    fifo.ack(sent[-1][0])

                self.true(fifo.wind.caught)

    def test_fifo_puts(self):

        with self.getTestDir() as dirn:

            sent = []
            conf = {'dir': dirn}

            with s_fifo.Fifo(conf) as fifo:
                fifo.resync(xmit=sent.append)
                fifo.puts(('foo', 'bar'))

            self.eq(tuple(sent), ((0, 4, 'foo'), (4, 8, 'bar')))

    def test_fifo_resync_race_put(self):
        with self.getTestDir() as dirn:
            N = 1000
            conf = {'dir': dirn}
            evt = threading.Event()
            items = ['foo' + str(i) for i in range(N)]
            sent = []

            def race(data):
                evt.set()
                time.sleep(0)
                sent.append(data[2])

            @firethread
            def otherwrite():
                evt.wait()
                fifo.puts(('attempting to mutate', 'during iteration'))

            with s_fifo.Fifo(conf) as fifo:
                fifo.puts(items)
                thr = otherwrite()
                fifo.resync(xmit=race)
                thr.join()

            self.len(N + 2, sent)
            self.eq(sent[0:N], items)
            self.eq(sent[N:N + 1], ['attempting to mutate'])
            self.eq(sent[N + 1:N + 2], ['during iteration'])

            with s_fifo.Fifo(conf) as fifo:
                fifo.resync(xmit=race)

            self.len(2 * (N + 2), sent)
            self.eq(sent[0:N], items)
            self.eq(sent[N:N + 1], ['attempting to mutate'])
            self.eq(sent[N + 1:N + 2], ['during iteration'])
            self.eq(sent[N + 2:2 * N + 2], items)
            self.eq(sent[2 * N + 2:2 * N + 3], ['attempting to mutate'])
            self.eq(sent[2 * N + 3:2 * N + 4], ['during iteration'])

    def test_fifo_resync_race_ack(self):
        with self.getTestDir() as dirn:
            N = 1000
            conf = {'dir': dirn}
            evt = threading.Event()
            items = ['foo' + str(i) for i in range(N)]
            sent = []

            def race(data):
                evt.set()
                time.sleep(0)
                sent.append(data[2])

            @firethread
            def otherwrite():
                evt.wait()

                # This call to ack will not actually cull anything because
                # it won't run until after iteration has completed.
                fifo.ack(100)

            with s_fifo.Fifo(conf) as fifo:
                fifo.puts(items)
                thr = otherwrite()
                fifo.resync(xmit=race)
                thr.join()

            # The end result should be all of the items in order.
            self.len(N, sent)
            self.eq(sent, items)

    def test_fifo_resync_race_ack_resync(self):
        with self.getTestDir() as dirn:
            N = 1000
            conf = {'dir': dirn}
            evt = threading.Event()
            items = ['foo' + str(i) for i in range(N)]
            sent = []

            def race(data):
                evt.set()
                time.sleep(0)
                sent.append(data[2])

            @firethread
            def otherwrite():
                evt.wait()

                # This call to ack will not actually cull anything because
                # its seqn is -1. Instead, it will call resync, which won't
                # until after iteration has completed.
                fifo.ack(-1)

            with s_fifo.Fifo(conf) as fifo:
                fifo.puts(items)
                thr = otherwrite()
                fifo.resync(xmit=race)
                thr.join()

            # The end result should be all of the items in order, followed by all of the items in order again
            self.len(2 * N, sent)
            self.eq(sent[0:N], items)
            self.eq(sent[N:2 * N], items)
