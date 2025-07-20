import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.pkgs.genpkg import loadPkgProto, main, tryLoadPkgProto

s_common.deprecated('synapse.tools.genpkg is deprecated. Please use synapse.tools.pkgs.genpkg.',
                    eolv='v2.217.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
