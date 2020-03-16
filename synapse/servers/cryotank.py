import sys
import asyncio

import synapse.cryotank as s_cryotank

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_cryotank.CryoTank.execmain(sys.argv[1:]))
