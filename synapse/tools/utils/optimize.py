import os
import sys
import asyncio
import warnings
import sysconfig
import importlib.util

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.parser as s_parser

descr = '''
Precompile a Python install so processes started from it load rather than build their
Python bytecode and the Storm grammar parser.

Everything is built for the interpreter running the tool, so run it with the same python
the services use.

Bytecode is compiled for the standard library, site-packages, and any additional
directories given. A file which does not compile cannot be imported either, so it is
reported but is not fatal.

With --check, nothing is written: the tool verifies that the bytecode is present and
current and that the Storm grammar parser loads from its cache.

Examples:

    python -m synapse.tools.utils.optimize

    python -m synapse.tools.utils.optimize --check
'''

def getInstallDirs():
    '''
    Get the directories of this Python install which hold importable modules.

    Returns:
        list: The directories, excluding any nested inside another one in the list.
    '''
    names = ('stdlib', 'platstdlib', 'purelib', 'platlib')
    dirs = sorted({os.path.abspath(sysconfig.get_path(name)) for name in names})

    retn = []
    for dirn in dirs:
        if any(dirn.startswith(prev + os.sep) for prev in retn):
            continue

        retn.append(dirn)

    return retn

async def compileDirs(dirs, levels):
    '''
    Compile Python bytecode for the given directories at the given optimization levels.

    Returns:
        int: The compileall exit code, which is 1 when any file did not compile.
    '''
    argv = [sys.executable, '-W', 'ignore::SyntaxWarning', '-m', 'compileall', '-q', '-j', '0']
    for level in levels:
        argv.extend(('-o', str(level)))

    proc = await asyncio.create_subprocess_exec(*argv, *dirs)
    return await proc.wait()

def isPycCurrent(path, pycpath):
    '''
    Check whether a bytecode file is current for its source, as the import system does.

    Returns:
        bool: True if the bytecode file matches this interpreter and the source.
    '''
    try:
        with open(pycpath, 'rb') as fd:
            head = fd.read(16)
    except OSError:
        return False

    if len(head) < 16 or head[:4] != importlib.util.MAGIC_NUMBER:
        return False

    # a hash based bytecode file is validated against the source at import, or never
    if int.from_bytes(head[4:8], 'little') & 0x1:
        return True

    info = os.stat(path)
    mtime = int.from_bytes(head[8:12], 'little')
    size = int.from_bytes(head[12:16], 'little')
    return mtime == int(info.st_mtime) & 0xFFFFFFFF and size == info.st_size & 0xFFFFFFFF

def compiles(path):
    try:
        with open(path, 'rb') as fd:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                compile(fd.read(), path, 'exec', dont_inherit=True)
        return True
    except Exception:
        return False

def checkDirs(dirs, levels):
    '''
    Find the importable sources in the given directories which lack current bytecode.

    Returns:
        list: The (path, level) tuples which lack current bytecode.
    '''
    missing = []
    for dirn in dirs:
        for root, subdirs, files in os.walk(dirn):
            subdirs[:] = [name for name in subdirs if name != '__pycache__']
            for name in files:
                if not name.endswith('.py'):
                    continue

                path = os.path.join(root, name)
                stale = [lvl for lvl in levels if not isPycCurrent(path, importlib.util.cache_from_source(path, optimization=lvl or ''))]
                if stale and compiles(path):
                    missing.extend((path, lvl) for lvl in stale)

    return missing

def getArgParser(outp):
    pars = s_cmd.Parser(prog='synapse.tools.utils.optimize', outp=outp, description=descr)
    pars.add_argument('--level', type=int, action='append', choices=(0, 1, 2), dest='levels',
                      help='A bytecode optimization level to compile (may be specified multiple times, default 0 and 1).')
    pars.add_argument('--check', action='store_true', default=False,
                      help='Verify the bytecode and Storm grammar parser cache without writing anything.')
    pars.add_argument('dirs', nargs='*', help='Additional directories to compile.')
    return pars

async def main(argv, outp=s_output.stdout):

    pars = getArgParser(outp)
    opts = pars.parse_args(argv)

    levels = opts.levels or [0, 1]
    dirs = getInstallDirs() + [os.path.abspath(dirn) for dirn in opts.dirs]

    if opts.check:
        return check(dirs, levels, outp)

    outp.printf(f'Compiling bytecode at optimization levels {levels}: {" ".join(dirs)}')

    code = await compileDirs(dirs, levels)
    if code not in (0, 1):
        outp.printf(f'ERROR: compileall exited with code {code}.')
        return 1

    if code == 1:
        outp.printf('Some files did not compile and were skipped.')

    s_parser.saveLarkParser()
    outp.printf(f'Saved the Storm grammar parser cache to {s_parser.LARK_CACHE_PATH}.')

    return 0

def check(dirs, levels, outp):

    retn = 0

    missing = checkDirs(dirs, levels)
    if missing:
        retn = 1
        count = len({path for path, level in missing})
        outp.printf(f'ERROR: {count} importable files lack current bytecode, including:')
        for path, level in missing[:20]:
            outp.printf(f'    {path} (optimization level {level})')
    else:
        outp.printf(f'Bytecode is current at optimization levels {levels}: {" ".join(dirs)}')

    if s_parser.larkcached:
        outp.printf(f'The Storm grammar parser loads from {s_parser.LARK_CACHE_PATH}.')
    else:
        retn = 1
        outp.printf(f'ERROR: The Storm grammar parser does not load from {s_parser.LARK_CACHE_PATH}.')

    return retn

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
