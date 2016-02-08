import os
import sys
import json
import argparse

import synapse.lib.webapp as s_webapp

# FIXME CONFIG FILE DOCS

def getArgParser():
    p = argparse.ArgumentParser()
    p.add_argument('config', help='json config file')
    return p

def main(argv):

    p = getArgParser()
    opts = p.parse_args(argv)

    with open(opts.config,'rb') as fd:
        config = json.loads( fd.read().decode('utf8') )

    settings = config.get('tornado',{})

    wapp = s_webapp.WebApp(**settings)

    wapp.load(config)

    wapp.main()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
