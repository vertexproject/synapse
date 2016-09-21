from __future__ import absolute_import,unicode_literals

import time
import sqlite3

import synapse.compat as s_compat
import synapse.cores.common as common

from synapse.compat import queue

int_t = s_compat.typeof(0)
str_t = s_compat.typeof('visi')
none_t = s_compat.typeof(None)

istable = '''
    SELECT
        name
    FROM
        sqlite_master
    WHERE
        type='table'
    AND
        name=?
'''

inittable = '''
CREATE TABLE %s (
    id VARCHAR,
    prop VARCHAR,
    strval TEXT,
    intval BIGINT,
    stamp BIGINT
);
'''

init_id_idx = 'CREATE INDEX %s_id_idx ON %s (id,prop)'
init_strval_idx = 'CREATE INDEX %s_prop_time_idx ON %s (prop,stamp)'
init_strval_idx = 'CREATE INDEX %s_strval_idx ON %s (prop,strval,stamp)'
init_intval_idx = 'CREATE INDEX %s_intval_idx ON %s (prop,intval,stamp)'

addrows = 'INSERT INTO %s (id,prop,strval,intval,stamp) VALUES (?,?,?,?,?)'
getrows_by_id = 'SELECT * FROM %s WHERE id=?'
getrows_by_range = 'SELECT * FROM %s WHERE prop=? and intval >= ? AND intval < ? LIMIT ?'
getrows_by_le = 'SELECT * FROM %s WHERE prop=? and intval <= ? LIMIT ?'
getrows_by_ge = 'SELECT * FROM %s WHERE prop=? and intval >= ? LIMIT ?'
getrows_by_id_prop = 'SELECT * FROM %s WHERE id=? AND prop=?'

################################################################################
getrows_by_prop = 'SELECT * FROM %s WHERE prop=? LIMIT ?'
getrows_by_prop_int = 'SELECT * FROM %s WHERE prop=? AND intval=? LIMIT ?'
getrows_by_prop_str = 'SELECT * FROM %s WHERE prop=? AND strval=? LIMIT ?'

getrows_by_prop_wmin = 'SELECT * FROM %s WHERE prop=? AND stamp >=? LIMIT ?'
getrows_by_prop_int_wmin = 'SELECT * FROM %s WHERE prop=? AND intval=? AND stamp >=? LIMIT ?'
getrows_by_prop_str_wmin = 'SELECT * FROM %s WHERE prop=? AND strval=? AND stamp >=? LIMIT ?'

getrows_by_prop_wmax = 'SELECT * FROM %s WHERE prop=? AND stamp<? LIMIT ?'
getrows_by_prop_int_wmax = 'SELECT * FROM %s WHERE prop=? AND intval=? AND stamp<? LIMIT ?'
getrows_by_prop_str_wmax = 'SELECT * FROM %s WHERE prop=? AND strval=? AND stamp<? LIMIT ?'

getrows_by_prop_wminmax = 'SELECT * FROM %s WHERE prop=? AND stamp>=? AND stamp<? LIMIT ?'
getrows_by_prop_int_wminmax = 'SELECT * FROM %s WHERE prop=? AND intval=? AND stamp>=? AND stamp<? LIMIT ?'
getrows_by_prop_str_wminmax = 'SELECT * FROM %s WHERE prop=? AND strval=? AND stamp>=? AND stamp<? LIMIT ?'
################################################################################
getsize_by_prop = 'SELECT COUNT(*) FROM %s WHERE prop=? LIMIT ?'
getsize_by_prop_int = 'SELECT COUNT(*) FROM %s WHERE prop=? AND intval=? LIMIT ?'
getsize_by_prop_str = 'SELECT COUNT(*) FROM %s WHERE prop=? AND strval=? LIMIT ?'

getsize_by_prop_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=? AND stamp>=? LIMIT ?'
getsize_by_prop_int_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=? AND intval=? AND stamp>=? LIMIT ?'
getsize_by_prop_str_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=? AND strval=? AND stamp>=? LIMIT ?'

