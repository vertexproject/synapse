import sqlite3
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
    strval VARCHAR,
    intval BIGINT,
    stamp BIGINT
);
'''
init_id_idx = 'CREATE INDEX %s_id_idx ON %s (id)'
init_strval_idx = 'CREATE INDEX %s_strval_idx ON %s (prop,strval,stamp)'
init_intval_idx = 'CREATE INDEX %s_intval_idx ON %s (prop,intval,stamp)'

addrows = 'INSERT INTO %s (id,prop,strval,intval,stamp) VALUES (?,?,?,?,?)'
getrows_by_id = 'SELECT * FROM %s WHERE id=?'
getrows_by_prop = 'SELECT * FROM %s WHERE prop=?'
getsize_by_prop = 'SELECT COUNT(*) FROM %s WHERE prop=?'

delrows_by_id = 'DELETE FROM %s WHERE id=?'

class WithCursor:

    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc, cls, trace):
        self.cursor.close()

class Cortex(common.Cortex):

    dbvar = '?'
    def cursor(self):
        return WithCursor( self.db.cursor() )

    def _initCortex(self):

        self.db = self.corinfo.get('db')
        if self.db == None:
            dbinfo = self.corinfo.get('dbinfo')
            self.db = self._initDataBase(dbinfo)

        self.tbname = self.corinfo.get('tablename','syncortex')

        if not self.tbname.isalnum():
            raise Exception('table name: %s ( must be alphanum! )' % (self.tbname,))

        self._initCorQueries()
        if not self._checkForTable( self.tbname ):
            self._initCorTable( self.tbname )

    def _initDataBase(self, dbinfo):
        # an existing connection?
        return sqlite3.connect(dbinfo.get('name'))

    def _prepQuery(self, query):
        # prep query strings by replacing all %s with table name
        # and all ? with db specific variable token
        tabtup = (self.tbname,) * query.count('%s')
        query = query % tabtup
        query = query.replace('?',self.dbvar)
        return query

    def _initCorQueries(self):
        self._q_istable = istable
        self._q_inittable = self._prepQuery(inittable)
        self._q_init_id_idx = self._prepQuery(init_id_idx)
        self._q_init_strval_idx = self._prepQuery(init_strval_idx)
        self._q_init_intval_idx = self._prepQuery(init_intval_idx)

        self._q_addrows = self._prepQuery(addrows)
        self._q_getrows_by_id = self._prepQuery(getrows_by_id)
        self._q_getrows_by_prop = self._prepQuery(getrows_by_prop)
        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop)

        self._q_delrows_by_id = self._prepQuery(delrows_by_id)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable,(name,)))

    def _initCorTable(self, name):
        # *still* doesn't implement "with"
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
        with self.cursor() as cur:
            cur.execute(q,r)

    def _getRowsById(self, ident):
        return self.select(self._q_getrows_by_id,(ident,))

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        r = [ prop ]
        q = self._q_getsize_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self.select(q,r)[0][0]

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        r = [ prop ]
        q = self._q_getrows_by_prop
        q,r = self._addQueryParams(q,r,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self.select(q,r)

    def _delRowsById(self, ident):
        self.delete(self._q_delrows_by_id,(ident,))

