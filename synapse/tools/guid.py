import sys

import synapse.common as s_common
import synapse.lib.output as s_output

def main(argv, outp=s_output.stdout):
    outp.printf(s_common.guid())

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