getsize_by_prop_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND stamp<? LIMIT ?'
getsize_by_prop_int_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND intval=? AND stamp<? LIMIT ?'
getsize_by_prop_str_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND strval=? AND stamp<? LIMIT ?'

getsize_by_prop_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND stamp>=? AND stamp<? LIMIT ?'
getsize_by_prop_int_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND intval=? AND stamp>=? AND stamp<? LIMIT ?'
getsize_by_prop_str_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=? AND strval=? AND stamp>=? AND stamp<? LIMIT ?'
################################################################################

getsize_by_range = 'SELECT COUNT(*) FROM %s WHERE prop=? and intval >= ? AND intval < ? LIMIT ?'
getsize_by_le = 'SELECT COUNT(*) FROM %s WHERE prop=? and intval <= ? LIMIT ?'
getsize_by_ge = 'SELECT COUNT(*) FROM %s WHERE prop=? and intval >= ? LIMIT ?'

delrows_by_id = 'DELETE FROM %s WHERE id=?'
delrows_by_id_prop = 'DELETE FROM %s WHERE id=? AND prop=?'

################################################################################
delrows_by_prop = 'DELETE FROM %s WHERE prop=?'
delrows_by_prop_int = 'DELETE FROM %s WHERE prop=? AND intval=?'
delrows_by_prop_str = 'DELETE FROM %s WHERE prop=? AND strval=?'

delrows_by_prop_wmin = 'DELETE FROM %s WHERE prop=? AND stamp>=?'
delrows_by_prop_int_wmin = 'DELETE FROM %s WHERE prop=? AND intval=? AND stamp>=?'
delrows_by_prop_str_wmin = 'DELETE FROM %s WHERE prop=? AND strval=? AND stamp>=?'

delrows_by_prop_wmax = 'DELETE FROM %s WHERE prop=? AND stamp<?'
delrows_by_prop_int_wmax = 'DELETE FROM %s WHERE prop=? AND intval=? AND stamp<?'
delrows_by_prop_str_wmax = 'DELETE FROM %s WHERE prop=? AND strval=? AND stamp<?'

delrows_by_prop_wminmax = 'DELETE FROM %s WHERE prop=? AND stamp>=? AND stamp<?'
delrows_by_prop_int_wminmax = 'DELETE FROM %s WHERE prop=? AND intval=? AND stamp>=? AND stamp<?'
delrows_by_prop_str_wminmax = 'DELETE FROM %s WHERE prop=? AND strval=? AND stamp>=? AND stamp<?'

################################################################################
getjoin_by_prop = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? LIMIT ?)'
getjoin_by_prop_int = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? LIMIT ?)'
getjoin_by_prop_str = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? LIMIT ?)'

getjoin_by_prop_wmin = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp>=? LIMIT ?)'
getjoin_by_prop_int_wmin = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? AND stamp>=? LIMIT ?)'
getjoin_by_prop_str_wmin = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? AND stamp>=? LIMIT ?)'

getjoin_by_prop_wmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp<? LIMIT ?)'
getjoin_by_prop_int_wmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? AND stamp<? LIMIT ?)'
getjoin_by_prop_str_wmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? AND stamp<? LIMIT ?)'

getjoin_by_prop_wminmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp>=? AND stamp<? LIMIT ?)'
getjoin_by_prop_int_wminmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? AND stamp>=? AND stamp<? LIMIT ?)'
getjoin_by_prop_str_wminmax = 'SELECT * from %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? AND stamp>=? AND stamp<? LIMIT ?)'

################################################################################
deljoin_by_prop = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?)'
deljoin_by_prop_int = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=?)'
deljoin_by_prop_str = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=?)'

deljoin_by_prop_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp>=? )'
deljoin_by_prop_int_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? AND stamp>=? )'
deljoin_by_prop_str_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? AND stamp>=? )'

deljoin_by_prop_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp<? )'
deljoin_by_prop_int_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=? AND stamp<? )'
deljoin_by_prop_str_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=? AND stamp<? )'

