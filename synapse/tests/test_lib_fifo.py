
from synapse.tests.common import *

import synapse.lib.fifo as s_fifo

class FifoTest(SynTest):

    def test_fifo_fifo(self):

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
