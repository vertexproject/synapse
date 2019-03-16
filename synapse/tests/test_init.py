
import synapse.tests.utils as s_t_utils

class InitTest(s_t_utils.SynTest):
    pass

    '''
    def test_init_modules(self):
        os.environ['SYN_MODULES'] = 'fakenotrealmod , badnothere,math'
        msg = 'SYN_MODULES failed: badnothere (NoSuchDyn: name=\'badnothere\')'
        with self.getLoggerStream('synapse', msg) as stream:
            imp.reload(synapse)
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())
        self.isin(('math', 2.0, None), synapse.lib.modules.call('sqrt', 4))
    '''