deljoin_by_prop_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND stamp>=? AND stamp <?)'
deljoin_by_prop_int_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND intval=?)'
deljoin_by_prop_str_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? AND strval=?)'
################################################################################

uprows_by_id_prop_str = 'UPDATE %s SET strval=? WHERE id=? and prop=?'
uprows_by_id_prop_int = 'UPDATE %s SET intval=? WHERE id=? and prop=?'

class WithCursor:

    def __init__(self, pool, db, cursor):
        self.db = db
        self.pool = pool
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc, cls, tb):
        self.cursor.close()

        self.db.commit()
        self.pool.putdb( self.db )

class DbPool:
    '''
    The DbPool allows generic db connection pooling using
    a factory/ctor method and a python queue.

    Example:

        def connectdb():
            # do stuff
            return db

        pool = DbPool(3, connectdb)

        with pool.cursor() as c:

    '''

    def __init__(self, size, ctor):
        # TODO: high/low water marks
        self.size = size
        self.ctor = ctor
        self.dbque = queue.Queue()

        for i in range(size):
            db = ctor()
            self.putdb( db )

    def cursor(self):
        db = self.dbque.get()
        cur = db.cursor()
        return WithCursor(self, db, cur)

    def putdb(self, db):
        '''
        Add/Return a db connection to the pool.
        '''
        self.dbque.put(db)

