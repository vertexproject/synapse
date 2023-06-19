import os
import sys
import tomllib

# Ensure our CI tag value matches our pyproject.toml value

def main(argv):
    envar = 'CIRCLE_TAG'
    if argv:
        envar = argv[0]
    etag = os.getenv('CIRCLE_TAG', '')
    etag = etag.lstrip('v')

    with open('pyproject.toml', 'r') as fd:
        data = tomllib.loads(fd.read())
        ptag = data.get('project', {}).get('version', 'project.version missing')

    if etag != ptag:
        info = f"Git tag from {envar} => {etag} does not match the version of this app: {ptag}"
        print(info)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
