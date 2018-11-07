import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.deploy as s_deploy

class DeployTest(s_t_utils.SynTest):
    def test_deploy_cells(self):
        outp = self.getTestOutp()
        argv = ['--cells', 'hehe', 'haha']
        ret = s_deploy.main(argv, outp)
        self.eq(ret, 0)
        outp.expect('Registered cells:')
        outp.expect('cortex')

    def test_deploy_auth(self):
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            argv = ['cortex', 'core', dirn, '--auth']
            ret = s_deploy.main(argv, outp)
            self.eq(ret, 0)
            d = s_common.yamlload(dirn, 'cells', 'core', 'boot.yaml')
            self.eq(d, {'auth:en': True,
                        'type': 'cortex',
                        'cell:name': 'core'})
            # Sad path
            outp = self.getTestOutp()
            argv = ['cortex', 'core', dirn, '--auth']
            ret = s_deploy.main(argv, outp)
            self.eq(ret, 1)
            outp.expect('cell directory already exists')

        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            argv = ['cortex', 'core', dirn, '--admin', 'pennywise:clownshoes']
            ret = s_deploy.main(argv, outp)
            self.eq(ret, 0)
            d = s_common.yamlload(dirn, 'cells', 'core', 'boot.yaml')
            self.eq(d, {'auth:en': True,
                        'type': 'cortex',
                        'cell:name': 'core',
                        'auth:admin': 'pennywise:clownshoes'})

    def test_deploy_dmonyaml(self):
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            argv = ['--listen', 'tcp://1.2.3.4:8080/', '--module', 'synapse.tests.utils', 'cortex', 'core', dirn]
            ret = s_deploy.main(argv, outp)
            self.eq(ret, 0)
            d = s_common.yamlload(dirn, 'dmon.yaml')
            self.eq(d, {'modules': ['synapse.tests.utils'],
                        'listen': 'tcp://1.2.3.4:8080/'})
            outp.expect('Loaded synapse.tests.utils@')

            # Sad path
            outp = self.getTestOutp()
            argv = ['--listen', 'tcp://1.2.3.4:8081/', 'cortex', 'core2', dirn]
            ret = s_deploy.main(argv, outp)
            self.eq(ret, 1)
            outp.expect('Cannot overwrite existing dmon.yaml file')
