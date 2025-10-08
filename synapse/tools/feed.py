import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.cortex.feed import logger, main

s_common.deprecated('synapse.tools.feed is deprecated. Please use synapse.tools.cortex.feed instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    s_cmd.exitmain(main)
