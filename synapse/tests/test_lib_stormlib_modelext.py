import synapse.tests.utils as s_test

import synapse.exc as s_exc

class StormtypesModelextTest(s_test.SynTest):

    async def test_lib_stormlib_modelext(self):
        async with self.getTestCore() as core:
            await core.callStorm('''
                $typeinfo = $lib.dict()
                $forminfo = $lib.dict(doc="A test form doc.")
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = $lib.dict(doc="A test prop doc.")
                $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)

                $univinfo = $lib.dict(doc="A test univ doc.")
                $lib.model.ext.addUnivProp(_woot, (int, $lib.dict()), $univinfo)

                $tagpropinfo = $lib.dict(doc="A test tagprop doc.")
                $lib.model.ext.addTagProp(score, (int, $lib.dict()), $tagpropinfo)
            ''')

            nodes = await core.nodes('[ _visi:int=10 :tick=20210101 ._woot=30 +#lol:score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.eq(nodes[0].get('tick'), 1609459200000)
            self.eq(nodes[0].get('._woot'), 30)
            self.eq(nodes[0].getTagProp('lol', 'score'), 99)

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addUnivProp(_woot, (time, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            await core.callStorm('_visi:int=10 | delnode')
            await core.callStorm('''
                $lib.model.ext.delTagProp(score)
                $lib.model.ext.delUnivProp(_woot)
                $lib.model.ext.delFormProp(_visi:int, tick)
                $lib.model.ext.delForm(_visi:int)
            ''')

            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('._woot'))
            self.none(core.model.prop('_visi:int:tick'))
            self.none(core.model.tagprop('score'))

            # Underscores can exist in extended names but only at specific locations
            q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
            $lib.model.ext.addFormProp('test:str', '_test:_myprop', $l, $d)
            '''
            self.none(await core.callStorm(q))
            q = '$lib.model.ext.addUnivProp(_woot:_stuff, (int, $lib.dict()), $lib.dict())'
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(_score, (int, $lib.dict()), $lib.dict())'''
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(some:_score, (int, $lib.dict()), $lib.dict())'''
            self.none(await core.callStorm(q))

            with self.raises(s_exc.BadPropDef):
                q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
                $lib.model.ext.addFormProp('test:str', '_test:_my^prop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
                $lib.model.ext.addFormProp('test:str', '_test::_myprop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addUnivProp(_woot^stuff, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addUnivProp(_woot:_stuff^2, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(some^score, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(_someones:_score^value, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            # Permission errors
            visi = await core.auth.addUser('visi')
            opts = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $typeinfo = $lib.dict()
                    $forminfo = $lib.dict(doc="A test form doc.")
                    $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $propinfo = $lib.dict(doc="A test prop doc.")
                    $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $univinfo = $lib.dict(doc="A test univ doc.")
                    $lib.model.ext.addUnivProp(".woot", (int, $lib.dict()), $univinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $tagpropinfo = $lib.dict(doc="A test tagprop doc.")
                    $lib.model.ext.addTagProp(score, (int, $lib.dict()), $tagpropinfo)
                ''', opts=opts)
