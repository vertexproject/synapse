import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.service.backup import logger, main, backup

s_common.deprecated('synapse.tools.backup is deprecated. Please use synapse.tools.service.backup instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, defval='DEBUG')
    s_cmd.exitmain(main)
