#!/usr/bin/env python
"""
Run lint checks for Synapse.

Requires pycodestyle to be installed.

Forked from https://gist.github.com/810399
Updated from https://github.com/cbrueffer/pep8-git-hook
"""
from __future__ import print_function
import os
import subprocess
import sys

# don't fill in both of these
# good codes
select_codes = ["E111", "E101",
                "E201", "E202", "E203", "E221", "E222", "E223", "E224", "E225",
                "E226", "E227", "E228", "E231", "E241", "E242", "E251",
                "E303", "E304",
                "E502",
                "E711", "E712", "E713", "E714", "E721",
                "E741", "E742", "E743",
                "W191",
                "W291", "W293", "W292",
                "W391",
                "W602", "W603",
                ]
ignore_codes = []
# Add things like "--max-line-length=120" below
overrides = ["--max-line-length=120",
             '--format=pylint',
             ]

def system(*args, **kwargs):
    kwargs.setdefault('stdout', subprocess.PIPE)
    proc = subprocess.Popen(args, **kwargs)
    out, err = proc.communicate()
    return out

def main():

    args = ['pycodestyle']
    if select_codes and ignore_codes:
        print('Error: select and ignore codes are mutually exclusive')
        sys.exit(1)
    elif select_codes:
        args.extend(('--select', ','.join(select_codes)))
    elif ignore_codes:
        args.extend(('--ignore', ','.join(ignore_codes)))
    args.extend(overrides)
    args.append('.')
    output = system(*args)
    if output:
        print('PEP8 style violations have been detected.\n')
        print(output.decode("utf-8"),)
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
