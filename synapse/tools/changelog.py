import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.utils.changelog import main

s_common.deprecated('synapse.tools.changelog is deprecated. Please use synapse.tools.utils.changelog instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
