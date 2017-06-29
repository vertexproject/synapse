#!/usr/bin/env python3

import os
import time
import subprocess

import synapse.tools.dmon as s_dmon

en = dict(os.environ)
en['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'synapse')
en['POSTGRES_DB'] = os.getenv('POSTGRES_DB', 'synapse')
en['POSTGRES_TABLE'] = os.getenv('POSTGRES_TABLE', 'cortex')
en['PGDATA'] = os.getenv('PGDATA', '/var/lib/postgresql/data')

subprocess.Popen('./docker-entrypoint.sh postgres', shell=True, cwd='/', env=en)

pgv = '%s/PG_VERSION' % (en['PGDATA'],)
while True:
    if os.path.isfile(pgv) and os.stat(pgv).st_size > 0:
        break
    print('waiting for PG to initialize')
    time.sleep(1)

print('initializing dmon main')
s_dmon.main(['/syndata/dmon.json'])
