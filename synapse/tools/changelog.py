import os
import re
import sys
import pprint
import asyncio
import argparse
import datetime
import textwrap
import traceback
import subprocess
import collections

import regex

import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.lib.schemas as s_schemas

defstruct = (
    ('type', None),
    ('desc', ''),
    ('prs', ()),
)

SKIP_FILES = (
    '.gitkeep',
)

version_regex = r'^v[0-9]\.[0-9]+\.[0-9]+((a|b|rc)[0-9]*)?$'
def gen(opts: argparse.Namespace,
        outp: s_output.OutPut):
    if opts.verbose:
        outp.printf(f'{opts=}')

    name = opts.name
    if name is None:
        name = f'{s_common.guid()}.yaml'
    fp = s_common.genpath(opts.cdir, name)

    data = dict(defstruct)
    data['type'] = opts.type
    data['desc'] = opts.desc

    if opts.pr:
        data['prs'] = [opts.pr]

    if opts.verbose:
        outp.printf('Validating data against schema')

    s_schemas._reqChanglogSchema(data)

    if opts.verbose:
        outp.printf('Saving the following information:')
        outp.printf(s_common.yamldump(data).decode())

    s_common.yamlsave(data, fp)

    outp.printf(f'Saved changelog entry to {fp=}')

    if opts.add:
        if opts.verbose:
            outp.printf('Adding file to git staging')
        argv = ['git', 'add', fp]
        ret = subprocess.run(argv, capture_output=True)
        if opts.verbose:
            outp.printf(f'stddout={ret.stdout}')
            outp.printf(f'stderr={ret.stderr}')
        ret.check_returncode()

    return 0

def format(opts: argparse.Namespace,
           outp: s_output.OutPut):
    if opts.verbose:
        outp.printf(f'{opts=}')

    if not regex.match(version_regex, opts.version):
        outp.printf(f'Failed to match {opts.version} vs {version_regex}')
        return 1

    entries = collections.defaultdict(list)

    files_processed = []  # Eventually for removing files from git.

    for fn in os.listdir(opts.cdir):
        if fn in SKIP_FILES:
            continue
        fp = s_common.genpath(opts.cdir, fn)
        if opts.verbose:
            outp.printf(f'Reading: {fp=}')
        try:
            data = s_common.yamlload(fp)
        except Exception as e:
            outp.printf(f'Error parsing yaml from {fp=}: {e}')
            continue

        if opts.verbose:
            outp.printf('Got the following data:')
            outp.printf(pprint.pformat(data))

        files_processed.append(fp)

        s_schemas._reqChanglogSchema(data)

        data.setdefault('prs', [])
        prs = data.get('prs')

        if opts.prs_from_git:

            argv = ['git', 'log', '--pretty=oneline', fp]
            ret = subprocess.run(argv, capture_output=True)
            if opts.verbose:
                outp.printf(f'stddout={ret.stdout}')
                outp.printf(f'stderr={ret.stderr}')
            ret.check_returncode()

            for line in ret.stdout.splitlines():
                line = line.decode()
                line = line.strip()
                if not line:
                    continue
                match = re.search('\\(#(?P<pr>\\d{1,})\\)', line)
                if match:
                    for pr in match.groups():
                        pr = int(pr)
                        if pr not in prs:
                            prs.append(pr)
                            if opts.verbose:
                                outp.printf(f'Added PR #{pr} to the pr list from [{line=}]')

        if opts.enforce_prs and not prs:
            outp.printf(f'Entry is missing PR numbers: {fp=}')
            return 1

        if opts.verbose:
            outp.printf(f'Got data from {fp=}')

        prs.sort() # sort the PRs inplace
        entries[data.get('type')].append(data)

    if not entries:
        outp.printf(f'No files passed validation from {opts.dir}')
        return 1

    if 'model' in entries:
        outp.printf('Model specific entries are not yet implemented.')
        return 1

    date = opts.date
    if date is None:
        date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    header = f'{opts.version} - {date}'
    text = f'{header}\n{"=" * len(header)}\n'

    for key, header in s_schemas._changelogTypes.items():
        dataz = entries.get(key)
        if dataz:
            text = text + f'\n{header}\n{"-" * len(header)}'
            dataz.sort(key=lambda x: x.get('prs'))
            for data in dataz:
                desc = data.get('desc')
                for line in textwrap.wrap(desc, initial_indent='- ', subsequent_indent='  ', width=opts.width):
                    text = f'{text}\n{line}'
                if not opts.hide_prs:
                    for pr in data.get('prs'):
                        text = f'{text}\n  (`#{pr} <https://github.com/vertexproject/synapse/pull/{pr}>`_)'
            if key == 'migration':
                text = text + '\n- See :ref:`datamigration` for more information about automatic migrations.'
            text = text + '\n'

    if opts.rm:
        if opts.verbose:
            outp.printf('Staging file removals in git')
        for fp in files_processed:
            argv = ['git', 'rm', fp]
            ret = subprocess.run(argv, capture_output=True)
            if opts.verbose:
                outp.printf(f'stddout={ret.stdout}')
                outp.printf(f'stderr={ret.stderr}')
            ret.check_returncode()

    outp.printf(text)

    return 0

