import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibItersTest(s_test.SynTest):

    async def test_stormlib_iters_zip(self):

        async with self.getTestCore() as core:

            async with s_test.matchContexts(self):

                q = '''
                for $item in $lib.iters.zip((1,2,3), (4,5,6), (7,8,9)) {
                    $lib.print($item)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormIsInPrint("['3', '6', '9']", msgs)

                q = '''
                for $item in $lib.iters.zip((1,2,3), (4,5,6), (7,8)) {
                    $lib.print($item)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4 it:dev:str=5 it:dev:str=6 ]
                }
                function emitter() {
                    emit 7
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormIsInPrint("['3', '6', '9']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4 it:dev:str=5 it:dev:str=6 ]
                }
                function emitter() {
                    emit 7
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                    $lib.raise(foo, bar)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormNotInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6', '9']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4  it:dev:str=5 it:dev:str=6]
                }
                function emitter() {
                    emit 7
                    $lib.raise(foo, bar)
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormNotInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6', '9']", msgs)

                err = "$lib.iters.zip() encountered errors in 1 iterators during " \
                      "iteration: (StormRaise: errname='foo' mesg='bar')"
                self.stormIsInErr(err, msgs)

                q = '''
                function e1() {
                    $lib.raise(foo, bar)
                }
                function e2() {
                    $lib.print($newp)
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $e1(), $e2()) {
                }
                '''
                msgs = await core.stormlist(q)

                err = "$lib.iters.zip() encountered errors in 2 iterators during iteration: " \
                      "(StormRaise: errname='foo' mesg='bar'), " \
                      "(NoSuchVar: mesg='Missing variable: newp' name='newp')"
                self.stormIsInErr(err, msgs)
