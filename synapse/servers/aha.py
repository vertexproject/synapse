# pragma: no cover
import sys
import asyncio

import synapse.lib.aha as s_aha

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_aha.AhaCell.execmain(sys.argv[1:]))