async def main(argv, outp=None):
    if outp is None:
        outp = s_output.OutPut()

    pars = makeargparser()

    opts = pars.parse_args(argv)
    if opts.git_dir_check:
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            outp.print('Current working directury must be the root of the repository.')
            return 1
    try:
        return opts.func(opts, outp)
    except Exception as e:
        outp.printf(f'Error running {opts.func}: {traceback.format_exc()}')
    return 1

def makeargparser():
    desc = '''Command line tool to manage changelog entries.
    This tool and any data formats associated with it may change at any time.
    '''
    pars = argparse.ArgumentParser('synapse.tools.changelog', description=desc)

    subpars = pars.add_subparsers(required=True,
                                  title='subcommands',
                                  dest='cmd', )
    gen_pars = subpars.add_parser('gen', help='Generate a new changelog entry.')
    gen_pars.set_defaults(func=gen)
    gen_pars.add_argument('-t', '--type', required=True, choices=list(s_schemas._changelogTypes.keys()),
                          help='The changelog type.')
    gen_pars.add_argument('desc', type=str,
                          help='The description to populate the initial changelog entry with.', )
    gen_pars.add_argument('-p', '--pr', type=int, default=False,
                          help='PR number associated with the changelog entry.')
    gen_pars.add_argument('-a', '--add', default=False, action='store_true',
                          help='Add the newly created file to the current git staging area.')
    # Hidden name override. Mainly for testing.
    gen_pars.add_argument('-n', '--name', default=None, type=str,
                          help=argparse.SUPPRESS)

    format_pars = subpars.add_parser('format', help='Format existing files into a RST block.')
    format_pars.set_defaults(func=format)
    mux_prs = format_pars.add_mutually_exclusive_group()
    mux_prs.add_argument('--hide-prs', default=False, action='store_true',
                         help='Hide PR entries.')
    mux_prs.add_argument('--enforce-prs', default=False, action='store_true',
                         help='Enforce PRs list to be populated with at least one number.', )
    format_pars.add_argument('--prs-from-git', default=False, action='store_true',
                             help='Attempt to populate any PR numbers from a given files commit history.')
    format_pars.add_argument('-w', '--width', help='Maximum column width to wrap descriptions at.',
                             default=79, type=int)
    format_pars.add_argument('--version', required=True, action='store', type=str,
                             help='Version number')
    format_pars.add_argument('-d', '--date', action='store', type=str,
                             help='Date to use with the changelog entry')
    format_pars.add_argument('-r', '--rm', default=False, action='store_true',
                             help='Stage the changelog files as deleted files in git.')

    for p in (gen_pars, format_pars):
        p.add_argument('-v', '--verbose', default=False, action='store_true',
                       help='Enable verbose output')
        p.add_argument('--cdir', default='./changes', action='store',
                       help='Directory of changelog files.')
        p.add_argument('--disable-git-dir-check', dest='git_dir_check', default=True, action='store_false',
                       help=argparse.SUPPRESS)

    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:], s_output.stdout)))
