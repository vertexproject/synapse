import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.utils.json2mpk import main

s_common.deprecated('synapse.tools.json2mpk is deprecated. Please use synapse.tools.utils.json2mpk instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
