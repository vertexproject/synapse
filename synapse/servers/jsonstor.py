# pragma: no cover
import sys
import asyncio

import synapse.lib.jsonstor as s_jsonstor

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_jsonstor.JsonStorCell.execmain(sys.argv[1:]))
