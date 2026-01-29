import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.utils.rstorm import logger, main

s_common.deprecated('synapse.tools.rstorm is deprecated. Please use synapse.tools.utils.rstorm instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger)
    s_cmd.exitmain(main)
