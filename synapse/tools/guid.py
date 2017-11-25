import synapse.common as s_common
import synapse.lib.output as s_output

def main(argv, outp=None):
    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    outp.printf(s_common.guid())

if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main(sys.argv))
