#!/usr/bin/env python

# Ensure rstorm execute properly.
# Check the changelog files for valid yaml, no multiline scalars, schema validation

import os
import re
import sys
import traceback
import subprocess

import yaml

basepath = os.path.split(__file__)[0]
# Inject the synapse directory into sys.path
sys.path.append(basepath + '/../')

changlogpath = os.path.join(basepath, '../changes')

try:
    import synapse.lib.schemas as s_schemas
except ImportError:
    print('Failed to import synapse schemas module')
    s_schemas = None

def check_changelogs(dirn):
    # Ensure all changelog files are valid yaml and do not contain multiline scalars
    for fn in os.listdir(dirn):
        if not fn.endswith('.yaml'):
            continue
        fp = os.path.abspath(os.path.join(dirn, fn))
        print(f'Checking {fp}')
        with open(fp, 'rb') as fd:
            bytz = fd.read()
        # Just asserting we are valid yaml to start with.
        data = yaml.load(bytz, yaml.SafeLoader)
        # And validate the schema.
        if s_schemas is not None:
            s_schemas._reqChangelogSchema(data)
        # Do we have multi-line scalers?
        if re.findall(r'[a-z0-9]\:\s+\|\s*\n', bytz.decode('utf8'), flags=re.IGNORECASE):
            if data.get('desc:literal') is not True:
                raise ValueError(f'multiline scaler detected in {fp} without desc:literal set to true')

    print('Validated changelog entries.')

def main():

    try:
        check_changelogs(changlogpath)
    except Exception:
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
