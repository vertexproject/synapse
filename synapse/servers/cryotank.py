# pragma: no cover
import sys
import asyncio

import synapse.cryotank as s_cryotank

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_cryotank.CryoCell.execmain(sys.argv[1:]))
