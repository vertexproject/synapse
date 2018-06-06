import os
import sys
import logging
import argparse

import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps

import synapse.lib.output as s_output

import synapse.tools.dmon as s_dmon

logger = logging.getLogger(__name__)

desc = '''
Deploy a cell to a daemon directory.
'''

def main(argv, outp=None):
    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = makeargpaser()
    opts = pars.parse_args(argv)

    if opts.module:
        mod = s_dyndeps.tryDynMod(opts.module)
        outp.printf(f'Loaded {opts.module}@{mod}')

    if opts.cells:
        outp.printf('Registered cells:')
        for cname, cpath in s_cells.getCells():
            outp.printf(f'{cname:<10} {cpath:>10}')
        return 0

    dirn = s_common.genpath(opts.dmonpath, 'cells', opts.cellname)
    if os.path.isdir(dirn):
        outp.printf(f'cell directory already exists: {dirn}')
        return 1

    dmon = {}
    if opts.listen:
        dmon['listen'] = opts.listen

    if opts.module:
        dmon['modules'] = [opts.module]

    if dmon:
        dmon.setdefault('modules', [])
        dmon_fp = os.path.join(opts.dmonpath, 'dmon.yaml')
        if os.path.exists(dmon_fp):
            outp.printf(f'Cannot overwrite existing dmon.yaml file. [{dmon_fp}]')
            return 1
        s_common.yamlsave(dmon, dmon_fp)

    boot = {
        'cell:name': opts.cellname,
    }

    if opts.auth:
        boot['auth:en'] = True

    if opts.admin:
        boot['auth:en'] = True
        boot['auth:admin'] = opts.admin

    outp.printf(f'Deploying a {opts.celltype} at: {dirn}')
    s_cells.deploy(opts.celltype, dirn, boot)
    return 0

def makeargpaser():
    pars = argparse.ArgumentParser('synapse.tools.deploy', description=desc)

    pars.add_argument('celltype', help='The cell type to deploy by name.')
    pars.add_argument('cellname', help='The cell type to deploy by name.')
    pars.add_argument('dmonpath', nargs='?', default=s_dmon.dmonpath,
                      help='The synapse.tools.dmon directory where the cell will be deployed.')

    pars.add_argument('--listen', action='store', help='URL for the daemon to listen to (only set if the dmon.yaml '
                                                       'does not exist).')
    pars.add_argument('--auth', action='store_true', help='Enable the cell auth subsystem.')
    pars.add_argument('--admin', help='Set the initial <user>:<passwd> as an admin (enables --auth).')
    pars.add_argument('--module', action='store', help='An additional module to load. This can be used to initialize '
                                                       'third party module code which may register additional Cells.')
    pars.add_argument('--cells', action='store_true', help='Print registered cell types and exit.')
    return pars

def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
