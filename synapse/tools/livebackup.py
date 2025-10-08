import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.service.livebackup import main

s_common.deprecated('synapse.tools.livebackup is deprecated. Please use synapse.tools.service.livebackup instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
