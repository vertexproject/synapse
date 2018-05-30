import synapse.exc as s_exc
import synapse.lib.auth as s_auth
import synapse.tests.common as s_t_common

class SnapTest(s_t_common.SynTest):

    def test_addNode_noperms(self):
        form = 'teststr'
        valu = 'cool'

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                with self.getTestDir() as dirn:
                    with s_auth.Auth(dirn) as auth:
                        user = auth.addUser('hatguy')
                        snap.setUser(user)

                        self.true(snap.strict)  # Following assertions based on snap.strict being true
                        self.raises(s_exc.AuthDeny, snap.addNode, form, valu)

                        # User can still create the node even if not allowed if snap is not in strict mode
                        snap.strict = False
                        self.nn(snap.addNode(form, valu))
