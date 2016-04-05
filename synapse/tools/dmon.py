import logging
import os
import sys
import json
import argparse

import synapse.daemon as s_daemon

LOG_LEVEL_CHOICES = ('debug', 'info', 'warning', 'error', 'critical')

# FIXME CONFIG FILE DOCS

def getArgParser():
    p = argparse.ArgumentParser(prog='dmon')
    p.add_argument('--listen', nargs='+', default=[], help='add a synapse link listener url (default: tcp://0.0.0.0:45654)')

    p.add_argument('--add-auth', help='specify an auth addon url')
    p.add_argument('--add-logger', help='specify a logger addon url')
    p.add_argument('--add-svcbus', help='specify an svcbus addon url')

    p.add_argument('--log-level', choices=LOG_LEVEL_CHOICES, help='specify the log level')

    p.add_argument('--run-auth', help='run a UserAuth by ctor url (/syn.auth)')
    #p.add_argument('--run-queen', help='run a hivemind cluster Queen')
    #p.add_argument('--run-drone', help='run a hivemind cluster Drone')
    p.add_argument('--run-svcbus', default=False, action='store_true', help='run and share a ServiceBus at /syn.svcbus')

    p.add_argument('configs', nargs='*', help='json config file(s)')

    return p

def main(argv):

    p = getArgParser()
    opts = p.parse_args(argv)

    dmon = s_daemon.Daemon()

    conf = {
        'ctors':[],
        'addons':[],
        'svc:run':[],
        'dmon:share':[],
    }

    # translate env vars to conf
    envsvc = os.getenv('syn.svcbus')
    if envsvc:
        conf['addons'].append( ('svcbus',envsvc) )

    # translate command line to conf
    if opts.add_auth:
        conf['addons'].append( ('auth',opts.add_auth) )

    if opts.add_logger:
        conf['addons'].append( ('logger',opts.add_logger) )

    if opts.add_svcbus:
        conf['addons'].append( ('svcbus', opts.add_svcbus) )

    if opts.run_svcbus:
        conf['ctors'].append( ('syn.svcbus','ctor://synapse.lib.service.SvcBus()') )
        conf['dmon:share'].append( ('syn.svcbus',{}) )

    if opts.run_auth:
        conf['ctors'].append( ('syn.auth', opts.run_auth) )
        conf['svc:run'].append( ('syn.auth', {}) )
        conf['dmon:share'].append( ('syn.auth',{}) )

    if opts.log_level:
        logging.basicConfig(level=opts.log_level.upper())
        logging.info("log level set to " + opts.log_level)

    dmon.loadDmonConf(conf)

    for path in opts.configs:
        dmon.loadDmonFile(path)

    # if the daemon still has no listeners, add a default
    if not dmon.links():
        dmon.listen('tcp://0.0.0.0:45654/')

    dmon.main()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
