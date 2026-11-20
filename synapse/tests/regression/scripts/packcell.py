'''
Pack a regression cell directory into the gzipped tar the tests extract.

Only uses the standard library, so a generator running on a 2.x Synapse can
import it from alongside itself.

    python packcell.py <celldir> [<celldir> ...]

writes <celldir>.tar.gz next to each cell directory.
'''
import os
import sys
import gzip
import tarfile

def pack(dirn, path):
    '''
    Pack the files of the cell in dirn into a gzipped tar at path.

    Only files are added, in sorted order, with their ownership, mode and mtime
    normalized, and the gzip header carries no name or mtime, so packing the
    same cell twice produces identical bytes.
    '''
    names = []
    for root, dirs, files in os.walk(dirn):
        for name in files:
            names.append(os.path.relpath(os.path.join(root, name), dirn))

    names.sort()

    with open(path, 'wb') as fd, gzip.GzipFile(filename='', mode='wb', fileobj=fd, mtime=0) as gz, \
         tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tar:
        for name in names:
            fullpath = os.path.join(dirn, name)

            info = tarfile.TarInfo(name.replace(os.sep, '/'))
            info.size = os.path.getsize(fullpath)
            info.mode = 0o644
            info.mtime = 0

            with open(fullpath, 'rb') as fd:
                tar.addfile(info, fd)

def main(argv):

    if not argv:
        print(__doc__)
        return 1

    for dirn in argv:
        dirn = os.path.abspath(dirn).rstrip(os.sep)
        path = f'{dirn}.tar.gz'
        pack(dirn, path)
        print(f'packed {dirn} -> {path}')

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
