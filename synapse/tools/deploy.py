import os
import sys
import argparse

import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps

import synapse.tools.dmon as s_dmon

desc = '''
Deploy a cell to a daemon directory.
'''

def main(argv):

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
    pars.add_argument('--cells', action='store_true')

    opts = pars.parse_args(argv)

    if opts.module:
        mod = s_dyndeps.tryDynMod(opts.module)
        print(f'Loaded {opts.module}@{mod}')

    if opts.cells:
        print('Registered cells:')
        for cname, cpath in s_cells.getCells():
            # print(f'[{cname}] {cpath:^12}')
            print(f'{cname:<10} {cpath:>10}')
        return 0

    dirn = s_common.genpath(opts.dmonpath, 'cells', opts.cellname)
    if os.path.isdir(dirn):
        print(f'cell directory already exists: {dirn}')
        return

    dmon = {}
    if opts.listen:
        dmon['listen'] = opts.listen

    if dmon:
        dmon.setdefault('modules', [])
        dmon_fp = os.path.join(opts.dmonpath, 'dmon.yaml')
        if os.path.exists(dmon_fp):
            raise s_exc.SynErr(mesg='Cannot smash existing dmon.yaml file.',
                               file=dmon_fp)
        s_common.yamlsave(dmon, dmon_fp)

    boot = {
        'cell:name': opts.cellname,
    }

    if opts.auth:
        boot['auth:en'] = True

    if opts.admin:
        boot['auth:en'] = True
        boot['auth:admin'] = opts.admin

    print(f'Deploying a {opts.celltype} at: {dirn}')
    s_cells.deploy(opts.celltype, dirn, boot)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
