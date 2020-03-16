import os
import sys
import asyncio

import synapse.axon as s_axon

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_cortex.Axon.execmain(sys.argv[1:]))
