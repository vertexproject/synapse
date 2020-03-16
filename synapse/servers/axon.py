# pragma: no cover
import sys
import asyncio

import synapse.axon as s_axon

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_axon.Axon.execmain(sys.argv[1:]))
