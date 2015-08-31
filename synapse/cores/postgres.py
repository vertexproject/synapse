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

    def _initCorQueries(self):
        s_c_sqlite.Cortex._initCorQueries(self)
        self._q_istable = istable

    def _initDbInfo(self):
        return {
            'host':self.link[1].get('host'),
            'user':self.link[1].get('authinfo',{}).get('user'),
            'port':self.link[1].get('port'),
            'passwd':self.link[1].get('authinfo',{}).get('passwd'),
            'database':self.link[1].get('path')[1:],
        }

