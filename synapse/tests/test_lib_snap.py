import synapse.exc as s_exc
import synapse.lib.auth as s_auth
import synapse.tests.common as s_t_common

class SnapTest(s_t_common.SynTest):

    def test_stor(self):
        with self.getTestCore() as core:

            # Readonly
            with core.snap(write=False) as snap:
                self.raises(s_exc.ReadOnlySnap, snap.stor, [])

            # Bulk
            with core.snap(write=True) as snap:
                snap.bulk = True
                self.eq(snap.bulksops, ())

                self.none(snap.stor((1,)))
                self.eq(snap.bulksops, (1,))

                self.none(snap.stor((2,)))
                self.eq(snap.bulksops, (1, 2,))

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