class Cortex(common.Cortex):

    dbvar = '?'
    dblim = -1

    def cursor(self):
        return self.dbpool.cursor()

    def _initDbInfo(self):
        name = self._link[1].get('path')[1:]
        if not name:
            raise Exception('No Path Specified!')

        return {'name':name}

    def _getDbLimit(self, limit):
        if limit != None:
            return limit
        return self.dblim

    def _rowsByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        q = self._q_getrows_by_range
        args = [ prop, valu[0], valu[1], limit ]

        rows = self.select(q,args)
        return self._foldTypeCols(rows)

    def _rowsByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_ge

        rows = self.select(q, [ prop, valu, limit ])
        return self._foldTypeCols(rows)

    def _rowsByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_le
        rows = self.select(q, [prop,valu,limit])
        return self._foldTypeCols(rows)

    def _sizeByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_range
        args = [ prop, valu[0], valu[1], limit ]
        return self.select(q,args)[0][0]

    def _sizeByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_ge
        args = [ prop, valu, limit ]
        return self.select(q,args)[0][0]

    def _sizeByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_le
        args = [ prop, valu, limit ]
        return self.select(q,args)[0][0]

    def _initDbConn(self):
        dbinfo = self._initDbInfo()
        db = sqlite3.connect(dbinfo.get('name'), check_same_thread=False)
        def onfini():
            db.close()
        self.onfini(onfini, weak=True)
        return db

    def _getTableName(self):
        return 'syncortex'

    def _initCortex(self):

        self.initSizeBy('ge',self._sizeByGe)
        self.initRowsBy('ge',self._rowsByGe)

        self.initSizeBy('le',self._sizeByLe)
        self.initRowsBy('le',self._rowsByLe)

        self.initTufosBy('in',self._tufosByIn)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

        self.dbpool = self._link[1].get('dbpool')
        if self.dbpool == None:
            pool = int( self._link[1].get('pool',1) )
            self.dbpool = DbPool(pool, self._initDbConn)

        table = self._getTableName()

        self._initCorQueries(table)
        if not self._checkForTable( table ):
            self._initCorTable( table )

    def _prepQuery(self, query, table):
        # prep query strings by replacing all %s with table name
        # and all ? with db specific variable token
        tabtup = (table,) * query.count('%s')
        query = query % tabtup
        query = query.replace('?',self.dbvar)
        return query

    def _initCorQueries(self, table):
        self._q_istable = istable
        self._q_inittable = self._prepQuery(inittable, table)
        self._q_init_id_idx = self._prepQuery(init_id_idx, table)
        self._q_init_strval_idx = self._prepQuery(init_strval_idx, table)
        self._q_init_intval_idx = self._prepQuery(init_intval_idx, table)

        self._q_addrows = self._prepQuery(addrows, table)
        self._q_getrows_by_id = self._prepQuery(getrows_by_id, table)
        self._q_getrows_by_range = self._prepQuery(getrows_by_range, table)
        self._q_getrows_by_ge = self._prepQuery(getrows_by_ge, table)
        self._q_getrows_by_le = self._prepQuery(getrows_by_le, table)
        self._q_getrows_by_id_prop = self._prepQuery(getrows_by_id_prop, table)

        ###################################################################################
        self._q_getrows_by_prop = self._prepQuery(getrows_by_prop, table)
        self._q_getrows_by_prop_wmin = self._prepQuery(getrows_by_prop_wmin, table)
        self._q_getrows_by_prop_wmax = self._prepQuery(getrows_by_prop_wmax, table)
        self._q_getrows_by_prop_wminmax = self._prepQuery(getrows_by_prop_wminmax, table)
        ###################################################################################
        self._q_getrows_by_prop_int = self._prepQuery(getrows_by_prop_int, table)
        self._q_getrows_by_prop_int_wmin = self._prepQuery(getrows_by_prop_int_wmin, table)
        self._q_getrows_by_prop_int_wmax = self._prepQuery(getrows_by_prop_int_wmax, table)
        self._q_getrows_by_prop_int_wminmax = self._prepQuery(getrows_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getrows_by_prop_str = self._prepQuery(getrows_by_prop_str, table)
        self._q_getrows_by_prop_str_wmin = self._prepQuery(getrows_by_prop_str_wmin, table)
        self._q_getrows_by_prop_str_wmax = self._prepQuery(getrows_by_prop_str_wmax, table)
        self._q_getrows_by_prop_str_wminmax = self._prepQuery(getrows_by_prop_str_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop = self._prepQuery(getjoin_by_prop, table)
        self._q_getjoin_by_prop_wmin = self._prepQuery(getjoin_by_prop_wmin, table)
        self._q_getjoin_by_prop_wmax = self._prepQuery(getjoin_by_prop_wmax, table)
        self._q_getjoin_by_prop_wminmax = self._prepQuery(getjoin_by_prop_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop_int = self._prepQuery(getjoin_by_prop_int, table)
        self._q_getjoin_by_prop_int_wmin = self._prepQuery(getjoin_by_prop_int_wmin, table)
        self._q_getjoin_by_prop_int_wmax = self._prepQuery(getjoin_by_prop_int_wmax, table)
        self._q_getjoin_by_prop_int_wminmax = self._prepQuery(getjoin_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop_str = self._prepQuery(getjoin_by_prop_str, table)
        self._q_getjoin_by_prop_str_wmin = self._prepQuery(getjoin_by_prop_str_wmin, table)
        self._q_getjoin_by_prop_str_wmax = self._prepQuery(getjoin_by_prop_str_wmax, table)
        self._q_getjoin_by_prop_str_wminmax = self._prepQuery(getjoin_by_prop_str_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop, table)
        self._q_getsize_by_prop_wmin = self._prepQuery(getsize_by_prop_wmin, table)
        self._q_getsize_by_prop_wmax = self._prepQuery(getsize_by_prop_wmax, table)
        self._q_getsize_by_prop_wminmax = self._prepQuery(getsize_by_prop_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop_int = self._prepQuery(getsize_by_prop_int, table)
        self._q_getsize_by_prop_int_wmin = self._prepQuery(getsize_by_prop_int_wmin, table)
        self._q_getsize_by_prop_int_wmax = self._prepQuery(getsize_by_prop_int_wmax, table)
        self._q_getsize_by_prop_int_wminmax = self._prepQuery(getsize_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop_str = self._prepQuery(getsize_by_prop_str, table)
        self._q_getsize_by_prop_str_wmin = self._prepQuery(getsize_by_prop_str_wmin, table)
        self._q_getsize_by_prop_str_wmax = self._prepQuery(getsize_by_prop_str_wmax, table)
        self._q_getsize_by_prop_str_wminmax = self._prepQuery(getsize_by_prop_str_wminmax, table)
        ###################################################################################

        self.qbuild = {
            'rowsbyprop':{
                (none_t,none_t,none_t):self._q_getrows_by_prop,
                (none_t,int_t,none_t):self._q_getrows_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getrows_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getrows_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getrows_by_prop_int,
                (int_t,int_t,none_t):self._q_getrows_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getrows_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getrows_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getrows_by_prop_str,
                (str_t,int_t,none_t):self._q_getrows_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getrows_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getrows_by_prop_str_wminmax,
            },
            'joinbyprop':{
                (none_t,none_t,none_t):self._q_getjoin_by_prop,
                (none_t,int_t,none_t):self._q_getjoin_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getjoin_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getjoin_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getjoin_by_prop_int,
                (int_t,int_t,none_t):self._q_getjoin_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getjoin_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getjoin_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getjoin_by_prop_str,
                (str_t,int_t,none_t):self._q_getjoin_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getjoin_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getjoin_by_prop_str_wminmax,
            },
            'sizebyprop':{
                (none_t,none_t,none_t):self._q_getsize_by_prop,
                (none_t,int_t,none_t):self._q_getsize_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getsize_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getsize_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getsize_by_prop_int,
                (int_t,int_t,none_t):self._q_getsize_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getsize_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getsize_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getsize_by_prop_str,
                (str_t,int_t,none_t):self._q_getsize_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getsize_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getsize_by_prop_str_wminmax,
            },
            'delrowsbyprop':{
                (none_t,none_t,none_t):self._prepQuery(delrows_by_prop, table),
                (none_t,int_t,none_t):self._prepQuery(delrows_by_prop_wmin, table),
                (none_t,none_t,int_t):self._prepQuery(delrows_by_prop_wmax, table),
                (none_t,int_t,int_t):self._prepQuery(delrows_by_prop_wminmax, table),

                (int_t,none_t,none_t):self._prepQuery(delrows_by_prop_int, table),
                (int_t,int_t,none_t):self._prepQuery(delrows_by_prop_int_wmin, table),
                (int_t,none_t,int_t):self._prepQuery(delrows_by_prop_int_wmax, table),
                (int_t,int_t,int_t):self._prepQuery(delrows_by_prop_int_wminmax, table),

                (str_t,none_t,none_t):self._prepQuery(delrows_by_prop_str, table),
                (str_t,int_t,none_t):self._prepQuery(delrows_by_prop_str_wmin, table),
                (str_t,none_t,int_t):self._prepQuery(delrows_by_prop_str_wmax, table),
                (str_t,int_t,int_t):self._prepQuery(delrows_by_prop_str_wminmax, table),
            },
            'deljoinbyprop':{
                (none_t,none_t,none_t):self._prepQuery(deljoin_by_prop, table),
                (none_t,int_t,none_t):self._prepQuery(deljoin_by_prop_wmin, table),
                (none_t,none_t,int_t):self._prepQuery(deljoin_by_prop_wmax, table),
                (none_t,int_t,int_t):self._prepQuery(deljoin_by_prop_wminmax, table),

                (int_t,none_t,none_t):self._prepQuery(deljoin_by_prop_int, table),
                (int_t,int_t,none_t):self._prepQuery(deljoin_by_prop_int_wmin, table),
                (int_t,none_t,int_t):self._prepQuery(deljoin_by_prop_int_wmax, table),
                (int_t,int_t,int_t):self._prepQuery(deljoin_by_prop_int_wminmax, table),

                (str_t,none_t,none_t):self._prepQuery(deljoin_by_prop_str, table),
                (str_t,int_t,none_t):self._prepQuery(deljoin_by_prop_str_wmin, table),
                (str_t,none_t,int_t):self._prepQuery(deljoin_by_prop_str_wmax, table),
                (str_t,int_t,int_t):self._prepQuery(deljoin_by_prop_str_wminmax, table),
            }
        }

        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop, table)

        self._q_getsize_by_ge = self._prepQuery(getsize_by_ge, table)
        self._q_getsize_by_le = self._prepQuery(getsize_by_le, table)
        self._q_getsize_by_range = self._prepQuery(getsize_by_range, table)

        self._q_delrows_by_id = self._prepQuery(delrows_by_id, table)
        self._q_delrows_by_id_prop = self._prepQuery(delrows_by_id_prop, table)

        self._q_uprows_by_id_prop_str = self._prepQuery(uprows_by_id_prop_str, table)
        self._q_uprows_by_id_prop_int = self._prepQuery(uprows_by_id_prop_int, table)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable,(name,)))

    def _initCorTable(self, name):
        with self.cursor() as c:
            c.execute(self._q_inittable)
            c.execute(self._q_init_id_idx)
            c.execute(self._q_init_strval_idx)
            c.execute(self._q_init_intval_idx)

    def _addRows(self, rows):
        rows = [ (i,p,None,v,t) if s_compat.isint(v) else (i,p,v,None,t) for i,p,v,t in rows ]
        with self.cursor() as c:
            c.executemany( self._q_addrows, rows )

    def update(self, q, r, ret=False):
        #print('UPDATE: %r %r' % (q,r))
        with self.cursor() as cur:
            cur.execute(q,r)
            if ret:
                return cur.fetchall()

            return cur.rowcount

    def select(self, q, r):
        #print('SELECT: %r %r' % (q,r))
        with self.cursor() as cur:
            cur.execute(q,r)
            return cur.fetchall()

    def delete(self, q, r):
        #print('DELETE: %s %r' % (q,r))
        with self.cursor() as cur:
            cur.execute(q,r)

    def _foldTypeCols(self, rows):
        ret = []
        for ident,prop,intval,strval,stamp in rows:

            if intval != None:
                ret.append( (ident,prop,intval,stamp) )
            else:
                ret.append( (ident,prop,strval,stamp) )
                
        return ret

    def _getRowsById(self, ident):
        rows = self.select(self._q_getrows_by_id,(ident,))
        return self._foldTypeCols(rows)

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('sizebyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return rows[0][0]

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('rowsbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _tufosByIn(self, prop, valus, limit=None):
        ret = []

        for valu in valus:
            res = self.getTufosByProp(prop, valu=valu, limit=limit)
            ret.extend(res)

            if limit != None:
                limit -= len(res)
                if limit <= 0:
                    break

        return ret

    def _runPropQuery(self, name, prop, valu=None, limit=None, mintime=None, maxtime=None, meth=None, nolim=False):
        limit = self._getDbLimit(limit)

        qkey = (s_compat.typeof(valu),s_compat.typeof(mintime),s_compat.typeof(maxtime))

        qargs = [ prop ]
        qargs.extend( [ v for v in (valu,mintime,maxtime) if v != None ] )

        if not nolim:
            qargs.append(limit)

        qstr = self.qbuild[name][qkey]
        #print('QNAM: %r' % (name,))
        #print('QKEY: %r' % (qkey,))
        #print('QSTR: %r' % (qstr,))
        #print('QARG: %r' % (qargs,))
        if meth == None:
            meth = self.select

        rows = meth(qstr,qargs)

        #print('QROW: %r' % (rows,))
        return rows

    def _delRowsByIdProp(self, ident, prop):
        self.delete( self._q_delrows_by_id_prop, (ident,prop))

    def _getRowsByIdProp(self, iden, prop):
        rows = self.select( self._q_getrows_by_id_prop, (iden,prop))
        return self._foldTypeCols(rows)

    def _setRowsByIdProp(self, ident, prop, valu):
        if s_compat.isint(valu):
            count = self.update( self._q_uprows_by_id_prop_int, (valu,ident,prop) )
        else:
            count = self.update( self._q_uprows_by_id_prop_str, (valu,ident,prop) )

        if count == 0:
            rows = [ (ident,prop,valu,int(time.time())), ]
            self._addRows(rows)

    def _delRowsById(self, ident):
        self.delete(self._q_delrows_by_id,(ident,))

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('deljoinbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,meth=self.delete, nolim=True)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self._runPropQuery('joinbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('delrowsbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,meth=self.delete, nolim=True)
