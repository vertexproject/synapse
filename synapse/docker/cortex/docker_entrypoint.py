#!/usr/bin/python3

##!/bin/bash
#set -e
#
#/pg_docker_entrypoint.sh postgres &
#python3 -m synapse.tools.dmon /cortex.conf

import os
import subprocess

en = {
    'POSTGRES_USER': os.getenv('POSTGRES_USER', 'synapse'),
    'POSTGRES_DB': os.getenv('POSTGRES_DB', 'synapse'),
    'POSTGRES_TABLE': os.getenv('POSTGRES_TABLE', 'cortex'),
    'PGDATA': os.getenv('PGDATA', '/var/lib/postgresql/data'),
    'PATH': os.getenv('PATH'),
}
print('EN: %r' % (en,))

subprocess.Popen('./pg_docker_entrypoint.sh postgres', shell=True, cwd='/', env=en)

 #dmon = 'python3 -m synapse.tools.dmon /cortex.conf'
import synapse.tools.dmon as s_dmon
print('calling dmon main')
s_dmon.main(['/cortex.conf'])

