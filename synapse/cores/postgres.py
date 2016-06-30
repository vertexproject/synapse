import time

from . import sqlite as s_c_sqlite

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

