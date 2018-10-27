import os
import threading

from synapse.exc import IsFini
import synapse.lib.sqlite as s_sqlite
import synapse.lib.threads as s_threads

import synapse.tests.utils as s_t_utils

class SqliteTest(s_t_utils.SynTest):

    def test_sqlite_pool(self):

        names = ['t1:write:0', 't0:read:0', 't1:done']
        steps = self.getTestSteps(names)

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'db0.db')

            with s_sqlite.pool(3, path) as pool:

                self.eq(pool.avail(), 3)
                with pool.xact() as xact:
                    self.eq(pool.avail(), 2)
                    xact.execute('CREATE TABLE test ( foo VARCHAR, bar INT )')
                self.eq(pool.avail(), 3)

                ###############################################################
                def t1():

                    with pool.xact() as xact1:
                        xact1.execute('INSERT INTO test (foo,bar) VALUES ("lol", 20)')
                        xact1.executemany('INSERT INTO test (foo,bar) VALUES (?, ?)', [('lol', 30), ('lol', 40)])
                        steps.step('t1:write:0', 't0:read:0', timeout=8)

                    steps.done('t1:done')
                ###############################################################

                thrd = s_threads.worker(t1)
                with pool.xact() as xact0:

                    # wait for t1 to hold a write xact open...
                    steps.wait('t1:write:0')

                    # we should be able to see his un-commited write due to shared cache
                    # ( using a select query to specifically avoid the write lock )
                    rows = list(xact0.select('SELECT * FROM test'))
                    self.isin(('lol', 20), rows)
                    self.isin(('lol', 30), rows)
                    self.isin(('lol', 40), rows)

                    # allow t1 to close the write xact
                    steps.step('t0:read:0', 't1:done', timeout=8)

                    # now we can write...
                    xact0.execute('INSERT INTO test (foo, bar) VALUES (?, ?)', ('hah', 30))

                self.none(thrd.join(timeout=8))

                with pool.xact() as xact2:
                    # we should see our previously commited write
                    rows = list(xact2.select('SELECT * FROM test WHERE foo = ?', ('hah',)))
                    self.len(1, rows)

                    self.eq(1, xact2.update('UPDATE test SET foo = ? WHERE foo = ?', ('heh', 'hah')))

            # ensure that the pool commit/fini wrote all data...
            with s_sqlite.pool(2, path) as pool:
                with pool.xact() as xact:
                    # we should see our previously commited write
                    rows = list(xact.select('SELECT * FROM test'))
                    self.len(4, rows)

            with s_sqlite.pool(2, path) as pool:
                with pool.xact() as xact:
                    pool.fini()
                    # the xact should be fini because the pool is fini
                    self.raises(IsFini, xact.select, 'SELECT * FROM test');
                    self.raises(IsFini, xact.wrlock);
