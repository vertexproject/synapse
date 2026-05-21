import sys
import subprocess

# Replace the embedded commit information with our current git commit

def main():
    try:
        ret = subprocess.run(['git', 'rev-parse', 'HEAD'],
                             capture_output=True,
                             timeout=15,
                             check=False,
                             text=True,
                             )
    except Exception as e:
        print(f'Error grabbing commit: {e}')
        return 1
    else:
        commit = ret.stdout.strip()
    fp = './synapse/lib/version.py'
    with open(fp, 'rb') as fd:
        buf = fd.read()
    content = buf.decode()
    new_content = content.replace("commit = ''", f"commit = '{commit}'")
    if content == new_content:
        print(f'Unable to insert commit into {fp}')
        return 1
    with open(fp, 'wb') as fd:
        _ = fd.write(new_content.encode())
    print(f'Inserted commit {commit} into {fp}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
