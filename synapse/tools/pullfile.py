import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.axon.pullfile import main

s_common.deprecated('synapse.tools.pullfile is deprecated. Please use synapse.tools.axon.pullfile instead.',
                    curv='v2.219.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)