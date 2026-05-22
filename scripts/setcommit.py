import os
import sys

def main(argv):
    commit = argv[0]
    print(f'Got commit {commit=}')
    src_path = argv[1]

    for (dirn, dirns, filenames) in os.walk(src_path):
        for filename in filenames:
            if filename == 'version.py':
                fpath = os.path.join(dirn, filename)
                print(f'Adding commit into {fpath=}')
                with open(fpath, 'rb') as fd:
                    buf = fd.read().decode('utf-8')

                content = buf.replace("commit = ''", f"commit='{commit}'")

                if content != buf:
                    print(f'Writing changes to {fpath=}')
                    with open(fpath, 'wb') as fd:
                        fd.truncate(0)
                        fd.write(content.encode())

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
