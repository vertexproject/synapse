import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.service.healthcheck import main

s_common.deprecated('synapse.tools.healthcheck is deprecated. Please use synapse.tools.service.healthcheck instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
