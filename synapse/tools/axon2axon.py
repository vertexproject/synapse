import synapse.common as s_common

import synapse.lib.cmd as s_cmd

from synapse.tools.axon.axon2axon import main

s_common.deprecated('synapse.tools.axon2axon is deprecated. Please use synapse.tools.axon.axon2axon instead.',
                    curv='v2.219.0')

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)