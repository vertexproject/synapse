#!/usr/bin/env python3

import os
import subprocess

import synapse.tools.dmon as s_dmon

en = {
    'POSTGRES_USER': os.getenv('POSTGRES_USER', 'synapse'),
    'POSTGRES_DB': os.getenv('POSTGRES_DB', 'synapse'),
    'POSTGRES_TABLE': os.getenv('POSTGRES_TABLE', 'cortex'),
    'PGDATA': os.getenv('PGDATA', '/var/lib/postgresql/data'),
    'PATH': os.getenv('PATH'),
}

subprocess.Popen('./pg_docker_entrypoint.sh postgres', shell=True, cwd='/', env=en)

print('initializing dmon main')
s_dmon.main(['/syndata/dmon.json'])

