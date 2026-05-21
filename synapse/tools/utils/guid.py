import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

async def main(argv, outp=s_output.stdout):
    outp.printf(s_common.guid())
    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
