from . import sqlite as s_c_sqlite

istable = '''
   SELECT 1
   FROM   information_schema.tables 
   WHERE    table_name = %s
'''

class Cortex(s_c_sqlite.Cortex):

    dbvar = '%s'

    def _initDbConn(self):
        import psycopg2
        dbinfo = self._initDbInfo()
        db = psycopg2.connect(**dbinfo)
        c = db.cursor()
        c.execute('SET enable_seqscan=false')
        c.close()
        return db

    def _initCorQueries(self, table):
        s_c_sqlite.Cortex._initCorQueries(self, table)
        self._q_istable = istable

    def _getTableName(self):
        path = self.link[1].get('path')
        if not path:
            return 'syncortex'

        parts = [ p for p in path.split('/') if p ]
        if len(parts) <= 1:
            return 'syncortex'

        return parts[1]

    def _initDbInfo(self):

        dbinfo = {}

        path = self.link[1].get('path')
        if path:
            parts = [ p for p in path.split('/') if p ]
            if parts:
                dbinfo['database'] = parts[0]

        host = self.link[1].get('host')
        if host != None:
            dbinfo['host'] = host

        port = self.link[1].get('port')
        if port != None:
            dbinfo['port'] = port

        user = self.link[1].get('user')
        if user != None:
            dbinfo['user'] = user

        passwd = self.link[1].get('passwd')
        if passwd != None:
            dbinfo['password'] = passwd

        return dbinfo

