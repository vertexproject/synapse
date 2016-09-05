import time

from . import sqlite as s_c_sqlite
from .sqlite import int_t, str_t, none_t


istable = '''
   SELECT 1
   FROM   information_schema.tables 
   WHERE    table_name = %s
'''

class Cortex(s_c_sqlite.Cortex):

    dbvar = '%s'
    dblim = None

    def _initDbConn(self):
        import psycopg2

        retry = self._link[1].get('retry',0)

        dbinfo = self._initDbInfo()

        db = None
        tries = 0
        while db == None:
            try:
                db = psycopg2.connect(**dbinfo)
            except Exception as e:
                tries += 1
                if tries > retry:
                    raise

                time.sleep(1)

        c = db.cursor()
        c.execute('SET enable_seqscan=false')
        c.close()
        return db

    def _initCorQueries(self, table):
        s_c_sqlite.Cortex._initCorQueries(self, table)
        self._q_istable = istable

        # Take advantage of postgres array support.
        self.qbuild['rowsinprop'] = self._expandCorQuery('SELECT * FROM %s WHERE prop=?', table)
        subselect = self._expandCorQuery('SELECT id FROM %s WHERE prop=?', table)
        self.qbuild['joininprop'] = {k: self._prepQuery('SELECT * from %s WHERE id IN (', table) + q + ')' for k, q in subselect.items()}

    def _expandCorQuery(self, query, table):
        limit = 'LIMIT ?'
        intv = 'AND intval IN ?'
        strv = 'AND strval IN ?'
        wmin = 'AND stamp>=?'
        wmax = 'AND stamp<?'
        queries = {
            (none_t, none_t, none_t): self._prepQuery(' '.join((query, limit)), table),
            (none_t, int_t, none_t): self._prepQuery(' '.join((query, wmin, limit)), table),
            (none_t, none_t, int_t): self._prepQuery(' '.join((query, wmax, limit)), table),
            (none_t, int_t, int_t): self._prepQuery(' '.join((query, wmin, wmax, limit)), table),
            (int_t, none_t, none_t): self._prepQuery(' '.join((query, intv, limit)), table),
            (int_t, int_t, none_t): self._prepQuery(' '.join((query, intv, wmin, limit)), table),
            (int_t, none_t, int_t): self._prepQuery(' '.join((query, intv, wmax, limit)), table),
            (int_t, int_t, int_t): self._prepQuery(' '.join((query, intv, wmin, wmax, limit)), table),
            (str_t, none_t, none_t): self._prepQuery(' '.join((query, strv, limit)), table),
            (str_t, int_t, none_t): self._prepQuery(' '.join((query, strv, wmin, limit)), table),
            (str_t, none_t, int_t): self._prepQuery(' '.join((query, strv, wmax, limit)), table),
            (str_t, int_t, int_t): self._prepQuery(' '.join((query, strv, wmin, wmax, limit)), table),
        }
        return queries

    def _getJoinInProp(self, prop, values, mintime=None, maxtime=None, limit=None):
        if values:
            rows = self._runPropQuery('joininprop',prop,valu=values,limit=limit,mintime=mintime,maxtime=maxtime)
            for row in self._foldTypeCols(rows):
                yield row

    def _getRowsInProp(self, prop, values, mintime=None, maxtime=None, limit=None):
        if values:
            rows = self._runPropQuery('rowsinprop',prop,valu=values,limit=limit,mintime=mintime,maxtime=maxtime)
            for row in self._foldTypeCols(rows):
                yield row

    def _getTableName(self):
        path = self._link[1].get('path')
        if not path:
            return 'syncortex'

        parts = [ p for p in path.split('/') if p ]
        if len(parts) <= 1:
            return 'syncortex'

        return parts[1]

    def _initDbInfo(self):

        dbinfo = {}

        path = self._link[1].get('path')
        if path:
            parts = [ p for p in path.split('/') if p ]
            if parts:
                dbinfo['database'] = parts[0]

        host = self._link[1].get('host')
        if host != None:
            dbinfo['host'] = host

        port = self._link[1].get('port')
        if port != None:
            dbinfo['port'] = port

        user = self._link[1].get('user')
        if user != None:
            dbinfo['user'] = user

        passwd = self._link[1].get('passwd')
        if passwd != None:
            dbinfo['password'] = passwd

        return dbinfo
