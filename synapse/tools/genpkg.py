import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.storm.pkg.gen import main, tryLoadPkgProto, loadPkgProto

s_common.deprecated('synapse.tools.genpkg is deprecated. Please use synapse.tools.storm.pkg.gen instead.',
                    curv='v2.225.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
