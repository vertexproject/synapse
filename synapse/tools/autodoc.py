import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.utils.autodoc import logger, main

s_common.deprecated('synapse.tools.autodoc is deprecated. Please use synapse.tools.utils.autodoc instead.',
                    curv='v2.224.0')

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    s_cmd.exitmain(main)
