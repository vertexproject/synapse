import ctypes
import platform

from synapse.lib.platforms.common import *

sysname = platform.system().lower()
if sysname == 'darwin':
    from synapse.lib.platforms.darwin import *

elif sysname == 'linux':
    from synapse.lib.platforms.linux import *

elif sysname == 'freebsd':
    from synapse.lib.platforms.freebsd import *

elif getattr(ctypes, 'windll', None):
    from synapse.lib.platforms.windows import *
