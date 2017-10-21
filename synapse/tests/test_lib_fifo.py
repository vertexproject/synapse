
from synapse.tests.common import *

import synapse.lib.fifo as s_fifo

class FifoTest(SynTest):

    def test_fifo_fdir(self):

        with self.getTestDir() as dirn:

            # some very small settings so we trigger
            # more of the cleanup / culling code...
            conf = {
                'fifo:dir': dirn,
                'fifo:file:maxsize': 1024,
                'fifo:window:max': 4,
                'fifo:window:min': 2,
                'fifo:window:fill': 1,
            }

            sent = []

            with s_fifo.FifoDir(conf) as fdir:

                fdir = s_fifo.FifoDir(conf)
                fdir.put('foo')

                fdir.resync(xmit=sent.append)

                self.eq(sent[0][2], 'foo')
                self.len(1, fdir.fifo.dequ)

                # these should all end up in the window
                fdir.put('bar')
                fdir.put('baz')
                fdir.put('faz')

                self.eq(sent[1][2], 'bar')
                self.eq(sent[2][2], 'baz')
                self.eq(sent[3][2], 'faz')

                self.len(4, fdir.fifo.dequ)
                self.true(fdir.fifo.caught)

                # the next should *not* make it in the window
                fdir.put('hehe')
                fdir.put('haha')
                fdir.put('hoho')

                self.len(4, fdir.fifo.dequ)
                self.false(fdir.fifo.caught)

                # ack 0 should shrink the window, but not fill()
                self.true(fdir.ack(sent[0][0]))
                self.len(3, fdir.fifo.dequ)

                # ack next should trigger fill and load hehe/haha
                # but still not catch us up...
                self.true(fdir.ack(sent[1][0]))

                self.len(6, sent)
                self.len(4, fdir.fifo.dequ)
                self.false(fdir.fifo.caught)

                # ack skip to the window end (which should also set caught)
                self.true(fdir.ack(sent[-1][0]))

                self.len(7, sent)
                self.true(fdir.fifo.caught)

                # now that we are caught up again, a put should xmit
                fdir.put('visi')
                self.eq(sent[-1][2], 'visi')

            # now lets check starting with an existing one...
            with s_fifo.FifoDir(conf) as fdir:

                sent = []
                fdir.resync(xmit=sent.append)

                self.eq(sent[0][2], 'hoho')
                self.eq(sent[1][2], 'visi')

                self.true(fdir.fifo.caught)

                # send a skip ack
                fdir.ack(sent[1][0])

                # put in enough messages to cause file next
                while fdir.atom.size != 0:
                    fdir.put('whee')

                self.len(2, fdir.seqs)
                self.false(fdir.fifo.caught)

                # put in enough that when we jump over to
                # reading this file, we will not be caught up
                fdir.put('foo1')
                fdir.put('bar1')
                fdir.put('baz1')
                fdir.put('faz1')
                fdir.put('zip1')

                self.true(os.path.isfile(fdir._getSeqPath(0)))

                while sent[-1][2] == 'whee':
                    fdir.ack(sent[-1][0])

                self.len(1, fdir.seqs)
                self.false(os.path.isfile(fdir._getSeqPath(0)))

                # the last message should be one of the following
                # ( we may not know exactly which due to whee mod math )
                self.true(sent[-1][2] in ('foo1', 'bar1', 'baz1', 'faz1'))
                self.false(fdir.fifo.caught)

                # by acking until faz1 we will fill zip1 into the window
                # and cause ourselves to be caught up again...
                # faz1 should be lifted into the window
                while sent[-1][2] != 'zip1':
                    fdir.ack(sent[-1][0])

                self.true(fdir.fifo.caught)
