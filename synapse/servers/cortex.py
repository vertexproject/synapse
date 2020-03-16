# pragma: no cover
import sys
import asyncio

import synapse.cortex as s_cortex

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_cortex.Cortex.execmain(sys.argv[1:]))
