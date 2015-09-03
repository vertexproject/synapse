import sqlite3

from synapse.compat import queue

import synapse.cores.common as common

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
getrows_by_prop = 'SELECT * FROM %s WHERE prop=?'
getrows_by_range = 'SELECT * FROM %s WHERE prop=? and intval >= ? AND intval < ?'

getsize_by_prop = 'SELECT COUNT(*) FROM %s WHERE prop=?'
getsize_by_range = 'SELECT COUNT(*) FROM %s WHERE prop=? and intval >= ? AND intval < ?'

delrows_by_id = 'DELETE FROM %s WHERE id=?'
delrows_by_prop = 'DELETE FROM %s WHERE prop=?'
deljoin_by_prop = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=? '

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

    def cursor(self):
        return self.dbpool.cursor()

    def _initDbInfo(self):
        return {'name':self.link[1].get('path')[1:]}

    def _rowsByRange(self, prop, valu, limit=None):
        q = self._q_getrows_by_range
        args = [ prop, valu[0], valu[1] ]

        if limit != None:
            q += ' LIMIT %d' % limit

        rows = self.select(q,args)
        return self._foldTypeCols(rows)

    def _sizeByRange(self, prop, valu, limit=None):
        q = self._q_getsize_by_range
        args = [ prop, valu[0], valu[1] ]

        if limit != None:
            q += ' LIMIT %d' % limit

        return self.select(q,args)[0][0]

    def _initDbConn(self):
        dbinfo = self._initDbInfo()
        return sqlite3.connect(dbinfo.get('name'))

    def _getTableName(self):
        return 'syncortex'

    def _initCortex(self):

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

        pool = int( self.link[1].get('pool',1) )

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
        self._q_getrows_by_prop = self._prepQuery(getrows_by_prop, table)
        self._q_getrows_by_range = self._prepQuery(getrows_by_range, table)

        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop, table)
        self._q_getsize_by_range = self._prepQuery(getsize_by_range, table)

        self._q_delrows_by_id = self._prepQuery(delrows_by_id, table)
        self._q_delrows_by_prop = self._prepQuery(delrows_by_prop, table)
        self._q_deljoin_by_prop = self._prepQuery(deljoin_by_prop, table)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable,(name,)))

    def _initCorTable(self, name):
        with self.cursor() as c:
            c.execute(self._q_inittable)
            c.execute(self._q_init_id_idx)
            c.execute(self._q_init_strval_idx)
            c.execute(self._q_init_intval_idx)

    def _addRows(self, rows):
        rows = [ (i,p,None,v,t) if type(v) == int else (i,p,v,None,t) for i,p,v,t in rows ]
        with self.cursor() as c:
            c.executemany( self._q_addrows, rows )

    def _addQueryParams(self, q, r, valu=None, limit=None, mintime=None, maxtime=None):
        if valu != None:
            if type(valu) == int:
                q += ' AND intval = ' + self.dbvar
                r.append(valu)
            else:
                q += ' AND strval = ' + self.dbvar
                r.append(valu)

        if mintime != None:
            q += ' AND stamp >= ' + self.dbvar
            r.append(mintime)

        if maxtime != None:
            q += ' AND stamp < ' + self.dbvar
            r.append(maxtime)

        if limit != None:
            q += ' LIMIT ' + self.dbvar
            r.append(limit)

        return q,r

    def select(self, q, r):
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
        r = [ prop ]
        q = self._q_getsize_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self.select(q,r)[0][0]

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        r = [ prop ]
        q = self._q_getrows_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        rows = self.select(q,r)
        return self._foldTypeCols(rows)

    def _delRowsById(self, ident):
        self.delete(self._q_delrows_by_id,(ident,))

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        r = [ prop ]
        q = self._q_deljoin_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,mintime=mintime,maxtime=maxtime)
        q += ' )' # terminate subselect
        self.delete(q,r)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        r = [ prop ]
        q = self._q_delrows_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,mintime=mintime,maxtime=maxtime)
        self.delete(q,r)

