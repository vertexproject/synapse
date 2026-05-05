# pragma: no cover
import sys
import asyncio

import synapse.cortex as s_cortex

if __name__ == '__main__':  # pragma: no cover
    s_cortex.Cortex.startmain(sys.argv[1:])
